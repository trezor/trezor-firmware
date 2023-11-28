from astroid import AsyncFunctionDef
from pylint.checkers import BaseChecker
from pylint.checkers.utils import check_messages
from pylint.interfaces import IAstroidChecker


class AsyncAwaitableChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = "async-awaitable-checker"
    priority = -1
    msgs = {
        "W9999": (
            'Async function "%s" is likely not meant to return an Awaitable.',
            "async-awaitable-return",
            "Used when an async function returns an Awaitable instead of the result.",
        ),
    }

    @check_messages("async-awaitable-return")
    def visit_asyncfunctiondef(self, node: AsyncFunctionDef):
        # Check if the return type is explicitly an Awaitable
        if node.returns and "Awaitable" in node.returns.as_string():
            self.add_message("async-awaitable-return", node=node, args=(node.name,))


def register(linter):
    """Required method to auto register this checker."""
    linter.register_checker(AsyncAwaitableChecker(linter))
