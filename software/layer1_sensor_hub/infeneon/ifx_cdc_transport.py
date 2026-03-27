"""Minimal low-level transport for Infineon IFX CDC devices."""

from __future__ import annotations

from dataclasses import dataclass

import serial  # type: ignore


def crc16_ccitt_false(data: bytes) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, xorout 0x0000, no reflect)."""

    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ 0x1021
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


@dataclass(frozen=True, slots=True)
class IfxCdcReply:
    payload: bytes
    crc_ok: bool


class IfxCdcTransport:
    """Binary frame transport over CDC ACM.

    Observed reply format (6 bytes):
      [cmd_echo][0x80][status_lo][status_hi][crc_hi][crc_lo]

    The CRC appears to be CRC16-CCITT-FALSE over the first 4 bytes, appended
    as big-endian (hi, lo).
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout_s: float = 0.3,
    ) -> None:
        self._ser = serial.Serial(port, baudrate=baudrate, timeout=timeout_s)
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass

    def request(self, frame: bytes, read_bytes: int = 4096) -> bytes:
        self._ser.write(frame)
        return self._ser.read(read_bytes)

    def _read_exact(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            chunk = self._ser.read(n - len(data))
            if not chunk:
                break
            data.extend(chunk)
        return bytes(data)

    def request_cmd4(self, cmd: int, a: int = 0, b: int = 0, c: int = 0) -> IfxCdcReply:
        """Send 4-byte command + CRC and read 6-byte reply when available."""

        payload = bytes([cmd & 0xFF, a & 0xFF, b & 0xFF, c & 0xFF])
        crc = crc16_ccitt_false(payload)
        frame = payload + bytes([(crc >> 8) & 0xFF, crc & 0xFF])
        self._ser.write(frame)
        raw = self._read_exact(6)
        if len(raw) < 6:
            return IfxCdcReply(payload=raw, crc_ok=False)
        body = raw[:4]
        got_crc = (raw[4] << 8) | raw[5]
        ok = crc16_ccitt_false(body) == got_crc
        return IfxCdcReply(payload=raw[:6], crc_ok=ok)
