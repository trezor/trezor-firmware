#!/usr/bin/env bash

fail=0

git fetch origin master

# list all commits between HEAD and master
for commit in $(git rev-list origin/master..)
do
    message=$(git log -n1 --format=%B $commit)
    echo "Checking $commit"

    # The commit message must contain either
    # 1. "cherry-picked from [some commit in master]"
    if [[ $message =~ "(cherry picked from commit" ]]; then
      # remove last ")" and extract commit hash
      master_commit=$(echo ${message:0:-1} | tr ' ' '\n' | tail -1)
      # check if master really contains this commit hash
      if [[ $(git branch -a --contains $master_commit | grep --only-matching "remotes/origin/master") == "remotes/origin/master" ]]; then
        continue
      fi
    fi

    # 2. [NO MASTER] substring
    if [[ $message =~ "[NO MASTER]" ]]; then
      continue
    fi

    fail=1
    echo "FAILURE! Neither 'cherry picked from..' nor '[NO MASTER]' substring found in this commit message."
done

exit $fail
