void fsm_msgStellarGetPublicKey(StellarGetPublicKey *msg)
{
    RESP_INIT(StellarPublicKey);

    CHECK_INITIALIZED

    CHECK_PIN

    // Will exit if the user does not confirm
    stellar_layoutGetPublicKey(msg->address_n, msg->address_n_count);

    // Read public key and write it to the response
    resp->has_public_key = true;
    resp->public_key.size = 32;
    stellar_getPubkeyAtAddress(msg->address_n, msg->address_n_count, resp->public_key.bytes, sizeof(resp->public_key.bytes));

    msg_write(MessageType_MessageType_StellarPublicKey, resp);

    layoutHome();
}

void fsm_msgStellarSignMessage(StellarSignMessage *msg)
{
    RESP_INIT(StellarMessageSignature);

    CHECK_INITIALIZED

	layoutSignMessage(msg->message.bytes, msg->message.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

    CHECK_PIN

    // Populate response message
    stellar_signMessage(msg->message.bytes, msg->message.size, msg->address_n, msg->address_n_count, resp->signature.bytes);
    resp->has_signature = true;
    resp->signature.size = 64;

    stellar_getPubkeyAtAddress(msg->address_n, msg->address_n_count, resp->public_key.bytes, sizeof(resp->public_key.bytes));
    resp->has_public_key = true;
    resp->public_key.size = 32;

    msg_write(MessageType_MessageType_StellarMessageSignature, resp);

    layoutHome();
}

void fsm_msgStellarVerifyMessage(StellarVerifyMessage *msg)
{
    if (!stellar_verifyMessage(msg)) {
        fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature"));
        return;
    }

    fsm_sendSuccess(_("Message verified"));
    layoutHome();
}

void fsm_msgStellarSignTx(StellarSignTx *msg)
{
    CHECK_INITIALIZED
    CHECK_PIN

    stellar_signingInit(msg);

    // Confirm transaction basics
    stellar_layoutTransactionSummary(msg);

    // Respond with a request for the first operation
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
}

void fsm_msgStellarCreateAccountOp(StellarCreateAccountOp *msg)
{
    stellar_confirmCreateAccountOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarPaymentOp(StellarPaymentOp *msg)
{
    // This will display additional dialogs to the user
    stellar_confirmPaymentOp(msg);

    // Last operation was confirmed, send a StellarSignedTx
    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarPathPaymentOp(StellarPathPaymentOp *msg)
{
    stellar_confirmPathPaymentOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarManageOfferOp(StellarManageOfferOp *msg)
{
    stellar_confirmManageOfferOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarCreatePassiveOfferOp(StellarCreatePassiveOfferOp *msg)
{
    stellar_confirmCreatePassiveOfferOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarSetOptionsOp(StellarSetOptionsOp *msg)
{
    stellar_confirmSetOptionsOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarChangeTrustOp(StellarChangeTrustOp *msg)
{
    stellar_confirmChangeTrustOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarAllowTrustOp(StellarAllowTrustOp *msg)
{
    stellar_confirmAllowTrustOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarAccountMergeOp(StellarAccountMergeOp *msg)
{
    stellar_confirmAccountMergeOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarManageDataOp(StellarManageDataOp *msg)
{
    stellar_confirmManageDataOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarBumpSequenceOp(StellarBumpSequenceOp *msg)
{
    stellar_confirmBumpSequenceOp(msg);

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}