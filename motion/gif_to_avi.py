"""Package rendered GIF frames as a Motion JPEG AVI without an external encoder."""
from io import BytesIO
from pathlib import Path
import struct
from PIL import Image, ImageSequence

ROOT = Path(__file__).parent
source = ROOT / "trainu-light.gif"
target = ROOT / "trainu-light.avi"
fps = 20


def u16(n): return struct.pack("<H", n)
def u32(n): return struct.pack("<I", n)
def fourcc(value): return value.encode("ascii")
def chunk(name, payload):
    return fourcc(name) + u32(len(payload)) + payload + (b"\0" if len(payload) & 1 else b"")
def list_chunk(name, payload): return chunk("LIST", fourcc(name) + payload)


with Image.open(source) as gif:
    width, height = gif.size
    frames = []
    for frame in ImageSequence.Iterator(gif):
        buf = BytesIO()
        frame.convert("RGB").save(buf, "JPEG", quality=91, subsampling=0)
        frames.append(buf.getvalue())

count = len(frames)
largest = max(map(len, frames))
avih = struct.pack("<14I", 1_000_000 // fps, largest * fps, 0, 0x10, count,
                   0, 1, largest, width, height, 0, 0, 0, 0)
strh = (fourcc("vids") + fourcc("MJPG") + u32(0) + u16(0) + u16(0)
        + u32(0) + u32(1) + u32(fps) + u32(0) + u32(count) + u32(largest)
        + u32(0xFFFFFFFF) + u32(0) + struct.pack("<4h", 0, 0, width, height))
strf = (u32(40) + struct.pack("<ii", width, height) + u16(1) + u16(24)
        + fourcc("MJPG") + u32(largest) + u32(0) * 4)
hdrl = list_chunk("hdrl", chunk("avih", avih) + list_chunk("strl", chunk("strh", strh) + chunk("strf", strf)))

movi_payload = bytearray()
index = bytearray()
for data in frames:
    offset = len(movi_payload) + 4  # offset from the movi list type
    movi_payload += chunk("00dc", data)
    index += fourcc("00dc") + u32(0x10) + u32(offset) + u32(len(data))

body = fourcc("AVI ") + hdrl + list_chunk("movi", movi_payload) + chunk("idx1", index)
target.write_bytes(fourcc("RIFF") + u32(len(body)) + body)
print(f"Wrote {target}: {count} frames, {width}x{height}, {count/fps:g}s")
