from common import *

if not utils.BITCOIN_ONLY:
    from apps.eos.actions import check_action
    from trezor.messages import EosTxActionAck


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEosActions(unittest.TestCase):
    def test_check_action(self):
        # return True
        self.assertEqual(check_action(EosTxActionAck(common=object(), buy_ram=object()), 'buyram', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), buy_ram_bytes=object()), 'buyrambytes', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), sell_ram=object()), 'sellram', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), delegate=object()), 'delegatebw', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), undelegate=object()), 'undelegatebw', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), refund=object()), 'refund', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), vote_producer=object()), 'voteproducer', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), update_auth=object()), 'updateauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), delete_auth=object()), 'deleteauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), link_auth=object()), 'linkauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), unlink_auth=object()), 'unlinkauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), new_account=object()), 'newaccount', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), transfer=object()), 'transfer', 'not_eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), unknown=[]), 'unknown', 'not_eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=object(), unknown=[]), 'buyram', 'buygoods'), True)

        # returns False
        self.assertEqual(check_action(EosTxActionAck(common=object(), buy_ram=object()), 'buyram', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object()), 'buyram', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), buy_ram_bytes=object()), 'buyrambytes', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), sell_ram=object()), 'sellram', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), delegate=object()), 'delegatebw', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), undelegate=object()), 'undelegatebw', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), refund=object()), 'refund', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object()), 'refund', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), vote_producer=object()), 'voteproducer', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), update_auth=object()), 'updateauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), delete_auth=object()), 'deleteauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), link_auth=object()), 'linkauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), unlink_auth=object()), 'unlinkauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object()), 'unlinkauth', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), new_account=object()), 'newaccount', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), transfer=object()), 'transfer', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object()), 'unknown', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), buy_ram=object()), 'test', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), unknown=[]), 'buyram', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=object(), unknown=[]), 'transfer', 'loveme'), False)


if __name__ == '__main__':
    unittest.main()
