# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).


## 1.0.1 [January 2021]

### Added
- Decouple files from original bootloader as it will be reworked and symlink
  magic will break
- Version in version.h must be kept to match the original bootloader,
  otherwise firmware update will fail (bootloader will look too old)

## 1.0.0 [August 2020]

### Added
- Initial version
