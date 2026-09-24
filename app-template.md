This is a follow-up to the standup discussion. I mixed a few ideas together and came up with this proposal:

`github:trezor/trezor-app-template` is a template repository for creating new
Trezor apps. It provides the project structure and boilerplate needed to start
quickly, and it is the single place that pins which SDK, app tool, and Rust
toolchain belong together.

The template shares its version with `trezor-app-sdk`: template tag `v0.5.0`
goes with `trezor-app-sdk 0.5.0` on crates.io, and the two are released
together. `trezor-app-tool` has its own version and its own release cadence;
one tool release typically serves several SDK releases. The template is what
records which tool version goes with which SDK version.

## Repository structure

```
trezor-app-template/
├── flake.nix                 # devShell + trezor-app-tool package (provides `cargo app-tool`);
│                             # sdk (= template) version, tool version and nightly date
│                             # in a `let` block at the top
├── template/                 # the cargo-generate template
│   ├── cargo-generate.toml   # placeholders: app id, vendor, ...
│   ├── Cargo.toml            # trezor-app-sdk = "=0.5.0", build profiles, [package.metadata.trezor]
│   ├── flake.nix             # one input: github:trezor/trezor-app-template/v0.5.0; re-exports its devShell
│   ├── src/main.rs
│   ├── ...
│   └── ...
├── README.md
└── .github/workflows/ci.yml 
```

The dev shell provides:

- the nightly Rust toolchain
- `trezor-app-tool` built from crates.io at the version the template pins for
  this SDK
- `cargo-generate`, git, `uv`, Python, `ruff`, `flake8`, `pyright`
- environment variables with the pinned
  versions, read by `cargo app-tool new`, `check` and `upgrade`

## Developer flow

The developer starts with:

```sh
nix develop github:trezor/trezor-app-template/v0.5.0
```

This downloads the template repository at that tag and enters its dev shell.
The version is chosen once, here. Inside the shell:

```sh
cargo app-tool new funnycoin
```

This runs `cargo generate` on the `template/` folder at the same tag and
creates the `funnycoin/` directory with a minimal app, including its own
`flake.nix` that points back at the template at `v0.5.0`.

From now on the developer works inside the app repository:

```sh
cd funnycoin
nix develop                          # no version needed; flake.lock remembers it
cargo app-tool build -m t3w1 --lang en -e
```

The SDK version is pinned in `Cargo.toml` and in the template tag of
`flake.nix`; the tool version and the toolchain follow from that tag. `cargo app-tool check` verifies that they agree and `build` runs the
same checks first, so entering the wrong shell fails immediately with a message
naming the file to fix.

## Upgrading to a newer SDK

The developer exits the shell and enters the new one:

```sh
nix develop github:trezor/trezor-app-template/v0.6.0
cargo app-tool upgrade
```

`upgrade` is part of `trezor-app-tool`. It takes the target versions from the
shell's environment variables (or from flags, for non-Nix users) and:

1. refuses to run if the git working tree is dirty, so the result can be reviewed with `git diff`
2. rewrites the SDK pin in `Cargo.toml`, the channel in `rust-toolchain.toml`, and the tag of the template input in `flake.nix`

It cannot fix the developer's code against SDK API changes. The changelog and
the first `cargo app-tool build` after the upgrade cover that.

