# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import binascii
import os
import warnings
from mnemonic import Mnemonic

from . import messages as proto
from . import tools
from .tools import expect, session

from .transport import enumerate_devices, get_transport


class TrezorDevice:
    '''
    This class is deprecated. (There is no reason for it to exist in the first
    place, it is nothing but a collection of two functions.)
    Instead, please use functions from the ``trezorlib.transport`` module.
    '''

    @classmethod
    def enumerate(cls):
        warnings.warn('TrezorDevice is deprecated.', DeprecationWarning)
        return enumerate_devices()

    @classmethod
    def find_by_path(cls, path):
        warnings.warn('TrezorDevice is deprecated.', DeprecationWarning)
        return get_transport(path, prefix_search=False)


@expect(proto.Success, field="message")
def apply_settings(client, label=None, language=None, use_passphrase=None, homescreen=None, passphrase_source=None, auto_lock_delay_ms=None):
    settings = proto.ApplySettings()
    if label is not None:
        settings.label = label
    if language:
        settings.language = language
    if use_passphrase is not None:
        settings.use_passphrase = use_passphrase
    if homescreen is not None:
        settings.homescreen = homescreen
    if passphrase_source is not None:
        settings.passphrase_source = passphrase_source
    if auto_lock_delay_ms is not None:
        settings.auto_lock_delay_ms = auto_lock_delay_ms

    out = client.call(settings)
    client.init_device()  # Reload Features
    return out


@expect(proto.Success, field="message")
def apply_flags(client, flags):
    out = client.call(proto.ApplyFlags(flags=flags))
    client.init_device()  # Reload Features
    return out


@expect(proto.Success, field="message")
def change_pin(client, remove=False):
    ret = client.call(proto.ChangePin(remove=remove))
    client.init_device()  # Re-read features
    return ret


@expect(proto.Success, field="message")
def set_u2f_counter(client, u2f_counter):
    ret = client.call(proto.SetU2FCounter(u2f_counter=u2f_counter))
    return ret


@expect(proto.Success, field="message")
def wipe(client):
    ret = client.call(proto.WipeDevice())
    client.init_device()
    return ret


@expect(proto.Success, field="message")
def recover(client, word_count, passphrase_protection, pin_protection, label, language, type=proto.RecoveryDeviceType.ScrambledWords, expand=False, dry_run=False):
    if client.features.initialized and not dry_run:
        raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

    if word_count not in (12, 18, 24):
        raise ValueError("Invalid word count. Use 12/18/24")

    client.recovery_matrix_first_pass = True

    client.expand = expand
    if client.expand:
        # optimization to load the wordlist once, instead of for each recovery word
        client.mnemonic_wordlist = Mnemonic('english')

    res = client.call(proto.RecoveryDevice(
        word_count=int(word_count),
        passphrase_protection=bool(passphrase_protection),
        pin_protection=bool(pin_protection),
        label=label,
        language=language,
        enforce_wordlist=True,
        type=type,
        dry_run=dry_run))

    client.init_device()
    return res


@expect(proto.Success, field="message")
@session
def reset(client, display_random, strength, passphrase_protection, pin_protection, label, language, u2f_counter=0, skip_backup=False):
    if client.features.initialized:
        raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

    # Begin with device reset workflow
    msg = proto.ResetDevice(display_random=display_random,
                            strength=strength,
                            passphrase_protection=bool(passphrase_protection),
                            pin_protection=bool(pin_protection),
                            language=language,
                            label=label,
                            u2f_counter=u2f_counter,
                            skip_backup=bool(skip_backup))

    resp = client.call(msg)
    if not isinstance(resp, proto.EntropyRequest):
        raise RuntimeError("Invalid response, expected EntropyRequest")

    external_entropy = os.urandom(32)
    # LOG.debug("Computer generated entropy: " + binascii.hexlify(external_entropy).decode())
    ret = client.call(proto.EntropyAck(entropy=external_entropy))
    client.init_device()
    return ret


@expect(proto.Success, field="message")
def backup(client):
    ret = client.call(proto.BackupDevice())
    return ret


@expect(proto.Success, field="message")
def load_device_by_mnemonic(client, mnemonic, pin, passphrase_protection, label, language='english', skip_checksum=False, expand=False):
    # Convert mnemonic to UTF8 NKFD
    mnemonic = Mnemonic.normalize_string(mnemonic)

    # Convert mnemonic to ASCII stream
    mnemonic = mnemonic.encode('utf-8')

    m = Mnemonic('english')

    if expand:
        mnemonic = m.expand(mnemonic)

    if not skip_checksum and not m.check(mnemonic):
        raise ValueError("Invalid mnemonic checksum")

    if client.features.initialized:
        raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

    resp = client.call(proto.LoadDevice(mnemonic=mnemonic, pin=pin,
                                        passphrase_protection=passphrase_protection,
                                        language=language,
                                        label=label,
                                        skip_checksum=skip_checksum))
    client.init_device()
    return resp


@expect(proto.Success, field="message")
def load_device_by_xprv(client, xprv, pin, passphrase_protection, label, language):
    if client.features.initialized:
        raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

    if xprv[0:4] not in ('xprv', 'tprv'):
        raise ValueError("Unknown type of xprv")

    if not 100 < len(xprv) < 112:  # yes this is correct in Python
        raise ValueError("Invalid length of xprv")

    node = proto.HDNodeType()
    data = binascii.hexlify(tools.b58decode(xprv, None))

    if data[90:92] != b'00':
        raise ValueError("Contain invalid private key")

    checksum = binascii.hexlify(tools.btc_hash(binascii.unhexlify(data[:156]))[:4])
    if checksum != data[156:]:
        raise ValueError("Checksum doesn't match")

    # version 0488ade4
    # depth 00
    # fingerprint 00000000
    # child_num 00000000
    # chaincode 873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508
    # privkey   00e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35
    # checksum e77e9d71

    node.depth = int(data[8:10], 16)
    node.fingerprint = int(data[10:18], 16)
    node.child_num = int(data[18:26], 16)
    node.chain_code = binascii.unhexlify(data[26:90])
    node.private_key = binascii.unhexlify(data[92:156])  # skip 0x00 indicating privkey

    resp = client.call(proto.LoadDevice(node=node,
                                        pin=pin,
                                        passphrase_protection=passphrase_protection,
                                        language=language,
                                        label=label))
    client.init_device()
    return resp


@expect(proto.Success, field="message")
def self_test(client):
    if client.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    return client.call(proto.SelfTest(payload=b'\x00\xFF\x55\xAA\x66\x99\x33\xCCABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\x00\xFF\x55\xAA\x66\x99\x33\xCC'))
