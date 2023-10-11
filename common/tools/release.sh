#!/bin/sh

HERE=$(dirname $0)

CHECK_OUTPUT=$(mktemp -d)
trap "rm -r $CHECK_OUTPUT" EXIT

$HERE/cointool.py check > $CHECK_OUTPUT/pre.txt

$HERE/cointool.py new-definitions -v
$HERE/support.py release

$HERE/cointool.py check > $CHECK_OUTPUT/post.txt

make -C $HERE/../.. gen

diff $CHECK_OUTPUT/pre.txt $CHECK_OUTPUT/post.txt
