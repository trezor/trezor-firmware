from micropython import const

from trezor.crypto import base58

from apps.ethereum.clear_signing import (
    AddressNameFormatter,
    Atomic,
    DisplayFormat,
    FieldDefinition,
    TokenAmountFormatter,
    parse_address,
    parse_uint256,
)

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/ercs/calldata-erc20-tokens.json#L27

APPROVE_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=base58.keccak_32(b"approve(address,uint256)"),
    intent="Approve",
    parameter_definitions=[
        Atomic(parse_address),  # _spender
        Atomic(parse_uint256),  # _value
    ],
    field_definitions=[
        FieldDefinition((0,), "Spender", AddressNameFormatter),
        FieldDefinition(
            (1,),
            "Amount",
            TokenAmountFormatter(
                threshold=0x8000000000000000000000000000000000000000000000000000000000000000
            ),
        ),
    ],
)
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

TRANSFER_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=base58.keccak_32(b"transfer(address,uint256)"),
    intent="Send",
    parameter_definitions=[
        Atomic(parse_address),  # _to
        Atomic(parse_uint256),  # _value
    ],
    field_definitions=[
        FieldDefinition((0,), "To", AddressNameFormatter),
        FieldDefinition((1,), "Amount", TokenAmountFormatter),
    ],
)

COMMON_DISPLAY_FORMATS = [APPROVE_DISPLAY_FORMAT, TRANSFER_DISPLAY_FORMAT]


def iterate_all_display_formats():
    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_Gauntlet_Core import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_WBTC_Morpho_Gauntlet_Core import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_WETH_Aave_v3 import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Aave_v3 import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_AAVE_Arbitrum import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_WETH_Morpho_Gauntlet_Core import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Morpho_Gauntlet_USDT_Prime import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Aave_v3 import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_EURC_Morpho_Gauntlet_Core import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_cbBTC_Morpho_Gauntlet_Core import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Morpho_Steakhouse_USDT_multisig import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Euler_Yield import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_MEV_Capital import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_WETH_Morpho_MEV_Capital import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Morpho_Smokehouse_USDT_multisig import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_RLUSD_Euler_Yield import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_Gauntlet_USDC_Core_multisig import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Morpho_Gauntlet_USDT_Core_multisig import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDe_Euler_Yield_USDE import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Morpho_Gauntlet_Prime import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_Steakhouse_USDC_multisig import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Euler_Yield import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_Smokehouse_USDC_multisig import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_Gauntlet_Prime import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_Re7_Base import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDT_Compound_v3 import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.kiln.calldata_Vault_USDC_Morpho_Gauntlet_USDC_Core_Base_multisig import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7FRAX import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_block_analitica_bbUSDT import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_csUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtUSDCp import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_smcbBTC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7WBTC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtUSDC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_block_analitica_mwcbBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtusdcf import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_b_protocol_reUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_mev_capital_pWBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_mev_capital_MCwBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_9summits_9SUSDCcore import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_midasUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7cbBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakRUSD import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtUSDCc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDCrwa import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDR import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_9summits_9SUSR import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7WETH import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_ionicUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtmsUSDc import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_block_analitica_mwETH import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_smWETH import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakEURC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_mMAI import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_bbqWSTETH import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_llamarisk_llama_crvUSD import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_b_protocol_reGOLD import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtAUSDc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDM import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakPAXG import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_block_analitica_mwEURC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtWETHc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_sbMorphoUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakPYUSD import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_9summits_9SETHc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtcbBTCc import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_uUSDC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_block_analitica_mwUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gteUSDc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_9summits_9SUSDC11Core import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtUSDCmkr import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDA import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_ionicWETH import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_elixirUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_hakutora_hUSDC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtEURCc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_fence_ERY import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7wstETH import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7USDA import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_9summits_9SETHcore import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_sbMorphotBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_msolvbtcbbn import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_block_analitica_bbUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_bbqUSDT import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtUSDT import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7USDC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDT import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakETH import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDQ import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_leadblock_USDC_RWA import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakWBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_b_protocol_recbBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_csUSDL import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakEURA import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtUSDCcore import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtUSDAcore import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakSUSDS import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_mev_capital_MCcbBTC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_steakUSDTlite import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtWETHe import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtDAIcore import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtWETH import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtWBTCc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_smUSDC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtmsETHc import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_apostro_aprUSDC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtLRTcore import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_bbqUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_b_protocol_reETH import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_gtLBTCc import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7RWA import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_fxUSDC import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_mhyETH import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_steakhouse_financial_bbqDAI import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_sparkdao_spDAI import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_mev_capital_MCwETH import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_degenUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_mDEGEN import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_meUSD import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_gauntlet_resolvUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_apostro_aprUSR import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_re7_labs_Re7USDT import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_sparkdao_sparkUSDC import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.morpho.calldata_block_analitica_bbETH import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.yieldxyz.calldata_yieldxyz_usde_vault import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.corestake.calldata_corestake import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.corestake.calldata_stakehub import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.corestake.calldata_coreagent import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.aave.calldata_lpv3 import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.aave.calldata_WrappedTokenGatewayV3 import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.walletconnect.calldata_wct import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.safe.calldata_BatchExecutor import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.tether.calldata_usdt import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.lido.calldata_wstETH_referral_staker import (
        DISPLAY_FORMATS,
    )

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.p2p.calldata_EigenPodManager import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.celo.calldata_celo_governance import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.celo.calldata_celo_validators import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.celo.calldata_locked_celo import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.celo.calldata_celo_accounts import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.celo.calldata_celo_election import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d

    from .clear_signing_registry.lifi.calldata_LIFIDiamond import DISPLAY_FORMATS

    for d in DISPLAY_FORMATS:
        yield d
