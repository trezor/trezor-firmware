use core::ops::DerefMut;

use rtl::{CSlice, CSliceMut};

use super::ffi;
use super::secret::{HazardGuard, SecretContext, SecretContextLock, ZeroableMemory};

pub const DHLEN: usize = ffi::NOISE_XXPSK3_DHLEN as usize;
pub const TAG_SIZE: usize = ffi::NOISE_XXPSK3_TAG_SIZE as usize;

pub type NoiseXXpsk3Ctx = SecretContext<ffi::noise_xxpsk3_initiator_t>;

// SAFETY: noise_xxpsk3_initiator_t is valid when zeroed
unsafe impl ZeroableMemory for ffi::noise_xxpsk3_initiator_t {}

impl HazardGuard<'_, ffi::noise_xxpsk3_initiator_t> {
    fn init(
        &mut self,
        psk: &[u8; DHLEN],
        static_private_key: &[u8; DHLEN],
        static_public_key: &[u8; DHLEN],
    ) -> Result<(), ()> {
        let res = unsafe {
            ffi::noise_xxpsk3_initiator_init(
                self.hazard_mut(),
                psk.as_ptr(),
                static_private_key.as_ptr(),
                static_public_key.as_ptr(),
            )
        };
        if res { return Ok(()) } else { return Err(()) }
    }

    fn create_request1(&mut self, payload: &[u8], request: &mut [u8]) -> Result<usize, ()> {
        let payload = CSlice::from(payload);
        let request = CSliceMut::from(request);
        let mut request_size = 0usize;
        let res = unsafe {
            ffi::noise_xxpsk3_initiator_create_request1(
                self.hazard_mut(),
                payload.ptr(),
                payload.len(),
                request.ptr(),
                request.len(),
                &mut request_size as *mut _,
            )
        };
        if res {
            assert!(request_size > 0 && request_size <= request.len());
            Ok(request_size)
        } else {
            Err(())
        }
    }

    fn handle_response1(
        &mut self,
        response: &[u8],
        remote_static_public_key: &mut [u8; DHLEN],
        payload: &mut [u8],
    ) -> Result<usize, ()> {
        let response = CSlice::from(response);
        let payload = CSliceMut::from(payload);
        let mut payload_size = 0usize;
        let res = unsafe {
            ffi::noise_xxpsk3_initiator_handle_response1(
                self.hazard_mut(),
                response.ptr(),
                response.len(),
                remote_static_public_key.as_mut_ptr(),
                payload.ptr(),
                payload.len(),
                &mut payload_size as *mut _,
            )
        };
        if res {
            assert!(payload_size <= payload.len());
            Ok(payload_size)
        } else {
            Err(())
        }
    }

    fn create_request2(&mut self, payload: &[u8], request: &mut [u8]) -> Result<usize, ()> {
        let payload = CSlice::from(payload);
        let request = CSliceMut::from(request);
        let mut request_size = 0usize;
        let res = unsafe {
            ffi::noise_xxpsk3_initiator_create_request2(
                self.hazard_mut(),
                payload.ptr(),
                payload.len(),
                request.ptr(),
                request.len(),
                &mut request_size as *mut _,
            )
        };
        if res {
            assert!(request_size > 0 && request_size <= request.len());
            Ok(request_size)
        } else {
            Err(())
        }
    }

    fn send_message(&mut self, payload: &[u8], ciphertext: &mut [u8]) -> Result<usize, ()> {
        let payload = CSlice::from(payload);
        let ciphertext = CSliceMut::from(ciphertext);
        let mut ciphertext_size = 0usize;
        let res = unsafe {
            ffi::noise_xxpsk3_send_message(
                &mut self.hazard_mut().transport_state,
                payload.ptr(),
                payload.len(),
                ciphertext.ptr(),
                ciphertext.len(),
                &mut ciphertext_size as *mut _,
            )
        };
        if res {
            assert!(ciphertext_size >= payload.len() && ciphertext_size <= ciphertext.len());
            Ok(ciphertext_size)
        } else {
            Err(())
        }
    }

    fn receive_message(&mut self, ciphertext: &[u8], payload: &mut [u8]) -> Result<usize, ()> {
        let ciphertext = CSlice::from(ciphertext);
        let payload = CSliceMut::from(payload);
        let mut payload_size = 0usize;
        let res = unsafe {
            ffi::noise_xxpsk3_receive_message(
                &mut self.hazard_mut().transport_state,
                ciphertext.ptr(),
                ciphertext.len(),
                payload.ptr(),
                payload.len(),
                &mut payload_size as *mut _,
            )
        };
        if res {
            assert!(payload_size <= ciphertext.len() && payload_size <= payload.len());
            Ok(payload_size)
        } else {
            Err(())
        }
    }
}

pub struct NoiseXXpsk3<D: DerefMut<Target = NoiseXXpsk3Ctx>>(SecretContextLock<D>);

impl<D: DerefMut<Target = NoiseXXpsk3Ctx>> NoiseXXpsk3<D> {
    pub fn new(
        ctx: D,
        psk: &[u8; DHLEN],
        static_private_key: &[u8; DHLEN],
        static_public_key: &[u8; DHLEN],
    ) -> Result<Self, ()> {
        let mut locked_ctx = SecretContextLock::new(ctx);
        locked_ctx
            .guarded()
            .init(psk, static_private_key, static_public_key)?;
        Ok(Self(locked_ctx))
    }

    pub fn create_request1(&mut self, payload: &[u8], request: &mut [u8]) -> Result<usize, ()> {
        self.0.guarded().create_request1(payload, request)
    }

    pub fn handle_response1(
        &mut self,
        response: &[u8],
        remote_static_public_key: &mut [u8; DHLEN],
        payload: &mut [u8],
    ) -> Result<usize, ()> {
        self.0
            .guarded()
            .handle_response1(response, remote_static_public_key, payload)
    }

    pub fn create_request2(&mut self, payload: &[u8], request: &mut [u8]) -> Result<usize, ()> {
        self.0.guarded().create_request2(payload, request)
    }

    pub fn send_message(&mut self, payload: &[u8], ciphertext: &mut [u8]) -> Result<usize, ()> {
        self.0.guarded().send_message(payload, ciphertext)
    }

    pub fn receive_message(&mut self, ciphertext: &[u8], payload: &mut [u8]) -> Result<usize, ()> {
        self.0.guarded().receive_message(ciphertext, payload)
    }
}
