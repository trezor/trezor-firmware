use heapless::Vec;

use super::{Error, ed25519, ffi};

const MAX_PUBKEYS: usize = 3;

/// Collective Ed25519 signature with a bitmask of participating public keys.
pub struct Signature {
    sigmask: u8,
    signature: ed25519::Signature,
}

impl Signature {
    /// `sigmask` is a bitmask over `public_keys` (bit 0 = first key).
    pub fn new(sigmask: u8, signature: ed25519::Signature) -> Self {
        Self { sigmask, signature }
    }
}

/// Verify a CoSi signature of `message`.
///
/// Combines the public keys selected by `signature.sigmask` and checks that at
/// least `threshold` of them participated.
pub fn verify(
    threshold: u8,
    message: &[u8],
    public_keys: &[ed25519::PublicKey],
    signature: &Signature,
) -> Result<(), Error> {
    if threshold < 1 {
        return Err(Error::InvalidParams);
    }
    let selected_keys = select_keys(signature.sigmask, public_keys)?;
    if selected_keys.len() < threshold as usize {
        return Err(Error::InvalidParams);
    }
    let combined_key = combine_publickeys(&selected_keys)?;
    ed25519::verify(message, &combined_key, &signature.signature)
}

fn select_keys(
    mut sigmask: u8,
    keys: &[ed25519::PublicKey],
) -> Result<Vec<ed25519::PublicKey, MAX_PUBKEYS>, Error> {
    let mut selected_keys = Vec::new();
    for key in keys {
        if sigmask & 1 != 0 {
            let result = selected_keys.push(*key);
            if result.is_err() {
                // selected_keys is sized to MAX_PUBKEYS.
                // if the push overflows, means there's too many pubkeys selected.
                return Err(Error::InvalidSigmask);
            }
        }
        sigmask >>= 1;
    }
    if sigmask != 0 {
        Err(Error::InvalidParams)
    } else {
        Ok(selected_keys)
    }
}

/// Combines `keys` into the public key a CoSi signature over them verifies
/// against (see [`verify`]).
pub fn combine_publickeys(keys: &[ed25519::PublicKey]) -> Result<ed25519::PublicKey, Error> {
    // The C code reads the first key unconditionally.
    if keys.is_empty() {
        return Err(Error::InvalidParams);
    }
    let mut combined_key = ed25519::PublicKey::default();
    // SAFETY: ffi
    let res = unsafe {
        ffi::ed25519_cosi_combine_publickeys(&mut combined_key as *mut _, keys.as_ptr(), keys.len())
    };
    if res == 0 {
        Ok(combined_key)
    } else {
        Err(Error::InvalidEncoding)
    }
}

#[cfg(test)]
mod test {
    use super::*;

    // RFC 8032 test vectors 1 and 2
    const KEY_A: &str = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a";
    const KEY_B: &str = "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c";

    fn key(hex_str: &str) -> ed25519::PublicKey {
        hex::decode(hex_str).unwrap().try_into().unwrap()
    }

    #[test]
    fn test_combine_single_key() {
        let a = key(KEY_A);
        assert_eq!(combine_publickeys(&[a]).unwrap(), a);
    }

    #[test]
    fn test_combine_is_order_independent() {
        let (a, b) = (key(KEY_A), key(KEY_B));
        let ab = combine_publickeys(&[a, b]).unwrap();
        assert_eq!(combine_publickeys(&[b, a]).unwrap(), ab);
        assert_ne!(ab, a);
        assert_ne!(ab, b);
    }

    #[test]
    fn test_combine_invalid_key() {
        // y = 2 is not on the curve
        let mut bad = [0u8; 32];
        bad[0] = 2;
        let res = combine_publickeys(&[key(KEY_A), bad]);
        assert!(matches!(res, Err(Error::InvalidEncoding)));
    }

    #[test]
    fn test_combine_no_keys() {
        assert!(matches!(combine_publickeys(&[]), Err(Error::InvalidParams)));
    }

    // Ported from core/tests/test_trezor.crypto.cosi.py, with fixed vectors
    // since the crate can't sign.
    const MESSAGE: [u8; 128] = {
        let mut message = [0u8; 128];
        let mut i = 0;
        while i < message.len() {
            message[i] = i as u8;
            i += 1;
        }
        message
    };

