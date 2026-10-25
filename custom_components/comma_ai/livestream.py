"""WebRTC live stream client for comma.ai devices.

This mirrors what comma connect does in the browser:

1. Fetch TURN credentials from ``/v1/me/turn``.
2. Create an offer with one receive-only H.264 video transceiver and a
   data channel named ``data``.
3. Send it to the device with the ``startStream`` athena JSON-RPC call;
   the device's ``webrtcd`` answers with its own SDP.
4. Video then flows peer-to-peer (or through TURN). The device sends a
   single video track; the camera is picked with a ``livestreamCameraSwitch``
   message on the data channel.

The device only accepts one streaming client and only streams while the car
is off (openpilot starts the stream processes on demand when offroad).
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aiortc import (
    RTCBundlePolicy,
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCRtpReceiver,
    RTCSessionDescription,
)
from aiortc.mediastreams import MediaStreamError

from .api import CommaAPIError
from .const import CAMERA_ROAD

if TYPE_CHECKING:
    from aiortc import RTCDataChannel
    from aiortc.mediastreams import MediaStreamTrack
    from av import VideoFrame
    from homeassistant.core import HomeAssistant

    from .api import CommaAPIClient

_LOGGER = logging.getLogger(__name__)

FALLBACK_STUN_SERVER = "stun:stun.l.google.com:19302"

# startStream may have to wait for the device to bring up its camera processes
START_STREAM_TIMEOUT = 45
CONNECT_TIMEOUT = 20
# Close the stream when no entity has asked for a frame for this long
IDLE_TIMEOUT = 30
# Wait before retrying after a failed connection attempt
ERROR_BACKOFF = 30
# Leave the device alone for a while after another client took it over
TAKEOVER_BACKOFF = 120
# A camera counts as wanted if it was asked for a frame within this window
WANTED_WINDOW = 3
# When both cameras are wanted, alternate between them at this interval
CAMERA_DWELL = 10
# After a camera switch, drop frames until a keyframe arrives (or this long)
SWITCH_SETTLE = 0.5
SWITCH_KEYFRAME_TIMEOUT = 3
# A frame older than this is not served without waiting for a newer one
FRESH_FRAME_AGE = 2

JPEG_QUALITY = 80


class CommaStreamError(Exception):
    """Raised when a live stream cannot be started."""


@dataclass
class _Frame:
    """Latest decoded frame of one camera."""

    seq: int
    frame: VideoFrame
    received_at: float
    jpeg: bytes | None = field(default=None, repr=False)


def _encode_jpeg(frame: VideoFrame) -> bytes:
    """Encode a decoded video frame as JPEG."""
    buf = io.BytesIO()
    frame.to_image().save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


def _parse_ice_servers(data: Any) -> list[RTCIceServer]:
    """Build aiortc ICE servers from the /v1/me/turn response."""
    servers: list[RTCIceServer] = []
    entries = data.get("iceServers") if isinstance(data, dict) else None
    for entry in entries or []:
        urls = entry.get("urls") or entry.get("url")
        if not urls:
            continue
        servers.append(
            RTCIceServer(
                urls=urls,
                username=entry.get("username"),
                credential=entry.get("credential"),
            )
        )

    # the device only gathers STUN candidates, so keep a STUN server around
    # to find a direct path even when no TURN credentials are available
    def has_stun(server: RTCIceServer) -> bool:
        urls = [server.urls] if isinstance(server.urls, str) else server.urls
        return any(url.startswith("stun") for url in urls)

    if not any(has_stun(server) for server in servers):
        servers.append(RTCIceServer(urls=FALLBACK_STUN_SERVER))
    return servers


def _rpc_error_message(error: Any) -> str:
    """Extract a readable message from a JSON-RPC error."""
    if isinstance(error, dict):
        data = error.get("data")
        if isinstance(data, dict) and data.get("message"):
            return str(data["message"])
        return str(error.get("message") or error)
    return str(error)


class CommaLiveStream:
    """Live stream of one comma device, shared by its camera entities."""

    def __init__(
        self, hass: HomeAssistant, api_client: CommaAPIClient, dongle_id: str
    ) -> None:
        """Initialize the live stream."""
        self.hass = hass
        self.api_client = api_client
        self.dongle_id = dongle_id

        self._task: asyncio.Task | None = None
        self._pc: RTCPeerConnection | None = None
        self._dc: RTCDataChannel | None = None
        self._reader: asyncio.Task | None = None
        self._closed = asyncio.Event()
        self._connected = False

        self._active_camera = CAMERA_ROAD
        self._switched_at = 0.0
        self._awaiting_keyframe = False

        self._last_request: dict[str, float] = {}
        self._backoff_until = 0.0
        self.last_error: str | None = None

        self._seq = 0
        self._frames: dict[str, _Frame] = {}
        self._frame_event = asyncio.Event()
        self._listeners: list[Callable[[], None]] = []

    @property
    def connected(self) -> bool:
        """Return True while video is flowing from the device."""
        return self._connected

    @property
    def active_camera(self) -> str:
        """Return the camera the device is currently streaming."""
        return self._active_camera

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Listen for stream state changes; returns a function to remove it."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_get_image(self, camera: str, timeout: float) -> bytes | None:
        """Return a JPEG of the camera, starting the stream if needed."""
        latest = self._frames.get(camera)
        self._request(camera)
        if (
            latest is not None
            and self._connected
            and self._active_camera == camera
            and time.monotonic() - latest.received_at < FRESH_FRAME_AGE
        ):
            return await self._jpeg(latest)

        frame = await self._wait_for_frame(camera, latest.seq if latest else 0, timeout)
        # fall back to the last frame we have, however old
        frame = frame or latest
        return await self._jpeg(frame) if frame else None

    async def async_next_image(
        self, camera: str, after_seq: int, timeout: float
    ) -> tuple[int, bytes] | None:
        """Wait for a frame newer than ``after_seq`` and return it as JPEG."""
        self._request(camera)
        frame = await self._wait_for_frame(camera, after_seq, timeout)
        if frame is None:
            return None
        return frame.seq, await self._jpeg(frame)

    async def async_stop(self) -> None:
        """Stop the stream."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._close()

    async def _jpeg(self, frame: _Frame) -> bytes:
        if frame.jpeg is None:
            frame.jpeg = await self.hass.async_add_executor_job(
                _encode_jpeg, frame.frame
            )
        return frame.jpeg

    async def _wait_for_frame(
        self, camera: str, after_seq: int, timeout: float
    ) -> _Frame | None:
        deadline = time.monotonic() + timeout
        while True:
            frame = self._frames.get(camera)
            if frame is not None and frame.seq > after_seq:
                return frame
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            # keep asking, so the camera gets switched to once allowed
            self._request(camera)
            if self._task is None or self._task.done():
                # the stream failed and is backing off; no frames are coming
                return None
            with contextlib.suppress(TimeoutError):
                async with asyncio.timeout(min(remaining, 1)):
                    await self._frame_event.wait()

    def _request(self, camera: str) -> None:
        """Note that a camera is wanted and make sure the stream runs."""
        now = time.monotonic()
        self._last_request[camera] = now
        if self._task is None or self._task.done():
            if now < self._backoff_until:
                return
            self._task = self.hass.async_create_background_task(
                self._run(), f"comma_ai livestream {self.dongle_id}"
            )
        self._maybe_switch_camera(camera)

    def _maybe_switch_camera(self, camera: str) -> None:
        if camera == self._active_camera:
            return
        if self._dc is None or self._dc.readyState != "open":
            return
        now = time.monotonic()
        active_wanted = (
            now - self._last_request.get(self._active_camera, 0) < WANTED_WINDOW
        )
        # time-share the single video track when both cameras are being viewed
        if active_wanted and now - self._switched_at < CAMERA_DWELL:
            return
        _LOGGER.debug(
            "Switching %s live stream from %s to %s",
            self.dongle_id,
            self._active_camera,
            camera,
        )
        self._send("livestreamCameraSwitch", {"camera": camera})
        # toggling video makes the device ask its encoder for a keyframe
        self._send("livestreamVideoEnable", {"enabled": False})
        self._send("livestreamVideoEnable", {"enabled": True})
        self._active_camera = camera
        self._switched_at = now
        self._awaiting_keyframe = True
        self._notify()

    def _send(self, msg_type: str, data: dict[str, Any]) -> None:
        if self._dc is not None and self._dc.readyState == "open":
            self._dc.send(json.dumps({"type": msg_type, "data": data}))

    async def _run(self) -> None:
        try:
            await self._connect()
            while not self._closed.is_set():
                idle = time.monotonic() - max(self._last_request.values(), default=0)
                if idle > IDLE_TIMEOUT:
                    _LOGGER.debug("Closing idle live stream for %s", self.dongle_id)
                    break
                with contextlib.suppress(TimeoutError):
                    async with asyncio.timeout(IDLE_TIMEOUT - idle + 1):
                        await self._closed.wait()
        except (CommaAPIError, CommaStreamError, TimeoutError) as err:
            self._fail(str(err) or "Timed out connecting to the device")
        except Exception as err:
            _LOGGER.exception("Unexpected error in %s live stream", self.dongle_id)
            self._fail(str(err))
        finally:
            await self._close()

    def _fail(self, reason: str, backoff: float = ERROR_BACKOFF) -> None:
        _LOGGER.warning("Live stream for %s unavailable: %s", self.dongle_id, reason)
        self.last_error = reason
        self._backoff_until = time.monotonic() + backoff

    async def _get_ice_servers(self) -> list[RTCIceServer]:
        try:
            return _parse_ice_servers(await self.api_client.get_turn_credentials())
        except (CommaAPIError, ValueError) as err:
            _LOGGER.debug("TURN credentials unavailable, using STUN only: %s", err)
            return _parse_ice_servers(None)

    async def _connect(self) -> None:
        self._closed.clear()
        self._active_camera = CAMERA_ROAD

        pc = RTCPeerConnection(
            RTCConfiguration(
                iceServers=await self._get_ice_servers(),
                bundlePolicy=RTCBundlePolicy.MAX_BUNDLE,
            )
        )
        self._pc = pc
        connected = asyncio.Event()

        transceiver = pc.addTransceiver("video", direction="recvonly")
        transceiver.setCodecPreferences(
            [
                codec
                for codec in RTCRtpReceiver.getCapabilities("video").codecs
                if codec.mimeType == "video/H264"
            ]
        )

        dc = pc.createDataChannel("data", ordered=True)
        self._dc = dc

        @pc.on("track")
        def on_track(track: MediaStreamTrack) -> None:
            if track.kind == "video":
                self._reader = self.hass.async_create_background_task(
                    self._read_track(track),
                    f"comma_ai livestream reader {self.dongle_id}",
                )

        @pc.on("connectionstatechange")
        def on_connection_state_change() -> None:
            _LOGGER.debug(
                "Live stream %s connection state: %s",
                self.dongle_id,
                pc.connectionState,
            )
            if pc.connectionState == "connected":
                connected.set()
            elif pc.connectionState in ("failed", "closed"):
                self._closed.set()

        @dc.on("open")
        def on_open() -> None:
            # the device always starts on the road camera
            if self._last_request:
                wanted = max(self._last_request, key=self._last_request.get)
                self._maybe_switch_camera(wanted)

        @dc.on("message")
        def on_message(message: str | bytes) -> None:
            self._handle_message(message)

        # aiortc gathers all ICE candidates here, as the device expects
        await pc.setLocalDescription(await pc.createOffer())

        _LOGGER.debug("Sending startStream offer to %s", self.dongle_id)
        response = await self.api_client.athena_rpc(
            self.dongle_id,
            "startStream",
            {"sdp": pc.localDescription.sdp, "enabled": True},
            timeout=START_STREAM_TIMEOUT,
        )
        if response is None:
            raise CommaStreamError("Device could not be reached")
        if response.get("error"):
            raise CommaStreamError(_rpc_error_message(response["error"]))
        result = response.get("result") or {}
        if result.get("error"):
            # "busy": another client already holds the stream
            raise CommaStreamError(result.get("message") or result["error"])

        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=result["sdp"], type="answer")
        )
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT):
                await connected.wait()
        except TimeoutError:
            # the device answered, so signaling worked but no ICE path was found
            raise CommaStreamError(
                "Device answered but no WebRTC connection could be made "
                "(check that UDP to the device or TURN server isn't blocked)"
            ) from None

        _LOGGER.debug("Live stream for %s connected", self.dongle_id)
        self.last_error = None
        self._connected = True
        self._notify()

    def _handle_message(self, message: str | bytes) -> None:
        try:
            msg = json.loads(message)
        except ValueError:
            return
        if not isinstance(msg, dict) or msg.get("type") != "disconnect":
            return

        reason = str(msg.get("data") or "Device ended the stream")
        _LOGGER.debug("Live stream for %s disconnected: %s", self.dongle_id, reason)
        if "another device" in reason.lower():
            # someone opened the stream elsewhere (e.g. comma connect); don't
            # immediately kick them off again
            self._fail(reason, TAKEOVER_BACKOFF)
        self._closed.set()

    async def _read_track(self, track: MediaStreamTrack) -> None:
        while True:
            try:
                frame: VideoFrame = await track.recv()
            except MediaStreamError:
                self._closed.set()
                return

            if self._awaiting_keyframe:
                since_switch = time.monotonic() - self._switched_at
                # frames still in flight from the previous camera, or deltas
                # that need a keyframe from the new one
                if since_switch < SWITCH_SETTLE or (
                    not frame.key_frame and since_switch < SWITCH_KEYFRAME_TIMEOUT
                ):
                    continue
                self._awaiting_keyframe = False

            self._seq += 1
            self._frames[self._active_camera] = _Frame(
                self._seq, frame, time.monotonic()
            )
            self._frame_event.set()
            self._frame_event = asyncio.Event()

    async def _close(self) -> None:
        was_connected = self._connected
        self._connected = False
        self._closed.set()
        if self._reader is not None:
            self._reader.cancel()
            self._reader = None
        self._dc = None
        if self._pc is not None:
            pc, self._pc = self._pc, None
            await pc.close()
        if was_connected:
            self._notify()
