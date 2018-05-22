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