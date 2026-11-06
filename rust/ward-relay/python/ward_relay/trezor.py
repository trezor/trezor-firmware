"""WARD forwarding on a borrowed trezorlib session; no device connection is opened."""


class WardHwi:
    """Borrow a caller-provided trezorlib session and restore its proof handler on exit."""

    def __init__(self, session, adapter):
        from trezorlib import messages, protobuf

        self.session = session
        self.adapter = adapter
        self._messages = messages
        self._protobuf = protobuf
        self._previous = None
        self._entered = False

    # FIXME(ward): same redesign as trezorlib.ward_relay.WardAdapter. While entered, `_pull` is
    # installed on the CLIENT-WIDE AppManifest, so it answers pulls from every session on that
    # client, not only this one. Scope it to one call on one session instead: install it in a
    # per-session `ward_hooks` slot around `forward`'s `session.call` only, restoring the
    # previous value from a local variable.
    def __enter__(self):
        if self._entered:
            raise RuntimeError("WARD session forwarding is already active")
        app = self.session.client.app
        self._previous = (app.ward_proof_callback, app.ward_node_callback)
        app.ward_proof_callback = self._pull
        app.ward_node_callback = self._pull
        self._entered = True
        return self

    def __exit__(self, *_):
        app = self.session.client.app
        app.ward_proof_callback, app.ward_node_callback = self._previous
        self._entered = False

    def _pull(self, request):
        """Answer a WARDProofRequest or WARDNodeRequest through wardd. A proof request
        wardd cannot serve is answered `unavailable` (the device may then use a sticky
        cached entry); a listing walk has no such fallback."""
        name = type(request).__name__
        try:
            answer = self.adapter.answer_ward_request(
                name, self._protobuf.to_dict(request)
            )
        except Exception:
            if name != "WARDProofRequest":
                raise
            # ACCEPTED: any wardd failure is reported as `unavailable`; the device may then
            # show a STICKY cached label, possibly stale, marked as cached.
            return self._messages.WARDProofAck(unavailable=True)
        return self._protobuf.dict_to_proto(
            getattr(self._messages, answer["name"]), answer["message"]
        )

    def forward(self, name, message):
        from trezorlib.exceptions import Cancelled, TrezorFailure

        if not self._entered:
            raise RuntimeError("Use WardHwi as a context manager")
        request = self._protobuf.dict_to_proto(getattr(self._messages, name), message)
        try:
            response = self.session.call(request)
        except TrezorFailure as error:
            response = error.failure
        except Cancelled as error:
            response = self._messages.Failure(
                code=self._messages.FailureType.ActionCancelled, message=str(error)
            )
        return type(response).__name__, self._protobuf.to_dict(response)

    def call(self, method, params):
        if not self._entered:
            raise RuntimeError("Use WardHwi as a context manager")
        return self.adapter.call(method, params, self.forward)
