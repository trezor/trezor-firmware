from common import *

if not utils.BITCOIN_ONLY:
    from apps.eos.actions import check_action
    from trezor.messages import (
        EosTxActionAck,
        EosActionBuyRam,
        EosActionBuyRamBytes,
        EosActionDelegate,
        EosActionDeleteAuth,
        EosActionLinkAuth,
        EosActionNewAccount,
        EosActionRefund,
        EosActionSellRam,
        EosActionTransfer,
        EosActionUnlinkAuth,
        EosActionUpdateAuth,
        EosActionVoteProducer,
        EosAsset,
        EosActionCommon,
    )

# Way of easily filling the required arguments into protobuf messages
common = EosActionCommon(
    account=5,
    name=5,
)
kwargs = {
    "payer": 5,
    "receiver": 5,
    "account": 5,
    "bytes": 5,
    "sender": 5,
    "permission": 5,
    "owner": 5,
    "voter": 5,
    "proxy": 5,
    "parent": 5,
    "auth": 5,
    "code": 5,
    "type": 5,
    "requirement": 5,
    "creator": 5,
    "name": 5,
    "active": 5,
    "sender": 5,
    "memo": 5,
    "net_quantity": 5,
    "cpu_quantity": 5,
    "transfer": 5,
    "quantity": 5,
}

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEosActions(unittest.TestCase):
    def test_check_action(self):
        # return True
        self.assertEqual(check_action(EosTxActionAck(common=common, buy_ram=EosActionBuyRam(**kwargs)), 'buyram', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, buy_ram_bytes=EosActionBuyRamBytes(**kwargs)), 'buyrambytes', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, sell_ram=EosActionSellRam(**kwargs)), 'sellram', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, delegate=EosActionDelegate(**kwargs)), 'delegatebw', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, undelegate=EosActionDeleteAuth(**kwargs)), 'undelegatebw', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, refund=EosActionRefund(**kwargs)), 'refund', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, vote_producer=EosActionVoteProducer(**kwargs)), 'voteproducer', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, update_auth=EosActionUpdateAuth(**kwargs)), 'updateauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, delete_auth=EosActionDeleteAuth(**kwargs)), 'deleteauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, link_auth=EosActionLinkAuth(**kwargs)), 'linkauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, unlink_auth=EosActionUnlinkAuth(**kwargs)), 'unlinkauth', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, new_account=EosActionNewAccount(**kwargs)), 'newaccount', 'eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, transfer=EosActionTransfer(**kwargs)), 'transfer', 'not_eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, unknown=[]), 'unknown', 'not_eosio'), True)
        self.assertEqual(check_action(EosTxActionAck(common=common, unknown=[]), 'buyram', 'buygoods'), True)

        # returns False
        self.assertEqual(check_action(EosTxActionAck(common=common, buy_ram=EosActionBuyRam(**kwargs)), 'buyram', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, ), 'buyram', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, buy_ram_bytes=EosActionBuyRamBytes(**kwargs)), 'buyrambytes', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, sell_ram=EosActionSellRam(**kwargs)), 'sellram', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, delegate=EosActionDelegate(**kwargs)), 'delegatebw', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, undelegate=EosActionDeleteAuth(**kwargs)), 'undelegatebw', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, refund=EosActionRefund(**kwargs)), 'refund', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, ), 'refund', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, vote_producer=EosActionVoteProducer(**kwargs)), 'voteproducer', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, update_auth=EosActionUpdateAuth(**kwargs)), 'updateauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, delete_auth=EosActionDeleteAuth(**kwargs)), 'deleteauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, link_auth=EosActionLinkAuth(**kwargs)), 'linkauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, unlink_auth=EosActionUnlinkAuth(**kwargs)), 'unlinkauth', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, ), 'unlinkauth', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, new_account=EosActionNewAccount(**kwargs)), 'newaccount', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, transfer=EosActionTransfer(**kwargs)), 'transfer', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, ), 'unknown', 'not_eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, buy_ram=EosActionBuyRam(**kwargs)), 'test', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, unknown=[]), 'buyram', 'eosio'), False)
        self.assertEqual(check_action(EosTxActionAck(common=common, unknown=[]), 'transfer', 'loveme'), False)


if __name__ == '__main__':
    unittest.main()
