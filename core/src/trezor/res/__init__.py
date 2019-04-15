try:
    from .resources import resdata
except ImportError:
    resdata = None


def load(name):
    """
    Loads resource of a given name as bytes.
    """
    return resdata[name]


def gettext(message):
    """
    Returns localized string. This function is aliased to _.
    """
    return message


_ = gettext
