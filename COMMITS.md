# Commits

Using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) is strongly recommended and might be enforced in future.

### Examples

```
docs: correct spelling of CHANGELOG
feat: allow provided config object to extend other configs
feat(lang): added polish language
```

### Git hook

Use this git hook to auto-check your commit messages. Save the following snippet into `.git/hooks/commit-msg`

```
#!/bin/sh
if ! grep -qE "^(build|ci|docs|feat|fix|perf|refactor|style|test|chore|revert)(\((common|core|crypto|legacy|python|storage|tools|vendor)\))?: " "$1" ; then
  echo "Conventional Commits validation failed"
  exit 1
fi
```

If you want to bypass commit-msg hook check, you may always use

```
git commit -m "foobar" --no-verify
```
