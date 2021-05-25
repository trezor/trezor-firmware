#!/usr/bin/env bash

base_branch=master
fail=0
subdirs="core python legacy/firmware legacy/bootloader"

changed_files=$(mktemp)
trap 'rm -- $changed_files' EXIT

git fetch origin "$base_branch"

check_feature_branch () {

    for commit in $(git rev-list origin/$base_branch..)
    do
        if git log -n1 --format=%B "$commit" | grep -iFq "[no changelog]"; then
            echo "Found [no changelog] in $commit, skipping."
            continue
        fi

        git show --pretty=format: --name-only "$commit" >> "$changed_files"
    done

    for subdir in $subdirs
    do
        echo "Checking $subdir"
        files=$(grep "^$subdir/" "$changed_files")

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

if echo "$CI_COMMIT_BRANCH" | grep -Eq "^(release|secfix)/"; then
    check_release_branch
else
    check_feature_branch
fi

if [[ "$fail" -ne 0 ]]; then
    echo "Please see https://docs.trezor.io/trezor-firmware/misc/changelog.html for instructions."
fi

exit $fail
