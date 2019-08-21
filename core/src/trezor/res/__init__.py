try:
    from .resources import resdata
except ImportError:
    resdata = {}


def load(name: str) -> bytes:
    """
    Loads resource of a given name as bytes.
    """
    return resdata[name]


def gettext(message: str) -> str:
    """
    Returns localized string. This function is aliased to _.
    """
    return message


_ = gettext
