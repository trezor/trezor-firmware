use core::{mem::MaybeUninit, pin::Pin};

use zeroize::{zeroize_flat_type, Zeroize};

use super::{ffi, Error};

type Memory = ffi::gcm_ctx;

impl Default for Memory {
    fn default() -> Self {
        // SAFETY: a zeroed block of memory is a valid aes_gcm
        unsafe { MaybeUninit::<Memory>::zeroed().assume_init() }
    }
}

// Can't use DefaultIsZeroes as we don't have Copy.
impl Zeroize for Memory {
    fn zeroize(&mut self) {
        // SAFETY:
        // - gcm_ctx does not contain references to outside data or dynamically sized
        //   data
        // - values do not have Drop impls
        // - can invalidate the type if it is used after this function is called on it -
        //   only used in Drop
        // - all zero bit pattern is valid context, see Default impl
        unsafe { zeroize_flat_type(self as *mut Self) };
    }
}

// Tag size is a parameter but we fix it to 16 here for simplicity.
pub const TAG_SIZE: usize = 16;
pub type Tag = [u8; TAG_SIZE];

// for bindgen RETURN_* macros are u32, just redefine the only one we are using
const RETURN_GOOD: i32 = 0;
const KEY_SIZES: [usize; 3] = [16, 24, 32];

#[repr(u8)]
#[derive(PartialEq)]
enum State {
    Init,
    Encrypting,
    Decrypting,
    Finished,
    Failed,
}

pub struct AesGcm<'a> {
    ctx: Pin<&'a mut Memory>,
    state: State,
}

impl<'a> AesGcm<'a> {
    pub fn new(mut ctx: Pin<&'a mut Memory>, key: &[u8], iv: &[u8]) -> Result<Self, Error> {
        if !KEY_SIZES.contains(&key.len()) {
            return Err(Error::InvalidParams);
        }
        // initialize the context
        // SAFETY: ffi
        let res = unsafe {
            ffi::gcm_init_and_key(
                key.as_ptr(),
                key.len() as _,
                ctx.as_mut().get_unchecked_mut(),
            )
        };
        ensure!(res == RETURN_GOOD, "gcm_init_and_key");
        let mut aesgcm = Self {
            ctx,
            state: State::Init,
        };
        aesgcm.reset(iv);
        Ok(aesgcm)
    }

    pub fn reset(&mut self, iv: &[u8]) {
        // SAFETY: ffi
        let res = unsafe {
            ffi::gcm_init_message(
                iv.as_ptr(),
                iv.len() as _,
                self.ctx.as_mut().get_unchecked_mut(),
            )
        };
        ensure!(res == RETURN_GOOD, "gcm_init_message");
        self.state = State::Init;
    }

