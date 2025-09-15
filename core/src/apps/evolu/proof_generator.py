from hashlib import sha256

private_key_hexdump = "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"
sign_request_challenge: int = 1234
sign_request_size: int = 10


buffer_sign_request = (
    b"EvoluSignRegistrationRequest"
    + b"|"
    + bytes.fromhex(private_key_hexdump)
    + b"|"
    + (sign_request_challenge).to_bytes(16)
    + b"|"
    + (sign_request_size).to_bytes(16)
)

buffer_get_node = b"EvoluGetNode" + b"|" + bytes.fromhex(private_key_hexdump)

print("sign_request \t", sha256(buffer_sign_request).hexdigest())
print("get_node \t", sha256(buffer_get_node).hexdigest())
