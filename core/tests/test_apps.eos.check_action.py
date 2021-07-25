from common import *

if not utils.BITCOIN_ONLY:
    from apps.eos.actions import check_action
    from trezor.messages import EosTxActionAck
    from trezor.messages import EosActionBuyRam
    from trezor.messages import EosActionBuyRamBytes
    from trezor.messages import EosActionDelegate
    from trezor.messages import EosActionDeleteAuth
    from trezor.messages import EosActionLinkAuth
    from trezor.messages import EosActionNewAccount
    from trezor.messages import EosActionRefund
    from trezor.messages import EosActionSellRam
    from trezor.messages import EosActionTransfer
    from trezor.messages import EosActionUndelegate
    from trezor.messages import EosActionUnlinkAuth
    from trezor.messages import EosActionUpdateAuth
    from trezor.messages import EosActionVoteProducer


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEosActions(unittest.TestCase):
    def test_check_action(self):
        # return True
        self.assertEqual(check_action(EosTxActionAck(buy_ram=EosActionBuyRam()), 'buyram', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(buy_ram_bytes=EosActionBuyRamBytes()), 'buyrambytes', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(sell_ram=EosActionSellRam()), 'sellram', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(delegate=EosActionDelegate()), 'delegatebw', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(undelegate=EosActionDeleteAuth()), 'undelegatebw', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(refund=EosActionRefund()), 'refund', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(vote_producer=EosActionVoteProducer()), 'voteproducer', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(update_auth=EosActionUpdateAuth()), 'updateauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(delete_auth=EosActionDeleteAuth()), 'deleteauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(link_auth=EosActionLinkAuth()), 'linkauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(unlink_auth=EosActionUnlinkAuth()), 'unlinkauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(new_account=EosActionNewAccount()), 'newaccount', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(transfer=EosActionTransfer()), 'transfer', 'not_eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(unknown=[]), 'unknown', 'not_eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(unknown=[]), 'buyram', 'buygoods'), True)

        # returns False
        self.assertEqual(check_action(EosTxActionAck(buy_ram=EosActionBuyRam()), 'buyram', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(), 'buyram', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(buy_ram_bytes=EosActionBuyRamBytes()), 'buyrambytes', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(sell_ram=EosActionSellRam()), 'sellram', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(delegate=EosActionDelegate()), 'delegatebw', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(undelegate=EosActionDeleteAuth()), 'undelegatebw', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(refund=EosActionRefund()), 'refund', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(), 'refund', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(vote_producer=EosActionVoteProducer()), 'voteproducer', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(update_auth=EosActionUpdateAuth()), 'updateauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(delete_auth=EosActionDeleteAuth()), 'deleteauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(link_auth=EosActionLinkAuth()), 'linkauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(unlink_auth=EosActionUnlinkAuth()), 'unlinkauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(), 'unlinkauth', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(new_account=EosActionNewAccount()), 'newaccount', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(transfer=EosActionTransfer()), 'transfer', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(), 'unknown', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(buy_ram=EosActionBuyRam()), 'test', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(unknown=[]), 'buyram', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(unknown=[]), 'transfer', 'loveme'), False)


if __name__ == '__main__':
    unittest.main()
