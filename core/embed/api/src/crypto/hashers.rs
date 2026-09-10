use crypto::{hmac, sha3, sha256, sha512};
use stabby::boxed::{Box, BoxedSlice};
use stabby::slice::Slice;
use stabby::vec::Vec;
use trezor_app_sdk::traits::crypto::Hasher;
use zeroize::{Zeroize, ZeroizeOnDrop};

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

pub type Sha3 = ConsumableHasher<sha3::Sha3Ctx>;

impl Sha3 {
    pub fn new(bit_size: u32, is_keccak: bool) -> Box<Self> {
        let mut new = Box::new(Self(Some(Default::default())));
        // COPY HAZARD: init is public information
        new.borrow_mut()
            .hazard_mut()
            .init(bit_size, is_keccak)
            .expect("Invalid parameters");
        new
    }
}

impl Hasher for Sha3 {
    extern "C" fn update<'a>(&mut self, data: Slice<'a, u8>) {
        let ctx = self.borrow_mut();
        // COPY HAZARD: we are heap-allocated and operating through a reference
        let mut guard = sha3::Sha3Guard::hazard_new(ctx);
        guard.update(data.as_slice());
    }

    extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
        let ctx = self.borrow_mut();
        // COPY HAZARD: we are heap-allocated and operating through a reference
        let mut guard = sha3::Sha3Guard::hazard_new(ctx);
        // allocate an appropriate-sized vector for the digest
        let mut digest = Vec::with_capacity(guard.hazard_mut().bit_size() as usize / 8);
        guard.finalize_into(&mut digest);
        self.consume();
        digest.into()
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
