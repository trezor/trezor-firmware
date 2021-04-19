#!/usr/bin/env bash

base_branch=master
fail=0
subdirs="core python legacy/firmware legacy/bootloader"

git fetch origin "$base_branch"

check_feature_branch () {
    for subdir in $subdirs
    do
        echo "Checking $subdir"
        files=$(git diff --name-only "origin/$base_branch..." -- "$subdir")

        if echo "$files" | grep . | grep -Fq -v .changelog.d; then
            if ! echo "$files" | grep -Fq .changelog.d; then
                fail=1
                echo "FAILURE! No changelog entry for changes in $subdir."
            fi
        fi
    done
}

check_release_branch () {
    if git diff --name-only "origin/$base_branch..." | grep -Fq .changelog.d; then
        fail=1
        echo "FAILURE! Changelog fragments not allowed in release branch:"
        git diff --name-only "origin/$base_branch..." | grep -F .changelog.d
    fi
}

if echo "$CI_COMMIT_BRANCH" | grep -q "^release/"; then
    check_release_branch
else
    check_feature_branch
fi

if [[ "$fail" -ne 0 ]]; then
    echo "Please see https://docs.trezor.io/trezor-firmware/misc/changelog.html for instructions."
fi

exit $fail
