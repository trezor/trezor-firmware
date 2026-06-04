use core::pin::Pin;

use zeroize::Zeroize;

use super::{ffi, memory::Memory, Error};

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
    ctx: Pin<&'a mut Memory<ffi::gcm_ctx>>,
    state: State,
}

impl<'a> AesGcm<'a> {
    pub fn new(
        mut ctx: Pin<&'a mut Memory<ffi::gcm_ctx>>,
        key: &[u8],
        iv: &[u8],
    ) -> Result<Self, Error> {
        if !KEY_SIZES.contains(&key.len()) {
            return Err(Error::InvalidParams);
        }
        // initialize the context
        // SAFETY: ffi
        let res =
            unsafe { ffi::gcm_init_and_key(key.as_ptr(), key.len() as cty::c_ulong, ctx.inner()) };
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
            ffi::gcm_init_message(iv.as_ptr(), iv.len() as cty::c_ulong, self.ctx.inner())
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
                data.len() as cty::c_ulong,
                self.ctx.inner(),
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
                data.len() as cty::c_ulong,
                self.ctx.inner(),
            )
        };
        ensure!(res == RETURN_GOOD, "gcm_decrypt");
        Ok(())
    }

    pub fn auth(&mut self, data: &[u8]) -> Result<(), Error> {
        self.check_state(&[State::Init, State::Encrypting, State::Decrypting])?;

        // SAFETY: ffi
        let res = unsafe {
            ffi::gcm_auth_header(data.as_ptr(), data.len() as cty::c_ulong, self.ctx.inner())
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
                tag.len() as cty::c_ulong,
                self.ctx.inner(),
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

    pub fn memory() -> Memory<ffi::gcm_ctx> {
        Memory::default()
    }
}

impl Drop for AesGcm<'_> {
    fn drop(&mut self) {
        self.ctx.zeroize();
    }
}

#[cfg(test)]
mod test {
    use super::{super::memory::init_ctx, *};

    struct Vector {
        key: &'static str,
        iv: &'static str,
        aad: &'static str,
        plaintext: &'static str,
        ciphertext: &'static str,
        tag: &'static str,
    }

    impl Vector {
        fn decoded(&self) -> (Vec<u8>, Vec<u8>, Vec<u8>, Vec<u8>, Vec<u8>) {
            let key = hex::decode(self.key).unwrap();
            let iv = hex::decode(self.iv).unwrap();
            let aad = hex::decode(self.aad).unwrap();
            let pt = hex::decode(self.plaintext).unwrap();
            let ct = hex::decode(self.ciphertext).unwrap();
            (key, iv, aad, pt, ct)
        }
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
            let (key, iv, aad, plaintext, ciphertext) = v.decoded();

            init_ctx!(AesGcm, ctx_enc, &key, &iv);
            let mut ctx_enc = ctx_enc.unwrap();
            init_ctx!(AesGcm, ctx_dec, &key, &iv);
            let mut ctx_dec = ctx_dec.unwrap();

            if !plaintext.is_empty() {
                let mut buffer = vec![0; plaintext.len()];
                let result = ctx_enc.encrypt(&plaintext, &mut buffer).unwrap();
                assert_eq!(hex::encode(result), v.ciphertext);

                let result = ctx_dec.decrypt(&ciphertext, &mut buffer).unwrap();
                assert_eq!(hex::encode(result), v.plaintext);
            }

            if !aad.is_empty() {
                ctx_enc.auth(&aad).unwrap();
                ctx_dec.auth(&aad).unwrap();
            }

