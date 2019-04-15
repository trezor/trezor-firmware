from trezor import loop

workflows = []
layouts = []
default = None
default_layout = None

# HACK: workaround way to stop the WebAuthn layout from the outside
webauthn_stop_signal = loop.signal()


def onstart(w):
    workflows.append(w)


def onclose(w):
    workflows.remove(w)
    if not layouts and default_layout:
        startdefault(default_layout)


def closedefault():
    global default

    if default:
        loop.close(default)
        default = None


def startdefault(layout):
    global default
    global default_layout

    if not default:
        default_layout = layout
        default = layout()
        loop.schedule(default)


def restartdefault():
    global default_layout
    d = default_layout
    closedefault()
    startdefault(d)


def onlayoutstart(l):
    closedefault()
    layouts.append(l)
    webauthn_stop_signal.send(None)


def onlayoutclose(l):
    if l in layouts:
        layouts.remove(l)
