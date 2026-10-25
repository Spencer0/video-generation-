#!/bin/bash
# Render every 3D shot for a video, sequentially (Cycles already uses all cores).
# Resumable: scene_bag.py skips frames that already exist.
# usage: bash pipeline/blender/render_all.sh <video_id> [res] [samples]
set -e
VID=${1:?video id}; RES=${2:-576}; SAMPLES=${3:-24}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BLENDER=${BLENDER:-/home/user/tools/blender-4.5.15-linux-x64/blender}
OUT=$ROOT/videos/$VID/build/frames
# shot -> frame count, derived from timeline.json beats (see BG_PLAN in assemble.py)
read -r A B C D <<<"$(python3 - "$ROOT/videos/$VID/build/timeline.json" <<'PY'
import json,sys; tl=json.load(open(sys.argv[1])); b={x['id']:x['frames'] for x in tl['beats']}
print(b['hook'], b['empty'], 168, 168)  # C/D nominal lengths are fixed in scene_bag.py SHOT_DUR
PY
)"
echo "frames: A=$A B=$B C=$C D=$D  (res=$RES samples=$SAMPLES)"
for S in A B C D; do
  N=${!S}
  $BLENDER -b -noaudio -P "$ROOT/pipeline/blender/scene_bag.py" -- --shot $S --start 0 --end $N --out "$OUT/$S" --res $RES --samples $SAMPLES 2>&1 | grep -E "^FRAME|Error|Traceback"
done
echo "all shots done"
