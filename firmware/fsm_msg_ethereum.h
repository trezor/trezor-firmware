void fsm_msgEthereumSignTx(EthereumSignTx *msg)
{
	CHECK_INITIALIZED

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count, NULL);
	if (!node) return;

	ethereum_signing_init(msg, node);
}

void fsm_msgEthereumTxAck(EthereumTxAck *msg)
{
	ethereum_signing_txack(msg);
}

void fsm_msgEthereumGetAddress(EthereumGetAddress *msg)
{
	RESP_INIT(EthereumAddress);

	CHECK_INITIALIZED

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count, NULL);
	if (!node) return;

	resp->address.size = 20;

	if (!hdnode_get_ethereum_pubkeyhash(node, resp->address.bytes))
		return;

	if (msg->has_show_display && msg->show_display) {
		char desc[16];
		strlcpy(desc, "Address:", sizeof(desc));

		uint32_t slip44 = msg->address_n[1] & 0x7fffffff;
		bool rskip60 = false;
		uint32_t chain_id = 0;
		// constants from trezor-common/defs/ethereum/networks.json
		switch (slip44) {
			case 137: rskip60 = true; chain_id = 30; break;
			case 37310: rskip60 = true; chain_id = 31; break;
		}

		char address[43] = { '0', 'x' };
		ethereum_address_checksum(resp->address.bytes, address + 2, rskip60, chain_id);

		if (!fsm_layoutAddress(address, desc, false, 0, msg->address_n, msg->address_n_count)) {
			return;
		}
	}

	msg_write(MessageType_MessageType_EthereumAddress, resp);
	layoutHome();
}

void fsm_msgEthereumSignMessage(EthereumSignMessage *msg)
{
	RESP_INIT(EthereumMessageSignature);

	CHECK_INITIALIZED

	layoutSignMessage(msg->message.bytes, msg->message.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count, NULL);
	if (!node) return;

	ethereum_message_sign(msg, node, resp);
	layoutHome();
}

void fsm_msgEthereumVerifyMessage(EthereumVerifyMessage *msg)
{
	CHECK_PARAM(msg->has_address, _("No address provided"));
	CHECK_PARAM(msg->has_message, _("No message provided"));

	if (ethereum_message_verify(msg) != 0) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature"));
		return;
	}

	char address[43] = { '0', 'x' };
	ethereum_address_checksum(msg->address.bytes, address + 2, false, 0);
	layoutVerifyAddress(address);
	if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	layoutVerifyMessage(msg->message.bytes, msg->message.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	fsm_sendSuccess(_("Message verified"));

	layoutHome();
}