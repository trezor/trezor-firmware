from TrezorCrypto import Ripemd160 as ripemd160
from TrezorCrypto import Sha256 as sha256
from TrezorCrypto import Sha512 as sha512

from . import hmac

def pbkdf2_hmac(name, password, salt, rounds, dklen=None):
    if name == 'sha256':
        digestmod = sha256
    elif name == 'sha512':
        digestmod = sha512
    elif name == 'ripemd160':
        digestmod = ripemd160
    else:
        raise ValueError('unknown digest', name)
    if dklen is None:
        dklen = digestmod.digest_size

    p = Pbkdf2(password, salt, rounds, digestmod, hmac)
    k = p.read(dklen)
    p.close()
    return k

#
# Copyright (C) 2007-2011 Dwayne C. Litzenberger <dlitz@dlitz.net>
# Copyright (C) 2016 Pavol Rusnak <stick@gk2.sk>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from ustruct import pack

class Pbkdf2(object):

    def __init__(self, passphrase, salt, iterations, digestmodule, macmodule):
        self.__macmodule = macmodule
        self.__digestmodule = digestmodule
        self.__passphrase = passphrase
        self.__salt = salt
        self.__iterations = iterations
        self.__prf = self._pseudorandom
        self.__blockNum = 0
        self.__buf = b''
        self.closed = False

    def _pseudorandom(self, key, msg):
        return self.__macmodule.new(key=key, msg=msg, digestmod=self.__digestmodule).digest()

    def read(self, numbytes):
        if self.closed:
            raise ValueError('file-like object is closed')
        size = len(self.__buf)
        blocks = [self.__buf]
        i = self.__blockNum
        while size < numbytes:
            i += 1
            U = self.__prf(self.__passphrase, self.__salt + pack('!L', i))
            block = U
            for j in range(2, 1 + self.__iterations):
                U = self.__prf(self.__passphrase, U)
                block = bytes([x ^ y for (x, y) in zip(block, U)])
            blocks.append(block)
            size += len(block)
        buf = b''.join(blocks)
        retval = buf[:numbytes]
        self.__buf = buf[numbytes:]
        self.__blockNum = i
        return retval

    def close(self):
        if not self.closed:
            del self.__passphrase
            del self.__salt
            del self.__iterations
            del self.__prf
            del self.__blockNum
            del self.__buf
            self.closed = True
