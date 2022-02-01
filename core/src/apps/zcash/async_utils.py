class async_generator:
    def __init__(self, func):
        self.func = func

    def __aiter__(self):
        self.iter = iter(self.func())
        self.x = None

    async def __anext__(self):
        try:
            self.x = await gen.send(self.x)
            return self.x
        except StopIteration:
            raise StopAsyncIteration

    def __call__(self):
        return self


class AsyncActionMapper:
    def __init__(self, agen):
        self.agen = agen

    def __aiter__(self):
        self.aiter = self.agen.__aiter__()
        return self

    async def __anext__(self):
        (txi, txo) = await self.aiter.__anext__()
        action_info = dict()

        if txi is not None:
            zip32.verify_path(txi.address_n)
            #master = await zip32.get_master(ctx)
            master = zip32.get_dummy_master()
            sk = master.derive(txi.address_n).spending_key()
            fvk = zcashlib.get_orchard_fvk(sk)
            action_info["spend_info"] = {
                "fvk": fvk,
                "note": txi.zcash.note,
            }

        if txo is not None:
            address = ShieldedAddress(txo)

            action_info["output_info"] = {
                "ovk_flag": txo.zcash.ovk_flag,
                "address": address.raw(),
                "value": txo.amount,
                "memo": txo.zcash.memo,
            }

            if txo.zcash.ovk_flag:
                zip32.verify_path(txo.address_n)
                #master = await zip32.get_master(ctx)
                master = zip32.get_dummy_master()
                sk = master.derive(txo.address_n).spending_key()
                fvk = zcash.get_orchard_fvk(sk)
                action_info["output_info"]["fvk"] = fvk

        return action_info


class AsyncZipGen:
    def __init__(self, agen1, agen2, n):
        self.agen1 = agen1
        self.agen2 = agen2
        self.n = n

    def __aiter__(self):
        self.i = 0
        self.aiter1 = self.agen1.__aiter__()
        self.aiter2 = self.agen2.__aiter__()
        return self

    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration  
        try:
            x1 = await self.agen1.__anext__()
        except StopAsyncIteration:
            x1 = None

        try:
            x2 = await self.agen2.__anext__()
        except StopAsyncIteration:
            x2 = None

        self.i += 1
        return (x1, x2)

class AsyncGenerator:
    def __init__(self, gen):
        pass

    def __call__(self):
        pass


class AsyncGen:
    """Asynchronously generates a sequence feed(0), feed(1), ... , feed(n-1).
    Identical to:
    async def async_gen(n, feed):
        for i in range(n):
            yield (await feed(i))
    """
    def __init__(self, n, feed):
        self.i = 0
        self.n = n
        self.feed = feed

    def __aiter__(self):
        # clones itself to zeroize self.i
        return AsyncGen(self.n, self.feed)

    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration
        txi = await self.feed(self.i)
        self.i += 1
        return txi

class ConstantAsyncGen:
    """Wrapper for async generators, which guarantees
    imutability of ouput sequence."""

    def __init__(self, agen):
        self.agen = agen
        self.digest = None

    def __aiter__(self, **kwargs):
        log.warning(__name__, str(kwargs))
        self.hasher = HashWriter(blake2b(outlen=32, personal=b"ConstantAsyncGen"))
        self.aiter = self.agen.__aiter__()
        return self

    async def __anext__(self):
        try:
            x = await self.aiter.__anext__()
            log.warning(__name__, "hasing" + str(x))
            self.hasher.write(protobuf.dump_message_buffer(x))
            return x
        except StopAsyncIteration:

            if self.digest is None:
                self.digest = self.hasher.get_digest()

            if self.digest != self.hasher.get_digest():
                raise ProcessError("Transaction has changed during signing")

            raise StopAsyncIteration

"""
class FixedMessageSequence:
    def __init__(self, get, length):
        self.get = get
        self.length = length
        self.sequence_digest = None
        self.locked = False

    def __aiter__(self):
        assert not self.locked
        self.locked = True
        self.i = 0
        self.hasher = HashWriter(blake2b(outlen=32))
        return self

    async def __anext__(self):
        pass
"""