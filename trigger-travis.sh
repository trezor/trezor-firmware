#!/bin/bash
# adapted from https://github.com/stephanmg/travis-dependent-builds

# variables
SOURCE=trezor/python-trezor

if [ "$TRAVIS_REPO_SLUG" != "$SOURCE" ]; then
    echo "not triggering from $TRAVIS_REPO_SLUG"
    exit 0;
fi

if [ "$TRAVIS_BRANCH" != "master" ]; then
    echo "not triggering from non-master branch"
    exit 0;
fi

if [ "$TRAVIS_PULL_REQUEST" != "false" ]; then
    echo "not triggering from pull requests"
    exit 0;
fi

if [[ "$TRAVIS_JOB_NUMBER" != *.1 ]]; then
    echo "not triggering for job number $TRAVIS_JOB_NUMBER (not first job in set)"
    exit 0;
fi

function trigger_build() {
    USER="$1"
    REPO="$2"
    BRANCH="$3"
    echo "attempting to trigger build of $USER/$REPO"

    MESSAGE=",\"message\": \"Triggered from upstream build of $TRAVIS_REPO_SLUG by commit "`git rev-parse --short HEAD`"\""

    # curl POST request content body
    BODY="{
      \"request\": {
      \"branch\":\"$BRANCH\"
      $MESSAGE
    }}"

    # make a POST request with curl (note %2F could be replaced with
    # / and additional curl arguments, however this works too!)
    curl -s -X POST \
      -H "Content-Type: application/json" \
      -H "Accept: application/json" \
      -H "Travis-API-Version: 3" \
      -H "Authorization: token ${TRAVIS_TOKEN}" \
      -d "$BODY" \
      https://api.travis-ci.org/repo/${USER}%2F${REPO}/requests \
      | tee /tmp/travis-request-output.$$.txt
    echo

    if grep -q '"@type": "error"' /tmp/travis-request-output.$$.txt; then
       cat /tmp/travis-request-output.$$.txt
       exit 1
    elif grep -q 'access denied' /tmp/travis-request-output.$$.txt; then
       cat /tmp/travis-request-output.$$.txt
       exit 1
    fi
}

# trigger both core and mcu
trigger_build trezor trezor-core master
trigger_build trezor trezor-mcu master
