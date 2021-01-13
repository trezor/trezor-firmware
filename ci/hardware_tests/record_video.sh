#!/usr/bin/env bash
if [ $# -ne 3 ]
  then
    echo "Usage: $0 video_dev commit_id [start|stop]"
fi

INPUTDEVICE=$1
COMMIT=$2
ACTION=$3
OUTPUTFILE=video_${COMMIT}_$(date +%s).mp4

if [ "$ACTION" == "start" ]; then
  echo "[software/video] Starting record to $OUTPUTFILE"
  ffmpeg -loglevel warning -f oss -f video4linux2 -i $INPUTDEVICE \
    -flush_packets 1 \
    -vf "drawtext=font=Dejavu Sans: \
    text='$COMMIT | %{localtime} | %{pts}': x=(w-tw)/2: y=h-(2*lh): fontcolor=white: box=1: boxcolor=0x00000000@1: fontsize=15" $OUTPUTFILE &
  export VPID=$!
elif [ "$ACTION" == "stop" ]; then
  echo "[software/video] Stopping the recording of $OUTPUTFILE"
  pkill ffmpeg
  sync
fi
