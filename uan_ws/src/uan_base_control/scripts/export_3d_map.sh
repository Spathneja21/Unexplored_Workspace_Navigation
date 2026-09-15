#!/usr/bin/env bash
# Export a 3D map from an rtabmap database: point cloud (+ optional mesh) and
# robot poses, then print a height sanity check of the cloud.
#
# Works on a temporary copy, so the database - including a live
# ~/.ros/rtabmap.db - is never touched.
#
#   rosrun uan_base_control export_3d_map.sh ~/uan_maps/room_3d.db
#   rosrun uan_base_control export_3d_map.sh ~/uan_maps/room_3d.db --mesh --voxel 0.01
#
# Note: rtabmap-export skips intermediate nodes (weight -1), so not every
# stored depth frame ends up in the cloud.

set -euo pipefail

usage() {
    cat <<EOF
usage: $(basename "$0") DATABASE.db [options]
  --out-dir DIR     where to write outputs (default: ~/uan_maps/exports)
  --name NAME       output file prefix (default: database file name)
  --voxel M         cloud voxel size in metres (default: 0.02)
  --max-range M     ignore depth beyond this range (default: 4)
  --mesh            also export a coloured mesh
EOF
    exit 1
}

[ $# -ge 1 ] || usage
DB=$(readlink -f "$1"); shift
[ -f "$DB" ] || { echo "no such database: $DB" >&2; exit 1; }

OUT_DIR="$HOME/uan_maps/exports"
NAME=$(basename "$DB" .db)
VOXEL=0.02
MAX_RANGE=4
MESH=()

while [ $# -gt 0 ]; do
    case "$1" in
        --out-dir)   OUT_DIR=$2; shift 2 ;;
        --name)      NAME=$2; shift 2 ;;
        --voxel)     VOXEL=$2; shift 2 ;;
        --max-range) MAX_RANGE=$2; shift 2 ;;
        --mesh)      MESH=(--mesh); shift ;;
        *)           usage ;;
    esac
done

mkdir -p "$OUT_DIR"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cp "$DB" "$WORK/map.db"

rtabmap-export --cloud --poses "${MESH[@]}" \
    --decimation 4 --voxel "$VOXEL" --max_range "$MAX_RANGE" \
    --output_dir "$OUT_DIR" --output "$NAME" \
    "$WORK/map.db"

echo
ls -lh "$OUT_DIR/$NAME"_*
echo
python3 "$(dirname "$(readlink -f "$0")")/cloud_stats.py" "$OUT_DIR/${NAME}_cloud.ply"