            let result = ctx_enc.finish().unwrap();
            assert_eq!(hex::encode(result), v.tag);
            let result = ctx_dec.finish().unwrap();
            assert_eq!(hex::encode(result), v.tag);
        }
    }

    #[test]
    fn test_state() {
        init_ctx!(AesGcm, ctx, &[0u8; 16], b"1");
        let mut ctx = ctx.unwrap();

        // ok: empty string tag
        ctx.finish().unwrap();

        // ok: any single operation
        // not ok: after reset
        let mut dest = [0u8; 16];
        ctx.reset(b"2");
        ctx.encrypt(b"asdf", &mut dest).unwrap();
        ctx.finish().unwrap();
        assert!(ctx.encrypt(b"asdf", &mut dest).is_err());

        ctx.reset(b"3");
        ctx.decrypt(b"fdsa", &mut dest).unwrap();
        ctx.finish().unwrap();
        assert!(ctx.decrypt(b"fdsa", &mut dest).is_err());

        ctx.reset(b"5");
        ctx.auth(b"foobar").unwrap();
        ctx.finish().unwrap();
        assert!(ctx.auth(b"foobar").is_err());

        // not ok: mixing encrypt and decrypt
        ctx.reset(b"6");
        ctx.encrypt(b"asdf", &mut dest).unwrap();
        ctx.encrypt_in_place(&mut dest).unwrap();
        assert!(ctx.decrypt(b"fdsa", &mut dest).is_err());

        ctx.reset(b"7");
        ctx.decrypt_in_place(&mut dest).unwrap();
        ctx.auth(b"foobar").unwrap();
        assert!(ctx.encrypt(b"fdsa", &mut dest).is_err());
    }

    // test vectors from
    // https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/mac/gcmtestvectors.zip
    const NIST_VECTORS: &[Vector] = &[
        Vector {
            key: "11754cd72aec309bf52f7687212e8957",
            iv: "3c819d9a9bed087615030b65",
            plaintext: "",
            aad: "",
            ciphertext: "",
            tag: "250327c674aaf477aef2675748cf6971",
        },
        Vector {
            key: "fe9bb47deb3a61e423c2231841cfd1fb",
            iv: "4d328eb776f500a2f7fb47aa",
            plaintext: "f1cc3818e421876bb6b8bbd6c9",
            aad: "",
            ciphertext: "b88c5c1977b35b517b0aeae967",
            tag: "43fd4727fe5cdb4b5b42818dea7ef8c9",
        },
        Vector {
            key: "6f44f52c2f62dae4e8684bd2bc7d16ee7c557330305a790d",
            iv: "9ae35825d7c7edc9a39a0732",
            plaintext: "37222d30895eb95884bbbbaee4d9cae1",
            aad: "1b4236b846fc2a0f782881ba48a067e9",
            ciphertext: "a54b5da33fc1196a8ef31a5321bfcaeb",
            tag: "1c198086450ae1834dd6c2636796bce2",
        },
        Vector {
            key: "05f714021372ae1c8d72c98e6307fbddb26ee27615860a9fb48ba4c3ea360a00",
            iv: "c0",
            plaintext: "ec3afbaa1447e47ce068bffb787bd0cadc9f0deceb11fa78e981271390578ae95891f26664b5e62d1fd5fd0d0767a54da5f86f",
            aad: "faf9fa457a8e70ea709da28545f18f041351e8d5",
            ciphertext: "c8c5816ba9e7e0d20820dc0064a519a277889f5ac9661c9882b5a9896fd12836c6721514e885b1d34f5e888d1d85abce8c2ebb",
            tag: "0856f211fade7d26d64478ca46025a3c",
        },
    ];

    // following tests ported from test_trezor.crypto.aesgcm.py
    #[test]
    fn test_gcm() {
        for v in NIST_VECTORS {
            let (key, iv, aad, pt, ct) = v.decoded();

            // Test encryption.
            init_ctx!(AesGcm, ctx, &key, &iv);
            let mut ctx = ctx.unwrap();
            if !aad.is_empty() {
                ctx.auth(&aad).unwrap();
            }
            let mut buffer = vec![0; pt.len()];
            let result = ctx.encrypt(&pt, &mut buffer).unwrap();
            assert_eq!(hex::encode(result), v.ciphertext);

            let result = ctx.finish().unwrap();
            assert_eq!(hex::encode(result), v.tag);

            // Test decryption.
            ctx.reset(&iv);
            if !aad.is_empty() {
                ctx.auth(&aad).unwrap();
            }
            let result = ctx.decrypt(&ct, &mut buffer).unwrap();
            assert_eq!(hex::encode(result), v.plaintext);

            let result = ctx.finish().unwrap();
            assert_eq!(hex::encode(result), v.tag);
        }
    }

    #[test]
    fn test_gcm_in_place() {
        for v in NIST_VECTORS {
            let (key, iv, aad, pt, ct) = v.decoded();

            // Test encryption.
            init_ctx!(AesGcm, ctx, &key, &iv);
            let mut ctx = ctx.unwrap();
            if !aad.is_empty() {
                ctx.auth(&aad).unwrap();
            }
            let mut buffer = Vec::new();
            buffer.extend_from_slice(&pt);
            ctx.encrypt_in_place(&mut buffer).unwrap();
            assert_eq!(hex::encode(buffer), v.ciphertext);

            let result = ctx.finish().unwrap();
            assert_eq!(hex::encode(result), v.tag);

            // Test decryption.
            ctx.reset(&iv);
            if !aad.is_empty() {
                ctx.auth(&aad).unwrap();
            }
            let mut buffer = Vec::new();
            buffer.extend_from_slice(&ct);
            ctx.decrypt_in_place(&mut buffer).unwrap();
            assert_eq!(hex::encode(buffer), v.plaintext);

            let result = ctx.finish().unwrap();
            assert_eq!(hex::encode(result), v.tag);
        }
    }

    #[test]
    fn test_gcm_chunks() {
        for v in NIST_VECTORS {
            let (key, iv, aad, pt, ct) = v.decoded();
            let chunk_len = pt.len() / 3;
            let mut buffer = vec![0; pt.len()];

            init_ctx!(AesGcm, ctx, &key, &iv);
            let mut ctx = ctx.unwrap();
            ctx.decrypt(&ct[..chunk_len], &mut buffer[..chunk_len])
                .unwrap();
            ctx.auth(aad.get(..7).unwrap_or(&[])).unwrap();
            ctx.decrypt(&ct[chunk_len..], &mut buffer[chunk_len..])
                .unwrap();
            ctx.auth(aad.get(7..).unwrap_or(&[])).unwrap();
            assert_eq!(hex::encode(buffer), v.plaintext);
            assert_eq!(hex::encode(ctx.finish().unwrap()), v.tag);

            buffer = vec![0; pt.len()];
            ctx.reset(&iv);
            ctx.auth(aad.get(..7).unwrap_or(&[])).unwrap();
            ctx.encrypt(&pt[..chunk_len], &mut buffer[..chunk_len])
                .unwrap();
            ctx.auth(aad.get(7..).unwrap_or(&[])).unwrap();
            ctx.encrypt(&pt[chunk_len..], &mut buffer[chunk_len..])
                .unwrap();
            assert_eq!(hex::encode(buffer), v.ciphertext);
            assert_eq!(hex::encode(ctx.finish().unwrap()), v.tag);
        }
    }

    #[test]
    fn test_gcm_chunks_in_place() {
        for v in NIST_VECTORS {
            let (key, iv, aad, pt, ct) = v.decoded();
            let chunk_len = pt.len() / 3;

            let mut buffer = ct;
            init_ctx!(AesGcm, ctx, &key, &iv);
            let mut ctx = ctx.unwrap();
            ctx.decrypt_in_place(&mut buffer[..chunk_len]).unwrap();
            ctx.auth(aad.get(..7).unwrap_or(&[])).unwrap();
            ctx.decrypt_in_place(&mut buffer[chunk_len..]).unwrap();
            ctx.auth(aad.get(7..).unwrap_or(&[])).unwrap();
            assert_eq!(hex::encode(buffer), v.plaintext);
            assert_eq!(hex::encode(ctx.finish().unwrap()), v.tag);

            let mut buffer = pt;
            ctx.reset(&iv);
            ctx.auth(aad.get(..7).unwrap_or(&[])).unwrap();
            ctx.encrypt_in_place(&mut buffer[..chunk_len]).unwrap();
            ctx.auth(aad.get(7..).unwrap_or(&[])).unwrap();
            ctx.encrypt_in_place(&mut buffer[chunk_len..]).unwrap();
            assert_eq!(hex::encode(buffer), v.ciphertext);
            assert_eq!(hex::encode(ctx.finish().unwrap()), v.tag);
        }
    }
}
