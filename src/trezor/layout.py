import sys

_new_layout = None
_current_layout = None

def change(layout):
    global _new_layout

    print("Changing layout to %s" % layout)
    _new_layout = layout

    yield _current_layout.throw(StopIteration())

def set_main(main_layout):
    global _new_layout
    global _current_layout

    _current_layout = main_layout
    while True:
        try:
            _current_layout = yield from _current_layout
        except Exception as e:
            sys.print_exception(e)
            _current_layout = main_layout
            continue

        if _new_layout != None:
            print("Switching to new layout %s" % _new_layout)
            _current_layout = _new_layout
            _new_layout = None

        elif not callable(_current_layout):
            print("Switching to main layout %s" % main_layout)
            _current_layout = main_layout
        else:
            print("Switching to proposed layout %s" % _current_layout)
