#!/usr/bin/env python3
"""Sanity-check an exported point cloud (.ply) without a GUI.

Prints point count, axis extents and a height histogram, then flags the two
failure modes seen on this robot:
  - flat:      the map came from the 2D lidar only (Grid/Sensor 0), so the
               cloud is a thin slice instead of walls with height
  - low ceiling: nothing above ~1.8 m, the signature of the camera tilted
               too far down (vendor default 15 deg)

Only needs numpy. Reads binary little-endian PLY as written by rtabmap-export.

    rosrun uan_base_control cloud_stats.py ~/uan_maps/exports/room_3d_cloud.ply
"""

import argparse
import re
import sys

import numpy as np

PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "<i2", "int16": "<i2", "ushort": "<u2", "uint16": "<u2",
    "int": "<i4", "int32": "<i4", "uint": "<u4", "uint32": "<u4",
    "float": "<f4", "float32": "<f4", "double": "<f8", "float64": "<f8",
}

FLAT_THRESHOLD_M = 0.3
LOW_CEILING_M = 1.8


def read_vertices(path):
    with open(path, "rb") as f:
        header = b""
        while not header.endswith(b"end_header\n"):
            line = f.readline()
            if not line:
                sys.exit("%s: no PLY end_header found" % path)
            header += line
        text = header.decode("ascii", errors="replace")
        if "binary_little_endian" not in text:
            sys.exit("%s: only binary_little_endian PLY is supported" % path)

        # rtabmap-export appends an `element camera` after the vertices; only
        # the vertex block's properties describe the per-point record.
        vertex_block = text.split("element vertex", 1)[1].split("element ", 1)[0]
        count = int(vertex_block.split()[0])
        props = re.findall(r"property (\w+) (\w+)", vertex_block)
        dtype = np.dtype([(name, PLY_TYPES[kind]) for kind, name in props])
        return np.frombuffer(f.read(count * dtype.itemsize), dtype=dtype, count=count)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ply", help="point cloud exported by rtabmap-export")
    parser.add_argument("--bin", type=float, default=0.2, help="histogram band height in m")
    args = parser.parse_args()

    pts = read_vertices(args.ply)
    print("%s\n%d points" % (args.ply, len(pts)))
    if len(pts) == 0:
        sys.exit(1)

    for axis in "xyz":
        v = pts[axis]
        print("%s: min %+.2f  p1 %+.2f  p99 %+.2f  max %+.2f m" % (
            axis, v.min(), np.percentile(v, 1), np.percentile(v, 99), v.max()))

    z = pts["z"]
    z_lo, z_hi = np.percentile(z, 1), np.percentile(z, 99)
    edges = np.arange(np.floor(z_lo / args.bin) * args.bin, z_hi + args.bin, args.bin)
    hist, edges = np.histogram(z, bins=edges)
    print("height histogram (1st-99th percentile):")
    for n, lo in zip(hist, edges):
        print("  %+.1f..%+.1f m %8d  %s" % (lo, lo + args.bin, n, "#" * int(50 * n / max(hist.max(), 1))))

    if z_hi - z_lo < FLAT_THRESHOLD_M:
        print("WARNING: cloud is flat (%.2f m tall) - map likely built from lidar only (Grid/Sensor 0)" % (z_hi - z_lo))
    elif z_hi < LOW_CEILING_M:
        print("NOTE: nothing above %.2f m - camera may be tilted too far down" % z_hi)


if __name__ == "__main__":
    main()
