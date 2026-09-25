#!/usr/bin/env bash
# 숏폼을 여러 구간으로 나눠 병렬 렌더 → 이어붙이고 사운드트랙 합치기
set -euo pipefail
cd "$(dirname "$0")/.."
FFMPEG=${FFMPEG:-ffmpeg}; FPS=30; TOTAL=$((48*FPS)); JOBS=${JOBS:-3}
mkdir -p frames/seg; : > frames/seg/list.txt
step=$(( (TOTAL + JOBS - 1) / JOBS ))
for ((j=0; j<JOBS; j++)); do
  a=$((j*step)); b=$(((j+1)*step))
  SCENE=shorts/scene.html FRAMES=$a:$b FFMPEG=$FFMPEG node render.mjs frames/seg/s$j.mp4 $FPS > frames/seg/log$j.txt 2>&1 &
  echo "file 's$j.mp4'" >> frames/seg/list.txt
done
wait
$FFMPEG -y -loglevel error -f concat -safe 0 -i frames/seg/list.txt -c copy frames/shorts_noaudio.mp4
python3 shorts/audio.py
$FFMPEG -y -loglevel error -i frames/shorts_noaudio.mp4 -i shorts/soundtrack.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart shorts/maeil_shorts.mp4
echo done
