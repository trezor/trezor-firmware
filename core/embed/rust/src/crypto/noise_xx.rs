use core::mem::{size_of, size_of_val, transmute, MaybeUninit};

use super::{aesgcm, ffi};

pub type Context = ffi::noise_context_t;

pub type HandshakeContext = ffi::noise_xx_handshake_context_t;

pub const MAX_PAYLOAD_LEN: usize = ffi::NOISE_XX_MAX_PAYLOAD_LEN as usize;
pub const PUBLIC_KEY_LEN: usize = 32;
pub const PRIVATE_KEY_LEN: usize = 32;
pub const HANDSHAKE_HASH_LEN: usize = 32;

impl HandshakeContext {
    pub fn handle_initiation_request(prologue: &[u8], request: &[u8]) -> Result<(Self, u8), ()> {
        if request.len() < size_of::<ffi::noise_xx_initiation_request_t>() {
            return Err(());
        }
        // SAFETY: size checked above, all bit patterns are valid
        let request: *const ffi::noise_xx_initiation_request_t =
            unsafe { transmute(request.as_ptr()) };
        // SAFETY: all-zero noise_xx_handshake_context_t is valid and expected
        let mut ctx =
            unsafe { MaybeUninit::<ffi::noise_xx_handshake_context_t>::zeroed().assume_init() };
        let mut payload = 0u8;
        // SAFETY: ffi
        let success = unsafe {
            ffi::noise_xx_handle_initiation_request(
                &mut ctx as _,
                prologue.as_ptr(),
                prologue.len(),
                &mut payload as *mut _,
                request,
            )
        };
        if !success {
            return Err(());
        }
        Ok((ctx, payload))
    }

    pub fn create_initiation_response(
        &mut self,
        static_private_key: &[u8; PRIVATE_KEY_LEN],
        response: &mut [u8],
    ) -> Result<usize, ()> {
        let response_size = size_of::<ffi::noise_xx_initiation_response_t>();
        if response.len() < response_size {
            return Err(());
        }
        // SAFETY: size checked above, all bit patterns are valid
        let response: *mut ffi::noise_xx_initiation_response_t =
            unsafe { transmute(response.as_mut_ptr()) };
        // SAFETY: ffi
        let success = unsafe {
            ffi::noise_xx_create_initiation_response(
                self as _,
                static_private_key.as_ptr(),
                response,
            )
        };
        if !success {
            return Err(());
        }
        Ok(response_size)
    }

    pub fn handle_completion_request(
        &mut self,
        request: &[u8],
        payload: &mut [u8],
    ) -> Result<(Context, usize), ()> {
        let mut ctx = unsafe { MaybeUninit::<Context>::zeroed().assume_init() };
        let mut request_struct =
            unsafe { MaybeUninit::<ffi::noise_xx_completion_request_t>::zeroed().assume_init() };
        let fixed_part_len: usize =
            size_of_val(&request_struct.encrypted_initiator_static_public_key);
        let variable_part_max_len: usize = size_of_val(&request_struct.encrypted_payload);

        let Some(var_len) = request.len().checked_sub(fixed_part_len) else {
            // input is shorter than the fixed part
            return Err(());
        };
        if var_len > variable_part_max_len {
            return Err(());
        }
        if payload.len() < MAX_PAYLOAD_LEN {
            return Err(());
        }
        request_struct
            .encrypted_initiator_static_public_key
            .copy_from_slice(&request[..fixed_part_len]);
        request_struct.encrypted_payload[..var_len]
            .copy_from_slice(&request[fixed_part_len..][..var_len]);
        request_struct.encrypted_payload_len = var_len;

        let mut payload_len: usize = 0;
        // SAFETY: ffi
        let success = unsafe {
            ffi::noise_xx_handle_completion_request(
                self as _,
                payload.as_mut_ptr(),
                &mut payload_len as *mut _,
                &mut ctx as _,
                &request_struct as _,
            )
        };
        if !success {
            return Err(());
        }

        Ok((ctx, payload_len))
    }

    pub fn remote_static_pubkey(&self) -> Option<&[u8; PUBLIC_KEY_LEN]> {
        match self.step {
            ffi::noise_xx_handshake_step_t_NOISE_XX_HANDSHAKE_I_RECEIVED_INITIATION_RESPONSE
            | ffi::noise_xx_handshake_step_t_NOISE_XX_HANDSHAKE_FINISHED => {
                Some(&self.remote_static_public_key)
            }
            _ => None,
        }
    }

    pub fn handshake_hash(&self) -> Option<&[u8; HANDSHAKE_HASH_LEN]> {
        match self.step {
            ffi::noise_xx_handshake_step_t_NOISE_XX_HANDSHAKE_FINISHED => {
                Some(&self.handshake_hash)
            }
            _ => None,
        }
    }
}

