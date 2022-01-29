# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import json
from decimal import Decimal

from trezorlib import btc


# https://btc1.trezor.io/api/tx-specific/f5e735549daeb480d4348f2574b8967a4f149715edb220a742d8bb654d668348
TX_JSON_BIG = """
{
  "txid": "f5e735549daeb480d4348f2574b8967a4f149715edb220a742d8bb654d668348",
  "hash": "6cc9b72db1440ce2de78a46c1fe6f8979807eddb14ab6e532947c83937520569",
  "version": 2,
  "size": 931,
  "vsize": 529,
  "weight": 2113,
  "locktime": 620109,
  "vin": [
    {
      "txid": "a1291df0b8ef7cce44d5ae7f31e50ef85aedc129cfcb5e1a82ab5ac917c39733",
      "vout": 4,
      "scriptSig": {
        "asm": "001476e4db8a1d5c4c238775df63899f71dfda0197f4",
        "hex": "16001476e4db8a1d5c4c238775df63899f71dfda0197f4"
      },
      "txinwitness": [
        "30440220395aeb2327c8860f42c671dec6807c962f73a67db8f7106691bc1d02095f075e0220471812cf1830b769246ddbeb9d99d034b2119415291fa6fe8fb33d6f39858e4f01",
        "030c9daf8f58ccd1733de05574964eaf2810c5d6e2375dee0f49603151cf589e1d"
      ],
      "sequence": 4294967294
    },
    {
      "txid": "05a049179ee576e3c3d6ae71011e08066aa6a588af31d6d61332215c65e8eebd",
      "vout": 3,
      "scriptSig": {
        "asm": "0014004bebeb0b79c94754f5458a3ed8a293370df7fb",
        "hex": "160014004bebeb0b79c94754f5458a3ed8a293370df7fb"
      },
      "txinwitness": [
        "3044022029283ef96d3def47843716e64606604044125c1642732102533076c9b1958ce9022071d0fb9504fe47b215ebc320113ec77936f143659b9fcdf4f5c9e872fdfec9b601",
        "025389a45a00c6d57e6a61258e95d6f7413f2c23274f7f82a7164ec040f7bf73ab"
      ],
      "sequence": 4294967294
    },
    {
      "txid": "05a049179ee576e3c3d6ae71011e08066aa6a588af31d6d61332215c65e8eebd",
      "vout": 7,
      "scriptSig": {
        "asm": "0014d07cba9645f2814af5ed30aef767234ddda9ac13",
        "hex": "160014d07cba9645f2814af5ed30aef767234ddda9ac13"
      },
      "txinwitness": [
        "3044022068dc9e81b98036014adfc6d6235a66caaf12a9060243fb768abd161024275443022075e89fa03d6a5f5d21ce778e97de521c5bb51e6eaa0f9eccd92f487d22410ed801",
        "03d79e1063b8b5bd169ac5b2791b57e19f43160c7e553baa0b243cb666d30c19f4"
      ],
      "sequence": 4294967294
    },
    {
      "txid": "05a049179ee576e3c3d6ae71011e08066aa6a588af31d6d61332215c65e8eebd",
      "vout": 8,
      "scriptSig": {
        "asm": "0014ae471e13840e2b5dcdec9c4a9b54ba11fe7b665c",
        "hex": "160014ae471e13840e2b5dcdec9c4a9b54ba11fe7b665c"
      },
      "txinwitness": [
        "304402206d2ddc00b36896e6cbd50dfae25e8ae81f0fbf902325f34a2c831a04503cd58202202fe96b43daa1281c96a5c9507a01956cfb0d4b94b5406a94d6de96c3b82bdf7d01",
        "03a261fa4d379512d74d8eb14a7f797f694bbbda5ff3dcc05a08a55be7dd2b2e00"
      ],
      "sequence": 4294967294
    },
    {
      "txid": "dc27d76fa566e14e97709c59e0b1c5e1b7628c96f6dc8cbca5816a381a4234cb",
      "vout": 14,
      "scriptSig": {
        "asm": "0014995cd732c74a3446f1ad35bafbd8d6f79828ef04",
        "hex": "160014995cd732c74a3446f1ad35bafbd8d6f79828ef04"
      },
      "txinwitness": [
        "304402202659160053eee86b6f27be4e82cb7f390597e923ae0f9d17b8e3864f6ae17a2602200468b59da0b6c1b1edd848dbbba802be74228b43dda9de5e9ad36b1e6558950101",
        "0393c79d23ae89f461f039b895dfd6f365ef5cc89f1a3ef030382f80c2cbd84caa"
      ],
      "sequence": 4294967294
    }
  ],
  "vout": [
    {
      "value": 0.42651353,
      "n": 0,
      "scriptPubKey": {
        "asm": "OP_HASH160 3a530afe02afe8dd7bc1b7d731550eec4f442666 OP_EQUAL",
        "hex": "a9143a530afe02afe8dd7bc1b7d731550eec4f44266687",
        "reqSigs": 1,
        "type": "scripthash",
        "addresses": [
          "371QbbRvKoqgSxfUm9Ly6qHoBJzuaBHDCT"
        ]
      }
    },
    {
      "value": 22.63125,
      "n": 1,
      "scriptPubKey": {
        "asm": "OP_HASH160 01a331e12b1d6789c8109d86f27e6fdd6105b194 OP_EQUAL",
        "hex": "a91401a331e12b1d6789c8109d86f27e6fdd6105b19487",
        "reqSigs": 1,
        "type": "scripthash",
        "addresses": [
          "31qg6iFQUxSdxyTk1RJyKmVPNvz7XV5s5c"
        ]
      }
    }
  ],
  "hex": "020000000001053397c317c95aab821a5ecbcf29c1ed5af80ee5317faed544ce7cefb8f01d29a1040000001716001476e4db8a1d5c4c238775df63899f71dfda0197f4feffffffbdeee8655c213213d6d631af88a5a66a06081e0171aed6c3e376e59e1749a0050300000017160014004bebeb0b79c94754f5458a3ed8a293370df7fbfeffffffbdeee8655c213213d6d631af88a5a66a06081e0171aed6c3e376e59e1749a0050700000017160014d07cba9645f2814af5ed30aef767234ddda9ac13feffffffbdeee8655c213213d6d631af88a5a66a06081e0171aed6c3e376e59e1749a0050800000017160014ae471e13840e2b5dcdec9c4a9b54ba11fe7b665cfeffffffcb34421a386a81a5bc8cdcf6968c62b7e1c5b1e0599c70974ee166a56fd727dc0e00000017160014995cd732c74a3446f1ad35bafbd8d6f79828ef04feffffff02d9ce8a020000000017a9143a530afe02afe8dd7bc1b7d731550eec4f44266687088ce4860000000017a91401a331e12b1d6789c8109d86f27e6fdd6105b19487024730440220395aeb2327c8860f42c671dec6807c962f73a67db8f7106691bc1d02095f075e0220471812cf1830b769246ddbeb9d99d034b2119415291fa6fe8fb33d6f39858e4f0121030c9daf8f58ccd1733de05574964eaf2810c5d6e2375dee0f49603151cf589e1d02473044022029283ef96d3def47843716e64606604044125c1642732102533076c9b1958ce9022071d0fb9504fe47b215ebc320113ec77936f143659b9fcdf4f5c9e872fdfec9b60121025389a45a00c6d57e6a61258e95d6f7413f2c23274f7f82a7164ec040f7bf73ab02473044022068dc9e81b98036014adfc6d6235a66caaf12a9060243fb768abd161024275443022075e89fa03d6a5f5d21ce778e97de521c5bb51e6eaa0f9eccd92f487d22410ed8012103d79e1063b8b5bd169ac5b2791b57e19f43160c7e553baa0b243cb666d30c19f40247304402206d2ddc00b36896e6cbd50dfae25e8ae81f0fbf902325f34a2c831a04503cd58202202fe96b43daa1281c96a5c9507a01956cfb0d4b94b5406a94d6de96c3b82bdf7d012103a261fa4d379512d74d8eb14a7f797f694bbbda5ff3dcc05a08a55be7dd2b2e000247304402202659160053eee86b6f27be4e82cb7f390597e923ae0f9d17b8e3864f6ae17a2602200468b59da0b6c1b1edd848dbbba802be74228b43dda9de5e9ad36b1e6558950101210393c79d23ae89f461f039b895dfd6f365ef5cc89f1a3ef030382f80c2cbd84caa4d760900",
  "blockhash": "000000000000000000031d097eeb2fe33a4c6fbf2dcebcdbd49051a4d7e37390",
  "confirmations": 13,
  "time": 1583317141,
  "blocktime": 1583317141
}
"""

