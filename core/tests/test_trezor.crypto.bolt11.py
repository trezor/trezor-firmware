from common import *

from trezor.crypto import bolt11

# from https://github.com/lightning/bolts/blob/master/11-payment-encoding.md#examples
# secret key = e126f68f7eafcc8b74f54d269fe206be715000f94dac067d1c04a8ca3b2db734
# public key = 03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad
VECTORS_BOLT11 = [
    ("lnbc1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdpl2pkx2ctnv5sxxmmwwd5kgetjypeh2ursdae8g6twvus8g6rfwvs8qun0dfjkxaq9qrsgq357wnc5r2ueh7ck6q93dj32dlqnls087fxdwk8qakdyafkq3yap9us6v52vjjsrvywa6rt52cm9r9zqt8r2t7mlcwspyetp5h2tztugp9lfyql",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=None,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="Please consider supporting this project",
        ),
    ),
    ("lnbc2500u1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdq5xysxxatsyp3k7enxv4jsxqzpu9qrsgquk0rl77nj30yxdy8j9vdx85fkpmdla2087ne0xh8nhedh8w27kyke0lp53ut353s06fv3qfegext0eh0ymjpf39tuven09sam30g4vgpfna3rh",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=2500 * 100 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="1 cup coffee",
        ),
    ),
    ("lnbc2500u1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdpquwpc4curk03c9wlrswe78q4eyqc7d8d0xqzpu9qrsgqhtjpauu9ur7fw2thcl4y9vfvh4m9wlfyz2gem29g5ghe2aak2pm3ps8fdhtceqsaagty2vph7utlgj48u0ged6a337aewvraedendscp573dxr",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=2500 * 100 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="ナンセンス 1杯",
        ),
    ),
    ("lnbc20m1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qrsgq7ea976txfraylvgzuxs8kgcw23ezlrszfnh8r6qtfpr6cxga50aj6txm9rxrydzd06dfeawfk6swupvz4erwnyutnjq7x39ymw6j38gp7ynn44",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=20 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description=None,
        ),
    ),
    ("lntb20m1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqfpp3x9et2e20v6pu37c5d9vax37wxq72un989qrsgqdj545axuxtnfemtpwkc45hx9d2ft7x04mt8q7y6t0k2dge9e7h8kpy9p34ytyslj3yu569aalz2xdk8xkd7ltxqld94u8h2esmsmacgpghe9k8",
        bolt11.Bolt11Invoice(
            network="tb",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=20 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description=None,
        ),
    ),
    ("lnbc20m1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqsfpp3qjmp7lwpagxun9pygexvgpjdc4jdj85fr9yq20q82gphp2nflc7jtzrcazrra7wwgzxqc8u7754cdlpfrmccae92qgzqvzq2ps8pqqqqqqpqqqqq9qqqvpeuqafqxu92d8lr6fvg0r5gv0heeeqgcrqlnm6jhphu9y00rrhy4grqszsvpcgpy9qqqqqqgqqqqq7qqzq9qrsgqdfjcdk6w3ak5pca9hwfwfh63zrrz06wwfya0ydlzpgzxkn5xagsqz7x9j4jwe7yj7vaf2k9lqsdk45kts2fd0fkr28am0u4w95tt2nsq76cqw0",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=20 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description=None,
        ),
    ),
    ("lnbc20m1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqfppj3a24vwu6r8ejrss3axul8rxldph2q7z99qrsgqz6qsgww34xlatfj6e3sngrwfy3ytkt29d2qttr8qz2mnedfqysuqypgqex4haa2h8fx3wnypranf3pdwyluftwe680jjcfp438u82xqphf75ym",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=20 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description=None,
        ),
    ),
    ("lnbc20m1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqfppqw508d6qejxtdg4y5r3zarvary0c5xw7k9qrsgqt29a0wturnys2hhxpner2e3plp6jyj8qx7548zr2z7ptgjjc7hljm98xhjym0dg52sdrvqamxdezkmqg4gdrvwwnf0kv2jdfnl4xatsqmrnsse",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=20 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description=None,
        ),
    ),
    ("lnbc20m1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqfp4qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q9qrsgq9vlvyj8cqvq6ggvpwd53jncp9nwc47xlrsnenq2zp70fq83qlgesn4u3uyf4tesfkkwwfg3qs54qe426hp3tz7z6sweqdjg05axsrjqp9yrrwc",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=20 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description=None,
        ),
    ),
    ("lnbc9678785340p1pwmna7lpp5gc3xfm08u9qy06djf8dfflhugl6p7lgza6dsjxq454gxhj9t7a0sd8dgfkx7cmtwd68yetpd5s9xar0wfjn5gpc8qhrsdfq24f5ggrxdaezqsnvda3kkum5wfjkzmfqf3jkgem9wgsyuctwdus9xgrcyqcjcgpzgfskx6eqf9hzqnteypzxz7fzypfhg6trddjhygrcyqezcgpzfysywmm5ypxxjemgw3hxjmn8yptk7untd9hxwg3q2d6xjcmtv4ezq7pqxgsxzmnyyqcjqmt0wfjjq6t5v4khxsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsxqyjw5qcqp2rzjq0gxwkzc8w6323m55m4jyxcjwmy7stt9hwkwe2qxmy8zpsgg7jcuwz87fcqqeuqqqyqqqqlgqqqqn3qq9q9qrsgqrvgkpnmps664wgkp43l22qsgdw4ve24aca4nymnxddlnp8vh9v2sdxlu5ywdxefsfvm0fq3sesf08uf6q9a2ke0hc9j6z6wlxg5z5kqpu2v9wz",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1572468703,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=967878534,
            payment_hash=unhexlify("462264ede7e14047e9b249da94fefc47f41f7d02ee9b091815a5506bc8abf75f"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="Blockstream Store: 88.85 USD for Blockstream Ledger Nano S x 1, \"Back In My Day\" Sticker x 2, \"I Got Lightning Working\" Sticker x 2 and 1 more items",
        ),
    ),
    ("lnbc25m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdq5vdhkven9v5sxyetpdeessp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs9q5sqqqqqqqqqqqqqqqqsgq2a25dxl5hrntdtn6zvydt7d66hyzsyhqs4wdynavys42xgl6sgx9c4g7me86a27t07mdtfry458rtjr0v92cnmswpsjscgt2vcse3sgpz3uapa",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=25 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="coffee beans",
        ),
    ),
    ("LNBC25M1PVJLUEZPP5QQQSYQCYQ5RQWZQFQQQSYQCYQ5RQWZQFQQQSYQCYQ5RQWZQFQYPQDQ5VDHKVEN9V5SXYETPDEESSP5ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYGS9Q5SQQQQQQQQQQQQQQQQSGQ2A25DXL5HRNTDTN6ZVYDT7D66HYZSYHQS4WDYNAVYS42XGL6SGX9C4G7ME86A27T07MDTFRY458RTJR0V92CNMSWPSJSCGT2VCSE3SGPZ3UAPA",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=25 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="coffee beans",
        ),
    ),
    ("lnbc25m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdq5vdhkven9v5sxyetpdeessp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs9q5sqqqqqqqqqqqqqqqqsgq2qrqqqfppnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqppnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpp4qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqhpnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqhp4qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqspnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqsp4qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqnp5qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqnpkqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqz599y53s3ujmcfjp5xrdap68qxymkqphwsexhmhr8wdz5usdzkzrse33chw6dlp3jhuhge9ley7j2ayx36kawe7kmgg8sv5ugdyusdcqzn8z9x",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=25 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="coffee beans",
        ),
    ),
    ("lnbc10m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdp9wpshjmt9de6zqmt9w3skgct5vysxjmnnd9jx2mq8q8a04uqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs9q2gqqqqqqsgq7hf8he7ecf7n4ffphs6awl9t6676rrclv9ckg3d3ncn7fct63p6s365duk5wrk202cfy3aj5xnnp5gs3vrdvruverwwq7yzhkf5a3xqpd05wjc",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1496314658,
            payee=unhexlify("03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"),
            amount=10 * 100_000 * 1000,
            payment_hash=unhexlify("0001020304050607080900010203040506070809000102030405060708090102"),
            payment_secret=unhexlify("1111111111111111111111111111111111111111111111111111111111111111"),
            description="payment metadata inside",
        ),
    ),
]

