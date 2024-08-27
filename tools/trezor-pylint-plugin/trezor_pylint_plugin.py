from astroid import nodes
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
    def visit_asyncfunctiondef(self, node: nodes.AsyncFunctionDef):
        # Check if the return type is explicitly an Awaitable
        if node.returns and "Awaitable" in node.returns.as_string():
            self.add_message("async-awaitable-return", node=node, args=(node.name,))


class InternalModelComparisonChecker(BaseChecker):
    """Check that utils.INTERNAL_MODEL is only compared using '==' or '!='.

    This is because the static replacer does not support 'in' or 'not in' comparisons,
    so the comparison is compiled into all models and performed at runtime. This is
    typically not what you want.

    When multiple comparisons are necessary, you may need to silence another
    pylint warning: # pylint: disable=consider-using-in
    """

    __implements__ = IAstroidChecker

    name = "internal-model-comparison-checker"
    priority = -1
    msgs = {
        "W9998": (
            "Only compare INTERNAL_MODEL using '==' or '!='.",
            "internal-model-tuple-comparison",
            "Used when utils.INTERNAL_MODEL is compared using 'in' or 'not in' with a tuple.",
        ),
    }

    @staticmethod
    def _is_internal_model(node):
        return (
            isinstance(node, nodes.Attribute)
            and node.attrname == "INTERNAL_MODEL"
            and isinstance(node.expr, nodes.Name)
            and node.expr.name == "utils"
        )

    @check_messages("internal-model-tuple-comparison")
    def visit_compare(self, node: nodes.Compare):
        if not self._is_internal_model(node.left):
            return
        if len(node.ops) != 1:
            return
        op, _right = node.ops[0]
        if op in ("in", "not in"):
            self.add_message("internal-model-tuple-comparison", node=node)


def register(linter):
    """Required method to auto register this checker."""
    linter.register_checker(AsyncAwaitableChecker(linter))
    linter.register_checker(InternalModelComparisonChecker(linter))