    // Generated with trezorlib's `cosi` module: keys from sha256(b"cosi test key
    // %d"), signatures with `sign_with_privkeys(MESSAGE, ...,
    // deterministic=True)`.
    const PUBLIC_KEYS: [&str; 10] = [
        "42b6ca46dbd24bd982e7963894e5ce6a28c227227d80519b8ed76175ff471e16",
        "7e7aab967b596b4c85f487510f61d5cbc34f1f254c3e7eeed45eb0abfe2dd5da",
        "b2e2d03405c8773b45994e1d3b87678e6e6962432485186e24179a2a0121dfef",
        "bbfe605edf7823c149d47398a9745dacada48fa5ec0dc0be95bbfe2084363abc",
        "f64a72c5f1c9cc07228363b6663a753884d154d0a7c7eb5be851c9fc6d9c036b",
        "ce31b63ebe87f1470017fd678b7eb457692e1a28ba619166ad8edc74c0f40643",
        "0955dbcdbcf747362bd728d59d1588e057f44f9eca3795a89e93c8177afb2d1a",
        "a51e4dc7f5dbd687c0c5d579e7ad86eba61036519d09033c272aacfd833a1c9e",
        "2ec84b009035978561e1d0ef42a6080897fda64f504588810fd7bb57e0096b64",
        "5ad0fb93e9bf46b62684a85ecf769fbf1c8dda11244f1627ae402fe9088e0593",
    ];

    // Combined key and signature of the first N keys, N = 1..=10.
    const COMBINED: [(&str, &str); 10] = [
        (
            "42b6ca46dbd24bd982e7963894e5ce6a28c227227d80519b8ed76175ff471e16",
            "f28cff737cacf0b2cb9e461bc3f1c12329735e76c1c76840ecbb7e7a2bab28c2269c27a5fb44c39d15bf0c160790760d1272717b085f3e736728ff09421c810f",
        ),
        (
            "4e52d2f9b75f187963ba9c7f9bb8ec63327ee292cdb11e010fe89bdffc6efab2",
            "af6a28025b5c8ff8aae9068c79cc52f0439a4d4d87cc0fc246760d5e7c43f10d3370d69e084021cff5c99878e1dc2f17eefe28eb0c13c884204322d7c75cd706",
        ),
        (
            "8ea60ebb604cf64a82c00d61d0b5f8462b8a98dba21714184101ab8269f26ff2",
            "ffcfea957a0a039eacde4fb5067b53a874683078bd83404805cbc1ceef7ca5a4bf4f0379ee55ace5adf766f24c336cfbecb4aed4f22736ac89dba16128fa6408",
        ),
        (
            "2b20a2263e8bd30e45cbd602027fe73fa1103d24f5eb213dfb39b8c3eb8b0b57",
            "5c22da2901a815b2575b96a286c20dda1fca9b49a8fec16f601dd5c2b995849494b298a86354dd1166b800c9d59538efbb5b6764ae05b78bb92abf375c701105",
        ),
        (
            "033ed12fa971fb7ba5969855466498c0ca2bd0cb4c35a95d7386f9b5a7381d19",
            "c5eb88c2100f2e41ae5386fbcde0c481062afa8fe5885e540e1115c88249e1933aae4b893132a22a05c00920ad3de041fdbc5946cb7392d42c7a65697e221001",
        ),
        (
            "501896a5650ac6942ae56b5e5f85d2688b882719ef859432519b9dcf9794b237",
            "ca21678d4716269b8325375a54478a544631cd674383c20dd2b6cd46542c1288f468ae14363e024add26a9dc05836614bd5670b6e1491ece54838f29f5fba106",
        ),
        (
            "aa5bdab025920e3979aaaed1d1cb40ba9e7e0785c43562184272518055649082",
            "38bbedddb7917f5700b5f718fd26e783894669d6bf9f44822dfc9382e4e834ffed88cef2bb59ed3a6ad3a1d420f95fb2191614dc3e268fb64c892e0a51644409",
        ),
        (
            "c7597897727fa4156c7c34598c0206a99a22b26ef759c0f02f2717cf46667a92",
            "26901b0e7e8f9770e60837dee83cdf3ca4d334b21f94cd566bae5a64e7acf9c35ba0e690f82124b5450642a126ad2b5f28bddc18ed30b47486c835f5ac696a0d",
        ),
        (
            "9be5b651d5ddbae8c47fff55fd5fddcf0d1676afc60c041bb1bf97bdb2905f7a",
            "9054e4b795ee75a0c8f78596213eaaae85a602ce6d9778a9d9d19454cb068756f94afa2ee219a64d3e7e2dd912e2c02084cf868ef52948a0f16b51a6c6574309",
        ),
        (
            "4f5920e47d7d02a91203e7e131d29f61dbd1bb1d71cb845118ef1a82e5e0c4d4",
            "1b34707e4e1df3a7151fd86b5276dfb220cd772437e2200df3ba3b25049dda8ac7e329ed87d978112d2db65f5e36efc25fb0c8da5611e455d971066e44879b01",
        ),
    ];

