void fsm_msgCipherKeyValue(CipherKeyValue *msg)
{
	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_key, _("No key provided"));
	CHECK_PARAM(msg->has_value, _("No value provided"));
	CHECK_PARAM(msg->value.size % 16 == 0, _("Value length must be a multiple of 16"));

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count, NULL);
	if (!node) return;

	bool encrypt = msg->has_encrypt && msg->encrypt;
	bool ask_on_encrypt = msg->has_ask_on_encrypt && msg->ask_on_encrypt;
	bool ask_on_decrypt = msg->has_ask_on_decrypt && msg->ask_on_decrypt;
	if ((encrypt && ask_on_encrypt) || (!encrypt && ask_on_decrypt)) {
		layoutCipherKeyValue(encrypt, msg->key);
		if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	uint8_t data[256 + 4];
	strlcpy((char *)data, msg->key, sizeof(data));
	strlcat((char *)data, ask_on_encrypt ? "E1" : "E0", sizeof(data));
	strlcat((char *)data, ask_on_decrypt ? "D1" : "D0", sizeof(data));

	hmac_sha512(node->private_key, 32, data, strlen((char *)data), data);

	RESP_INIT(CipheredKeyValue);
	if (encrypt) {
		aes_encrypt_ctx ctx;
		aes_encrypt_key256(data, &ctx);
		aes_cbc_encrypt(msg->value.bytes, resp->value.bytes, msg->value.size, ((msg->iv.size == 16) ? (msg->iv.bytes) : (data + 32)), &ctx);
	} else {
		aes_decrypt_ctx ctx;
		aes_decrypt_key256(data, &ctx);
		aes_cbc_decrypt(msg->value.bytes, resp->value.bytes, msg->value.size, ((msg->iv.size == 16) ? (msg->iv.bytes) : (data + 32)), &ctx);
	}
	resp->has_value = true;
	resp->value.size = msg->value.size;
	msg_write(MessageType_MessageType_CipheredKeyValue, resp);
	layoutHome();
}

void fsm_msgSignIdentity(SignIdentity *msg)
{
	RESP_INIT(SignedIdentity);

	CHECK_INITIALIZED

	layoutSignIdentity(&(msg->identity), msg->has_challenge_visual ? msg->challenge_visual : 0);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	uint8_t hash[32];
	if (!msg->has_identity || cryptoIdentityFingerprint(&(msg->identity), hash) == 0) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid identity"));
		layoutHome();
		return;
	}

	uint32_t address_n[5];
	address_n[0] = 0x80000000 | 13;
	address_n[1] = 0x80000000 | hash[ 0] | (hash[ 1] << 8) | (hash[ 2] << 16) | ((uint32_t) hash[ 3] << 24);
	address_n[2] = 0x80000000 | hash[ 4] | (hash[ 5] << 8) | (hash[ 6] << 16) | ((uint32_t) hash[ 7] << 24);
	address_n[3] = 0x80000000 | hash[ 8] | (hash[ 9] << 8) | (hash[10] << 16) | ((uint32_t) hash[11] << 24);
	address_n[4] = 0x80000000 | hash[12] | (hash[13] << 8) | (hash[14] << 16) | ((uint32_t) hash[15] << 24);

	const char *curve = SECP256K1_NAME;
	if (msg->has_ecdsa_curve_name) {
		curve = msg->ecdsa_curve_name;
	}
	HDNode *node = fsm_getDerivedNode(curve, address_n, 5, NULL);
	if (!node) return;

	bool sign_ssh = msg->identity.has_proto && (strcmp(msg->identity.proto, "ssh") == 0);
	bool sign_gpg = msg->identity.has_proto && (strcmp(msg->identity.proto, "gpg") == 0);

	int result = 0;
	layoutProgressSwipe(_("Signing"), 0);
	if (sign_ssh) { // SSH does not sign visual challenge
		result = sshMessageSign(node, msg->challenge_hidden.bytes, msg->challenge_hidden.size, resp->signature.bytes);
	} else if (sign_gpg) { // GPG should sign a message digest
		result = gpgMessageSign(node, msg->challenge_hidden.bytes, msg->challenge_hidden.size, resp->signature.bytes);
	} else {
		uint8_t digest[64];
		sha256_Raw(msg->challenge_hidden.bytes, msg->challenge_hidden.size, digest);
		sha256_Raw((const uint8_t *)msg->challenge_visual, strlen(msg->challenge_visual), digest + 32);
		result = cryptoMessageSign(&(coins[0]), node, InputScriptType_SPENDADDRESS, digest, 64, resp->signature.bytes);
	}

	if (result == 0) {
		hdnode_fill_public_key(node);
		if (strcmp(curve, SECP256K1_NAME) != 0) {
			resp->has_address = false;
		} else {
			resp->has_address = true;
			hdnode_get_address(node, 0x00, resp->address, sizeof(resp->address)); // hardcoded Bitcoin address type
		}
		resp->has_public_key = true;
		resp->public_key.size = 33;
		memcpy(resp->public_key.bytes, node->public_key, 33);
		if (node->public_key[0] == 1) {
			/* ed25519 public key */
			resp->public_key.bytes[0] = 0;
		}
		resp->has_signature = true;
		resp->signature.size = 65;
		msg_write(MessageType_MessageType_SignedIdentity, resp);
	} else {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Error signing identity"));
	}
	layoutHome();
}

