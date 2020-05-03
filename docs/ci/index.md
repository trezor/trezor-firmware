# CI

The complete test suite is running on a public [GitLab CI](https://gitlab.com/satoshilabs/trezor/trezor-firmware). If you are an external contributor, we also have a [Travis instance](https://travis-ci.org/trezor/trezor-firmware) where a small subset of tests is running as well - mostly style and easy fast checks, which are quite common to fail for new contributors.

See this [list](jobs.md) of CI jobs descriptions for more info. 

The CI folder contains all the .yml GitLab files that are included in the main `.gitlab.yml` to provide some basic structure. All GitLab CI Jobs run inside a docker image, which is built using the present `Dockerfile`. This image is stored in the GitLab registry.