    // Signature of the keys selected by sigmask `i + 1` out of the first 5.
    const SIGMASK_SIGNATURES: [&str; 31] = [
        "f28cff737cacf0b2cb9e461bc3f1c12329735e76c1c76840ecbb7e7a2bab28c2269c27a5fb44c39d15bf0c160790760d1272717b085f3e736728ff09421c810f",
        "c667248bafea6786675c45cf94dfa204cd6daea60eb6cbec6d5f38a465cfb23fb874cddc4948b1c80c01229dcab9fa9e7c3c3dc3cbe61dc0a065670d62278e0e",
        "af6a28025b5c8ff8aae9068c79cc52f0439a4d4d87cc0fc246760d5e7c43f10d3370d69e084021cff5c99878e1dc2f17eefe28eb0c13c884204322d7c75cd706",
        "88638f36d5a1030ce162594017cb164ec2ba250c563788badd407b83c454bf373dc53aaf22588bdc035d9d818459894f1111d5bdb2f778cb907a8106e8a16306",
        "428c8e51813e734b7ad0bcd9cafb1d331a00d33674612a16845bd696a933364d791376d73a15ee7f9db8f121d85b462b169f81f5ff6ff57bc0075119b6fb960d",
        "f278a6398cd0df89637f8a9bd027e2572ccc606ce1e1f5454a3185b2fd186c2a16cad9e314b9acf8816e59b40203f734e0c76c9f59be2b1c1a32828c8e707a08",
        "ffcfea957a0a039eacde4fb5067b53a874683078bd83404805cbc1ceef7ca5a4bf4f0379ee55ace5adf766f24c336cfbecb4aed4f22736ac89dba16128fa6408",
        "921d48a09c642abb3e2d2d3c7ae2a977d0ba3f48aff8a27f078bbe7ab5d94d16a7537a2428b4e219278274847a7e28a829a7cc604c9da9e6575585ea7db26102",
        "11eaf869fbfd3d00633b823771095f1330f714df69d857956969b9d74d48db87d71eb3329f635754829f1e1e484eb510e6200a1a4c1e9a51c7e02f873bd43a0a",
        "3f351232d95d3156d8054103dbd2d0b0fced65f3f54ea258b2461f4da0965f986706bf9f05d10f257c2af417ef00b0007ebebef4db442cebb088f498545b440c",
        "46f8fcac7a8828157c0f9bb95b23765f5148b4d1709f848916313b59e30f450d47da0228c4a9866f716e486c4120343ac74942b6a0be9e7069a901e8be9c9b05",
        "6315a74cb16cecba543f94cfc4de93c1dafd6ebc08095d2046252970b7d994866dbac9eb5b2c8c05fa3cdd582c8055b83a6d435a728f871b9bad1aefe9e9800d",
        "4ab6846c503f261ef73224c6d1c8a344f7f1087f6331148a0a87cdf01ddad4f325d298bc8bcc69d16f4f52cfd8704e13707a90f255fa6e73a4e30134ef4eed00",
        "1eb5af49712a4e69baa74142cdfc696c509c8f2e881e6d8edebd2bb1f09b5e93e48df667db95333f0d2305fa7653937fd8b1c7f741c7f42a6d8fb111f79fcc06",
        "5c22da2901a815b2575b96a286c20dda1fca9b49a8fec16f601dd5c2b995849494b298a86354dd1166b800c9d59538efbb5b6764ae05b78bb92abf375c701105",
        "bf3ad2683dd7039e97551c04e0a7f5bbe91176cca4dfedc2ca79ded833d2632b75758d5d17e5f8b40be6c7281a859fb43629854aaa8537d9d085fdce9b0ff805",
        "efe41eaa7a55252f1d31d825465ea976519b1dba172c0d83c8064062f377bf81dd9abe5e10baf0eec016859f09b3e001f9660a58941cc6061d355ca1df7eec0a",
        "85d6e376bcdc60f5e925f03f9a19d5e8834604c1c3383de885bf82b8c37f2c5db4282d29ae363a36ca7d4fd99f4c2450963aa3dbd7abd82fbaea8b834f17ee0e",
        "587ca4c52b2926ed02ec1640a6e79103107075d0837da3663526e6ceb3bc12cc3277d895f07217d5eb5416675fcbef25a26afc2364aee0493d356fef94cb5209",
        "398d16026a3f294555a4805f9783c1e975380ee0387525c770865e3cc0fe2e048bdecefe41910bdac678c729f558691e7d73e9d9133ff32635ceca3c5559a307",
        "7756304265eacf2d389be5e3b8a2dae1e55c54b76c98f74b504b9c699c66e6e688886bf12010ea2eced0468fc36364728b60a168db9344542ec6950f311da50b",
        "5dc6a3d2fe0264e50c2d1a75151edb2f8e205b6050c724ffa7c57665f53ce3e86dab029218a5c7cc1277906433b99aa30dbca5994f167c1101252f1ef66ae303",
        "1ccb53fa36c960cc2a826370f813200cc818959dfc301cc0033a1ed0560a13622441ad093f2193a547bdcbc3d8cd7189d144b9099b1993e0b49781c5d8acff03",
        "1ceb4ffe0af21c1242b0d0e3190410e41c81081bf1b0415b33f89cad67e1d3e855bd8f40fece996dfc4249dcf8416020ca5d30348869538f0dca8ab393919a04",
        "c6a9277bc603a42e09b7d7c5625b63ac97d64c3f091aebc17c0e2c9a635b7091d879e270a3f10826d67452dbadc36993362634d03044522fa1b0871a1ca70a0e",
        "268758e1784d16ad9f1422065a944b5bf7fd54750445acd7d3ba6e4a5af82a8cf31e8d3fad005e566d8a5bc034c81a565bb853c9f3b4ed52ba1419e1c91b0400",
        "6f6239d0adfcd0e685e78e1d9c81730b97716e33f57155f45c67cbd57c879c03c65c29fad2c5c0ba1f78fdb4251a442b27c12e6eb62cf5bc179ff77ff91bbf04",
        "9a75ac91a9a2c0528e291e52c166e5a1fba19347882f8203c61dd9d85707255d4415019bae9aa4f6a9fca1c1535f3f5f4a90dd223266a8268e658dd4cd782106",
        "245e7480362f1d63ef40304fa66a1173358e277e85402939ffc950d856e9ec1961d49a05afd08bf422005d03bbc0084e0ec2cbb98482f539b78ade11f75fbd06",
        "3e18fe6162d0c71191702f1d260680b99c4ba0f1a50740b9af3e4afb3ca5310d1b7f4f9eaae724a932d9e597cecc69aab17b9d9e376fa82809af142818caf001",
        "c5eb88c2100f2e41ae5386fbcde0c481062afa8fe5885e540e1115c88249e1933aae4b893132a22a05c00920ad3de041fdbc5946cb7392d42c7a65697e221001",
    ];

