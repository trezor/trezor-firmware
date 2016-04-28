_new_layout = None
_current_layout = None

def change_layout(layout):
    global _new_layout

    print("Changing layout to %s" % layout)
    _new_layout = layout

    yield _current_layout.throw(StopIteration())

def set_main_layout(main_layout):
    global _new_layout
    global _current_layout

    layout = main_layout
    while True:
        try:
            _current_layout = layout()
            layout = yield from _current_layout
        except Exception as e:
            print("Layout thrown exception %s" % str(e))
            _current_layout = main_layout
            continue

        if _new_layout != None:
            print("Switching to new layout %s" % _new_layout)
            layout = _new_layout
            _new_layout = None

        elif layout == None:
            print("Switching to main layout %s" % main_layout)
            layout = main_layout
        else:
            print("Switching to proposed layout %s" % layout)