    pub fn encrypt<'b>(
        &mut self,
        plaintext: &[u8],
        buffer: &'b mut [u8],
    ) -> Result<&'b [u8], Error> {
        let buffer = buffer
            .get_mut(..plaintext.len())
            .ok_or(Error::InvalidParams)?;
        buffer.copy_from_slice(plaintext);
        match self.encrypt_in_place(buffer) {
            Err(e) => {
                buffer.zeroize(); // wipe plaintext from buffer on failure
                Err(e)
            }
            _ => Ok(buffer),
        }
    }

    pub fn encrypt_in_place(&mut self, data: &mut [u8]) -> Result<(), Error> {
        self.check_state(&[State::Init, State::Encrypting])?;
        self.state = State::Encrypting;

        let res = unsafe {
            ffi::gcm_encrypt(
                data.as_mut_ptr(),
                data.len() as _,
                self.ctx.as_mut().get_unchecked_mut(),
            )
        };
        ensure!(res == RETURN_GOOD, "gcm_encrypt");
        Ok(())
    }

    pub fn decrypt<'b>(
        &mut self,
        ciphertext: &[u8],
        buffer: &'b mut [u8],
    ) -> Result<&'b [u8], Error> {
        let buffer = buffer
            .get_mut(..ciphertext.len())
            .ok_or(Error::InvalidParams)?;
        buffer.copy_from_slice(ciphertext);
        self.decrypt_in_place(buffer)?;
        Ok(buffer)
    }

    pub fn decrypt_in_place(&mut self, data: &mut [u8]) -> Result<(), Error> {
        self.check_state(&[State::Init, State::Decrypting])?;
        self.state = State::Decrypting;

        // SAFETY: ffi
        let res = unsafe {
            ffi::gcm_decrypt(
                data.as_mut_ptr(),
                data.len() as _,
                self.ctx.as_mut().get_unchecked_mut(),
            )
        };
        ensure!(res == RETURN_GOOD, "gcm_decrypt");
        Ok(())
    }

    pub fn auth(&mut self, data: &[u8]) -> Result<(), Error> {
        self.check_state(&[State::Init, State::Encrypting, State::Decrypting])?;

        // SAFETY: ffi
        let res = unsafe {
            ffi::gcm_auth_header(
                data.as_ptr(),
                data.len() as _,
                self.ctx.as_mut().get_unchecked_mut(),
            )
        };
        ensure!(res == RETURN_GOOD, "gcm_auth_header");
        Ok(())
    }

    pub fn finish(&mut self) -> Result<Tag, Error> {
        self.check_state(&[State::Init, State::Encrypting, State::Decrypting])?;
        self.state = State::Finished;

        let mut tag = [0u8; TAG_SIZE];
        // SAFETY: ffi
        let res = unsafe {
            ffi::gcm_compute_tag(
                tag.as_mut_ptr(),
                tag.len() as _,
                self.ctx.as_mut().get_unchecked_mut(),
            )
        };
        if res != RETURN_GOOD {
            self.state = State::Failed;
            return Err(Error::InvalidContext);
        }
        Ok(tag)
    }

    fn check_state(&self, allowed: &[State]) -> Result<(), Error> {
        if !allowed.contains(&self.state) {
            return Err(Error::InvalidContext);
        }
        Ok(())
    }

    pub fn memory() -> Memory {
        Memory::default()
    }
}

impl Drop for AesGcm<'_> {
    fn drop(&mut self) {
        self.ctx.zeroize();
    }
}

#[allow(unused_macros)]
macro_rules! init_ctx {
    ($name:ident, $key:expr, $iv:expr) => {
        // assign the backing memory to $name...
        let mut $name = crate::crypto::aesgcm::AesGcm::memory();
        // ... then make it inaccessible by overwriting the binding, and pin it
        #[allow(unused_mut)]
        let mut $name = unsafe {
            crate::crypto::aesgcm::AesGcm::new(core::pin::Pin::new_unchecked(&mut $name), $key, $iv)
        };
    };
}

#[cfg(test)]
mod test {
    use super::*;

    struct Vector {
        key: &'static str,
        iv: &'static str,
        aad: &'static str,
        plaintext: &'static str,
        ciphertext: &'static str,
        tag: &'static str,
    }

