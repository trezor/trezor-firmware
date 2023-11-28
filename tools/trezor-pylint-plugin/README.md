# Custom Pylint rule checker

For now, it catches the following problem (`async-awaitable-return`):

```python
async def show_foo() -> Awaitable[None]:
    return show_something("foo")
```

This is almost certainly a mistake -- the caller would need to say `await (await
show_foo())` to actually show the foo.

The function should be one of:

```python
async def show_foo() -> None:
    return await show_something("foo")

# ... or ...

def show_foo() -> Awaitable[None]:
    return show_something("foo")
```
