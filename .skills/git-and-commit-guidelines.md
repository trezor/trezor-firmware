# Git and Commit Guidelines

## Conventional Commits (mandatory)

Format: `<type>(<scope>): <description>`

**Types:** `feat`, `fix`, `refactor`, `test`, `chore`, `docs`, `ci`, `perf`, `style`, `revert`

**Scopes:** `core`, `common`, `crypto`, `legacy`, `python`, `storage`, `tools`, `vendor`

Multiple scopes are fine: `feat(tests, ethereum): ...`

### Examples from this repo

```
feat(core): propagate method to choose backup handler
fix(python): trezorctl should use recent THP credentials first
refactor(core): simplify recovery flow
test(core): remove unused imports from unittests
chore(deps): bump pygments from 2.19.2 to 2.20.0
chore(common): add options to THP messages
docs(core): fix recovery-related comment
ci: compare Cargo.lock to common ancestor instead of main
```

## Pull requests

Follow the template at `.github/pull_request_template.md` when opening a PR.
