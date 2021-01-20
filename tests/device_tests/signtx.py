from trezorlib import messages

T = messages.RequestType


def request_input(n: int, tx_hash: bytes = None) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXINPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_output(n: int, tx_hash: bytes = None) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXOUTPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_orig_input(n: int, tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXORIGINPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_orig_output(n: int, tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXORIGOUTPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_payment_req(n):
    return messages.TxRequest(
        request_type=T.TXPAYMENTREQ,
        details=messages.TxRequestDetailsType(request_index=n),
    )


def request_meta(tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXMETA,
        details=messages.TxRequestDetailsType(tx_hash=tx_hash),
    )


def request_finished() -> messages.TxRequest:
    return messages.TxRequest(request_type=T.TXFINISHED)


def request_extra_data(ofs: int, len: int, tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXEXTRADATA,
        details=messages.TxRequestDetailsType(
            tx_hash=tx_hash, extra_data_offset=ofs, extra_data_len=len
        ),
    )
