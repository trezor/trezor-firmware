try:
    from .resources import resdata
except ImportError:
    resdata = None

def load(name):
    if resdata and name in resdata:
        return resdata[name]
    with open(name, 'rb') as f:
        return f.read()

def gettext(message):
    return message

_ = gettext
