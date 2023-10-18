#!/usr/bin/env bash

fail=0

git fetch origin main

# list all commits between HEAD and main
for commit in $(git rev-list origin/main..)
do
    message=$(git log -n1 --format=%B $commit)
    echo "Checking $commit"

    # The commit message must contain either
    # 1. "cherry-picked from [some commit in main]"
    if [[ $message =~ "(cherry picked from commit" ]]; then
      # remove last ")" and extract commit hash
      main_commit=$(echo ${message:0:-1} | tr ' ' '\n' | tail -1)
      # check if main really contains this commit hash
      if [[ $(git branch -a --contains $main_commit | grep --only-matching "remotes/origin/main") == "remotes/origin/main" ]]; then
        continue
      fi
    fi

    # 2. [RELEASE ONLY] substring
    if [[ $message =~ "[RELEASE ONLY]" ]]; then
      continue
    fi

    fail=1
    echo "FAILURE! Neither 'cherry picked from..' nor '[RELEASE ONLY]' substring found in this commit message."
done

exit $fail