void fsm_msgGetECDHSessionKey(GetECDHSessionKey *msg)
{
	RESP_INIT(ECDHSessionKey);

	CHECK_INITIALIZED

	layoutDecryptIdentity(&msg->identity);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	uint8_t hash[32];
	if (!msg->has_identity || cryptoIdentityFingerprint(&(msg->identity), hash) == 0) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid identity"));
		layoutHome();
		return;
	}

	uint32_t address_n[5];
	address_n[0] = 0x80000000 | 17;
	address_n[1] = 0x80000000 | hash[ 0] | (hash[ 1] << 8) | (hash[ 2] << 16) | ((uint32_t) hash[ 3] << 24);
	address_n[2] = 0x80000000 | hash[ 4] | (hash[ 5] << 8) | (hash[ 6] << 16) | ((uint32_t) hash[ 7] << 24);
	address_n[3] = 0x80000000 | hash[ 8] | (hash[ 9] << 8) | (hash[10] << 16) | ((uint32_t) hash[11] << 24);
	address_n[4] = 0x80000000 | hash[12] | (hash[13] << 8) | (hash[14] << 16) | ((uint32_t) hash[15] << 24);

	const char *curve = SECP256K1_NAME;
	if (msg->has_ecdsa_curve_name) {
		curve = msg->ecdsa_curve_name;
	}

	const HDNode *node = fsm_getDerivedNode(curve, address_n, 5, NULL);
	if (!node) return;

	int result_size = 0;
	if (hdnode_get_shared_key(node, msg->peer_public_key.bytes, resp->session_key.bytes, &result_size) == 0) {
		resp->has_session_key = true;
		resp->session_key.size = result_size;
		msg_write(MessageType_MessageType_ECDHSessionKey, resp);
	} else {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Error getting ECDH session key"));
	}
	layoutHome();
}

