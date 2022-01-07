# Trezor Core coding style

## Python coding style

Run `make pystyle` from repository root to perform all style checks and auto-format
where possible.

### General style notes

See rules for exceptions in the [Exceptions documentation](./exceptions.md).

#### Type annotations

We prefer Python 3.10 style annotations:

* instead of `List[int]`, use `list[int]`, dtto for `Tuple`, `Dict` and `Set`
* instead of `Optional[int]`, use `int | None`
* instead of `Union[int, str]`, use `int | str`

This also applies inside `if TYPE_CHECKING` branches.

#### Type-checking imports

At run-time, the `typing` module is not available. There is compile-time magic that
removes all `from typing` imports and contents of `if TYPE_CHECKING` branches.

It is important to put typing-only imports into `if TYPE_CHECKING`, to make sure that
these modules are not needlessly pulled in at run-time.

Due to the compile-time magic, it is always possible to put a `from typing` import
at top level. The style for doing that are as follows:

* If the module needs to import other modules, create type aliases, TypeVars or
  Protocols, the only top-level import should be `TYPE_CHECKING`. Everything else
  (including other items from `typing` module) should be imported in the `TYPE_CHECKING`
  branch:
  ```python
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from typing import Any, TypeVar, Union
      from trezor.messages import SomeMessage

      TypeAlias = Union[int, str]
      T = TypeVar("T")
  ```
* If the module _only_ needs items from `typing`, you should not create a
  `TYPE_CHECKING` branch, and instead import all required items on top level:
  ```python
  from typing import Any, Iterator, Sequence
  ```

### Tools

Configurations of specific Python style tools (`isort`, `flake8`, `pylint`) can be found
in root [`setup.cfg`].

[`setup.cfg`]: https://github.com/trezor/trezor-firmware/blob/master/setup.cfg

#### Formatting

We are auto-formatting code with `black` and use the [`black` code
style](https://black.readthedocs.io/en/stable/the_black_code_style/index.html).

We use `isort` to organize imports.

#### Linting

We use `flake8` lints, disabling only those that conflict with `black` code style.

We use a select subset of `pylint` checks that are hard-enforced.

#### Type checking

We use `pyright` for type-checking. The codebase is fully type-checked, except for
the Monero app (as of 2022-01).


## C coding style

Formatting is done by `clang-format`. We are using the [Google code
style](https://google.github.io/styleguide/cppguide.html).

Run `make cstyle` from repository root to auto-format.

## Rust coding style

Formatting is done by `rustfmt`. We are using the [Rust
style](https://github.com/rust-dev-tools/fmt-rfcs/blob/master/guide/guide.md).

Run `make ruststyle` from repository root to auto-format.
