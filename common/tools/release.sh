#!/bin/sh

if [ -z "$COINMARKETCAP_API_KEY" ]; then
    echo "Please set \$COINMARKETCAP_API_KEY"
    exit 1
fi

HERE=$(dirname $0)

CHECK_OUTPUT=$(mktemp -d)
trap "rm -r $CHECK_OUTPUT" EXIT

$HERE/cointool.py check > $CHECK_OUTPUT/pre.txt

ETH_DIR=$HERE/../defs/ethereum
ETH_REPOS="chains tokens"

for dir in $ETH_REPOS; do
    (
        cd $ETH_DIR/$dir; \
        git checkout master; \
        git pull origin master
    )
done

$HERE/support.py release

$HERE/cointool.py check > $CHECK_OUTPUT/post.txt

make -C $HERE/../.. gen

diff $CHECK_OUTPUT/pre.txt $CHECK_OUTPUT/post.txt

$HERE/coins_details.py
