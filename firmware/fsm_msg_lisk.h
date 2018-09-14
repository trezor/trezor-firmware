void fsm_msgLiskGetAddress(LiskGetAddress *msg)
{
    CHECK_INITIALIZED

    CHECK_PIN

    RESP_INIT(LiskAddress);

    HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n, msg->address_n_count, NULL);
    if (!node) return;

    resp->has_address = true;

    if (!hdnode_get_lisk_address(node, resp->address))
		return;

	if (msg->has_show_display && msg->show_display) {
		char desc[16];
		strlcpy(desc, "Address:", sizeof(desc));

		if (!fsm_layoutAddress(resp->address, desc, true, 0, msg->address_n, msg->address_n_count)) {
			return;
		}
	}

    msg_write(MessageType_MessageType_LiskAddress, resp);

    layoutHome();
}

void fsm_msgLiskGetPublicKey(LiskGetPublicKey *msg)
{
    CHECK_INITIALIZED

    CHECK_PIN

    RESP_INIT(LiskPublicKey);

    HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n, msg->address_n_count, NULL);
    if (!node) return;

    hdnode_fill_public_key(node);

    resp->has_public_key = true;
    resp->public_key.size = 32;

	if (msg->has_show_display && msg->show_display) {
		layoutLiskPublicKey(&node->public_key[1]);
		if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

    memcpy(&resp->public_key.bytes, &node->public_key[1], sizeof(resp->public_key.bytes));

    msg_write(MessageType_MessageType_LiskPublicKey, resp);

    layoutHome();
}

void fsm_msgLiskSignMessage(LiskSignMessage *msg)
{
    CHECK_INITIALIZED

    CHECK_PIN

    RESP_INIT(LiskMessageSignature);

    HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n, msg->address_n_count, NULL);
    if (!node) return;

    hdnode_fill_public_key(node);

    lisk_sign_message(node, msg, resp);

    msg_write(MessageType_MessageType_LiskMessageSignature, resp);

    layoutHome();
}

void fsm_msgLiskVerifyMessage(LiskVerifyMessage *msg)
{
    if (lisk_verify_message(msg)) {
        char address[23];
        lisk_get_address_from_public_key((const uint8_t*)&msg->public_key, address);

        layoutLiskVerifyAddress(address);
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
    } else {
        fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature"));
    }

    layoutHome();
}

void fsm_msgLiskSignTx(LiskSignTx *msg)
{
	CHECK_INITIALIZED

	CHECK_PIN

    RESP_INIT(LiskSignedTx);

    HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n, msg->address_n_count, NULL);
    if (!node) return;

    hdnode_fill_public_key(node);

    lisk_sign_tx(node, msg, resp);

    msg_write(MessageType_MessageType_LiskSignedTx, resp);

    layoutHome();
}
