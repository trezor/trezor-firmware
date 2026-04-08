from noise import InitiatorXXPsk3, ResponderXXPsk3

from crypto import generate_private_key


def test_handshake_and_transport():
    psk = b"psk"
    prologue = b"prologue"
    initiator_static_public_key = generate_private_key()
    responder_static_public_key = generate_private_key()

    initiator = InitiatorXXPsk3(initiator_static_public_key, prologue, psk)
    responder = ResponderXXPsk3(responder_static_public_key, prologue, psk)

    message1 = initiator.create_request1()
    responder.handle_request1(message1)

    message2 = responder.create_response1()
    initiator.handle_response1(message2)

    message3 = initiator.create_request2()
    responder.handle_request2(message3)

    initiator_transport_state = initiator.get_transport_state()
    responder_transport_state = responder.get_transport_state()

    assert (
        initiator_transport_state.handshake_hash
        == responder_transport_state.handshake_hash
    )

    ciphertext1 = initiator_transport_state.send_cipher_state.encrypt_with_ad(
        b"associated_data_1", b"plaintext_1"
    )
    plaintext1 = responder_transport_state.receive_cipher_state.decrypt_with_ad(
        b"associated_data_1", ciphertext1
    )
    assert plaintext1 == b"plaintext_1"

    ciphertext2 = responder_transport_state.send_cipher_state.encrypt_with_ad(
        b"associated_data_2", b"plaintext_2"
    )
    plaintext2 = initiator_transport_state.receive_cipher_state.decrypt_with_ad(
        b"associated_data_2", ciphertext2
    )
    assert plaintext2 == b"plaintext_2"
