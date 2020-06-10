#!/usr/bin/env bash 
if [ $# -ne 2 ]
  then
    echo "Usage: $0 commit_id [start|stop]"
fi

OUTPUTFILE=video_$1_$(date +%s).mp4
INPUTDEVICE=/dev/video0

if [ "$2" == "start" ]; then
  echo "[software/video] Starting record to $OUTPUTFILE"
  ffmpeg -loglevel panic -f oss -f video4linux2 -i $INPUTDEVICE \
    -vf "drawtext=font=Dejavu Sans: \
    text='$1 | %{localtime} | %{pts}': x=(w-tw)/2: y=h-(2*lh): fontcolor=white: box=1: boxcolor=0x00000000@1: fontsize=15" $OUTPUTFILE &
  export VPID=$!
elif [ "$2" == "stop" ]; then
  echo "[software/video] Stopping the recording of $OUTPUTFILE"
  pkill ffmpeg
  sync
fi
