"""Lightweight image dimension probing without heavy dependencies."""
from __future__ import annotations

import struct
from pathlib import Path
from typing import BinaryIO, Optional

_EXR_MAGIC = 20000630


def read_image_dimensions(path: str | Path) -> tuple[Optional[int], Optional[int]]:
    """Return width and height for common image formats, or (None, None)."""

    file_path = Path(path)
    if not file_path.is_file():
        return None, None

    try:
        with file_path.open("rb") as handle:
            header = handle.read(32)
    except OSError:
        return None, None

    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        width, height = struct.unpack(">II", header[16:24])
        return int(width), int(height)

    if header.startswith(b"\xff\xd8\xff"):
        return _jpeg_dimensions(file_path)

    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return _webp_dimensions(file_path)

    if len(header) >= 8 and struct.unpack("<I", header[:4])[0] == _EXR_MAGIC:
        return _exr_dimensions(file_path)

    return None, None


def max_image_dimension(path: str | Path) -> Optional[int]:
    """Return max(width, height) when dimensions are known."""

    width, height = read_image_dimensions(path)
    if width is None or height is None:
        return None
    return max(width, height)


def _jpeg_dimensions(path: Path) -> tuple[Optional[int], Optional[int]]:
    try:
        with path.open("rb") as handle:
            handle.read(2)
            while True:
                marker_prefix = handle.read(1)
                if not marker_prefix:
                    break
                if marker_prefix != b"\xff":
                    continue
                marker = handle.read(1)
                if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7"}:
                    handle.read(3)
                    height, width = struct.unpack(">HH", handle.read(4))
                    return int(width), int(height)
                segment_size_bytes = handle.read(2)
                if len(segment_size_bytes) != 2:
                    break
                segment_size = struct.unpack(">H", segment_size_bytes)[0]
                handle.seek(segment_size - 2, 1)
    except OSError:
        return None, None
    return None, None


def _webp_dimensions(path: Path) -> tuple[Optional[int], Optional[int]]:
    try:
        with path.open("rb") as handle:
            handle.seek(12)
            chunk_header = handle.read(8)
            if chunk_header[:4] != b"VP8 ":
                return None, None
            handle.read(4)
            frame_tag = handle.read(3)
            if len(frame_tag) != 3:
                return None, None
            width = struct.unpack("<H", frame_tag[0:2])[0] & 0x3FFF
            height = struct.unpack("<H", bytes([frame_tag[1], frame_tag[2]]))[0] & 0x3FFF
            return int(width), int(height)
    except OSError:
        return None, None
    return None, None


def _exr_dimensions(path: Path) -> tuple[Optional[int], Optional[int]]:
    """Read OpenEXR dataWindow/displayWindow without the OpenEXR library."""

    try:
        with path.open("rb") as handle:
            magic = struct.unpack("<I", handle.read(4))[0]
            if magic != _EXR_MAGIC:
                return None, None
            handle.read(4)  # version flags

            data_window: tuple[Optional[int], Optional[int]] = (None, None)
            while True:
                name = _read_cstring(handle)
                if not name:
                    break
                type_name = _read_cstring(handle)
                if not type_name:
                    break
                size_bytes = handle.read(4)
                if len(size_bytes) != 4:
                    break
                (value_size,) = struct.unpack("<I", size_bytes)
                value = handle.read(value_size)
                padding = (4 - (value_size % 4)) % 4
                if padding:
                    handle.read(padding)
                if type_name == "box2i" and len(value) >= 16 and name in {
                    "dataWindow",
                    "displayWindow",
                }:
                    x_min, y_min, x_max, y_max = struct.unpack("<iiii", value[:16])
                    width = int(x_max - x_min + 1)
                    height = int(y_max - y_min + 1)
                    if width > 0 and height > 0:
                        data_window = (width, height)
            return data_window
    except OSError:
        return None, None
    return None, None


def _read_cstring(handle: BinaryIO) -> str:
    chars: list[int] = []
    while True:
        chunk = handle.read(1)
        if not chunk:
            break
        byte = chunk[0]
        if byte == 0:
            break
        chars.append(byte)
    return bytes(chars).decode("ascii", errors="ignore")
