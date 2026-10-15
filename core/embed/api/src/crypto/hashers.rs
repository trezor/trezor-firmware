use crypto::{hmac, sha3, sha256, sha512};
use stabby::boxed::{Box, BoxedSlice};
use stabby::slice::Slice;
use trezor_app_sdk::traits::crypto::Hasher;
use zeroize::{Zeroize, ZeroizeOnDrop};

/// A [`Hasher`] state that can be finalized exactly once: [`Self::consume`]
/// drops the inner context (zeroizing it via its own `Zeroize` impl) so a
/// finalized hasher can't be updated/finalized again, and the whole wrapper
/// is itself `ZeroizeOnDrop` so an app that drops a
/// [`BoxedHasher`](trezor_app_sdk::traits::crypto::BoxedHasher) without ever
/// calling `finalize` still doesn't leak hasher state (which,
/// for HMAC, includes the key).
#[derive(Zeroize, ZeroizeOnDrop)]
pub struct ConsumableHasher<T: Zeroize>(Option<T>);

impl<T: Zeroize> ConsumableHasher<T> {
    pub fn borrow_mut(&mut self) -> &mut T {
        self.0.as_mut().expect("Hasher has been finalized")
    }

    pub fn consume(&mut self) {
        self.0 = None;
    }
}

impl<T: Default + Zeroize> Default for ConsumableHasher<T> {
    fn default() -> Self {
        Self(Some(T::default()))
    }
}

macro_rules! impl_hasher {
    ($name:ident, $guard:path) => {
        impl Hasher for $name {
            extern "C" fn update<'a>(&mut self, data: Slice<'a, u8>) {
                let ctx = self.borrow_mut();
                // COPY HAZARD: we are heap-allocated and operating through a reference
                let mut guard = <$guard>::hazard_new(ctx);
                guard.update(data.as_slice());
            }

            extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
                let ctx = self.borrow_mut();
                // COPY HAZARD: we are heap-allocated and operating through a reference
                let mut guard = <$guard>::hazard_new(ctx);
                let digest = guard.finalize();
                self.consume();
                BoxedSlice::from(&digest[..])
            }
        }
    };
}

pub type Sha256 = ConsumableHasher<sha256::Sha256Ctx>;
impl_hasher!(Sha256, sha256::Sha256Guard);

impl Sha256 {
    pub fn new() -> Box<Self> {
        let mut new = Box::new(Self(Some(Default::default())));
        // COPY HAZARD: init is public information
        new.borrow_mut().hazard_mut().init();
        new
    }
}

pub type Sha512 = ConsumableHasher<sha512::Sha512Ctx>;
impl_hasher!(Sha512, sha512::Sha512Guard);

impl Sha512 {
    pub fn new() -> Box<Self> {
        let mut new = Box::new(Self(Some(Default::default())));
        // COPY HAZARD: init is public information
        new.borrow_mut().hazard_mut().init();
        new
    }
}

/// SHA-3 / Keccak state: the secret context plus the (public) variant flag,
/// which picks the finalization. The digest size is derived from the context.
#[derive(Default, Zeroize)]
pub struct Sha3State {
    ctx: sha3::Sha3Ctx,
    is_keccak: bool,
}

pub type Sha3 = ConsumableHasher<Sha3State>;

impl Sha3 {
    pub fn new(bit_size: u32, is_keccak: bool) -> Box<Self> {
        let mut new = Box::new(Self(Some(Sha3State {
            is_keccak,
            ..Default::default()
        })));
        // COPY HAZARD: init is public information
        assert!(
            new.borrow_mut().ctx.hazard_mut().init(bit_size).is_ok(),
            "Invalid parameters"
        );
        new
    }
}

impl Hasher for Sha3 {
    extern "C" fn update<'a>(&mut self, data: Slice<'a, u8>) {
        let state = self.borrow_mut();
        // COPY HAZARD: we are heap-allocated and operating through a reference
        let mut guard = sha3::Sha3Guard::hazard_new(&mut state.ctx);
        guard.update(data.as_slice());
    }

    extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
        let state = self.borrow_mut();
        let is_keccak = state.is_keccak;
        // COPY HAZARD: we are heap-allocated and operating through a reference
        let mut guard = sha3::Sha3Guard::hazard_new(&mut state.ctx);
        let mut buffer = [0u8; 64];
        let digest = &mut buffer[..guard.hazard_mut().digest_size()];
        if is_keccak {
            guard.keccak_finalize(digest);
        } else {
            guard.sha3_finalize(digest);
        }
        let digest = BoxedSlice::from(&*digest);
        self.consume();
        digest
    }
}

pub type HmacSha256 = ConsumableHasher<hmac::HmacSha256Ctx>;
impl_hasher!(HmacSha256, hmac::HmacSha256Guard);

impl HmacSha256 {
    pub fn new(key: &[u8]) -> Box<Self> {
        let mut new = Box::new(Self(Some(Default::default())));
        // COPY HAZARD: we are heap-allocated and operating through a reference
        let mut guard = hmac::HmacSha256Guard::hazard_new(new.borrow_mut());
        guard.init(key);
        new
    }
}

pub type HmacSha512 = ConsumableHasher<hmac::HmacSha512Ctx>;
impl_hasher!(HmacSha512, hmac::HmacSha512Guard);

impl HmacSha512 {
    pub fn new(key: &[u8]) -> Box<Self> {
        let mut new = Box::new(Self(Some(Default::default())));
        // COPY HAZARD: we are heap-allocated and operating through a reference
        let mut guard = hmac::HmacSha512Guard::hazard_new(new.borrow_mut());
        guard.init(key);
        new
    }
}
