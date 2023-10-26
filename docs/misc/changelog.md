# Changelog

Our releases are accompanied by changelogs based on the
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format. We are using
the [towncrier](https://github.com/twisted/towncrier) utility to generate them
at the time a new version is released. There are currently 8 such changelogs
for different components of the repository:

* **[`core/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/core/CHANGELOG.md)** for Trezor T firmware
* **[`core/embed/boardloader/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/core/embed/boardloader/CHANGELOG.md)** for Trezor T boardloader
* **[`core/embed/bootloader/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/core/embed/bootloader/CHANGELOG.md)** for Trezor T bootloader
* **[`core/embed/bootloader_ci/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/core/embed/bootloader_ci/CHANGELOG.md)** for Trezor T CI bootloader
* **[`legacy/firmware/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/legacy/firmware/CHANGELOG.md)** for Trezor 1 firmware
* **[`legacy/bootloader/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/legacy/bootloader/CHANGELOG.md)** for Trezor 1 bootloader
* **[`legacy/intermediate_fw/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/legacy/intermediate_fw/CHANGELOG.md)** for Trezor 1 intermediate firmware
* **[`python/CHANGELOG.md`](https://github.com/trezor/trezor-firmware/blob/master/python/CHANGELOG.md)** for Python client library

## Adding changelog entry

[`towncrier`](https://github.com/twisted/towncrier) aims to create changelogs
that are convenient to read, at the expense of being somewhat inconvenient to
create.

Furthermore every changelog entry should be linked to a GitHub issue or pull
request number. If you don't want to create an issue just to satisfy this rule
you can use self-reference to your change's pull request number by first
creating the PR and then adding the entry. If this is not suitable, the word
`noissue` can be used in place of the issue number.

There are a few types of changelog entries, as described by the [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) format:

* `added`
* `changed`
* `deprecated`
* `removed`
* `fixed`
* `security`
* `incompatible` (for backwards incompatible changes)

Entries are added by creating files in the `.changelog.d` directory where the
file name is `<number>.<type>` and contains single line describing the change.
As an example, an entry describing bug fix for issue 1234 in Trezor T firmware
is added by creating file `core/.changelog.d/1234.fixed`. The file can be
formatted with markdown. If more entries are desired for single issue number and
type you can add numeral suffix, e.g. `1234.fixed.1`, `1234.fixed.2`, etc.

You can also add this entry using your `$VISUAL` editor by running `towncrier
create --edit 1234.fixed` in the `core` directory.

### Changes that only affect a subset of hardware models

If an entry is only relevant for certain model, put the internal name in square
brackets at the beginning of the entry. If there are multiple relevant models,
separate them by comas. Examples: `[T2T1] Fix some bug.`, `[T2T1,T2W1] Fix all
bugs.`.

## Not adding changelog entry

If you don't add an entry for changes in your branch, the `changelog prebuild`
CI job will remind you by failing. Sometimes adding an entry does not really make
sense, in that case you can include `[no changelog]` anywhere in the commit
message to exclude that commit from the check.

## Generating changelog at the time of release

When it's time to release new version of a repository component the formatted
changelog needs to be generated using the `tools/generate-changelog.py` script.
It accepts repo subdirectory and the version number as arguments and you can
specify the release date if it's different from today's date:

```
tools/generate-changelog.py --date "20th April 2021" legacy/firmware 1.10.0
```

## Cherry-picking changes to release branch

Branches named `release/YY.MM` already have their corresponding `CHANGELOG.md`
section generated. When cherry-picking bug fix to such branch you need to
bypass towncrier and edit `CHANGELOG.md` directly.
