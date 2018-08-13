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

import os
import warnings

from mnemonic import Mnemonic

from . import messages as proto
from .tools import expect, session
from .transport import enumerate_devices, get_transport


class TrezorDevice:
    """
    This class is deprecated. (There is no reason for it to exist in the first
    place, it is nothing but a collection of two functions.)
    Instead, please use functions from the ``trezorlib.transport`` module.
    """

    @classmethod
    def enumerate(cls):
        warnings.warn("TrezorDevice is deprecated.", DeprecationWarning)
        return enumerate_devices()

    @classmethod
    def find_by_path(cls, path):
        warnings.warn("TrezorDevice is deprecated.", DeprecationWarning)
        return get_transport(path, prefix_search=False)


@expect(proto.Success, field="message")
def apply_settings(
    client,
    label=None,
    language=None,
    use_passphrase=None,
    homescreen=None,
    passphrase_source=None,
    auto_lock_delay_ms=None,
):
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
def recover(
    client,
    word_count,
    passphrase_protection,
    pin_protection,
    label,
    language,
    type=proto.RecoveryDeviceType.ScrambledWords,
    expand=False,
    dry_run=False,
):
    if client.features.initialized and not dry_run:
        raise RuntimeError(
            "Device is initialized already. Call wipe_device() and try again."
        )

    if word_count not in (12, 18, 24):
        raise ValueError("Invalid word count. Use 12/18/24")

    client.recovery_matrix_first_pass = True

    client.expand = expand
    if client.expand:
        # optimization to load the wordlist once, instead of for each recovery word
        client.mnemonic_wordlist = Mnemonic("english")

    res = client.call(
        proto.RecoveryDevice(
            word_count=int(word_count),
            passphrase_protection=bool(passphrase_protection),
            pin_protection=bool(pin_protection),
            label=label,
            language=language,
            enforce_wordlist=True,
            type=type,
            dry_run=dry_run,
        )
    )

    client.init_device()
    return res


@expect(proto.Success, field="message")
@session
def reset(
    client,
    display_random,
    strength,
    passphrase_protection,
    pin_protection,
    label,
    language,
    u2f_counter=0,
    skip_backup=False,
):
    if client.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call wipe_device() and try again."
        )

    # Begin with device reset workflow
    msg = proto.ResetDevice(
        display_random=display_random,
        strength=strength,
        passphrase_protection=bool(passphrase_protection),
        pin_protection=bool(pin_protection),
        language=language,
        label=label,
        u2f_counter=u2f_counter,
        skip_backup=bool(skip_backup),
    )

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
