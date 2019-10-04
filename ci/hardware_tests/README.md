# Hardware tests

Hardware tests are device tests that run against an actual device instead of an emulator.
This works thanks to [tpmb](https://github.com/mmahut/tpmb), which is a small arduino
device capable of pushing an actual buttons on the device. Currently T1 is supported
but TT might follow.

See `ci/test.yml` "hardware legacy device test" what exactly is run.
