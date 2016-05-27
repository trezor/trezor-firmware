def loadres(name):
    with open(name, 'rb') as f:
        return f.read()

def gettext(message):
    return message

_ = gettext