# https://btc1.trezor.io/api/tx-specific/317f8a6e343384bd7d1a06ca25407d991ad3fc956e4ebedc66e1ec3b2ed9ccc6
TX_JSON_COINBASE = """
{
  "txid": "317f8a6e343384bd7d1a06ca25407d991ad3fc956e4ebedc66e1ec3b2ed9ccc6",
  "hash": "a55b6b60791108e5bd6b014a3527be285867744d58baba4ca7bcc9ea713533a3",
  "version": 2,
  "size": 342,
  "vsize": 315,
  "weight": 1260,
  "locktime": 0,
  "vin": [
    {
      "coinbase": "03737609040a995f5e626a30332f4254432e434f4d2ffabe6d6db1d4bc579e23d79b7a494282f8189a5e99567ce755a1dd25e1964fcda592ac21080000007296cd102f0461a3aee6070000000000",
      "sequence": 4294967295
    }
  ],
  "vout": [
    {
      "value": 12.56294353,
      "n": 0,
      "scriptPubKey": {
        "asm": "0 97cfc76442fe717f2a3f0cc9c175f7561b661997",
        "hex": "001497cfc76442fe717f2a3f0cc9c175f7561b661997",
        "reqSigs": 1,
        "type": "witness_v0_keyhash",
        "addresses": [
          "bc1qjl8uwezzlech723lpnyuza0h2cdkvxvh54v3dn"
        ]
      }
    },
    {
      "value": 0,
      "n": 1,
      "scriptPubKey": {
        "asm": "OP_RETURN aa21a9edcc94907af04544c15ac0bd15520012b98edbb04c604b20f43306382831850da9",
        "hex": "6a24aa21a9edcc94907af04544c15ac0bd15520012b98edbb04c604b20f43306382831850da9",
        "type": "nulldata"
      }
    },
    {
      "value": 0,
      "n": 2,
      "scriptPubKey": {
        "asm": "OP_RETURN 52534b424c4f434b3a738dd5336a7d4869904cb27f7d5b5afd534c360b6d0b9c45e2fafc2a00210406",
        "hex": "6a2952534b424c4f434b3a738dd5336a7d4869904cb27f7d5b5afd534c360b6d0b9c45e2fafc2a00210406",
        "type": "nulldata"
      }
    },
    {
      "value": 0,
      "n": 3,
      "scriptPubKey": {
        "asm": "OP_RETURN b9e11b6df9e2d9e640ea4dc449b522003347a2c0aa421b4128f4644560c508e78a433684",
        "hex": "6a24b9e11b6df9e2d9e640ea4dc449b522003347a2c0aa421b4128f4644560c508e78a433684",
        "type": "nulldata"
      }
    }
  ],
  "hex": "020000000001010000000000000000000000000000000000000000000000000000000000000000ffffffff4e03737609040a995f5e626a30332f4254432e434f4d2ffabe6d6db1d4bc579e23d79b7a494282f8189a5e99567ce755a1dd25e1964fcda592ac21080000007296cd102f0461a3aee6070000000000ffffffff04d187e14a0000000016001497cfc76442fe717f2a3f0cc9c175f7561b6619970000000000000000266a24aa21a9edcc94907af04544c15ac0bd15520012b98edbb04c604b20f43306382831850da900000000000000002b6a2952534b424c4f434b3a738dd5336a7d4869904cb27f7d5b5afd534c360b6d0b9c45e2fafc2a002104060000000000000000266a24b9e11b6df9e2d9e640ea4dc449b522003347a2c0aa421b4128f4644560c508e78a4336840120000000000000000000000000000000000000000000000000000000000000000000000000",
  "blockhash": "00000000000000000008f5eb1ce2bac08ecd50041fa162e45470dda519fc159d",
  "confirmations": 1,
  "time": 1583323402,
  "blocktime": 1583323402
}
"""


