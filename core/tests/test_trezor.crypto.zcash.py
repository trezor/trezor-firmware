from common import *

from trezor.crypto import zcash

TESTVECTORS_KEY_COMPONENTS = [
    {
        "sk": unhexlify("5d7a8f739a2d9e945b0ce152a8049e294c4d6e66b164939daffa2ef6ee692148"),
        "ask": unhexlify("8eb8c401c287a6c13a2c345ad82172d86be4a8853525db602d14f630f4e61c17"),
        "ak": unhexlify("740bbe5d0580b2cad430180d02cc128b9a140d5e07c151721dc16d25d4e20f15"),
        "nk": unhexlify("9f2f826738945ad01f47f70db0c367c246c20c61ff5583948c39dea968fefd1b"),
        "rivk": unhexlify("021ccf89604f5f7cc6e034b32d338908b819fbe325fee6458b56b4ca71a7e43d"),
        "ivk": unhexlify("85c8b5cd1ac3ec3ad7092132f97f0178b075c81a139fd460bbe0dfcd75514724"),
        "ovk": unhexlify("bcc7065e59910b35993f59505be209b14bf02488750bbc8b1acdcf108c362004"),
        "dk": unhexlify("31d6a685be570f9faf3ca8b052e887840b2c9f8d67224ca82aefb9e2ee5bedaf"),
        "default_d": unhexlify("8ff3386971cb64b8e77899"),
        "default_pk_d": unhexlify("08dd8ebd7de92a68e586a34db8fea999efd2016fae76750afae7ee941646bcb9"),
        "note_v": 15643327852135767324,
        "note_rho": unhexlify("2cb5b406ed8985e18130ab33362697b0e4e4c763ccb8f676495c222f7fba1e31"),
        "note_rseed": unhexlify("defa3d5a57efc2e1e9b01a035587d5fb1a38e01d94903d3c3e0ad3360c1d3710"),
        "note_cmx": unhexlify("4502e339901e397717839167cbb4037e0ecf6813b51c81fe085a7b782f124228"),
        "note_nf": unhexlify("1b32edbbe4d18f28876de262518ad31122701f8c0a52e98047a337876e7eea19"),
    },
    {
        "sk": unhexlify("acd20b183e31d49f25c9a138f49b1a537edcf04be34a9851a7af9db6990ed83d"),
        "ask": unhexlify("41d47cc96313b4821dfc129651c3137f44d9cad16b3dc08133c3d2df0d0c5320"),
        "ak": unhexlify("6de1349830d66d7b97fe231fc7b02ad64323629cfed1e3aa24ef052f56e4002a"),
        "nk": unhexlify("a8b73d979b6eaada8924bcbdc63a9ef4e87346f230aba6bbe1e2b43c5bea6b22"),
        "rivk": unhexlify("dacb2f2a9ced363171821aaf5d8cd902bc5e3a5a41fb51ae61a9f02dc89d1d12"),
        "ivk": unhexlify("563a6db60c74c2db08492cbae3bb083f1aeabffbcf42551d0ac64f2690536711"),
        "ovk": unhexlify("71cd30640fdb63f8d1305029e940e53fd5ec04a8ccad419578c242fec05b9af7"),
        "dk": unhexlify("9d9bd44525e7ae06b03ae6d4aecde6ae0927a7c667d5d9f8176b544695dfec11"),
        "default_d": unhexlify("7807ca650858814d5022a8"),
        "default_pk_d": unhexlify("3d3de4d52c77fd0b630a40dc38212487b2ff6eeef56d8c6a6163e854aff04189"),
        "note_v": 4481649511318637270,
        "note_rho": unhexlify("a51b0052ad8084a8b9da948d320dadd64f5431e61ddf658d24ae67c22c8d1309"),
        "note_rseed": unhexlify("131fc00fe7f235734276d38d47f1e191e00c7a1d48af046827591e9733a97fa6"),
        "note_cmx": unhexlify("c7ad794c563e32cad47d47dcda7884692848dce29ba4febd93202b7305f90300"),
        "note_nf": unhexlify("2cf067bc21d66320e51b9fbdc8ae031c2c96373db43b7b1a45056c00c65d4320"),
    },
    {
        "sk": unhexlify("b679f3dc601d008285edcbdae69ce8fc1be4aac00ff2711ebd931de518856878"),
        "ask": unhexlify("ce8b65a7236511b2eaf19f72a3d6db7d062b66f516307d198706e5f6928e1615"),
        "ak": unhexlify("efa5f1debeead0940a619ce0017bedb426657b2d07406664d895312ea1c3b334"),
        "nk": unhexlify("04514ea048b94363dea7cb3be8d62582ac52922e0865f662743b05eae8715f17"),
        "rivk": unhexlify("2a328f994f6e5ad29ca811ed344968ea2cfc3fd231030e37bbd56db42640231c"),
        "ivk": unhexlify("609ecbc3d8cee3be2b2a2362951f58b74482adfaeee1c40f94030440f558aa30"),
        "ovk": unhexlify("dfd30f62aa319c6f53e24c1f48c1de961b9001cb988b80b3eda244fcfeb25f83"),
        "dk": unhexlify("236bc3f3d02f960280eedede108d3685049f239aa67c48558f7c01d3fd469ecd"),
        "default_d": unhexlify("6424f71a3ad197426498f4"),
        "default_pk_d": unhexlify("eccb6a5780204237987232bc098f89acc475c3f74bd69e2f35d44736f48f3c14"),
        "note_v": 14496603531126387959,
        "note_rho": unhexlify("32b4f473f468a008e72389fc03880d780cb07fcfaabe3f1a84b27db59a4a153d"),
        "note_rseed": unhexlify("882d2b2103596555ed9494c6ac893c49723833ec8926c1039586a7afcf4a0d9c"),
        "note_cmx": unhexlify("03ce20cea194b7559a8a90471d28a3c053c3720ad49f40d27c2dcce335005616"),
        "note_nf": unhexlify("16fa2c3497fc09ad90dd349202a24b69892dc80629b2d1bfebaf41708f0fb10c"),
    },
    {
        "sk": unhexlify("731e985d99589c8bb838e8aaf745533ed9e8ae3a1cd074a51a20da8aba18d1db"),
        "ask": unhexlify("426a7844f305b9d4e07ea52a39001c9b336cfc0d6fa15ef3d11c3d7b74f08c2d"),
        "ak": unhexlify("b1e0acbc69bf377b85abf0f5a10be72c3b640006ff08505280e4f00fadf76328"),
        "nk": unhexlify("cf36ad6a066cd213e1d767ab071dc1167885c4168bc2e2175448563ad13f333d"),
        "rivk": unhexlify("c41bbad35105a80314b79624b675241220b331f12592617bdb705bfcce72ae38"),
        "ivk": unhexlify("f79fe802e4d24307a6aaf85d19f5e0833740bae598dc7c880ac609631de15819"),
        "ovk": unhexlify("f96366bc6eabd232549ebb43b4ed6fd81d330373c5b566904e9af11a6bab8d77"),
        "dk": unhexlify("803e348573022bf8932f23ee7a325ea283879c652412b8606be3198c4b782c47"),
        "default_d": unhexlify("db8c305524bc0deaa85d97"),
        "default_pk_d": unhexlify("04ea8c1320ffbbadfe96f0c6ff16b607111b5583bfb6f1ea45275ef2aa2d879b"),
        "note_v": 6792346249443327211,
        "note_rho": unhexlify("4b192232ecb9f0c02411e52596bc5e90457e745939ffedbd12863ce71a02af11"),
        "note_rseed": unhexlify("7d417adb3d15cc54dcb1fce467500c6b8fb86b12b56da9c382857deecc40a98d"),
        "note_cmx": unhexlify("a9b11baf3034b65c6424841bfe023f8eda1313c30aa27de92e21a108316e8219"),
        "note_nf": unhexlify("72d6308960351f7b26fa64603fe4dfd867bd5eb367ba2b7ca491c923c0ead222"),
    },
    {
        "sk": unhexlify("5f2935395ee4762dd21afdbb5d47fa9a6dd984d567db2857b927b7fae2db5871"),
        "ask": unhexlify("118073285164e6557358fbc41a8135cb062f8676cb61f9aa52d19a09fac55802"),
        "ak": unhexlify("0d262de3609433fe5b7c862bc48ef56d832009f7242e1f7c770a12241dfa2807"),
        "nk": unhexlify("51baf333cff1f2d0c7e3cff4d301299dc1efe98300314a541938029b45cc1521"),
        "rivk": unhexlify("228feb79219873c7a7606e52973c85f460465a6059083919ed73eb805c118301"),
        "ivk": unhexlify("76f49cf8a3192185616a9a0da0c76ec2c2756159bce186a1862b6e6e59442d11"),
        "ovk": unhexlify("eb72b6c31e837fd837aacb61fabace75a19dd9dd5b4b3a3ee723c14da77b4be8"),
        "dk": unhexlify("ee19f8ddd9da0634245143c4b43afc7d78c549c82054a9d84007b56217dbfdd6"),
        "default_d": unhexlify("aae36e094de07bc16f898e"),
        "default_pk_d": unhexlify("b6533dcbfff0f6c1ceefa84799bda3de7334326ccd65f7ce92ff3d9e6e1f140b"),
        "note_v": 4079549063511228677,
        "note_rho": unhexlify("2670dc82d39026c6cb4cd4b0f7f5aa2a4f5a5341ec5dd715406f2fdd2afa733f"),
        "note_rseed": unhexlify("5f641c8c21862a1bafce2609d9eecfa158cfb5cd79f88008e315dc7d8388e76c"),
        "note_cmx": unhexlify("0ffbca1d5921fa0a8c5116ae137e37f2c118d52125628d8a3f412ce0e6530e04"),
        "note_nf": unhexlify("e62b8ed83540146cd23cac74eed7d773d80224a5aa30d68e35572ee883d1b704"),
    },
    {
        "sk": unhexlify("1782fd2795d18a763624c25fa959cc97489ce75745824b77868c53239cfbdf73"),
        "ask": unhexlify("f6ef328d24761d6d3ccd25d47196e8109c038fe17c59a7f05b98d66bebc64124"),
        "ak": unhexlify("d11787ca582f948e450718b36998df28bb0f1021ea843f867f8a170f5c33901f"),
        "nk": unhexlify("9e997d9d269787268e092a7c85417da530ea42fac668a749af55dfb71cdbbe09"),
        "rivk": unhexlify("136c6fe2e2b79c5156db5047d8d5e795dfc0bdc0880853a44adb7392c02f941b"),
        "ivk": unhexlify("028b640564b24905de9292ba5b9810addd86bed0fb3b2d6b37f26dd238a7db13"),
        "ovk": unhexlify("98d6a4bf6801d8ba0d0b67ea7b805207abc0348fc562005a59a27a8a46fa6add"),
        "dk": unhexlify("d0baef6012d308efbb769a99cca2928cede8db277645a777eaf1722cd08450b3"),
        "default_d": unhexlify("cc7ce734b075a01b92aaca"),
        "default_pk_d": unhexlify("3da5273a5667c766b8231206180f158ac02af3f06ecca6ec7c38c75d33600320"),
        "note_v": 5706402952489856202,
        "note_rho": unhexlify("a1df0e5b87b5bece477a709649e950060591394812951e1fe3895b8cc3d14d2c"),
        "note_rseed": unhexlify("f6556df6ed4b4ddd3d9a69f53357d7767f4f5ccbdbc596631277f8fecd08cb05"),
        "note_cmx": unhexlify("63cee37e3c7b4e6cc939a2e63ada74f85ea48ba07a4f92ccbd34faa42dfd4916"),
        "note_nf": unhexlify("4c99bfa8c20dba59bb7347da16c43b73c88794c9ebcd0dd2b25ee7bb836f9520"),
    },
    {
        "sk": unhexlify("6b95e3025b9792fff7f244fc716269b926d62e9596fa825c6bf21aff9e68625a"),
        "ask": unhexlify("757d158d07356b3bc2c9e51c558a9b316bddbc360b8beb6e2ae3b0618f062d2e"),
        "ak": unhexlify("449a90d2e8d1a037642a97096c916543462a137ffea37baf41ef286bb732be2c"),
        "nk": unhexlify("fd3164c632bec94ce9fb2f302263b884abb9c10e55e448647f6798495c9d083f"),
        "rivk": unhexlify("c0b36b56070fff2fdf38eba11a7424957195014cba43a56bd1b1658e66a39d00"),
        "ivk": unhexlify("976a8788191b87e4c13f2c6d23b4f3595e0228e245e96eef1d24b293296a191c"),
        "ovk": unhexlify("1ed0eda5a4086131261a2ed4429261e4276a26d42859fabda31aa96709874371"),
        "dk": unhexlify("5e5b60c05b53d0bcd2da46a1312912515cc7cf2d974c117c8ddea9fab620c668"),
        "default_d": unhexlify("99af6bf3f475bde889aaca"),
        "default_pk_d": unhexlify("acdcd348ca45ee583278303846ca078459d5be5c5dcf347e3b9a34cba124b4a3"),
        "note_v": 2558469029534639129,
        "note_rho": unhexlify("722db041a3ef66fa483afd3c2e19e59444a64add6df1d963f5dd5b5010d3d025"),
        "note_rseed": unhexlify("f0287c4cf19c75f33d51ddddba5d657b43ee8da645443814cc7329f3e9b4e54c"),
        "note_cmx": unhexlify("1e619e46bb62b61d4e1cf3622ea70a908de7f076ecf87f541e0b7b48ad4a2601"),
        "note_nf": unhexlify("3b948db21608e9acb22a5417b98c0dedd527a96487814e6420cbff6e4eee4e31"),
    },
    {
        "sk": unhexlify("236c29af3923101756d9fa4bd0f7d2ddaacb6b0f86a2658e0a07a05ac5b95005"),
        "ask": unhexlify("b4ded90d62117f18f3dd5fdb22238a35ca37c40feec845ce5fc27fe8bca5ef0f"),
        "ak": unhexlify("4efd5a2ef1ffa99a0ff62b767d44b3651ffa1c696915ac00a25ea3ac7dff9901"),
        "nk": unhexlify("02ab995ce98f63025fb62428a0fbf52f2522e6a27261078a9f4d6a36a1c05d39"),
        "rivk": unhexlify("d9840d0bd89520abbca7f10be6eba366f86ec3b78dbdf1ebfe20d99512af1515"),
        "ivk": unhexlify("58f5bb5c3231152529423b67fa432879112635cda0da2ec2419c6fe91ea48d24"),
        "ovk": unhexlify("78f5d348672e8d209c41b783f8ca14a77b3ea3e6004ca4e0c25aa44563981dcb"),
        "dk": unhexlify("5d7fe396bbfd2267aca711ab5b3e1f024f4911f3a181732f1322a1592f9e0ebe"),
        "default_d": unhexlify("2fbe4b4b1edff33123ce65"),
        "default_pk_d": unhexlify("eb2c6fee341eade07d7487997aa723697d05e62960df379c9e4a8d476dfac5bf"),
        "note_v": 15425828902564319772,
        "note_rho": unhexlify("736c23357c85f45791e1708029d9824d90704607f387a03e49bf983657443134"),
        "note_rseed": unhexlify("5a7877efaa8a08e73081ef8d62cb780ab6883a50a0d470190dfba10a857f8284"),
        "note_cmx": unhexlify("c8528f722cd3e47dc99e1e388056370815a9d037973d85cac7ea38b5a716fa3b"),
        "note_nf": unhexlify("acc2ed2c7e3b197e5cdb4a576357d5f135391626c7a825d10aa260ae0b958128"),
    },
    {
        "sk": unhexlify("2d3825b3d6da0573d316eb160dc0b716c48fbd467f75b780149ae8808f4e68f5"),
        "ask": unhexlify("2d6e973e1754d41787934c34558cfe993844199972d9a6348b7a3dadfcb6772a"),
        "ak": unhexlify("762159a414f574b539750f22c8863b02d25cc10c9071fc0219e97f9392d0670c"),
        "nk": unhexlify("2591edf7ef4cf2184c34be93fcf612915042f15ab5084b14e166795b09cea133"),
        "rivk": unhexlify("758fb250dd2950e5d2b2eed7ffcf94ae67cde125b95b479e2377813a85a03d2f"),
        "ivk": unhexlify("6ea4363cb2df62b10da1308a0b9679bd0f7495ffe7d4e2618f54df9b670c3316"),
        "ovk": unhexlify("a63cbcd31ba136d83b8f1e88efb60055ef6f98252ddbd75f625f44dcb6632c72"),
        "dk": unhexlify("02f07408f33e8712e4c9ec42de5604200109861724d33eb6368b70f65e0a1621"),
        "default_d": unhexlify("08df1d4b45c673a459ff58"),
        "default_pk_d": unhexlify("268cc24b38a62880b6ee3cbcb85a712fa686cffca6db2feec5f3c3566f84218f"),
        "note_v": 12606128263924155660,
        "note_rho": unhexlify("12f6b02fe806b94569cd4059f396bf29b99d0a40e5e1711ca944f72d436a102f"),
        "note_rseed": unhexlify("ca4b97693da0b086fe9d2e7162470d02e0f05d4bec9512bfb3f38327296efaa7"),
        "note_cmx": unhexlify("6a1195aa0536f60ecfaecbdf5374e494ea072a2b867b5f694340c96fc370a910"),
        "note_nf": unhexlify("b0f1602a2b1af2fc55f15950a6838385e5e39fecfd05ccec799b75c65c8da235"),
    },
    {
        "sk": unhexlify("4328b118c27402c70c3a90b49ad4bbc68e37c0aa7d9b3fe17799d73b841e7517"),
        "ask": unhexlify("28dc45f11544425c1bef8661da11155fdbb7e3bcfc0f0d49e6f131e7c09d352f"),
        "ak": unhexlify("0d211a9060fbaa664e41a734ad1d8d4b025f8cc160e1f4e95f0a853ebc416a2b"),
        "nk": unhexlify("3e88f2071fd9a2bb26cda2ea856aa0fb3a80a87d2fb6136fab85e36c5b38d824"),
        "rivk": unhexlify("2c373882c408cd5fd482a0c9816fc32203a10fbfce0e200ccfd9ee307c5e1224"),
        "ivk": unhexlify("bb9e20b2991c996da21e3ecd39fb7b3aa2babc6bde186f7dd8a875d10c51a430"),
        "ovk": unhexlify("9321838a2db7f168f0ce77c45b211ffbb9b365e85e6731d909700553de492b28"),
        "dk": unhexlify("3df583361b3338bb6815f85872e39f04df5008524884af0f8c559716fcb14958"),
        "default_d": unhexlify("4c4064c47a5ca6e75d4644"),
        "default_pk_d": unhexlify("f517174be258923278cf458908c0735649f1899db99c3ba9003f4ba30ab0d210"),
        "note_v": 625536973899669523,
        "note_rho": unhexlify("03fd69442eb7681ec2a05600054e92eed555028f21b6a155268a2dd6640a6930"),
        "note_rseed": unhexlify("1a52a38d4d9f9f957ae35af7167118141ce4c9be0a6a492fe79f1581a155fa3a"),
        "note_cmx": unhexlify("f70ebf0f5ee5da6c6cdeff8fec2f8eed65c88e6755daf114d554af1967a7f40a"),
        "note_nf": unhexlify("95649728465e682ac057ad876294d700c27feba2f750922f955185706261c30c"),
    },
]


