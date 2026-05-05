# trezor-firmware — Agents notes

## Skills

**All skills are mandatory reading** before making changes.

- [Project structure](.skills/project-structure.md) – Repo layout, key directories, generated files
- [Setup requirements](.skills/setup-requirements.md) – Environment bootstrap (nix-shell + uv)
- [Build commands](.skills/build-commands.md) – Emulator and firmware build commands, model names
- [Git and commit guidelines](.skills/git-and-commit-guidelines.md) – Conventional commits format and scopes
- [Tests](.skills/tests.md) – Running device, Python unit, and Rust unit tests
- [Comments](.skills/comments.md) – Code comment conventions

## Formatting (mandatory)

After any code changes, run formatting from the repo root before finishing:

```sh
make style
```
