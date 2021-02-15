from trezorlib import messages

T = messages.RequestType


def request_input(n, tx_hash=None):
    return messages.TxRequest(
        request_type=T.TXINPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_output(n, tx_hash=None):
    return messages.TxRequest(
        request_type=T.TXOUTPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_orig_input(n, tx_hash):
    return messages.TxRequest(
        request_type=T.TXORIGINPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_orig_output(n, tx_hash):
    return messages.TxRequest(
        request_type=T.TXORIGOUTPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_meta(tx_hash):
    return messages.TxRequest(
        request_type=T.TXMETA,
        details=messages.TxRequestDetailsType(tx_hash=tx_hash),
    )


def request_finished():
    return messages.TxRequest(request_type=T.TXFINISHED)


def request_extra_data(ofs, len, tx_hash):
    return messages.TxRequest(
        request_type=T.TXEXTRADATA,
        details=messages.TxRequestDetailsType(
            tx_hash=tx_hash, extra_data_offset=ofs, extra_data_len=len
        ),
    )
