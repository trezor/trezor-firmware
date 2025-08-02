import pytest

# TODO: undo when event loop restarts are done
pytestmark = [pytest.skip(allow_module_level=True)]
