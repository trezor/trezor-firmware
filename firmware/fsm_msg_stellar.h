void fsm_msgStellarGetAddress(StellarGetAddress *msg)
{
    RESP_INIT(StellarAddress);

    CHECK_INITIALIZED

    CHECK_PIN

    HDNode *node = stellar_deriveNode(msg->address_n, msg->address_n_count);
    if (!node) {
        fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to derive private key"));
        return;
    }

    if (msg->has_show_display && msg->show_display) {
        const char **str_addr_rows = stellar_lineBreakAddress(node->public_key + 1);
        layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), _("Share public account ID?"),
            str_addr_rows[0],
            str_addr_rows[1],
            str_addr_rows[2],
            NULL,
            NULL, NULL
            );
        if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
            fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
            layoutHome();
            return;
        }
    }

    resp->has_address = true;
    stellar_publicAddressAsStr(node->public_key + 1, resp->address, sizeof(resp->address));

    msg_write(MessageType_MessageType_StellarAddress, resp);

    layoutHome();
}

void fsm_msgStellarGetPublicKey(StellarGetPublicKey *msg)
{
    RESP_INIT(StellarPublicKey);

    CHECK_INITIALIZED

    CHECK_PIN

    HDNode *node = stellar_deriveNode(msg->address_n, msg->address_n_count);
    if (!node) {
        fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to derive private key"));
        return;
    }

    if (msg->has_show_display && msg->show_display) {
        char hex[32 * 2 + 1];
        data2hex(node->public_key + 1, 32, hex);
        const char **str_pubkey_rows = split_message((const uint8_t *)hex, 32 * 2, 16);
        layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), _("Share public account ID?"),
            str_pubkey_rows[0],
            str_pubkey_rows[1],
            str_pubkey_rows[2],
            str_pubkey_rows[3],
            NULL, NULL
            );
        if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
            fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
            layoutHome();
            return;
        }
    }

    // Read public key and write it to the response
    resp->has_public_key = true;
    resp->public_key.size = 32;
    memcpy(resp->public_key.bytes, node->public_key + 1, 32);

    msg_write(MessageType_MessageType_StellarPublicKey, resp);

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