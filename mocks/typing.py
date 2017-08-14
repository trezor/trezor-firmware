__names_get = [
    'AbstractSet',
    'AsyncIterable',
    'AsyncIterator',
    'Awaitable',
    'ByteString',
    'Callable',
    'Container',
    'DefaultDict',
    'Dict',
    'Generator',
    'Generic',
    'ItemsView',
    'Iterable',
    'Iterator',
    'KeysView',
    'List',
    'Mapping',
    'MappingView',
    'MutableMapping',
    'MutableSequence',
    'MutableSet',
    'Optional',
    'Reversible',
    'Sequence',
    'Set',
    'Tuple',
    'Type',
    'Union',
    'ValuesView',
]

__names_obj = [
    'Any',
    'AnyStr',
    'Hashable',
    'Sized',
    'SupportsAbs',
    'SupportsFloat',
    'SupportsInt',
    'SupportsRound',
    'Text',
]


class __dummy:

    def __getitem__(self, *args):
        return object


__t = __dummy()

for __n in __names_get:
    globals()[__n] = __t

for __n in __names_obj:
    globals()[__n] = object


def TypeVar(*args):
    return object


def NewType(*args):
    return lambda x: x


TYPE_CHECKING = False