    // first 10 vectors from https://github.com/BrianGladman/modes/blob/master/testvals/gcm.1
    const AES_GCM_VECTORS: &[Vector] = &[
        Vector {
            key: "00000000000000000000000000000000",
            iv: "000000000000000000000000",
            aad: "",
            plaintext: "",
            ciphertext: "",
            tag: "58e2fccefa7e3061367f1d57a4e7455a",
        },
        Vector {
            key: "00000000000000000000000000000000",
            iv: "000000000000000000000000",
            aad: "",
            plaintext: "00000000000000000000000000000000",
            ciphertext: "0388dace60b6a392f328c2b971b2fe78",
            tag: "ab6e47d42cec13bdf53a67b21257bddf",
        },
        Vector {
            key: "feffe9928665731c6d6a8f9467308308",
            iv: "cafebabefacedbaddecaf888",
            aad: "",
            plaintext: "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b391aafd255",
            ciphertext: "42831ec2217774244b7221b784d0d49ce3aa212f2c02a4e035c17e2329aca12e21d514b25466931c7d8f6a5aac84aa051ba30b396a0aac973d58e091473f5985",
            tag: "4d5c2af327cd64a62cf35abd2ba6fab4",
        },
		Vector {
			key: "feffe9928665731c6d6a8f9467308308",
			iv: "cafebabefacedbaddecaf888",
			aad: "feedfacedeadbeeffeedfacedeadbeefabaddad2",
            plaintext: "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39",
			ciphertext: "42831ec2217774244b7221b784d0d49ce3aa212f2c02a4e035c17e2329aca12e21d514b25466931c7d8f6a5aac84aa051ba30b396a0aac973d58e091",
			tag: "5bc94fbc3221a5db94fae95ae7121a47",
        },
		Vector {
			key: "feffe9928665731c6d6a8f9467308308",
			iv: "cafebabefacedbad",
			aad: "feedfacedeadbeeffeedfacedeadbeefabaddad2",
            plaintext: "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39",
			ciphertext: "61353b4c2806934a777ff51fa22a4755699b2a714fcdc6f83766e5f97b6c742373806900e49f24b22b097544d4896b424989b5e1ebac0f07c23f4598",
			tag: "3612d2e79e3b0785561be14aaca2fccb",
        },
		Vector {
			key: "feffe9928665731c6d6a8f9467308308",
			iv: "9313225df88406e555909c5aff5269aa6a7a9538534f7da1e4c303d2a318a728c3c0c95156809539fcf0e2429a6b525416aedbf5a0de6a57a637b39b",
			aad: "feedfacedeadbeeffeedfacedeadbeefabaddad2",
            plaintext: "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39",
			ciphertext: "8ce24998625615b603a033aca13fb894be9112a5c3a211a8ba262a3cca7e2ca701e4a9a4fba43c90ccdcb281d48c7c6fd62875d2aca417034c34aee5",
			tag: "619cc5aefffe0bfa462af43c1699d050",
        },
		Vector {
			key: "000000000000000000000000000000000000000000000000",
			iv: "000000000000000000000000",
            aad: "",
            plaintext: "",
            ciphertext: "",
			tag: "cd33b28ac773f74ba00ed1f312572435",
        },
		Vector {
			key: "000000000000000000000000000000000000000000000000",
			iv: "000000000000000000000000",
            aad: "",
            plaintext: "00000000000000000000000000000000",
			ciphertext: "98e7247c07f0fe411c267e4384b0f600",
			tag: "2ff58d80033927ab8ef4d4587514f0fb",
        },
		Vector {
			key: "feffe9928665731c6d6a8f9467308308feffe9928665731c",
			iv: "cafebabefacedbaddecaf888",
            aad: "",
            plaintext: "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b391aafd255",
			ciphertext: "3980ca0b3c00e841eb06fac4872a2757859e1ceaa6efd984628593b40ca1e19c7d773d00c144c525ac619d18c84a3f4718e2448b2fe324d9ccda2710acade256",
			tag: "9924a7c8587336bfb118024db8674a14",
        },
		Vector {
			key: "feffe9928665731c6d6a8f9467308308feffe9928665731c",
			iv: "cafebabefacedbaddecaf888",
			aad: "feedfacedeadbeeffeedfacedeadbeefabaddad2",
            plaintext: "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39",
			ciphertext: "3980ca0b3c00e841eb06fac4872a2757859e1ceaa6efd984628593b40ca1e19c7d773d00c144c525ac619d18c84a3f4718e2448b2fe324d9ccda2710",
			tag: "2519498e80f1478f37ba55bd6d27618c",
        },
    ];

    #[test]
    fn test_vectors() {
        for v in AES_GCM_VECTORS {
            let key = hex::decode(v.key).unwrap();
            let iv = hex::decode(v.iv).unwrap();
            let aad = hex::decode(v.aad).unwrap();
            let plaintext = hex::decode(v.plaintext).unwrap();

            init_ctx!(ctx, key.as_slice(), iv.as_slice());
            let mut ctx = ctx.unwrap();

            if !plaintext.is_empty() {
                let mut buffer = vec![0; plaintext.len()];
                let result = ctx
                    .encrypt(plaintext.as_slice(), buffer.as_mut_slice())
                    .unwrap();
                let result = hex::encode(result);
                assert_eq!(result, v.ciphertext);
            }

            if !aad.is_empty() {
                ctx.auth(aad.as_slice()).unwrap();
            }

            let result = ctx.finish().unwrap();
            let result = hex::encode(result);
            assert_eq!(result, v.tag);
        }
    }
}