def test_from_json():
    tx_dict = json.loads(TX_JSON_BIG, parse_float=Decimal)
    tx = btc.from_json(tx_dict)

    assert tx.version == 2
    assert tx.lock_time == 620109
    assert len(tx.inputs) == 5
    assert len(tx.bin_outputs) == 2
    assert sum(o.amount for o in tx.bin_outputs) == 2305776353

    for v, i in zip(tx_dict["vin"], tx.inputs):
        assert i.prev_hash.hex() == v["txid"]
        assert i.prev_index == v["vout"]
        assert i.script_sig.hex() == v["scriptSig"]["hex"]
        assert i.sequence == v["sequence"]

    for v, o in zip(tx_dict["vout"], tx.bin_outputs):
        assert o.amount == int(Decimal(v["value"]) * (10 ** 8))
        assert o.script_pubkey.hex() == v["scriptPubKey"]["hex"]


def test_coinbase_from_json():
    tx_dict = json.loads(TX_JSON_COINBASE, parse_float=Decimal)
    tx = btc.from_json(tx_dict)

    assert tx.version == 2
    assert tx.lock_time == 0
    assert len(tx.inputs) == 1
    assert len(tx.bin_outputs) == 4
    assert sum(o.amount for o in tx.bin_outputs) == 1256294353

    coinbase = tx.inputs[0]
    assert coinbase.prev_hash == b"\x00" * 32
    assert coinbase.prev_index == 2 ** 32 - 1
    assert coinbase.script_sig.hex() == tx_dict["vin"][0]["coinbase"]
