import mock

from trezorlib.transport import all_transports


def test_all_transports_without_hid():
    # import all transports, assume this doesn't fail
    transports_ref = all_transports()
    # also shouldn't fail when bridge transport is missing
    with mock.patch.dict('sys.modules', {'trezorlib.transport.bridge': None}):
        transports = all_transports()
        # there should now be less transports
        assert len(transports_ref) > len(transports)
