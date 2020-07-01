try:
    from .resources import load_resource
except ImportError:
    raise RuntimeError("Please regenerate resources via 'make res'")


def load(name: str) -> bytes:
    """
    Loads resource of a given name as bytes.
    """
    return load_resource(name)


def gettext(message: str) -> str:
    """
    Returns localized string. This function is aliased to _.
    """
    return message


_ = gettext
