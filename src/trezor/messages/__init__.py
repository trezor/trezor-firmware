from trezor.messages import MessageType

if __debug__:
    from trezor import log

type_to_name = {}  # int -> string, reverse table of wire_type mapping
registered = {}  # int -> class, dynamically registered message types


def register(msg_type):
    '''Register custom message type in runtime.'''
    if __debug__:
        log.debug(__name__, 'register %s', msg_type)
    registered[msg_type.MESSAGE_WIRE_TYPE] = msg_type


def get_type(wire_type):
    '''Get message class for handling given wire_type.'''
    if wire_type in registered:
        # message class is explicitly registered
        msg_type = registered[wire_type]
    else:
        # import message class from trezor.messages dynamically
        name = type_to_name[wire_type]
        module = __import__('trezor.messages.%s' % name, None, None, (name, ), 0)
        msg_type = getattr(module, name)
    return msg_type


# build reverse table of wire types
for msg_name in dir(MessageType):
    type_to_name[getattr(MessageType, msg_name)] = msg_name
