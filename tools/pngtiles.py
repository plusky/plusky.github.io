"""Cut a PNG into tiles of at most MAX px height, so a full-page screenshot can be read in parts.

    python3 -I tools/pngtiles.py [--max 1500] IN.png OUT_PREFIX

Writes OUT_PREFIX-01.png, OUT_PREFIX-02.png, ... and prints their paths. Handles 8-bit RGB and RGBA,
non-interlaced, which is what Firefox writes.
"""
import argparse
import struct
import sys
import zlib

SIG = b"\x89PNG\r\n\x1a\n"


def chunks(data):
    pos = len(SIG)
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        yield kind, data[pos + 8 : pos + 8 + n]
        pos += 12 + n


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def unfilter(raw, width, height, bpp):
    stride = width * bpp
    rows = []
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        ftype = raw[pos]
        line = bytearray(raw[pos + 1 : pos + 1 + stride])
        pos += 1 + stride
        if ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                up_left = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + paeth(left, prev[i], up_left)) & 0xFF
        elif ftype != 0:
            raise ValueError(f"unknown filter type {ftype}")
        rows.append(bytes(line))
        prev = line
    return rows


def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def write_png(path, width, rows, color_type):
    ihdr = struct.pack(">IIBBBBB", width, len(rows), 8, color_type, 0, 0, 0)
    raw = b"".join(b"\x00" + r for r in rows)
    with open(path, "wb") as f:
        f.write(SIG + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def main():
    ap = argparse.ArgumentParser(description="Cut a PNG into tiles of limited height.")
    ap.add_argument("--max", type=int, default=1500)
    ap.add_argument("png")
    ap.add_argument("prefix")
    args = ap.parse_args()
    with open(args.png, "rb") as f:
        data = f.read()
    if not data.startswith(SIG):
        sys.exit(f"pngtiles: {args.png} is not a PNG")
    idat = []
    for kind, body in chunks(data):
        if kind == b"IHDR":
            width, height, depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
    if depth != 8 or color_type not in (2, 6) or interlace:
        sys.exit(f"pngtiles: {args.png}: only 8-bit RGB or RGBA, non-interlaced")
    bpp = 3 if color_type == 2 else 4
    rows = unfilter(zlib.decompress(b"".join(idat)), width, height, bpp)
    for n, top in enumerate(range(0, height, args.max), 1):
        path = f"{args.prefix}-{n:02d}.png"
        write_png(path, width, rows[top : top + args.max], color_type)
        print(path)


if __name__ == "__main__":
    main()
