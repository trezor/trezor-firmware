# Trezor Common

This project contains files shared among Trezor projects. All changes are happening inside the [Trezor Firmware repository](https://github.com/trezor/trezor-firmware).

We also export this project to the [trezor-common repository](https://github.com/trezor/trezor-common) as a read-only copy so third parties may depend on that instead of the whole monorepo. It is meant to be used as a submodule using:

```
git submodule add https://github.com/trezor/trezor-common.git trezor-common
```