TESTVECTORS_F4JUMBLE = [
    {
        "normal": unhexlify("5d7a8f739a2d9e945b0ce152a8049e294c4d6e66b164939daffa2ef6ee6921481cdd86b3cc4318d9614fc820905d042b"),
        "jumbled": unhexlify("0304d029141b995da5387c125970673504d6c764d91ea6c082123770c7139ccd88ee27368cd0c0921a0444c8e5858d22"),
    },
    {
        "normal": unhexlify("b1ef9ca3f24988c7b3534201cfb1cd8dbf69b8250c18ef41294ca97993db546c1fe01f7e9c8e36d6a5e29d4e30a73594bf5098421c69378af1e40f64e125946f"),
        "jumbled": unhexlify("5271fa3321f3adbcfb075196883d542b438ec6339176537daf859841fe6a56222bff76d1662b5509a9e1079e446eeedd2e683c31aae3ee1851d7954328526be1"),
    },
    {
        "normal": unhexlify("62c2fa7b2fecbcb64b6968912a6381ce3dc166d56a1d62f5a8d7551db5fd9313e8c7203d996af7d477083756d59af80d06a745f44ab023752cb5b406ed8985e18130ab33362697b0e4e4c763ccb8f676495c222f7fba1e31defa3d5a57efc2e1e9b01a035587d5fb1a38e01d94903d3c3e0ad3360c1d3710acd20b183e31d49f"),
        "jumbled": unhexlify("498cf1b1ba6f4577effe64151d67469adc30acc325e326207e7d78487085b4162669f82f02f9774c0cc26ae6e1a76f1e266c6a9a8a2f4ffe8d2d676b1ed71cc47195a3f19208998f7d8cdfc0b74d2a96364d733a62b4273c77d9828aa1fa061588a7c4c88dd3d3dde02239557acfaad35c55854f4541e1a1b3bc8c17076e7316"),
    },
    {
        "normal": unhexlify("25c9a138f49b1a537edcf04be34a9851a7af9db6990ed83dd64af3597c04323ea51b0052ad8084a8b9da948d320dadd64f5431e61ddf658d24ae67c22c8d1309131fc00fe7f235734276d38d47f1e191e00c7a1d48af046827591e9733a97fa6b679f3dc601d008285edcbdae69ce8fc1be4aac00ff2711ebd931de518856878f7"),
        "jumbled": unhexlify("7508a3a146714f229db91b543e240633ed57853f6451c9db6d64c6e86af1b88b28704f608582c53c51ce7d5b8548827a971d2b98d41b7f6258655902440cd66ee11e84dbfac7d2a43696fd0468810a3d9637c3fa58e7d2d341ef250fa09b9fb71a78a41d389370138a55ea58fcde779d714a04e0d30e61dc2d8be0da61cd684509"),
    },
    {
        "normal": unhexlify("3476f21a482ec9378365c8f7393c94e2885315eb4671098b79535e790fe53e29fef2b3766697ac32b4f473f468a008e72389fc03880d780cb07fcfaabe3f1a84b27db59a4a153d882d2b2103596555ed9494c6ac893c49723833ec8926c1039586a7afcf4a0d9c731e985d99589c8bb838e8aaf745533ed9e8ae3a1cd074a51a20da8aba18d1dbebbc862ded42435e92476930d069896cff30eb414f727b89e001afa2fb8dc3436d75a4a6f26572504b192232ecb9f0c02411e52596bc5e9045"),
        "jumbled": unhexlify("5139912fe8b95492c12731995a0f4478dbeb81ec36653a21bc80d673f3c6a0feef70b6c566f9d34bb726c098648382d105afb19b2b8486b73cbd47a17a0d2d1fd593b14bb9826c5d114b850c6f0cf3083a6f61e38e42713a37ef7997ebd2b376c8a410d797b3932e5a6e39e726b2894ce79604b4ae3c00acaea3be2c1dfe697fa644755102cf9ad78794d0594585494fe38ab56fa6ef3271a68a33481015adf3944c115311421a7dc3ce73ef2abf47e18a6aca7f9dd25a85ce8dbd6f1ad89c8d"),
    },
    {
        "normal": unhexlify("7e745939ffedbd12863ce71a02af117d417adb3d15cc54dcb1fce467500c6b8fb86b12b56da9c382857deecc40a98d5f2935395ee4762dd21afdbb5d47fa9a6dd984d567db2857b927b7fae2db587105415d4642789d38f50b8dbcc129cab3d17d19f3355bcf73cecb8cb8a5da01307152f13936a270572670dc82d39026c6cb4cd4b0f7f5aa2a4f5a5341ec5dd715406f2fdd2afa733f5f641c8c21862a1bafce2609d9eecfa158cfb5cd79f88008e315dc7d8388e76c1782fd2795d18a763624"),
        "jumbled": unhexlify("1a52585e652da6ea46994954905cb79f55fca58171a4d7f773a57d23ed9ddec0c745ef0f4588fa7b2b68d69cdd25e5eb0e08c20523a3957171f1730ab0636faee75da2dc9e89562f0653d4e9422179286ae8305f01371f47ab16eed692c3895ce2fd655e4b19651c35d83c81894f687055b581114440646508e39a49b0d5a99004560af7367cc2738344d4e797a995ed66df72228e3d3746674337104700144c73b6db27d238c9e1770662feb0957d5028b5086f3839aacf275022dd7e7e983b6d"),
    },
]

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCryptoZcash(unittest.TestCase):        
    def test_get_orchard_fvk(self):
        for kc in TESTVECTORS_KEY_COMPONENTS:
            fvk = zcash.get_orchard_fvk(kc["sk"])
            self.assertEqual(fvk[ 0:32], kc["ak"])
            self.assertEqual(fvk[32:64], kc["nk"])
            self.assertEqual(fvk[64:96], kc["rivk"])

    def test_get_orchard_ivk(self):
        for kc in TESTVECTORS_KEY_COMPONENTS:
            ivk = zcash.get_orchard_ivk(kc["sk"])[32:]
            self.assertEqual(ivk, kc["ivk"])  

    def test_get_orchard_address(self):
        for kc in TESTVECTORS_KEY_COMPONENTS:
            addr = zcash.get_orchard_address(kc["sk"], 0)
            self.assertEqual(addr[:11], kc["default_d"])
            self.assertEqual(addr[11:], kc["default_pk_d"])

    def test_f4jumble(self):
        for tv in TESTVECTORS_F4JUMBLE:
            message = bytearray(tv["normal"])
            zcash.f4jumble(message)
            self.assertEqual(message, tv["jumbled"])
            zcash.f4jumble_inv(message)
            self.assertEqual(message, tv["normal"])


if __name__ == '__main__':
    unittest.main()
