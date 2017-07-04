from . import wire_types


def get_type_name(wire_type):
    for name in dir(wire_types):
        if getattr(wire_types, name) == wire_type:
            return name


def get_type(wire_type):
    name = get_type_name(wire_type)
    module = __import__('trezor.messages.%s' % name, None, None, (name, ), 0)
    return getattr(module, name)
