if __debug__:
    import sys

    from trezorlog import debug, error, info, warning  # noqa: F401

    def exception(name: str, exc: BaseException) -> None:
        # we are using `__class__.__name__` to avoid importing ui module
        # we also need to instruct typechecker to ignore the missing argument
        # in ui.Result exception
        if exc.__class__.__name__ == "Result":
            debug(
                name,
                "ui.Result: %s",
                exc.value,  # type: ignore [Cannot access attribute "value" for class "BaseException"]
            )
        elif exc.__class__.__name__ == "Cancelled":
            debug(name, "ui.Cancelled")
        else:
            error(name, "exception:")
            # since mypy 0.770 we cannot override sys, so print_exception is unknown
            sys.print_exception(exc)  # type: ignore ["print_exception" is not a known attribute of module]
