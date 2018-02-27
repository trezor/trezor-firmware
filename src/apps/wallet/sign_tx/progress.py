_progress = 0
_steps = 0


def init(inputs, outputs):
    global _progress, _steps
    _progress = 0
    _steps = inputs + outputs + inputs + outputs + inputs


def advance():
    global _progress, _steps
    _progress += 1
    p = int(1000 * _progress / _steps)
    # TODO: draw progress circle using loader
    print("%d" % p)
