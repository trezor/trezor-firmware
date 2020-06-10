# Contribute to Trezor Firmware

Please read the general instructions you can find on our
[wiki](https://wiki.trezor.io/Developers_guide:Contributing).

Your Pull Request should follow these criteria:

- The code is properly tested.
- Tests must pass on [CI](https://travis-ci.org/trezor/trezor-firmware).
- The code is properly formatted. Use `make style_check` to check the format
  and `make style` to do the required changes.
- The generated files are up-to-date. Use `make gen` in repository root to make
  it happen.
- Commits must have concise commit messages, the imperative mood is preferred
  ([rationale](https://gist.github.com/robertpainsi/b632364184e70900af4ab688decf6f53)).
- Multiple commits per PR are allowed, but please do not use reverts, etc.
  Use rebase.
- Do not use merge (e.g. merge trezor/master into ...).
  Again, use rebase.
- Do not force push to PRs. If you are implementing some comments from a
  review, use _fixup_ commits (e.g. `git commit --fixup HEAD`) and push those.
- After the PR is finally approved _autosquash_ these commits and force push
  (`git rebase -i master --autosquash`).
- Do not resolve review comments. Inform the reviewer that you have fixed the
  issue (simply by commenting "Done" or similar). The reviewer will resolve the
  discussion after reviewing your fix.