#[cfg(feature = "test")]
impl HandshakeContext {
    pub fn create_initiation_request(
        prologue: &[u8],
        payload: u8,
        request: &mut [u8],
    ) -> Result<(Self, usize), ()> {
        let request_len = size_of::<ffi::noise_xx_initiation_request_t>();
        if request.len() < request_len {
            return Err(());
        }
        // SAFETY: size checked above, all bit patterns are valid
        let request: *mut ffi::noise_xx_initiation_request_t =
            unsafe { transmute(request.as_ptr()) };
        // SAFETY: all-zero noise_xx_handshake_context_t is valid and expected
        let mut ctx =
            unsafe { MaybeUninit::<ffi::noise_xx_handshake_context_t>::zeroed().assume_init() };
        // SAFETY: ffi
        let success = unsafe {
            ffi::noise_xx_create_initiation_request(
                &mut ctx as _,
                prologue.as_ptr(),
                prologue.len(),
                payload,
                request,
            )
        };
        if !success {
            return Err(());
        }

        Ok((ctx, request_len))
    }

    pub fn handle_initiation_response(&mut self, response: &[u8]) -> Result<(), ()> {
        let response_len = size_of::<ffi::noise_xx_initiation_response_t>();
        if response.len() < response_len {
            return Err(());
        }
        // SAFETY: size checked above, all bit patterns are valid
        let response: *const ffi::noise_xx_initiation_response_t =
            unsafe { transmute(response.as_ptr()) };
        // SAFETY: ffi
        let success = unsafe { ffi::noise_xx_handle_initiation_response(self as _, response) };
        if !success {
            return Err(());
        }
        Ok(())
    }

    pub fn create_completion_request(
        &mut self,
        static_private_key: &[u8; PRIVATE_KEY_LEN],
        payload: &[u8],
        request: &mut [u8],
    ) -> Result<(Context, usize), ()> {
        let mut request_struct =
            unsafe { MaybeUninit::<ffi::noise_xx_completion_request_t>::zeroed().assume_init() };
        let fixed_part_len: usize =
            size_of_val(&request_struct.encrypted_initiator_static_public_key);
        let variable_part_max_len: usize = size_of_val(&request_struct.encrypted_payload);

        let var_len = payload.len() + aesgcm::TAG_SIZE;
        if var_len > variable_part_max_len {
            return Err(());
        }
        let request_len = fixed_part_len + var_len;
        if request.len() < fixed_part_len + var_len {
            return Err(());
        }
        // SAFETY: zeroed ctx is expected
        let mut ctx = unsafe { MaybeUninit::<Context>::zeroed().assume_init() };
        // SAFETY: ffi
        let success = unsafe {
            ffi::noise_xx_create_completion_request(
                self as _,
                static_private_key.as_ptr(),
                payload.as_ptr(),
                payload.len(),
                &mut ctx as _,
                &mut request_struct as _,
            )
        };
        if !success || request_struct.encrypted_payload_len != var_len {
            return Err(());
        }
        request[..fixed_part_len]
            .copy_from_slice(&request_struct.encrypted_initiator_static_public_key);
        request[fixed_part_len..][..var_len]
            .copy_from_slice(&request_struct.encrypted_payload[..var_len]);

        Ok((ctx, request_len))
    }

    pub fn remote_ephemeral_pubkey(&self) -> Option<&[u8; PUBLIC_KEY_LEN]> {
        match self.step {
            ffi::noise_xx_handshake_step_t_NOISE_XX_HANDSHAKE_I_RECEIVED_INITIATION_RESPONSE
            | ffi::noise_xx_handshake_step_t_NOISE_XX_HANDSHAKE_R_RECEIVED_INITIATION_REQUEST
            | ffi::noise_xx_handshake_step_t_NOISE_XX_HANDSHAKE_R_SENT_INITIATION_RESPONSE => {
                Some(&self.remote_ephemeral_public_key)
            }
            _ => None,
        }
    }
}

impl Context {
    pub fn send_message_inplace(
        &mut self,
        associated_data: &[u8],
        in_out: &mut [u8],
        plaintext_len: usize,
    ) -> Result<usize, ()> {
        let ciphertext_len = plaintext_len + aesgcm::TAG_SIZE;
        if in_out.len() < ciphertext_len {
            return Err(());
        }
        // SAFETY: ffi
        let success = unsafe {
            ffi::noise_send_message_inplace(
                self as _,
                associated_data.as_ptr(),
                associated_data.len(),
                in_out.as_mut_ptr(),
                plaintext_len,
            )
        };
        if !success {
            return Err(());
        }
        Ok(ciphertext_len)
    }

    pub fn receive_message_inplace(
        &mut self,
        associated_data: &[u8],
        in_out: &mut [u8],
    ) -> Result<usize, ()> {
        let ciphertext_len = in_out.len();
        let Some(plaintext_len) = ciphertext_len.checked_sub(aesgcm::TAG_SIZE) else {
            return Err(());
        };
        // SAFETY: ffi
        let success = unsafe {
            ffi::noise_receive_message_inplace(
                self as _,
                associated_data.as_ptr(),
                associated_data.len(),
                in_out.as_mut_ptr(),
                ciphertext_len,
            )
        };
        if !success {
            return Err(());
        }
        Ok(plaintext_len)
    }
}
