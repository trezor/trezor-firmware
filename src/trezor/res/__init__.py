try:
    from .resources import resdata
except ImportError:
    resdata = None


def load(name):
    '''
    Loads resource of a given name as bytes.
    '''
    if resdata and name in resdata:
        return resdata[name]
    with open(name, 'rb') as f:
        return f.read()


def gettext(message):
    '''
    Returns localized string. This function is aliased to _.
    '''
    return message


_ = gettext
