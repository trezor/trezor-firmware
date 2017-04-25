from trezor.messages.CoinType import CoinType

# the following list is generated using tools/coins-gen.py
# do not edit manually!
COINS = [
    CoinType(
        coin_name='Bitcoin',
        coin_shortcut='BTC',
        address_type=0,
        maxfee_kb=300000,
        address_type_p2sh=5,
        address_type_p2wpkh=6,
        address_type_p2wsh=10,
        signed_message_header='Bitcoin Signed Message:\n',
        xpub_magic=0x0488b21e,
        xprv_magic=0x0488ade4,
        bip44=0,
    ),
    CoinType(
        coin_name='Testnet',
        coin_shortcut='TEST',
        address_type=111,
        maxfee_kb=10000000,
        address_type_p2sh=196,
        address_type_p2wpkh=3,
        address_type_p2wsh=40,
        signed_message_header='Bitcoin Signed Message:\n',
        xpub_magic=0x043587cf,
        xprv_magic=0x04358394,
        bip44=1,
    ),
    CoinType(
        coin_name='Namecoin',
        coin_shortcut='NMC',
        address_type=52,
        maxfee_kb=10000000,
        address_type_p2sh=5,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Namecoin Signed Message:\n',
        xpub_magic=0x019da462,
        xprv_magic=0x019d9cfe,
        bip44=7,
    ),
    CoinType(
        coin_name='Litecoin',
        coin_shortcut='LTC',
        address_type=48,
        maxfee_kb=1000000,
        address_type_p2sh=5,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Litecoin Signed Message:\n',
        xpub_magic=0x019da462,
        xprv_magic=0x019d9cfe,
        bip44=2,
    ),
    CoinType(
        coin_name='Dogecoin',
        coin_shortcut='DOGE',
        address_type=30,
        maxfee_kb=1000000000,
        address_type_p2sh=22,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Dogecoin Signed Message:\n',
        xpub_magic=0x02facafd,
        xprv_magic=0x02fac398,
        bip44=3,
    ),
    CoinType(
        coin_name='Dash',
        coin_shortcut='DASH',
        address_type=76,
        maxfee_kb=100000,
        address_type_p2sh=16,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='DarkCoin Signed Message:\n',
        xpub_magic=0x02fe52cc,
        xprv_magic=0x02fe52f8,
        bip44=5,
    ),
    CoinType(
        coin_name='Zcash',
        coin_shortcut='ZEC',
        address_type=7352,
        maxfee_kb=1000000,
        address_type_p2sh=7357,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Zcash Signed Message:\n',
        xpub_magic=0x0488b21e,
        xprv_magic=0x0488ade4,
        bip44=133,
    ),
    CoinType(
        coin_name='Zcash Testnet',
        coin_shortcut='TAZ',
        address_type=7461,
        maxfee_kb=10000000,
        address_type_p2sh=7354,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Zcash Signed Message:\n',
        xpub_magic=0x043587cf,
        xprv_magic=0x04358394,
        bip44=1,
    ),
]


def by_shortcut(shortcut):
    for c in COINS:
        if c.coin_shortcut == shortcut:
            return c
    raise ValueError('Unknown coin shortcut "%s"' % shortcut)


def by_name(name):
    for c in COINS:
        if c.coin_name == name:
            return c
    raise ValueError('Unknown coin name "%s"' % name)


def by_address_type(version):
    for c in COINS:
        if c.address_type == version:
            return c
    raise ValueError('Unknown coin address type %d' % version)
