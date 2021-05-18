# CI

The complete test suite is running on a public [GitLab CI](https://gitlab.com/satoshilabs/trezor/trezor-firmware). We currently do not have a CI for external contributors. If needed we will repush your PR to enable the CI.

See this [list](jobs.md) of CI jobs descriptions for more info.

The CI folder contains all the .yml GitLab files that are included in the main `.gitlab.yml` to provide some basic structure. All GitLab CI Jobs run inside a docker image, which is built using the present `Dockerfile`. This image is stored in the GitLab registry.
