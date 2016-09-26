from . import wire_types


def get_protobuf_type_name(wire_type):
    for name in dir(wire_types):
        if getattr(wire_types, name) == wire_type:
            return name


def get_protobuf_type(wire_type):
    name = get_protobuf_type_name(wire_type)
    module = __import__('.%s' % name, None, None, (name,), 1)
    return getattr(module, name)
