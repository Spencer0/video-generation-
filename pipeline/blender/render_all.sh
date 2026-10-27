#!/bin/bash
# Render every 3D shot for a video, sequentially (Cycles already uses all cores).
# Resumable: scene_bag.py skips frames that already exist.
# usage: bash pipeline/blender/render_all.sh <video_id> [res] [samples]
set -e
VID=${1:?video id}; RES=${2:-576}; SAMPLES=${3:-24}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BLENDER=${BLENDER:-/home/user/tools/blender-4.5.15-linux-x64/blender}
OUT=$ROOT/videos/$VID/build/frames
# scene script + shot frame counts come from videos/<id>/script.json ("scene", "shots")
SCENE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['scene'])" "$ROOT/videos/$VID/script.json")
SHOTS=$(python3 -c "import json,sys; print(' '.join(f'{k}:{v}' for k,v in json.load(open(sys.argv[1]))['shots'].items()))" "$ROOT/videos/$VID/script.json")
FPS=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('fps',24))" "$ROOT/videos/$VID/script.json")
echo "scene=$SCENE shots=$SHOTS (res=$RES samples=$SAMPLES)"
for KV in $SHOTS; do
  S=${KV%%:*}; N=${KV##*:}
  $BLENDER -b -noaudio -P "$ROOT/$SCENE" -- --shot $S --start 0 --end $N --out "$OUT/$S" --res $RES --samples $SAMPLES --fps $FPS 2>&1 | grep --line-buffered -E "^FRAME|Error|Traceback"
done
echo "all shots done"
