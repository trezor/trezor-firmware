#!/usr/bin/env bash

git fetch origin master:master  # on CIs it is common to fetch only the current branch

messages=$(git log --format=%s master..)  # commit messages between this branch and master

if [[ $messages =~ "fixup!" ]]; then
  echo 'Failure: Some commit message contains "fixup!" string.'
  exit 1
else
  echo 'Success: No commit messages containing "fixup!" string.'
fi
