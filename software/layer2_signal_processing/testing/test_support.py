"""Shared test helpers for Layer 2 unit tests."""

from __future__ import annotations

import struct
import sys
import types


def ensure_serial_stub() -> None:
    """Stub pyserial so Layer 1 modules can be imported without the dependency."""
    if "serial" in sys.modules:
        return

    serial_module = types.ModuleType("serial")
    serial_module.SerialException = Exception
    serial_module.Serial = object
    serial_module.EIGHTBITS = 8
    serial_module.PARITY_NONE = "N"
    serial_module.STOPBITS_ONE = 1

    serial_tools = types.ModuleType("serial.tools")
    serial_list_ports = types.ModuleType("serial.tools.list_ports")
    serial_list_ports.comports = lambda: []
    serial_tools.list_ports = serial_list_ports
    serial_module.tools = serial_tools

    sys.modules["serial"] = serial_module
    sys.modules["serial.tools"] = serial_tools
    sys.modules["serial.tools.list_ports"] = serial_list_ports


def build_layer1_raw_frame(
    *,
    frame_header_size: int,
    magic_word: bytes,
    frame_number: int,
    timestamp_cycles: int,
    tlvs: list[tuple[int, bytes]],
) -> bytes:
    body = bytearray()
    for tlv_type, data in tlvs:
        body.extend(struct.pack("<II", tlv_type, len(data)))
        body.extend(data)

    total_len = frame_header_size + len(body)
    header_fields = struct.pack(
        "<8I",
        0x01020304,
        total_len,
        0x6843,
        frame_number,
        timestamp_cycles,
        0,
        len(tlvs),
        0,
    )
    return magic_word + header_fields + bytes(body)
