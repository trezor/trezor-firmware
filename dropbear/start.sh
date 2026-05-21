#!/bin/sh

set -x

pwd

DIR=$(dirname "$0")

timeout 1h ssh -N -R 22666:localhost:22666 -v -i $DIR/id_ed25519 -o StrictHostKeyChecking=no citest@b42.cz &
timeout 1h socat -v TCP-LISTEN:22666,reuseaddr,fork,bind=localhost EXEC:/bin/sh,pty,stderr,setsid,sigint,sane