# test vectors created manually
VECTORS_CUSTOM = [
    ("lnbc538340n1p3q7l23pp57vysk3kakcfynz09du0zy87zy7n4gc6czqettc7c5v9v2fsrs9nqdpa2pskjepqw3hjq3r0deshgefqw3hjqjzjgcs8vv3qyq5y7unyv4ezqj2y8gszjxqy9ghlcqpjsp50lm6njtrm9qlyaac8252x4s4l3eu0aryx7zjjw4zrq6hgpk2evwqrzjqtesdx359t3gswn09838tur09zjk5m4zutvk7kyg5vnxg3xu74ptvzhchqqq3kgqqyqqqqqqqqqqqqgq9q9qyyssqlg84727az93gg8n37gv994w3r6dj0u8dk55qjlstappyuehq3mqjcafkyj2a39xp0w34mnzy04hzqnct7fecd380wfa0kc0en8v006sqxqchh5",
        bolt11.Bolt11Invoice(
            network="bc",
            timestamp=1645182289,
            payee=unhexlify("0285c280641305f1641a9e08718d5f4b1ea3bde8003beec4acfbefb5dde207ae4d"),
            amount=53834000,
            payment_hash=unhexlify("f3090b46ddb6124989e56f1e221fc227a75463581032b5e3d8a30ac526038166"),
            payment_secret=unhexlify("7ff7a9c963d941f277b83aa8a35615fc73c7f4643785293aa218357406cacb1c"),
            description="Paid to Donate to HRF v2  (Order ID: )",
        ),
    ),
]