    fn signature(hex_str: &str) -> ed25519::Signature {
        hex::decode(hex_str).unwrap().try_into().unwrap()
    }

    #[test]
    fn test_cosi() {
        let keys = PUBLIC_KEYS.map(key);
        for (n, (combined, sig)) in COMBINED.iter().enumerate() {
            let combined_key = combine_publickeys(&keys[..=n]).unwrap();
            assert_eq!(combined_key, key(combined));
            assert!(ed25519::verify(&MESSAGE, &combined_key, &signature(sig)).is_ok());
        }
    }

    #[test]
    fn test_select_keys() {
        let keys = PUBLIC_KEYS.map(key);
        let keys = &keys[..5];
        // all 5-bit sigmasks
        for sigmask in 1..32u8 {
            let expected: std::vec::Vec<_> = (0..5)
                .filter(|i| sigmask & (1 << i) != 0)
                .map(|i| keys[i])
                .collect();
            match select_keys(sigmask, keys) {
                Ok(selected) => assert_eq!(&selected[..], &expected[..]),
                Err(Error::InvalidSigmask) => assert!(expected.len() > MAX_PUBKEYS),
                Err(_) => panic!("unexpected error for sigmask {sigmask}"),
            }
        }
        // a bit beyond the keys
        assert!(matches!(
            select_keys(0b100000, keys),
            Err(Error::InvalidParams)
        ));
    }

    #[test]
    fn test_verify() {
        let keys = PUBLIC_KEYS.map(key);
        let keys = &keys[..5];
        // all 5-bit sigmasks
        for (sigmask, sig) in (1..32u8).zip(SIGMASK_SIGNATURES) {
            let count = sigmask.count_ones() as u8;
            let sig = Signature::new(sigmask, signature(sig));
            if count as usize > MAX_PUBKEYS {
                let res = verify(1, &MESSAGE, keys, &sig);
                assert!(matches!(res, Err(Error::InvalidSigmask)));
                continue;
            }
            assert!(verify(count, &MESSAGE, keys, &sig).is_ok());
            assert!(verify(1, &MESSAGE, keys, &sig).is_ok());
            assert!(verify(count + 1, &MESSAGE, keys, &sig).is_err());
            assert!(verify(count, b"other message", keys, &sig).is_err());
        }
        // a threshold of 0 is refused
        let sig = Signature::new(1, signature(SIGMASK_SIGNATURES[0]));
        assert!(matches!(
            verify(0, &MESSAGE, keys, &sig),
            Err(Error::InvalidParams)
        ));
    }
}
