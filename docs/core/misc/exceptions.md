# Exceptions in Core

From version 2.3.0 we try to follow few rules about how we use exceptions. All new
code MUST follow these.

## Usage

You MAY use any exceptions in Core's logic. Exceptions from `wire.errors` SHOULD be
the final exceptions that are thrown and SHOULD NOT be caught. Note that `wire.Error`
is a type of exception that is intended to be sent out over the wire. It should only
be used in contexts where that behavior is appropriate.

Custom exception type hierarchies SHOULD always be derived directly from Exception.
They SHOULD NOT be derived from other built-in exceptions (such as ValueError,
TypeError, etc.)

Deriving a custom exception type signals an intention to catch and handle it
somewhere in the code. For this reason, custom exception types SHOULD NOT be derived
from wire.Error and subclasses.

Exception strings, including in internal exceptions, SHOULD only be used in cases
where the text is intended to be shown on the host. Exception strings MUST NOT
contain any sensitive information. An explanation of an internal exception MAY be
placed as a comment on the raise statement, to aid debugging. If an exception is
thrown with no arguments, the exception class SHOULD be thrown instead of a new
object, i.e., `raise CustomError` instead of `raise CustomError()`.

## Tl;dr

- Do not use `wire.errors` for `try-catch` statements, use other exceptions.
- Use `wire.errors` solely as a way to communicate errors to the Host, do not include
them somewhere deep in the stack.
- Do not put sensitive information in exception's message. If you are not sure, do not
add any message and provide a comment next to the `raise` statement.
- Use `raise CustomError` instead of `raise CustomError()` if you are omitting the
exception message.
