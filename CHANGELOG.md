The changelog format is bound to change as we figure out a way to autogenerate it.

## version 0.9.1 (released 2018-03-05)

- proper support for Trezor model T
- gradually dropping Python 2 compatibility (pypi package will now be marked as Python 3 only)
- support for Monacoin
- improvements to `trezorctl`:
  - add pretty-printing of features and protobuf debug dumps (fixes #199)
  - support `TREZOR_PATH` environment variable to preselect a Trezor device.
