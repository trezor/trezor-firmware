from common import *
from trezor import wire
from trezor.enums import CardanoCertificateType, CardanoTxSigningMode
from trezor.messages import CardanoTxCertificate, CardanoPoolParametersType

from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.cardano.certificates import validate_certificate
    from apps.cardano.helpers import protocol_magics, network_ids
    from apps.cardano.helpers.account_path_check import AccountPathChecker


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoCertificate(unittest.TestCase):
    def test_validate_certificate(self):
        valid_test_vectors = [
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_REGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_REGISTRATION,
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                ),
                CardanoTxSigningMode.MULTISIG_TRANSACTION,
            ),
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DELEGATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DELEGATION,
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                ),
                CardanoTxSigningMode.MULTISIG_TRANSACTION,
            ),
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DEREGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DEREGISTRATION,
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                ),
                CardanoTxSigningMode.MULTISIG_TRANSACTION,
            ),
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_POOL_REGISTRATION,
                    pool_parameters=CardanoPoolParametersType(
                        pool_id=unhexlify(
                            "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                        ),
                        vrf_key_hash=unhexlify(
                            "198890ad6c92e80fbdab554dda02da9fb49d001bbd96181f3e07f7a6ab0d0640"
                        ),
                        pledge=500000000,
                        cost=340000000,
                        margin_numerator=1,
                        margin_denominator=2,
                        reward_account="stake1uya87zwnmax0v6nnn8ptqkl6ydx4522kpsc3l3wmf3yswygwx45el",
                        owners_count=1,
                        relays_count=1,
                        metadata=None,
                    ),
                ),
                CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
            ),
        ]

        invalid_test_vectors = [
            # STAKE_REGISTRATION neither path or script_hash is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_REGISTRATION,
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_REGISTRATION both path and script_hash are set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_REGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_REGISTRATION pool is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_REGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_REGISTRATION pool parameters are set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_REGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    pool_parameters=CardanoPoolParametersType(
                        pool_id=unhexlify(
                            "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                        ),
                        vrf_key_hash=unhexlify(
                            "198890ad6c92e80fbdab554dda02da9fb49d001bbd96181f3e07f7a6ab0d0640"
                        ),
                        pledge=500000000,
                        cost=340000000,
                        margin_numerator=1,
                        margin_denominator=2,
                        reward_account="stake1uya87zwnmax0v6nnn8ptqkl6ydx4522kpsc3l3wmf3yswygwx45el",
                        owners_count=1,
                        relays_count=1,
                    ),
                ),
                CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
            ),
            # STAKE_DELEGATION neither path or script_hash is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DELEGATION,
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_DELEGATION both path and script_hash are set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DELEGATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_DELEGATION pool parameters are set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DELEGATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                    pool_parameters=CardanoPoolParametersType(
                        pool_id=unhexlify(
                            "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                        ),
                        vrf_key_hash=unhexlify(
                            "198890ad6c92e80fbdab554dda02da9fb49d001bbd96181f3e07f7a6ab0d0640"
                        ),
                        pledge=500000000,
                        cost=340000000,
                        margin_numerator=1,
                        margin_denominator=2,
                        reward_account="stake1uya87zwnmax0v6nnn8ptqkl6ydx4522kpsc3l3wmf3yswygwx45el",
                        owners_count=1,
                        relays_count=1,
                    ),
                ),
                CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
            ),
            # STAKE_DEREGISTRATION neither path or script_hash is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DEREGISTRATION,
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_DEREGISTRATION both path and script_hash are set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DEREGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_DEREGISTRATION pool is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DEREGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_DEREGISTRATION pool parameters are set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_DEREGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    pool_parameters=CardanoPoolParametersType(
                        pool_id=unhexlify(
                            "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                        ),
                        vrf_key_hash=unhexlify(
                            "198890ad6c92e80fbdab554dda02da9fb49d001bbd96181f3e07f7a6ab0d0640"
                        ),
                        pledge=500000000,
                        cost=340000000,
                        margin_numerator=1,
                        margin_denominator=2,
                        reward_account="stake1uya87zwnmax0v6nnn8ptqkl6ydx4522kpsc3l3wmf3yswygwx45el",
                        owners_count=1,
                        relays_count=1,
                    ),
                ),
                CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
            ),
            # STAKE_POOL_REGISTRATION pool parameters are not set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_POOL_REGISTRATION,
                ),
                CardanoTxSigningMode.ORDINARY_TRANSACTION,
            ),
            # STAKE_POOL_REGISTRATION path is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_POOL_REGISTRATION,
                    path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                    pool_parameters=CardanoPoolParametersType(
                        pool_id=unhexlify(
                            "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                        ),
                        vrf_key_hash=unhexlify(
                            "198890ad6c92e80fbdab554dda02da9fb49d001bbd96181f3e07f7a6ab0d0640"
                        ),
                        pledge=500000000,
                        cost=340000000,
                        margin_numerator=1,
                        margin_denominator=2,
                        reward_account="stake1uya87zwnmax0v6nnn8ptqkl6ydx4522kpsc3l3wmf3yswygwx45el",
                        owners_count=1,
                        relays_count=1,
                    ),
                ),
                CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
            ),
            # STAKE_POOL_REGISTRATION script hash is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_POOL_REGISTRATION,
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                    pool_parameters=CardanoPoolParametersType(
                        pool_id=unhexlify(
                            "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                        ),
                        vrf_key_hash=unhexlify(
                            "198890ad6c92e80fbdab554dda02da9fb49d001bbd96181f3e07f7a6ab0d0640"
                        ),
                        pledge=500000000,
                        cost=340000000,
                        margin_numerator=1,
                        margin_denominator=2,
                        reward_account="stake1uya87zwnmax0v6nnn8ptqkl6ydx4522kpsc3l3wmf3yswygwx45el",
                        owners_count=1,
                        relays_count=1,
                    ),
                ),
                CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
            ),
            # STAKE_POOL_REGISTRATION pool is set
            (
                CardanoTxCertificate(
                    type=CardanoCertificateType.STAKE_POOL_REGISTRATION,
                    script_hash=unhexlify(
                        "29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd"
                    ),
                    pool=unhexlify(
                        "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                    ),
                    pool_parameters=CardanoPoolParametersType(
                        pool_id=unhexlify(
                            "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb4973"
                        ),
                        vrf_key_hash=unhexlify(
                            "198890ad6c92e80fbdab554dda02da9fb49d001bbd96181f3e07f7a6ab0d0640"
                        ),
                        pledge=500000000,
                        cost=340000000,
                        margin_numerator=1,
                        margin_denominator=2,
                        reward_account="stake1uya87zwnmax0v6nnn8ptqkl6ydx4522kpsc3l3wmf3yswygwx45el",
                        owners_count=1,
                        relays_count=1,
                    ),
                ),
                CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
            ),
        ]

        for certificate, signing_mode in valid_test_vectors:
            validate_certificate(
                certificate,
                signing_mode,
                protocol_magics.MAINNET,
                network_ids.MAINNET,
                AccountPathChecker(),
            )

        for certificate, signing_mode in invalid_test_vectors:
            with self.assertRaises(wire.ProcessError):
                validate_certificate(
                    certificate,
                    signing_mode,
                    protocol_magics.MAINNET,
                    network_ids.MAINNET,
                    AccountPathChecker(),
                )


if __name__ == "__main__":
    unittest.main()