INVALID = [
    "lnbc2500u1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdpquwpc4curk03c9wlrswe78q4eyqc7d8d0xqzpuyk0sg5g70me25alkluzd2x62aysf2pyy8edtjeevuv4p2d5p76r4zkmneet7uvyakky2zr4cusd45tftc9c5fh0nnqpnl2jfll544esqchsrnt",
    "pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdpquwpc4curk03c9wlrswe78q4eyqc7d8d0xqzpuyk0sg5g70me25alkluzd2x62aysf2pyy8edtjeevuv4p2d5p76r4zkmneet7uvyakky2zr4cusd45tftc9c5fh0nnqpnl2jfll544esqchsrny",
    "lnbc2500u1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdq5xysxxatsyp3k7enxv4jsxqzpusp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs9qrsgqwgt7mcn5yqw3yx0w94pswkpq6j9uh6xfqqqtsk4tnarugeektd4hg5975x9am52rz4qskukxdmjemg92vvqz8nvmsye63r5ykel43pgz7zq0g2",
    "lnbc1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdpl2pkx2ctnv5sxxmmwwd5kgetjypeh2ursdae8g6na6hlh",
    "lnbc2500x1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdq5xysxxatsyp3k7enxv4jsxqzpusp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs9qrsgqrrzc4cvfue4zp3hggxp47ag7xnrlr8vgcmkjxk3j5jqethnumgkpqp23z9jclu3v0a7e0aruz366e9wqdykw6dxhdzcjjhldxq0w6wgqcnu43j",
    "lnbc2500000001p1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdq5xysxxatsyp3k7enxv4jsxqzpusp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs9qrsgq0lzc236j96a95uv0m3umg28gclm5lqxtqqwk32uuk4k6673k6n5kfvx3d2h8s295fad45fdhmusm8sjudfhlf6dcsxmfvkeywmjdkxcp99202x",
]

class TestCryptoBolt11(unittest.TestCase):

    def test_vectors(self):
        for i, p in VECTORS_BOLT11 + VECTORS_CUSTOM:
            d = bolt11.bolt11_decode(i)
            self.assertObjectEqual(d, p)

    def test_invalid(self):
        for i in INVALID:
            with self.assertRaises(Exception):
                bolt11.bolt11_decode(i)


if __name__ == "__main__":
    unittest.main()
