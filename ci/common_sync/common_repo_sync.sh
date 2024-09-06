#!/usr/bin/env bash

COMMON_REPO_TOKEN="$BOT_TOKEN"
COMMON_REPO_USER="$BOT_USERNAME"

# checkout to temporary branch
git checkout -B tmp

# setup trezor-common remote
git remote add sync-common https://$COMMON_REPO_USER:$COMMON_REPO_TOKEN@github.com/trezor/trezor-common.git 2>/dev/null

# top commit in HEAD before monorepo was introduced
TOP_COMMIT_IN_COMMON=893fd219d4a01bcffa0cd9cfa631856371ec5aa9

# convert contents of the repository so that common/ is the root
git filter-repo --refs $TOP_COMMIT_IN_COMMON..HEAD --subdirectory-filter=common/ --force

# filter out .gitrepo
git filter-repo --refs $TOP_COMMIT_IN_COMMON..HEAD --path .gitrepo --invert-paths

# push changes to trezor-common repository
git push sync-common tmp:master

# cleanup
git remote remove sync-common
