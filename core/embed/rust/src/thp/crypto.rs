use trezor_thp::channel::{Backend, Cipher, Hash, DH};

use crate::crypto::{aesgcm, curve25519, memory::init_ctx, sha256};

pub struct TrezorCryptoCurve25519;

impl DH for TrezorCryptoCurve25519 {
    type Key = curve25519::Scalar;
    type Pubkey = curve25519::Point;
    type Output = curve25519::Point;

    fn name() -> &'static str {
        "25519"
    }

    fn genkey() -> Self::Key {
        curve25519::Scalar::generate()
    }

    fn pubkey(scalar: &Self::Key) -> Self::Pubkey {
        curve25519::Point::from_secret(scalar)
    }

    fn dh(scalar: &Self::Key, point: &Self::Pubkey) -> Result<Self::Output, ()> {
        Ok(point.multiply(scalar))
    }
}

pub struct TrezorCryptoAesGcm;

impl Cipher for TrezorCryptoAesGcm {
    fn name() -> &'static str {
        "AESGCM"
    }

    type Key = [u8; 32]; // FIXME Zeroizing

    fn encrypt(key: &Self::Key, nonce: u64, ad: &[u8], plaintext: &[u8], out: &mut [u8]) {
        assert!(plaintext.len().checked_add(Self::tag_len()) == Some(out.len()));

        let mut full_nonce = [0u8; 12];
        full_nonce[4..].copy_from_slice(&nonce.to_be_bytes());

        let (in_out, tag_out) = out.split_at_mut(plaintext.len());
        in_out.copy_from_slice(plaintext);

        init_ctx!(aesgcm::AesGcm, ctx, key, &full_nonce);
        let mut ctx = unwrap!(ctx);
        unwrap!(ctx.encrypt_in_place(in_out));
        unwrap!(ctx.auth(ad));
        let tag = unwrap!(ctx.finish());
        tag_out.copy_from_slice(&tag);
    }

    fn encrypt_in_place(
        key: &Self::Key,
        nonce: u64,
        ad: &[u8],
        in_out: &mut [u8],
        plaintext_len: usize,
    ) -> usize {
        assert!(plaintext_len
            .checked_add(16)
            .is_some_and(|l| l <= in_out.len()));

        let mut full_nonce = [0u8; 12];
        full_nonce[4..].copy_from_slice(&nonce.to_be_bytes());

        let (in_out, tag_out) = in_out[..plaintext_len + 16].split_at_mut(plaintext_len);

        init_ctx!(aesgcm::AesGcm, ctx, key, &full_nonce);
        let mut ctx = unwrap!(ctx);
        unwrap!(ctx.encrypt_in_place(in_out));
        unwrap!(ctx.auth(ad));
        let tag = unwrap!(ctx.finish());
        tag_out.copy_from_slice(&tag);

        plaintext_len + 16
    }

    fn decrypt(
        key: &Self::Key,
        nonce: u64,
        ad: &[u8],
        ciphertext: &[u8],
        out: &mut [u8],
    ) -> Result<(), ()> {
        assert!(ciphertext.len().checked_sub(16) == Some(out.len()));

        let mut full_nonce = [0u8; 12];
        full_nonce[4..].copy_from_slice(&nonce.to_be_bytes());

        out.copy_from_slice(&ciphertext[..out.len()]);
        let tag = &ciphertext[out.len()..];

        init_ctx!(aesgcm::AesGcm, ctx, key, &full_nonce);
        let mut ctx = unwrap!(ctx);
        unwrap!(ctx.decrypt_in_place(out));
        unwrap!(ctx.auth(ad));
        let computed_tag = unwrap!(ctx.finish());
        if computed_tag != tag {
            return Err(());
        }

        Ok(())
    }

    fn decrypt_in_place(
        key: &Self::Key,
        nonce: u64,
        ad: &[u8],
        in_out: &mut [u8],
        ciphertext_len: usize,
    ) -> Result<usize, ()> {
        assert!(ciphertext_len <= in_out.len());
        assert!(ciphertext_len >= 16);

        let mut full_nonce = [0u8; 12];
        full_nonce[4..].copy_from_slice(&nonce.to_be_bytes());

        let (in_out, tag) = in_out[..ciphertext_len].split_at_mut(ciphertext_len - 16);

        init_ctx!(aesgcm::AesGcm, ctx, key, &full_nonce);
        let mut ctx = unwrap!(ctx);
        unwrap!(ctx.decrypt_in_place(in_out));
        unwrap!(ctx.auth(ad));
        let computed_tag = unwrap!(ctx.finish());
        if computed_tag != tag {
            return Err(());
        }

        Ok(in_out.len())
    }
}

pub type TrezorCryptoSha256 = sha256::NoPinSha256;

impl Hash for TrezorCryptoSha256 {
    fn name() -> &'static str {
        "SHA256"
    }

    type Block = [u8; 64];
    type Output = sha256::Digest;

    fn input(&mut self, data: &[u8]) {
        self.update(data);
    }

    fn result(&mut self) -> Self::Output {
        let mut digest = sha256::Digest::default();
        self.finalize_into(&mut digest);
        digest
    }
}

pub struct TrezorCrypto;

impl Backend for TrezorCrypto {
    type DH = TrezorCryptoCurve25519;
    type Cipher = TrezorCryptoAesGcm;
    type Hash = TrezorCryptoSha256;

    fn random_bytes(dest: &mut [u8]) {
        crate::trezorhal::random::bytes(dest);
    }
}
