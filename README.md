# Trezor Firmware

![img](https://repository-images.githubusercontent.com/180590388/968e6880-6538-11e9-9da6-4aef78157e94)

## Repository Structure

* **[`ci`](ci/)**: [Gitlab CI](https://gitlab.com/satoshilabs/trezor/trezor-firmware) configuration files
* **[`common/defs`](common/defs/)**: JSON coin definitions and support tables
* **[`common/protob`](common/protob/)**: Common protobuf definitions for the Trezor protocol
* **[`common/tools`](common/tools/)**: Tools for managing coin definitions and related data
* **[`core`](core/)**: Trezor Core, firmware implementation for Trezor T
* **[`crypto`](crypto/)**: Stand-alone cryptography library used by both Trezor Core and the Trezor One firmware
* **[`docs`](docs/)**: Assorted documentation
* **[`legacy`](legacy/)**: Trezor One firmware implementation
* **[`python`](python/)**: Python [client library](https://pypi.org/project/trezor) and the `trezorctl` command
* **[`storage`](storage/)**: NORCOW storage implementation used by both Trezor Core and the Trezor One firmware
* **[`tests`](tests/)**: Firmware unit test suite
* **[`tools`](tools/)**: Miscellaneous build and helper scripts
* **[`vendor`](vendor/)**: Submodules for external dependencies


## Contribute

See [CONTRIBUTING.md](docs/misc/contributing.md).

Also please have a look at the docs, either in the `docs` folder or at  [docs.trezor.io](https://docs.trezor.io) before contributing. The [misc](docs/misc/index.md) chapter should be read in particular because it contains some useful assorted knowledge.

## Security vulnerability disclosure

Please report suspected security vulnerabilities in private to [security@satoshilabs.com](mailto:security@satoshilabs.com), also see [the disclosure section on the Trezor.io website](https://trezor.io/security/). Please do NOT create publicly viewable issues for suspected security vulnerabilities.

## Issue Labels

### Priority

Label     | Meaning (SLA)
----------|--------------
P1 Urgent | The current release + potentially immediate hotfix (30 days)
P2 High   | The next release (60 days)
P3 Medium | Within the next 3 releases (90 days)
P4 Low    | Anything outside the next 3 releases (120 days)

#### Severity

Label       | Impact
------------|-------
S1 Blocker  | Outage, broken feature with no workaround
S2 Critical | Broken feature, workaround too complex & unacceptable
S3 Major    | Broken feature, workaround acceptable
S4 Low      | Functionality inconvenience or cosmetic issue

## CI

The complete test suite is running on a public [GitLab CI](https://gitlab.com/satoshilabs/trezor/trezor-firmware). If you are an external contributor, we also have a [Travis instance](https://travis-ci.org/trezor/trezor-firmware) where a small subset of tests is running as well - mostly style and easy fast checks, which are quite common to fail for new contributors.

## Documentation

See the `docs` folder or visit [docs.trezor.io](https://docs.trezor.io).