/* ECIES disabled
void fsm_msgEncryptMessage(EncryptMessage *msg)
{
	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_pubkey, _("No public key provided"));
	CHECK_PARAM(msg->has_message, _("No message provided"));
	CHECK_PARAM(msg->pubkey.size == 33, _("Invalid public key provided"));
	curve_point pubkey;
	CHECK_PARAM(ecdsa_read_pubkey(&secp256k1, msg->pubkey.bytes, &pubkey) == 1, _("Invalid public key provided"));

	bool display_only = msg->has_display_only && msg->display_only;
	bool signing = msg->address_n_count > 0;
	RESP_INIT(EncryptedMessage);
	const HDNode *node = 0;
	uint8_t address_raw[MAX_ADDR_RAW_SIZE];
	if (signing) {
		const CoinInfo *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
		if (!coin) return;

		CHECK_PIN

		node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count, NULL);
		if (!node) return;
		hdnode_get_address_raw(node, coin->address_type, address_raw);
	}
	layoutEncryptMessage(msg->message.bytes, msg->message.size, signing);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	layoutProgressSwipe(_("Encrypting"), 0);
	if (cryptoMessageEncrypt(&pubkey, msg->message.bytes, msg->message.size, display_only, resp->nonce.bytes, &(resp->nonce.size), resp->message.bytes, &(resp->message.size), resp->hmac.bytes, &(resp->hmac.size), signing ? node->private_key : 0, signing ? address_raw : 0) != 0) {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Error encrypting message"));
		layoutHome();
		return;
	}
	resp->has_nonce = true;
	resp->has_message = true;
	resp->has_hmac = true;
	msg_write(MessageType_MessageType_EncryptedMessage, resp);
	layoutHome();
}

void fsm_msgDecryptMessage(DecryptMessage *msg)
{
	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_nonce, _("No nonce provided"));
	CHECK_PARAM(msg->has_message, _("No message provided"));
	CHECK_PARAM(msg->has_hmac, _("No message hmac provided"));

	CHECK_PARAM(msg->nonce.size == 33, _("Invalid nonce key provided"));
	curve_point nonce_pubkey;
	CHECK_PARAM(ecdsa_read_pubkey(&secp256k1, msg->nonce.bytes, &nonce_pubkey) == 1, _("Invalid nonce provided"));

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count, NULL);
	if (!node) return;

	layoutProgressSwipe(_("Decrypting"), 0);
	RESP_INIT(DecryptedMessage);
	bool display_only = false;
	bool signing = false;
	uint8_t address_raw[MAX_ADDR_RAW_SIZE];
	if (cryptoMessageDecrypt(&nonce_pubkey, msg->message.bytes, msg->message.size, msg->hmac.bytes, msg->hmac.size, node->private_key, resp->message.bytes, &(resp->message.size), &display_only, &signing, address_raw) != 0) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	if (signing) {
		base58_encode_check(address_raw, 21, resp->address, sizeof(resp->address));
	}
	layoutDecryptMessage(resp->message.bytes, resp->message.size, signing ? resp->address : 0);
	protectButton(ButtonRequestType_ButtonRequest_Other, true);
	if (display_only) {
		resp->has_address = false;
		resp->has_message = false;
		memset(resp->address, 0, sizeof(resp->address));
		memset(&(resp->message), 0, sizeof(resp->message));
	} else {
		resp->has_address = signing;
		resp->has_message = true;
	}
	msg_write(MessageType_MessageType_DecryptedMessage, resp);
	layoutHome();
}
*/

void fsm_msgCosiCommit(CosiCommit *msg)
{
	RESP_INIT(CosiCommitment);

	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_data, _("No data provided"));

	layoutCosiCommitSign(msg->address_n, msg->address_n_count, msg->data.bytes, msg->data.size, false);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n, msg->address_n_count, NULL);
	if (!node) return;

	uint8_t nonce[32];
	sha256_Raw(msg->data.bytes, msg->data.size, nonce);
	rfc6979_state rng;
	init_rfc6979(node->private_key, nonce, &rng);
	generate_rfc6979(nonce, &rng);

	resp->has_commitment = true;
	resp->has_pubkey = true;
	resp->commitment.size = 32;
	resp->pubkey.size = 32;

	ed25519_publickey(nonce, resp->commitment.bytes);
	ed25519_publickey(node->private_key, resp->pubkey.bytes);

	msg_write(MessageType_MessageType_CosiCommitment, resp);
	layoutHome();
}

void fsm_msgCosiSign(CosiSign *msg)
{
	RESP_INIT(CosiSignature);

	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_data, _("No data provided"));
	CHECK_PARAM(msg->has_global_commitment && msg->global_commitment.size == 32, _("Invalid global commitment"));
	CHECK_PARAM(msg->has_global_pubkey && msg->global_pubkey.size == 32, _("Invalid global pubkey"));

	layoutCosiCommitSign(msg->address_n, msg->address_n_count, msg->data.bytes, msg->data.size, true);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n, msg->address_n_count, NULL);
	if (!node) return;

	uint8_t nonce[32];
	sha256_Raw(msg->data.bytes, msg->data.size, nonce);
	rfc6979_state rng;
	init_rfc6979(node->private_key, nonce, &rng);
	generate_rfc6979(nonce, &rng);

	resp->has_signature = true;
	resp->signature.size = 32;

	ed25519_cosi_sign(msg->data.bytes, msg->data.size, node->private_key, nonce, msg->global_commitment.bytes, msg->global_pubkey.bytes, resp->signature.bytes);

	msg_write(MessageType_MessageType_CosiSignature, resp);
	layoutHome();
}