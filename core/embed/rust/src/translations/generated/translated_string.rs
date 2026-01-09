//! generated from translated_string.rs.mako
//! (by running `make templates` in `core`)
//! do not edit manually!

#![cfg_attr(rustfmt, rustfmt_skip)]
#[cfg(feature = "micropython")]
use crate::micropython::qstr::Qstr;

pub struct StringsBlob {
    pub text: &'static str,
    pub offsets: &'static [(TranslatedString, u16)],
}

#[derive(Copy, Clone, FromPrimitive, PartialEq, Eq, PartialOrd, Ord)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[cfg_attr(test, derive(Debug))]
#[repr(u16)]
#[allow(non_camel_case_types)]
pub enum TranslatedString {
    addr_mismatch__contact_support_at = 0,  // "Please contact Trezor support at"
    addr_mismatch__key_mismatch = 1,  // "Key mismatch?"
    addr_mismatch__mismatch = 2,  // "Address mismatch?"
    addr_mismatch__support_url = 3,  // "trezor.io/support"
    addr_mismatch__wrong_derivation_path = 4,  // "Wrong derivation path for selected account."
    addr_mismatch__xpub_mismatch = 5,  // "XPUB mismatch?"
    address__public_key = 6,  // "Public key"
    address__title_cosigner = 7,  // "Cosigner"
    address__title_receive_address = 8,  // "Receive address"
    address__title_yours = 9,  // "Yours"
    address_details__derivation_path_colon = 10,  // "Derivation path:"
    address_details__title_receive_address = 11,  // "Receive address"
    address_details__title_receiving_to = 12,  // "Receiving to"
    authenticate__confirm_template = 13,  // "Allow connected app to check the authenticity of your {0}?"
    authenticate__header = 14,  // "Authenticate device"
    auto_lock__change_template = 15,  // "Auto-lock Trezor after {0} of inactivity?"
    auto_lock__title = 16,  // {"Bolt": "Auto-lock delay", "Caesar": "Auto-lock delay", "Delizia": "Auto-lock delay", "Eckhart": "Auto-lock"}
    backup__can_back_up_anytime = 17,  // "You can back up your Trezor once, at any time."
    backup__it_should_be_backed_up = 18,  // {"Bolt": "You should back up your new wallet right now.", "Caesar": "You should back up your new wallet right now.", "Delizia": "You should back up your new wallet right now.", "Eckhart": "Back up your new wallet now."}
    backup__it_should_be_backed_up_now = 19,  // "It should be backed up now!"
    backup__new_wallet_created = 20,  // "Wallet created.\n"
    backup__new_wallet_successfully_created = 21,  // "Wallet created successfully."
    backup__recover_anytime = 22,  // "You can use your backup to recover your wallet at any time."
    backup__title_backup_wallet = 23,  // "Back up wallet"
    backup__title_skip = 24,  // "Skip backup"
    backup__want_to_skip = 25,  // "Are you sure you want to skip the backup?"
    bitcoin__commitment_data = 38,  // "Commitment data"
    bitcoin__confirm_locktime = 39,  // "Confirm locktime"
    bitcoin__create_proof_of_ownership = 40,  // "Do you want to create a proof of ownership?"
    bitcoin__high_mining_fee_template = 41,  // "The mining fee of\n{0}\nis unexpectedly high."
    bitcoin__locktime_no_effect = 42,  // "Locktime is set but will have no effect."
    bitcoin__locktime_set_to = 43,  // "Locktime set to"
    bitcoin__locktime_set_to_blockheight = 44,  // "Locktime set to blockheight"
    bitcoin__lot_of_change_outputs = 45,  // "A lot of change-outputs."
    bitcoin__multiple_accounts = 46,  // "Multiple accounts"
    bitcoin__new_fee_rate = 47,  // "New fee rate:"
    bitcoin__simple_send_of = 48,  // "Simple send of"
    bitcoin__ticket_amount = 49,  // "Ticket amount"
    bitcoin__title_confirm_details = 50,  // "Confirm details"
    bitcoin__title_finalize_transaction = 51,  // "Finalize transaction"
    bitcoin__title_high_mining_fee = 52,  // "High mining fee"
    bitcoin__title_meld_transaction = 53,  // "Meld transaction"
    bitcoin__title_modify_amount = 54,  // "Modify amount"
    bitcoin__title_payjoin = 55,  // "Payjoin"
    bitcoin__title_proof_of_ownership = 56,  // "Proof of ownership"
    bitcoin__title_purchase_ticket = 57,  // "Purchase ticket"
    bitcoin__title_update_transaction = 58,  // "Update transaction"
    bitcoin__unknown_path = 59,  // "Unknown path"
    bitcoin__unknown_transaction = 60,  // "Unknown transaction"
    bitcoin__unusually_high_fee = 61,  // "Unusually high fee."
    bitcoin__unverified_external_inputs = 62,  // "The transaction contains unverified external inputs."
    bitcoin__valid_signature = 63,  // "The signature is valid."
    bitcoin__voting_rights = 64,  // "Voting rights to"
    buttons__abort = 65,  // "Abort"
    buttons__access = 66,  // "Access"
    buttons__again = 67,  // "Again"
    buttons__allow = 68,  // "Allow"
    buttons__back = 69,  // "Back"
    buttons__back_up = 70,  // "Back up"
    buttons__cancel = 71,  // "Cancel"
    buttons__change = 72,  // "Change"
    buttons__check = 73,  // "Check"
    buttons__check_again = 74,  // "Check again"
    buttons__close = 75,  // "Close"
    buttons__confirm = 76,  // "Confirm"
    buttons__continue = 77,  // "Continue"
    buttons__details = 78,  // "Details"
    buttons__enable = 79,  // "Enable"
    buttons__enter = 80,  // "Enter"
    buttons__enter_share = 81,  // "Enter share"
    buttons__export = 82,  // "Export"
    buttons__format = 83,  // "Format"
    buttons__go_back = 84,  // "Go back"
    buttons__hold_to_confirm = 85,  // "Hold to confirm"
    buttons__info = 86,  // "Info"
    buttons__install = 87,  // "Install"
    buttons__more_info = 88,  // "More info"
    buttons__ok_i_understand = 89,  // "Ok, I understand"
    buttons__purchase = 90,  // "Purchase"
    buttons__quit = 91,  // "Quit"
    buttons__restart = 92,  // "Restart"
    buttons__retry = 93,  // "Retry"
    buttons__select = 94,  // "Select"
    buttons__set = 95,  // "Set"
    buttons__show_all = 96,  // "Show all"
    buttons__show_details = 97,  // "Show details"
    buttons__show_words = 98,  // "Show words"
    buttons__skip = 99,  // "Skip"
    buttons__try_again = 100,  // "Try again"
    buttons__turn_off = 101,  // "Turn off"
    buttons__turn_on = 102,  // "Turn on"
    #[cfg(feature = "universal_fw")]
    cardano__addr_base = 103,  // "Base"
    #[cfg(feature = "universal_fw")]
    cardano__addr_enterprise = 104,  // "Enterprise"
    #[cfg(feature = "universal_fw")]
    cardano__addr_legacy = 105,  // "Legacy"
    #[cfg(feature = "universal_fw")]
    cardano__addr_pointer = 106,  // "Pointer"
    #[cfg(feature = "universal_fw")]
    cardano__addr_reward = 107,  // "Reward"
    #[cfg(feature = "universal_fw")]
    cardano__address_no_staking = 108,  // "address - no staking rewards."
    #[cfg(feature = "universal_fw")]
    cardano__amount_burned_decimals_unknown = 109,  // "Amount burned (decimals unknown):"
    #[cfg(feature = "universal_fw")]
    cardano__amount_minted_decimals_unknown = 110,  // "Amount minted (decimals unknown):"
    #[cfg(feature = "universal_fw")]
    cardano__amount_sent_decimals_unknown = 111,  // "Amount sent (decimals unknown):"
    #[cfg(feature = "universal_fw")]
    cardano__anonymous_pool = 112,  // "Pool has no metadata (anonymous pool)"
    #[cfg(feature = "universal_fw")]
    cardano__asset_fingerprint = 113,  // "Asset fingerprint:"
    #[cfg(feature = "universal_fw")]
    cardano__auxiliary_data_hash = 114,  // "Auxiliary data hash:"
    #[cfg(feature = "universal_fw")]
    cardano__block = 115,  // "Block"
    #[cfg(feature = "universal_fw")]
    cardano__catalyst = 116,  // "Catalyst"
    #[cfg(feature = "universal_fw")]
    cardano__certificate = 117,  // "Certificate"
    #[cfg(feature = "universal_fw")]
    cardano__change_output = 118,  // "Change output"
    #[cfg(feature = "universal_fw")]
    cardano__check_all_items = 119,  // "Check all items carefully."
    #[cfg(feature = "universal_fw")]
    cardano__choose_level_of_details = 120,  // "Choose level of details:"
    #[cfg(feature = "universal_fw")]
    cardano__collateral_input_id = 121,  // "Collateral input ID:"
    #[cfg(feature = "universal_fw")]
    cardano__collateral_input_index = 122,  // "Collateral input index:"
    #[cfg(feature = "universal_fw")]
    cardano__collateral_output_contains_tokens = 123,  // "The collateral return output contains tokens."
    #[cfg(feature = "universal_fw")]
    cardano__collateral_return = 124,  // "Collateral return"
    #[cfg(feature = "universal_fw")]
    cardano__confirm_signing_stake_pool = 126,  // "Confirm signing the stake pool registration as an owner."
    #[cfg(feature = "universal_fw")]
    cardano__confirm_transaction = 127,  // "Confirm transaction"
    #[cfg(feature = "universal_fw")]
    cardano__confirming_a_multisig_transaction = 128,  // "Confirming a multisig transaction."
    #[cfg(feature = "universal_fw")]
    cardano__confirming_a_plutus_transaction = 129,  // "Confirming a Plutus transaction."
    #[cfg(feature = "universal_fw")]
    cardano__confirming_pool_registration = 130,  // "Confirming pool registration as owner."
    #[cfg(feature = "universal_fw")]
    cardano__confirming_transaction = 131,  // "Confirming a transaction."
    #[cfg(feature = "universal_fw")]
    cardano__cost = 132,  // "Cost"
    #[cfg(feature = "universal_fw")]
    cardano__credential_mismatch = 133,  // "Credential doesn't match payment credential."
    #[cfg(feature = "universal_fw")]
    cardano__datum_hash = 134,  // "Datum hash:"
    #[cfg(feature = "universal_fw")]
    cardano__delegating_to = 135,  // "Delegating to:"
    #[cfg(feature = "universal_fw")]
    cardano__for_account_and_index_template = 136,  // "for account {0} and index {1}:"
    #[cfg(feature = "universal_fw")]
    cardano__for_account_template = 137,  // "for account {0}:"
    #[cfg(feature = "universal_fw")]
    cardano__for_key_hash = 138,  // "for key hash:"
    #[cfg(feature = "universal_fw")]
    cardano__for_script = 139,  // "for script:"
    #[cfg(feature = "universal_fw")]
    cardano__inline_datum = 140,  // "Inline datum"
    #[cfg(feature = "universal_fw")]
    cardano__input_id = 141,  // "Input ID:"
    #[cfg(feature = "universal_fw")]
    cardano__input_index = 142,  // "Input index:"
    #[cfg(feature = "universal_fw")]
    cardano__intro_text_change = 143,  // "The following address is a change address. Its"
    #[cfg(feature = "universal_fw")]
    cardano__intro_text_owned_by_device = 144,  // "The following address is owned by this device. Its"
    #[cfg(feature = "universal_fw")]
    cardano__intro_text_registration_payment = 145,  // "The vote key registration payment address is owned by this device. Its"
    #[cfg(feature = "universal_fw")]
    cardano__key_hash = 146,  // "key hash"
    #[cfg(feature = "universal_fw")]
    cardano__margin = 147,  // "Margin"
    #[cfg(feature = "universal_fw")]
    cardano__multisig_path = 148,  // "multi-sig path"
    #[cfg(feature = "universal_fw")]
    cardano__nested_scripts_template = 149,  // "Contains {0} nested scripts."
    #[cfg(feature = "universal_fw")]
    cardano__network = 150,  // "Network:"
    #[cfg(feature = "universal_fw")]
    cardano__no_output_tx = 151,  // "Transaction has no outputs, network cannot be verified."
    #[cfg(feature = "universal_fw")]
    cardano__nonce = 152,  // "Nonce:"
    #[cfg(feature = "universal_fw")]
    cardano__other = 153,  // "other"
    #[cfg(feature = "universal_fw")]
    cardano__path = 154,  // "path"
    #[cfg(feature = "universal_fw")]
    cardano__pledge = 155,  // "Pledge"
    #[cfg(feature = "universal_fw")]
    cardano__pointer = 156,  // "pointer"
    #[cfg(feature = "universal_fw")]
    cardano__policy_id = 157,  // "Policy ID"
    #[cfg(feature = "universal_fw")]
    cardano__pool_metadata_hash = 158,  // "Pool metadata hash:"
    #[cfg(feature = "universal_fw")]
    cardano__pool_metadata_url = 159,  // "Pool metadata url:"
    #[cfg(feature = "universal_fw")]
    cardano__pool_owner = 160,  // "Pool owner:"
    #[cfg(feature = "universal_fw")]
    cardano__pool_reward_account = 161,  // "Pool reward account:"
    #[cfg(feature = "universal_fw")]
    cardano__reference_input_id = 162,  // "Reference input ID:"
    #[cfg(feature = "universal_fw")]
    cardano__reference_input_index = 163,  // "Reference input index:"
    #[cfg(feature = "universal_fw")]
    cardano__reference_script = 164,  // "Reference script"
    #[cfg(feature = "universal_fw")]
    cardano__required_signer = 165,  // "Required signer"
    #[cfg(feature = "universal_fw")]
    cardano__reward = 166,  // "reward"
    #[cfg(feature = "universal_fw")]
    cardano__reward_address = 167,  // "Address is a reward address."
    #[cfg(feature = "universal_fw")]
    cardano__reward_eligibility_warning = 168,  // "Warning: The address is not a payment address, it is not eligible for rewards."
    #[cfg(feature = "universal_fw")]
    cardano__rewards_go_to = 169,  // "Rewards go to:"
    #[cfg(feature = "universal_fw")]
    cardano__script = 170,  // "script"
    #[cfg(feature = "universal_fw")]
    cardano__script_all = 171,  // "All"
    #[cfg(feature = "universal_fw")]
    cardano__script_any = 172,  // "Any"
    #[cfg(feature = "universal_fw")]
    cardano__script_data_hash = 173,  // "Script data hash:"
    #[cfg(feature = "universal_fw")]
    cardano__script_hash = 174,  // "Script hash:"
    #[cfg(feature = "universal_fw")]
    cardano__script_invalid_before = 175,  // "Invalid before"
    #[cfg(feature = "universal_fw")]
    cardano__script_invalid_hereafter = 176,  // "Invalid hereafter"
    #[cfg(feature = "universal_fw")]
    cardano__script_key = 177,  // "Key"
    #[cfg(feature = "universal_fw")]
    cardano__script_n_of_k = 178,  // "N of K"
    #[cfg(feature = "universal_fw")]
    cardano__script_reward = 179,  // "script reward"
    #[cfg(feature = "universal_fw")]
    cardano__sending = 180,  // "Sending"
    #[cfg(feature = "universal_fw")]
    cardano__show_simple = 181,  // "Show Simple"
    #[cfg(feature = "universal_fw")]
    cardano__sign_tx_path_template = 182,  // "Sign transaction with {0}"
    #[cfg(feature = "universal_fw")]
    cardano__stake_delegation = 183,  // "Stake delegation"
    #[cfg(feature = "universal_fw")]
    cardano__stake_deregistration = 184,  // "Stake key deregistration"
    #[cfg(feature = "universal_fw")]
    cardano__stake_pool_registration = 185,  // "Stakepool registration"
    #[cfg(feature = "universal_fw")]
    cardano__stake_pool_registration_pool_id = 186,  // "Stake pool registration\nPool ID:"
    #[cfg(feature = "universal_fw")]
    cardano__stake_registration = 187,  // "Stake key registration"
    #[cfg(feature = "universal_fw")]
    cardano__staking_key_for_account = 188,  // "Staking key for account"
    #[cfg(feature = "universal_fw")]
    cardano__to_pool = 189,  // "to pool:"
    #[cfg(feature = "universal_fw")]
    cardano__token_minting_path = 190,  // "token minting path"
    #[cfg(feature = "universal_fw")]
    cardano__total_collateral = 191,  // "Total collateral:"
    #[cfg(feature = "universal_fw")]
    cardano__transaction = 192,  // "Transaction"
    #[cfg(feature = "universal_fw")]
    cardano__transaction_contains_minting_or_burning = 193,  // "The transaction contains minting or burning of tokens."
    #[cfg(feature = "universal_fw")]
    cardano__transaction_contains_script_address_no_datum = 194,  // "The following transaction output contains a script address, but does not contain a datum."
    #[cfg(feature = "universal_fw")]
    cardano__transaction_id = 196,  // "Transaction ID:"
    #[cfg(feature = "universal_fw")]
    cardano__transaction_no_collateral_input = 197,  // "The transaction contains no collateral inputs. Plutus script will not be able to run."
    #[cfg(feature = "universal_fw")]
    cardano__transaction_no_script_data_hash = 198,  // "The transaction contains no script data hash. Plutus script will not be able to run."
    #[cfg(feature = "universal_fw")]
    cardano__transaction_output_contains_tokens = 199,  // "The following transaction output contains tokens."
    #[cfg(feature = "universal_fw")]
    cardano__ttl = 200,  // "TTL:"
    #[cfg(feature = "universal_fw")]
    cardano__unknown_collateral_amount = 201,  // "Unknown collateral amount."
    #[cfg(feature = "universal_fw")]
    cardano__unusual_path = 202,  // "Path is unusual."
    #[cfg(feature = "universal_fw")]
    cardano__valid_since = 203,  // "Valid since:"
    #[cfg(feature = "universal_fw")]
    cardano__verify_script = 204,  // "Verify script"
    #[cfg(feature = "universal_fw")]
    cardano__vote_key_registration = 205,  // "Vote key registration (CIP-36)"
    #[cfg(feature = "universal_fw")]
    cardano__vote_public_key = 206,  // "Vote public key:"
    #[cfg(feature = "universal_fw")]
    cardano__voting_purpose = 207,  // "Voting purpose:"
    #[cfg(feature = "universal_fw")]
    cardano__warning = 208,  // "Warning"
    #[cfg(feature = "universal_fw")]
    cardano__weight = 209,  // "Weight:"
    #[cfg(feature = "universal_fw")]
    cardano__withdrawal_for_address_template = 210,  // "Confirm withdrawal for {0} address:"
    #[cfg(feature = "universal_fw")]
    cardano__x_of_y_signatures_template = 211,  // "Requires {0} out of {1} signatures."
    coinjoin__access_account = 212,  // "Access your coinjoin account?"
    coinjoin__do_not_disconnect = 213,  // "Do not disconnect your Trezor!"
    coinjoin__max_mining_fee = 214,  // "Max mining fee"
    coinjoin__max_rounds = 215,  // "Max rounds"
    coinjoin__title = 216,  // "Authorize coinjoin"
    coinjoin__title_progress = 218,  // {"Bolt": "Coinjoin in progress", "Caesar": "Coinjoin in progress", "Delizia": "Coinjoin in progress", "Eckhart": "Coinjoin in progress..."}
    coinjoin__waiting_for_others = 219,  // "Waiting for others"
    confirm_total__fee_rate_colon = 220,  // "Fee rate:"
    confirm_total__sending_from_account = 221,  // "Sending from account:"
    confirm_total__title_fee = 222,  // "Fee info"
    confirm_total__title_sending_from = 223,  // "Sending from"
    #[cfg(feature = "debug")]
    debug__loading_seed = 224,  // "Loading seed"
    #[cfg(feature = "debug")]
    debug__loading_seed_not_recommended = 225,  // "Loading private seed is not recommended."
    device_name__change_template = 226,  // "Change device name to {0}?"
    device_name__title = 227,  // "Device name"
    entropy__send = 228,  // "Do you really want to send entropy?"
    entropy__title_confirm = 230,  // "Confirm entropy"
    #[cfg(feature = "universal_fw")]
    eos__about_to_sign_template = 231,  // {"Bolt": "You are about to sign {0}.", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__action_name = 232,  // {"Bolt": "Action Name:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__arbitrary_data = 233,  // {"Bolt": "Arbitrary data", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__buy_ram = 234,  // {"Bolt": "Buy RAM", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__bytes = 235,  // {"Bolt": "Bytes:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__cancel_vote = 236,  // {"Bolt": "Cancel vote", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__checksum = 237,  // {"Bolt": "Checksum:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__code = 238,  // {"Bolt": "Code:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__contract = 239,  // {"Bolt": "Contract:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__cpu = 240,  // {"Bolt": "CPU:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__creator = 241,  // {"Bolt": "Creator:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__delegate = 242,  // {"Bolt": "Delegate", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__delete_auth = 243,  // {"Bolt": "Delete Auth", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__from = 244,  // {"Bolt": "From:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__link_auth = 245,  // {"Bolt": "Link Auth", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__memo = 246,  // {"Bolt": "Memo", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__name = 247,  // {"Bolt": "Name:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__net = 248,  // {"Bolt": "NET:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__new_account = 249,  // {"Bolt": "New account", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__owner = 250,  // {"Bolt": "Owner:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__parent = 251,  // {"Bolt": "Parent:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__payer = 252,  // {"Bolt": "Payer:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__permission = 253,  // {"Bolt": "Permission:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__proxy = 254,  // {"Bolt": "Proxy:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__receiver = 255,  // {"Bolt": "Receiver:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__refund = 256,  // {"Bolt": "Refund", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__requirement = 257,  // {"Bolt": "Requirement:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__sell_ram = 258,  // {"Bolt": "Sell RAM", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__sender = 259,  // {"Bolt": "Sender:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    send__sign_transaction = 260,  // "Sign transaction"
    #[cfg(feature = "universal_fw")]
    eos__threshold = 261,  // {"Bolt": "Threshold:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__to = 262,  // {"Bolt": "To:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__transfer = 263,  // {"Bolt": "Transfer:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__type = 264,  // {"Bolt": "Type:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__undelegate = 265,  // {"Bolt": "Undelegate", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__unlink_auth = 266,  // {"Bolt": "Unlink Auth", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__update_auth = 267,  // {"Bolt": "Update Auth", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__vote_for_producers = 268,  // {"Bolt": "Vote for producers", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__vote_for_proxy = 269,  // {"Bolt": "Vote for proxy", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    eos__voter = 270,  // {"Bolt": "Voter:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    ethereum__amount_sent = 271,  // "Amount sent:"
    #[cfg(feature = "universal_fw")]
    ethereum__data_size_template = 273,  // "Size: {0} bytes"
    #[cfg(feature = "universal_fw")]
    ethereum__gas_limit = 274,  // "Gas limit"
    #[cfg(feature = "universal_fw")]
    ethereum__gas_price = 275,  // "Gas price"
    #[cfg(feature = "universal_fw")]
    ethereum__max_gas_price = 276,  // "Max fee per gas"
    #[cfg(feature = "universal_fw")]
    ethereum__name_and_version = 277,  // "Name and version"
    #[cfg(feature = "universal_fw")]
    ethereum__new_contract = 278,  // "New contract will be deployed"
    #[cfg(feature = "universal_fw")]
    ethereum__no_message_field = 279,  // "No message field"
    #[cfg(feature = "universal_fw")]
    ethereum__priority_fee = 280,  // "Max priority fee"
    #[cfg(feature = "universal_fw")]
    ethereum__show_full_array = 281,  // "Show full array"
    #[cfg(feature = "universal_fw")]
    ethereum__show_full_domain = 282,  // "Show full domain"
    #[cfg(feature = "universal_fw")]
    ethereum__show_full_message = 283,  // "Show full message"
    #[cfg(feature = "universal_fw")]
    ethereum__show_full_struct = 284,  // "Show full struct"
    #[cfg(feature = "universal_fw")]
    ethereum__sign_eip712 = 285,  // "Really sign EIP-712 typed data?"
    #[cfg(feature = "universal_fw")]
    ethereum__title_input_data = 286,  // "Input data"
    #[cfg(feature = "universal_fw")]
    ethereum__title_confirm_domain = 287,  // "Confirm domain"
    #[cfg(feature = "universal_fw")]
    ethereum__title_confirm_message = 288,  // "Confirm message"
    #[cfg(feature = "universal_fw")]
    ethereum__title_confirm_struct = 289,  // "Confirm struct"
    #[cfg(feature = "universal_fw")]
    ethereum__title_confirm_typed_data = 290,  // "Confirm typed data"
    #[cfg(feature = "universal_fw")]
    ethereum__title_signing_address = 291,  // "Signing address"
    #[cfg(feature = "universal_fw")]
    ethereum__units_template = 292,  // "{0} units"
    #[cfg(feature = "universal_fw")]
    ethereum__unknown_token = 293,  // "Unknown token"
    #[cfg(feature = "universal_fw")]
    ethereum__valid_signature = 294,  // "The signature is valid."
    experimental_mode__enable = 295,  // "Enable experimental features?"
    experimental_mode__only_for_dev = 296,  // "Only for development and beta testing!"
    experimental_mode__title = 297,  // "Experimental mode"
    #[cfg(feature = "universal_fw")]
    fido__already_registered = 298,  // "Already registered"
    #[cfg(feature = "universal_fw")]
    fido__device_already_registered = 299,  // "This device is already registered with this application."
    #[cfg(feature = "universal_fw")]
    fido__device_already_registered_with_template = 300,  // "This device is already registered with {0}."
    #[cfg(feature = "universal_fw")]
    fido__device_not_registered = 301,  // "This device is not registered with this application."
    #[cfg(feature = "universal_fw")]
    fido__does_not_belong = 302,  // {"Bolt": "The credential you are trying to import does\nnot belong to this authenticator.", "Caesar": "The credential you are trying to import does\nnot belong to this authenticator.", "Delizia": "The credential you are trying to import does\nnot belong to this authenticator.", "Eckhart": "The credential you are trying to import does not belong to this authenticator."}
    #[cfg(feature = "universal_fw")]
    fido__erase_credentials = 303,  // {"Bolt": "erase all credentials?", "Caesar": "erase all credentials?", "Delizia": "erase all credentials?", "Eckhart": "Delete all of the saved credentials?"}
    #[cfg(feature = "universal_fw")]
    fido__export_credentials = 304,  // "Export information about the credentials stored on this device?"
    #[cfg(feature = "universal_fw")]
    fido__not_registered = 305,  // "Not registered"
    #[cfg(feature = "universal_fw")]
    fido__not_registered_with_template = 306,  // "This device is not registered with\n{0}."
    #[cfg(feature = "universal_fw")]
    fido__please_enable_pin_protection = 307,  // "Please enable PIN protection."
    #[cfg(feature = "universal_fw")]
    fido__title_authenticate = 308,  // "FIDO2 authenticate"
    #[cfg(feature = "universal_fw")]
    fido__title_import_credential = 309,  // "Import credential"
    #[cfg(feature = "universal_fw")]
    fido__title_list_credentials = 310,  // "List credentials"
    #[cfg(feature = "universal_fw")]
    fido__title_register = 311,  // "FIDO2 register"
    #[cfg(feature = "universal_fw")]
    fido__title_remove_credential = 312,  // "Remove credential"
    #[cfg(feature = "universal_fw")]
    fido__title_reset = 313,  // "FIDO2 reset"
    #[cfg(feature = "universal_fw")]
    fido__title_u2f_auth = 314,  // "U2F authenticate"
    #[cfg(feature = "universal_fw")]
    fido__title_u2f_register = 315,  // "U2F register"
    #[cfg(feature = "universal_fw")]
    fido__title_verify_user = 316,  // "FIDO2 verify user"
    #[cfg(feature = "universal_fw")]
    fido__unable_to_verify_user = 317,  // "Unable to verify user."
    #[cfg(feature = "universal_fw")]
    fido__wanna_erase_credentials = 318,  // "Do you really want to erase all credentials?"
    firmware_update__title = 319,  // "Update firmware"
    firmware_update__title_fingerprint = 320,  // "FW fingerprint"
    homescreen__click_to_connect = 321,  // "Click to Connect"
    homescreen__click_to_unlock = 322,  // "Click to Unlock"
    homescreen__title_backup_failed = 323,  // "Backup failed"
    homescreen__title_backup_needed = 324,  // "Backup needed"
    homescreen__title_coinjoin_authorized = 325,  // "Coinjoin authorized"
    homescreen__title_experimental_mode = 326,  // "Experimental mode"
    homescreen__title_no_usb_connection = 327,  // "No USB connection"
    homescreen__title_pin_not_set = 328,  // "PIN not set"
    homescreen__title_seedless = 329,  // "Seedless"
    homescreen__title_set = 330,  // "Change wallpaper"
    inputs__back = 331,  // {"Bolt": "", "Caesar": "BACK", "Delizia": "", "Eckhart": ""}
    inputs__cancel = 332,  // {"Bolt": "", "Caesar": "CANCEL", "Delizia": "", "Eckhart": ""}
    inputs__delete = 333,  // {"Bolt": "", "Caesar": "DELETE", "Delizia": "", "Eckhart": ""}
    inputs__enter = 334,  // {"Bolt": "", "Caesar": "ENTER", "Delizia": "", "Eckhart": ""}
    inputs__return = 335,  // {"Bolt": "", "Caesar": "RETURN", "Delizia": "", "Eckhart": ""}
    inputs__show = 336,  // {"Bolt": "", "Caesar": "SHOW", "Delizia": "", "Eckhart": ""}
    inputs__space = 337,  // {"Bolt": "", "Caesar": "SPACE", "Delizia": "", "Eckhart": ""}
    joint__title = 338,  // "Joint transaction"
    joint__to_the_total_amount = 339,  // "To the total amount:"
    joint__you_are_contributing = 340,  // "You are contributing:"
    language__change_to_template = 341,  // "Change language to {0}?"
    language__changed = 342,  // "Language changed successfully"
    language__progress = 343,  // {"Bolt": "Changing language", "Caesar": "Changing language", "Delizia": "Changing language", "Eckhart": "Changing language..."}
    language__title = 344,  // "Language settings"
    lockscreen__tap_to_connect = 345,  // "Tap to connect"
    lockscreen__tap_to_unlock = 346,  // "Tap to unlock"
    lockscreen__title_locked = 347,  // "Locked"
    lockscreen__title_not_connected = 348,  // "Not connected"
    misc__decrypt_value = 349,  // "Decrypt value"
    misc__encrypt_value = 350,  // "Encrypt value"
    misc__title_suite_labeling = 351,  // "Suite labeling"
    modify_amount__decrease_amount = 352,  // {"Bolt": "Decrease amount by:", "Caesar": "Decrease amount by:", "Delizia": "Decrease amount by:", "Eckhart": "Decrease amount by"}
    modify_amount__increase_amount = 353,  // {"Bolt": "Increase amount by:", "Caesar": "Increase amount by:", "Delizia": "Increase amount by:", "Eckhart": "Increase amount by"}
    modify_amount__new_amount = 354,  // {"Bolt": "New amount:", "Caesar": "New amount:", "Delizia": "New amount:", "Eckhart": "New amount"}
    modify_amount__title = 355,  // "Modify amount"
    modify_fee__decrease_fee = 356,  // {"Bolt": "Decrease fee by:", "Caesar": "Decrease fee by:", "Delizia": "Decrease fee by:", "Eckhart": "Decrease fee by"}
    modify_fee__fee_rate = 357,  // "Fee rate:"
    modify_fee__increase_fee = 358,  // {"Bolt": "Increase fee by:", "Caesar": "Increase fee by:", "Delizia": "Increase fee by:", "Eckhart": "Increase fee by"}
    modify_fee__new_transaction_fee = 359,  // {"Bolt": "New transaction fee:", "Caesar": "New transaction fee:", "Delizia": "New transaction fee:", "Eckhart": "New transaction fee"}
    modify_fee__no_change = 360,  // {"Bolt": "Fee did not change.\n", "Caesar": "Fee did not change.\n", "Delizia": "Fee did not change.\n", "Eckhart": "Fee did not change"}
    modify_fee__title = 361,  // "Modify fee"
    modify_fee__transaction_fee = 362,  // {"Bolt": "Transaction fee:", "Caesar": "Transaction fee:", "Delizia": "Transaction fee:", "Eckhart": "Transaction fee"}
    #[cfg(feature = "universal_fw")]
    monero__confirm_export = 363,  // "Confirm export"
    #[cfg(feature = "universal_fw")]
    monero__confirm_ki_sync = 364,  // "Confirm ki sync"
    #[cfg(feature = "universal_fw")]
    monero__confirm_refresh = 365,  // "Confirm refresh"
    #[cfg(feature = "universal_fw")]
    monero__confirm_unlock_time = 366,  // "Confirm unlock time"
    #[cfg(feature = "universal_fw")]
    monero__hashing_inputs = 367,  // "Hashing inputs"
    #[cfg(feature = "universal_fw")]
    monero__payment_id = 368,  // "Payment ID"
    #[cfg(feature = "universal_fw")]
    monero__postprocessing = 369,  // "Postprocessing..."
    #[cfg(feature = "universal_fw")]
    monero__processing = 370,  // "Processing..."
    #[cfg(feature = "universal_fw")]
    monero__processing_inputs = 371,  // "Processing inputs"
    #[cfg(feature = "universal_fw")]
    monero__processing_outputs = 372,  // "Processing outputs"
    #[cfg(feature = "universal_fw")]
    monero__signing = 373,  // "Signing..."
    #[cfg(feature = "universal_fw")]
    monero__signing_inputs = 374,  // "Signing inputs"
    #[cfg(feature = "universal_fw")]
    monero__unlock_time_set_template = 375,  // "Unlock time for this transaction is set to {0}"
    #[cfg(feature = "universal_fw")]
    monero__wanna_export_tx_der = 376,  // "Do you really want to export tx_der\nfor tx_proof?"
    #[cfg(feature = "universal_fw")]
    monero__wanna_export_tx_key = 377,  // "Do you really want to export tx_key?"
    #[cfg(feature = "universal_fw")]
    monero__wanna_export_watchkey = 378,  // "Do you really want to export watch-only credentials?"
    #[cfg(feature = "universal_fw")]
    monero__wanna_start_refresh = 379,  // "Do you really want to\nstart refresh?"
    #[cfg(feature = "universal_fw")]
    monero__wanna_sync_key_images = 380,  // "Do you really want to\nsync key images?"
    #[cfg(feature = "universal_fw")]
    nem__absolute = 381,  // {"Bolt": "absolute", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__activate = 382,  // {"Bolt": "Activate", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__add = 383,  // {"Bolt": "Add", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_action = 384,  // {"Bolt": "Confirm action", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_address = 385,  // {"Bolt": "Confirm address", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_creation_fee = 386,  // {"Bolt": "Confirm creation fee", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_mosaic = 387,  // {"Bolt": "Confirm mosaic", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_multisig_fee = 388,  // {"Bolt": "Confirm multisig fee", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_namespace = 389,  // {"Bolt": "Confirm namespace", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_payload = 390,  // {"Bolt": "Confirm payload", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_properties = 391,  // {"Bolt": "Confirm properties", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_rental_fee = 392,  // {"Bolt": "Confirm rental fee", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__confirm_transfer_of = 393,  // {"Bolt": "Confirm transfer of", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__convert_account_to_multisig = 394,  // {"Bolt": "Convert account to multisig account?", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__cosign_transaction_for = 395,  // {"Bolt": "Cosign transaction for", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__cosignatory = 396,  // {"Bolt": " cosignatory", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__create_mosaic = 397,  // {"Bolt": "Create mosaic", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__create_namespace = 398,  // {"Bolt": "Create namespace", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__deactivate = 399,  // {"Bolt": "Deactivate", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__decrease = 400,  // {"Bolt": "Decrease", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__description = 401,  // {"Bolt": "Description:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__divisibility_and_levy_cannot_be_shown = 402,  // {"Bolt": "Divisibility and levy cannot be shown for unknown mosaics", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__encrypted = 403,  // {"Bolt": "Encrypted", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__final_confirm = 404,  // {"Bolt": "Final confirm", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__immutable = 405,  // {"Bolt": "immutable", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__increase = 406,  // {"Bolt": "Increase", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__initial_supply = 407,  // {"Bolt": "Initial supply:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__initiate_transaction_for = 408,  // {"Bolt": "Initiate transaction for", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__levy_divisibility = 409,  // {"Bolt": "Levy divisibility:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__levy_fee = 410,  // {"Bolt": "Levy fee:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__levy_fee_of = 411,  // {"Bolt": "Confirm mosaic levy fee of", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__levy_mosaic = 412,  // {"Bolt": "Levy mosaic:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__levy_namespace = 413,  // {"Bolt": "Levy namespace:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__levy_recipient = 414,  // {"Bolt": "Levy recipient:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__levy_type = 415,  // {"Bolt": "Levy type:", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__modify_supply_for = 416,  // {"Bolt": "Modify supply for", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__modify_the_number_of_cosignatories_by = 417,  // {"Bolt": "Modify the number of cosignatories by ", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__mutable = 418,  // {"Bolt": "mutable", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__of = 419,  // {"Bolt": "of", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__percentile = 420,  // {"Bolt": "percentile", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__raw_units_template = 421,  // {"Bolt": "{0} raw units", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__remote_harvesting = 422,  // {"Bolt": " remote harvesting?", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__remove = 423,  // {"Bolt": "Remove", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__set_minimum_cosignatories_to = 424,  // {"Bolt": "Set minimum cosignatories to ", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__sign_tx_fee_template = 425,  // {"Bolt": "Sign this transaction\nand pay {0}\nfor network fee?", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__supply_change = 426,  // {"Bolt": "Supply change", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__supply_units_template = 427,  // {"Bolt": "{0} supply by {1} whole units?", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__transferable = 428,  // {"Bolt": "Transferable?", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__under_namespace = 429,  // {"Bolt": "under namespace", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__unencrypted = 430,  // {"Bolt": "Unencrypted", "Caesar": "", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    nem__unknown_mosaic = 431,  // {"Bolt": "Unknown mosaic!", "Caesar": "", "Delizia": "", "Eckhart": ""}
    passphrase__access_wallet = 432,  // "Access passphrase wallet?"
    passphrase__always_on_device = 433,  // "Always enter your passphrase on Trezor?"
    passphrase__from_host_not_shown = 434,  // "Passphrase provided by connected app will be used but will not be displayed due to the device settings."
    passphrase__wallet = 435,  // "Passphrase wallet"
    passphrase__hide = 436,  // {"Bolt": "Hide passphrase coming from app?", "Caesar": "Hide passphrase coming from app?", "Delizia": "Hide passphrase coming from app?", "Eckhart": "Hide your passphrase on Trezor entered on connected app?"}
    passphrase__next_screen_will_show_passphrase = 437,  // "The next screen shows your passphrase."
    passphrase__please_enter = 438,  // "Please enter your passphrase."
    passphrase__revoke_on_device = 439,  // "Do you want to revoke the passphrase on device setting?"
    passphrase__title_confirm = 440,  // "Confirm passphrase"
    passphrase__title_enter = 441,  // "Enter passphrase"
    passphrase__title_hide = 442,  // "Hide passphrase"
    passphrase__title_settings = 443,  // "Passphrase settings"
    passphrase__title_source = 444,  // "Passphrase source"
    passphrase__turn_off = 445,  // "Turn off passphrase protection?"
    passphrase__turn_on = 446,  // "Turn on passphrase protection?"
    pin__change = 447,  // "Change PIN"
    pin__changed = 448,  // "PIN changed."
    pin__cursor_will_change = 449,  // "Position of the cursor will change between entries for enhanced security."
    pin__diff_from_wipe_code = 450,  // "The new PIN must be different from your wipe code."
    pin__disabled = 451,  // "PIN protection\nturned off."
    pin__enabled = 452,  // "PIN protection\nturned on."
    pin__enter = 453,  // "Enter PIN"
    pin__enter_new = 454,  // "Enter new PIN"
    pin__entered_not_valid = 455,  // "The PIN you have entered is not valid."
    pin__info = 456,  // {"Bolt": "PIN will be required to access this device.", "Caesar": "PIN will be required to access this device.", "Delizia": "PIN will be required to access this device.", "Eckhart": "The PIN will be required to access this device."}
    pin__invalid_pin = 457,  // "Invalid PIN"
    pin__last_attempt = 458,  // "Last attempt"
    pin__mismatch = 459,  // "Entered PINs do not match!"
    pin__pin_mismatch = 460,  // "PIN mismatch"
    pin__please_check_again = 461,  // "Please check again."
    pin__reenter_new = 462,  // "Re-enter new PIN"
    pin__reenter_to_confirm = 463,  // "Please re-enter PIN to confirm."
    pin__should_be_long = 464,  // "PIN should be 4-50 digits long."
    pin__title_check_pin = 465,  // "Check PIN"
    pin__title_settings = 466,  // "PIN settings"
    pin__title_wrong_pin = 467,  // "Wrong PIN"
    pin__tries_left = 468,  // "tries left"
    pin__turn_off = 469,  // "Are you sure you want to turn off PIN protection?"
    pin__turn_on = 470,  // "Turn on PIN protection?"
    pin__wrong_pin = 471,  // "Wrong PIN"
    plurals__contains_x_keys = 472,  // "key|keys"
    plurals__lock_after_x_hours = 473,  // "hour|hours"
    plurals__lock_after_x_milliseconds = 474,  // "millisecond|milliseconds"
    plurals__lock_after_x_minutes = 475,  // "minute|minutes"
    plurals__lock_after_x_seconds = 476,  // "second|seconds"
    plurals__sign_x_actions = 477,  // "action|actions"
    plurals__transaction_of_x_operations = 478,  // "operation|operations"
    plurals__x_groups_needed = 479,  // "group|groups"
    plurals__x_shares_needed = 480,  // "share|shares"
    progress__authenticity_check = 481,  // "Checking authenticity..."
    progress__done = 482,  // "Done"
    progress__loading_transaction = 483,  // "Loading transaction..."
    progress__locking_device = 484,  // "Locking the device..."
    progress__one_second_left = 485,  // "1 second left"
    progress__please_wait = 486,  // {"Bolt": "Please wait", "Caesar": "Please wait", "Delizia": "Please wait", "Eckhart": "Please wait..."}
    storage_msg__processing = 487,  // {"Bolt": "Processing", "Caesar": "Processing", "Delizia": "Processing", "Eckhart": "Processing..."}
    progress__refreshing = 488,  // "Refreshing..."
    progress__signing_transaction = 489,  // "Signing transaction..."
    progress__syncing = 490,  // "Syncing..."
    progress__x_seconds_left_template = 491,  // "{0} seconds left"
    reboot_to_bootloader__restart = 492,  // "Trezor will restart in bootloader mode."
    reboot_to_bootloader__title = 493,  // "Go to bootloader"
    reboot_to_bootloader__version_by_template = 494,  // "Firmware version {0}\nby {1}"
    recovery__cancel_dry_run = 495,  // "Cancel backup check"
    recovery__check_dry_run = 496,  // {"Bolt": "Check your backup?", "Caesar": "Check your backup?", "Delizia": "Check your backup?", "Eckhart": "Let's do a wallet backup check."}
    recovery__cursor_will_change = 497,  // "Position of the cursor will change between entries for enhanced security."
    recovery__dry_run_bip39_valid_match = 498,  // "The entered wallet backup is valid and matches the one in this device."
    recovery__dry_run_bip39_valid_mismatch = 499,  // "The entered wallet backup is valid but does not match the one in the device."
    recovery__dry_run_slip39_valid_match = 500,  // "The entered recovery shares are valid and match what is currently in the device."
    recovery__dry_run_slip39_valid_mismatch = 501,  // {"Bolt": "The entered recovery shares are valid but do not match what is currently in the device.", "Caesar": "The entered recovery shares are valid but do not match what is currently in the device.", "Delizia": "The entered wallet backup is valid but doesn't match the one on this device.", "Eckhart": "The entered wallet backup is valid but doesn't match the one on this device."}
    recovery__enter_any_share = 502,  // "Enter any share"
    recovery__enter_backup = 503,  // "Enter your backup."
    recovery__enter_different_share = 504,  // "Enter a different share."
    recovery__enter_share_from_diff_group = 505,  // "Enter share from a different group."
    recovery__group_num_template = 506,  // {"Bolt": "Group {0}", "Caesar": "Group {0}", "Delizia": "Group {0}", "Eckhart": "Group #{0}"}
    recovery__group_threshold_reached = 507,  // "Group threshold reached."
    recovery__invalid_wallet_backup_entered = 508,  // "Invalid wallet backup entered."
    recovery__invalid_share_entered = 509,  // "Invalid recovery share entered."
    recovery__more_shares_needed = 510,  // {"Bolt": "More shares needed", "Caesar": "More shares needed", "Delizia": "More shares needed", "Eckhart": "More shares needed."}
    recovery__num_of_words = 511,  // "Select the number of words in your backup."
    recovery__only_first_n_letters = 512,  // "You'll only have to select the first 2-4 letters of each word."
    recovery__progress_will_be_lost = 513,  // "All progress will be lost."
    recovery__share_already_entered = 515,  // {"Bolt": "Share already entered", "Caesar": "Share already entered", "Delizia": "Share already entered", "Eckhart": "Share already entered."}
    recovery__share_from_another_multi_share_backup = 516,  // "You have entered a share from a different backup."
    recovery__share_num_template = 517,  // {"Bolt": "Share {0}", "Caesar": "Share {0}", "Delizia": "Share {0}", "Eckhart": "Share #{0}"}
    recovery__title = 518,  // "Recover wallet"
    recovery__title_cancel_dry_run = 519,  // "Cancel backup check"
    recovery__title_cancel_recovery = 520,  // "Cancel recovery"
    recovery__title_dry_run = 521,  // "Backup check"
    recovery__title_recover = 522,  // "Recover wallet"
    recovery__title_remaining_shares = 523,  // "Remaining shares"
    recovery__type_word_x_of_y_template = 524,  // "Type word {0} of {1}"
    recovery__wallet_recovered = 525,  // {"Bolt": "Wallet recovery completed", "Caesar": "Wallet recovery completed", "Delizia": "Wallet recovery completed", "Eckhart": "Wallet recovery completed."}
    recovery__wanna_cancel_dry_run = 526,  // "Are you sure you want to cancel the backup check?"
    recovery__wanna_cancel_recovery = 527,  // "Are you sure you want to cancel the recovery process?"
    recovery__word_count_template = 528,  // "({0} words)"
    recovery__word_x_of_y_template = 529,  // {"Bolt": "Word {0} of {1}", "Caesar": "Word {0} of {1}", "Delizia": "Word {0} of {1}", "Eckhart": "Word {0}\nof {1}"}
    recovery__x_more_items_starting_template_plural = 530,  // {"Bolt": "{count} more {plural} starting", "Caesar": "{count} more {plural} starting", "Delizia": "{count} more {plural} starting", "Eckhart": "You need {count} more {plural} starting"}
    recovery__x_more_shares_needed_template_plural = 531,  // {"Bolt": "{count} more {plural} needed", "Caesar": "{count} more {plural} needed", "Delizia": "{count} more {plural} needed", "Eckhart": "{count} more {plural} needed."}
    recovery__x_of_y_entered_template = 532,  // {"Bolt": "{0} of {1} shares entered", "Caesar": "{0} of {1} shares entered", "Delizia": "{0} of {1} shares entered", "Eckhart": "{0} of {1} shares entered."}
    recovery__you_have_entered = 533,  // "You have entered"
    reset__advanced_group_threshold_info = 534,  // "The group threshold specifies the number of groups required to recover your wallet."
    reset__all_x_of_y_template = 535,  // {"Bolt": "all {0} of {1} shares", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__any_x_of_y_template = 536,  // {"Bolt": "any {0} of {1} shares", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__button_create = 537,  // "Create wallet"
    reset__button_recover = 538,  // "Recover wallet"
    reset__by_continuing = 539,  // {"Bolt": "By continuing you agree to Trezor Company's terms and conditions.", "Caesar": "By continuing you agree to Trezor Company's terms and conditions.", "Delizia": "By continuing you agree to Trezor Company's terms and conditions.", "Eckhart": "By continuing, you agree to Trezor Company's Terms of Use."}
    reset__check_backup_title = 540,  // "Check backup"
    reset__check_group_share_title_template = 541,  // "Check g{0} - share {1}"
    reset__check_wallet_backup_title = 542,  // "Check wallet backup"
    reset__check_share_title_template = 543,  // "Check share #{0}"
    reset__continue_with_next_share = 544,  // "Continue with the next share."
    reset__continue_with_share_template = 545,  // "Continue with share #{0}."
    reset__finished_verifying_group_template = 546,  // "You have finished verifying your recovery shares for group {0}."
    reset__finished_verifying_wallet_backup = 547,  // "You have finished verifying your wallet backup."
    reset__finished_verifying_shares = 548,  // "You have finished verifying your recovery shares."
    reset__group_description = 549,  // "A group is made up of recovery shares."
    reset__group_info = 550,  // "Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds."
    reset__group_share_checked_successfully_template = 551,  // "Group {0} - Share {1} checked successfully."
    reset__group_share_title_template = 552,  // {"Bolt": "Group {0} - share {1}", "Caesar": "Group {0} - share {1}", "Delizia": "Group {0} - share {1}", "Eckhart": "Group #{0} - Share #{1}"}
    reset__more_info_at = 553,  // "More info at"
    reset__need_all_share_template = 554,  // {"Bolt": "For recovery you need all {0} of the shares.", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__need_any_share_template = 555,  // {"Bolt": "For recovery you need any {0} of the shares.", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__needed_to_form_a_group = 556,  // {"Bolt": "needed to form a group. ", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__needed_to_recover_your_wallet = 557,  // {"Bolt": "needed to recover your wallet. ", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__never_make_digital_copy = 558,  // "Never put your backup anywhere digital."
    reset__num_of_share_holders_template = 559,  // "{0} people or locations will each hold one share."
    reset__num_of_shares_advanced_info_template = 560,  // "Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}."
    reset__num_of_shares_basic_info_template = 561,  // {"Bolt": "Each recovery share is a sequence of {0} words. Next you will choose how many shares you need to recover your wallet.", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__num_shares_for_group_template = 562,  // "The required number of shares to form Group {0}."
    reset__number_of_shares_info = 563,  // "= total number of unique word lists used for wallet backup."
    reset__one_share = 564,  // {"Bolt": "1 share", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__only_one_share_will_be_created = 565,  // "Only one share will be created."
    reset__recovery_wallet_backup_title = 566,  // "Wallet backup"
    reset__recovery_share_title_template = 567,  // "Recovery share #{0}"
    reset__required_number_of_groups = 568,  // "The required number of groups for recovery."
    reset__select_correct_word = 569,  // "Select the correct word for each position."
    reset__select_word_template = 570,  // {"Bolt": "Select {0} word", "Caesar": "Select {0} word", "Delizia": "Select {0} word", "Eckhart": "Select word #{0} from your wallet backup"}
    reset__select_word_x_of_y_template = 571,  // "Select word {0} of {1}:"
    reset__set_it_to_count_template = 572,  // {"Bolt": "Set it to {0} and you will need ", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__share_checked_successfully_template = 573,  // "Share #{0} checked successfully."
    reset__share_words_title = 574,  // "Standard backup"
    reset__slip39_checklist_num_groups = 575,  // "Number of groups"
    reset__slip39_checklist_num_shares = 576,  // "Number of shares"
    reset__slip39_checklist_set_num_groups = 577,  // "Set number of groups"
    reset__slip39_checklist_set_num_shares = 578,  // "Set number of shares"
    reset__slip39_checklist_set_sizes = 579,  // "Set sizes and thresholds"
    reset__slip39_checklist_set_sizes_longer = 580,  // "Set size and threshold for each group"
    reset__slip39_checklist_set_threshold = 581,  // {"Bolt": "Set threshold", "Caesar": "Set threshold", "Delizia": "Set threshold", "Eckhart": "Set recovery threshold"}
    reset__slip39_checklist_title = 582,  // "Backup checklist"
    reset__slip39_checklist_write_down = 583,  // "Write down and check all shares"
    reset__slip39_checklist_write_down_recovery = 584,  // "Write down & check all wallet backup shares"
    reset__the_threshold_sets_the_number_of_shares = 585,  // {"Bolt": "The threshold sets the number of shares ", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__threshold_info = 586,  // "= minimum number of unique word lists used for recovery."
    reset__title_backup_is_done = 587,  // "Backup is done"
    reset__title_create_wallet = 588,  // "Create wallet"
    reset__title_group_threshold = 590,  // "Group threshold"
    reset__title_number_of_groups = 591,  // "Number of groups"
    reset__title_number_of_shares = 592,  // "Number of shares"
    reset__title_set_group_threshold = 593,  // "Set group threshold"
    reset__title_set_number_of_groups = 594,  // "Set number of groups"
    reset__title_set_number_of_shares = 595,  // "Set number of shares"
    reset__title_set_threshold = 596,  // "Set threshold"
    reset__to_form_group_template = 597,  // {"Bolt": "to form Group {0}.", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__tos_link = 598,  // {"Bolt": "trezor.io/tos", "Caesar": "trezor.io/tos", "Delizia": "trezor.io/tos", "Eckhart": "More at trezor.io/tos"}
    reset__total_number_of_shares_in_group_template = 599,  // "Set the total number of shares in Group {0}."
    reset__use_your_backup = 600,  // "Use your backup when you need to recover your wallet."
    reset__write_down_words_template = 601,  // "Write the following {0} words in order on your wallet backup card."
    reset__wrong_word_selected = 602,  // "Wrong word selected!"
    reset__you_need_one_share = 603,  // {"Bolt": "For recovery you need 1 share.", "Caesar": "", "Delizia": "", "Eckhart": ""}
    reset__your_backup_is_done = 604,  // "Your backup is done."
    #[cfg(feature = "universal_fw")]
    ripple__confirm_tag = 605,  // "Confirm tag"
    #[cfg(feature = "universal_fw")]
    ripple__destination_tag_template = 606,  // "Destination tag:\n{0}"
    rotation__change_template = 607,  // "Change display orientation to {0}?"
    rotation__east = 608,  // "east"
    rotation__north = 609,  // "north"
    rotation__south = 610,  // "south"
    rotation__title_change = 611,  // "Display orientation"
    rotation__west = 612,  // "west"
    safety_checks__approve_unsafe_always = 613,  // "Trezor will allow you to approve some actions which might be unsafe."
    safety_checks__approve_unsafe_temporary = 614,  // "Trezor will temporarily allow you to approve some actions which might be unsafe."
    safety_checks__enforce_strict = 615,  // "Do you really want to enforce strict safety checks (recommended)?"
    safety_checks__title = 616,  // "Safety checks"
    safety_checks__title_safety_override = 617,  // "Safety override"
    sd_card__all_data_will_be_lost = 618,  // {"Bolt": "All data on the SD card will be lost.", "Caesar": "", "Delizia": "All data on the SD card will be lost.", "Eckhart": ""}
    sd_card__card_required = 619,  // {"Bolt": "SD card required.", "Caesar": "", "Delizia": "SD card required.", "Eckhart": ""}
    sd_card__disable = 620,  // {"Bolt": "Do you really want to remove SD card protection from your device?", "Caesar": "", "Delizia": "Do you really want to remove SD card protection from your device?", "Eckhart": ""}
    sd_card__disabled = 621,  // {"Bolt": "You have successfully disabled SD protection.", "Caesar": "", "Delizia": "You have successfully disabled SD protection.", "Eckhart": ""}
    sd_card__enable = 622,  // {"Bolt": "Do you really want to secure your device with SD card protection?", "Caesar": "", "Delizia": "Do you really want to secure your device with SD card protection?", "Eckhart": ""}
    sd_card__enabled = 623,  // {"Bolt": "You have successfully enabled SD protection.", "Caesar": "", "Delizia": "You have successfully enabled SD protection.", "Eckhart": ""}
    sd_card__error = 624,  // {"Bolt": "SD card error", "Caesar": "", "Delizia": "SD card error", "Eckhart": ""}
    sd_card__format_card = 625,  // {"Bolt": "Format SD card", "Caesar": "", "Delizia": "Format SD card", "Eckhart": ""}
    sd_card__insert_correct_card = 626,  // {"Bolt": "Please insert the correct SD card for this device.", "Caesar": "", "Delizia": "Please insert the correct SD card for this device.", "Eckhart": ""}
    sd_card__please_insert = 627,  // {"Bolt": "Please insert your SD card.", "Caesar": "", "Delizia": "Please insert your SD card.", "Eckhart": ""}
    sd_card__please_unplug_and_insert = 628,  // {"Bolt": "Please unplug the device and insert your SD card.", "Caesar": "", "Delizia": "Please unplug the device and insert your SD card.", "Eckhart": ""}
    sd_card__problem_accessing = 629,  // {"Bolt": "There was a problem accessing the SD card.", "Caesar": "", "Delizia": "There was a problem accessing the SD card.", "Eckhart": ""}
    sd_card__refresh = 630,  // {"Bolt": "Do you really want to replace the current SD card secret with a newly generated one?", "Caesar": "", "Delizia": "Do you really want to replace the current SD card secret with a newly generated one?", "Eckhart": ""}
    sd_card__refreshed = 631,  // {"Bolt": "You have successfully refreshed SD protection.", "Caesar": "", "Delizia": "You have successfully refreshed SD protection.", "Eckhart": ""}
    sd_card__restart = 632,  // {"Bolt": "Do you want to restart Trezor in bootloader mode?", "Caesar": "", "Delizia": "Do you want to restart Trezor in bootloader mode?", "Eckhart": ""}
    sd_card__title = 633,  // {"Bolt": "SD card protection", "Caesar": "", "Delizia": "SD card protection", "Eckhart": ""}
    sd_card__title_problem = 634,  // {"Bolt": "SD card problem", "Caesar": "", "Delizia": "SD card problem", "Eckhart": ""}
    sd_card__unknown_filesystem = 635,  // {"Bolt": "Unknown filesystem.", "Caesar": "", "Delizia": "Unknown filesystem.", "Eckhart": ""}
    sd_card__unplug_and_insert_correct = 636,  // {"Bolt": "Please unplug the device and insert the correct SD card.", "Caesar": "", "Delizia": "Please unplug the device and insert the correct SD card.", "Eckhart": ""}
    sd_card__use_different_card = 637,  // {"Bolt": "Use a different card or format the SD card to the FAT32 filesystem.", "Caesar": "", "Delizia": "Use a different card or format the SD card to the FAT32 filesystem.", "Eckhart": ""}
    sd_card__wanna_format = 638,  // {"Bolt": "Do you really want to format the SD card?", "Caesar": "", "Delizia": "Do you really want to format the SD card?", "Eckhart": ""}
    sd_card__wrong_sd_card = 639,  // {"Bolt": "Wrong SD card.", "Caesar": "", "Delizia": "Wrong SD card.", "Eckhart": ""}
    send__confirm_sending = 641,  // "Sending amount"
    send__from_multiple_accounts = 642,  // "Sending from multiple accounts."
    send__including_fee = 643,  // "Including fee:"
    send__maximum_fee = 644,  // "Maximum fee"
    send__receiving_to_multisig = 645,  // "Receiving to a multisig address."
    send__title_confirm_sending = 646,  // "Confirm sending"
    send__title_joint_transaction = 647,  // "Joint transaction"
    send__title_receiving_to = 648,  // "Receiving to"
    send__title_sending = 649,  // "Sending"
    send__title_sending_amount = 650,  // "Sending amount"
    send__title_sending_to = 651,  // "Sending to"
    send__to_the_total_amount = 652,  // "To the total amount:"
    send__transaction_id = 654,  // "Transaction ID"
    send__you_are_contributing = 655,  // "You are contributing:"
    share_words__words_in_order = 656,  // " words in order."
    share_words__wrote_down_all = 657,  // "I wrote down all "
    sign_message__bytes_template = 658,  // "{0} Bytes"
    sign_message__confirm_address = 659,  // "Signing address"
    sign_message__confirm_message = 660,  // "Confirm message"
    sign_message__message_size = 661,  // "Message size"
    sign_message__verify_address = 662,  // "Verify address"
    #[cfg(feature = "universal_fw")]
    solana__account_index = 663,  // "Account index"
    #[cfg(feature = "universal_fw")]
    solana__associated_token_account = 664,  // "Associated token account"
    #[cfg(feature = "universal_fw")]
    solana__confirm_multisig = 665,  // "Confirm multisig"
    #[cfg(feature = "universal_fw")]
    solana__expected_fee = 666,  // "Expected fee"
    #[cfg(feature = "universal_fw")]
    solana__instruction_accounts_template = 667,  // "Instruction contains {0} accounts and its data is {1} bytes long."
    #[cfg(feature = "universal_fw")]
    solana__instruction_data = 668,  // "Instruction data"
    #[cfg(feature = "universal_fw")]
    solana__instruction_is_multisig = 669,  // "The following instruction is a multisig instruction."
    #[cfg(feature = "universal_fw")]
    solana__is_provided_via_lookup_table_template = 670,  // "{0} is provided via a lookup table."
    #[cfg(feature = "universal_fw")]
    solana__lookup_table_address = 671,  // "Lookup table address"
    #[cfg(feature = "universal_fw")]
    solana__multiple_signers = 672,  // "Multiple signers"
    #[cfg(feature = "universal_fw")]
    solana__transaction_contains_unknown_instructions = 674,  // "Transaction contains unknown instructions."
    #[cfg(feature = "universal_fw")]
    solana__transaction_requires_x_signers_template = 675,  // "Transaction requires {0} signers which increases the fee."
    #[cfg(feature = "universal_fw")]
    stellar__account_merge = 676,  // "Account Merge"
    #[cfg(feature = "universal_fw")]
    stellar__account_thresholds = 677,  // "Account Thresholds"
    #[cfg(feature = "universal_fw")]
    stellar__add_signer = 678,  // "Add Signer"
    #[cfg(feature = "universal_fw")]
    stellar__add_trust = 679,  // "Add trust"
    #[cfg(feature = "universal_fw")]
    stellar__all_will_be_sent_to = 680,  // "All XLM will be sent to"
    #[cfg(feature = "universal_fw")]
    stellar__allow_trust = 681,  // "Allow trust"
    words__asset = 682,  // "Asset"
    #[cfg(feature = "universal_fw")]
    stellar__balance_id = 683,  // "Balance ID"
    #[cfg(feature = "universal_fw")]
    stellar__bump_sequence = 684,  // "Bump Sequence"
    #[cfg(feature = "universal_fw")]
    stellar__buying = 685,  // "Buying:"
    #[cfg(feature = "universal_fw")]
    stellar__claim_claimable_balance = 686,  // "Claim Claimable Balance"
    #[cfg(feature = "universal_fw")]
    stellar__clear_data = 687,  // "Clear data"
    #[cfg(feature = "universal_fw")]
    stellar__clear_flags = 688,  // "Clear flags"
    #[cfg(feature = "universal_fw")]
    stellar__confirm_issuer = 689,  // "Confirm Issuer"
    #[cfg(feature = "universal_fw")]
    stellar__confirm_memo = 690,  // "Confirm memo"
    #[cfg(feature = "universal_fw")]
    stellar__confirm_operation = 692,  // "Confirm operation"
    #[cfg(feature = "universal_fw")]
    stellar__confirm_timebounds = 694,  // "Confirm timebounds"
    #[cfg(feature = "universal_fw")]
    stellar__create_account = 695,  // "Create Account"
    #[cfg(feature = "universal_fw")]
    stellar__debited_amount = 696,  // "Debited amount"
    #[cfg(feature = "universal_fw")]
    stellar__delete = 697,  // "Delete"
    #[cfg(feature = "universal_fw")]
    stellar__delete_passive_offer = 698,  // "Delete Passive Offer"
    #[cfg(feature = "universal_fw")]
    stellar__delete_trust = 699,  // "Delete trust"
    #[cfg(feature = "universal_fw")]
    stellar__destination = 700,  // "Destination"
    #[cfg(feature = "universal_fw")]
    stellar__exchanges_require_memo = 701,  // "Memo is not set.\nTypically needed when sending to exchanges."
    #[cfg(feature = "universal_fw")]
    stellar__final_confirm = 702,  // "Final confirm"
    #[cfg(feature = "universal_fw")]
    stellar__hash = 703,  // "Hash"
    #[cfg(feature = "universal_fw")]
    stellar__high = 704,  // "High:"
    #[cfg(feature = "universal_fw")]
    stellar__home_domain = 705,  // "Home Domain"
    #[cfg(feature = "universal_fw")]
    stellar__inflation = 706,  // "Inflation"
    #[cfg(feature = "universal_fw")]
    stellar__issuer_template = 709,  // "{0} issuer"
    #[cfg(feature = "universal_fw")]
    stellar__key = 710,  // "Key:"
    #[cfg(feature = "universal_fw")]
    stellar__limit = 711,  // "Limit"
    #[cfg(feature = "universal_fw")]
    stellar__low = 712,  // "Low:"
    #[cfg(feature = "universal_fw")]
    stellar__master_weight = 713,  // "Master Weight:"
    #[cfg(feature = "universal_fw")]
    stellar__medium = 714,  // "Medium:"
    #[cfg(feature = "universal_fw")]
    stellar__new_offer = 715,  // "New Offer"
    #[cfg(feature = "universal_fw")]
    stellar__new_passive_offer = 716,  // "New Passive Offer"
    #[cfg(feature = "universal_fw")]
    stellar__no_memo_set = 717,  // "No memo set!"
    #[cfg(feature = "universal_fw")]
    stellar__no_restriction = 718,  // "[no restriction]"
    #[cfg(feature = "universal_fw")]
    stellar__path_pay = 720,  // "Path Pay"
    #[cfg(feature = "universal_fw")]
    stellar__path_pay_at_least = 721,  // "Path Pay at least"
    #[cfg(feature = "universal_fw")]
    stellar__pay = 722,  // "Pay"
    #[cfg(feature = "universal_fw")]
    stellar__pay_at_most = 723,  // "Pay at most"
    #[cfg(feature = "universal_fw")]
    stellar__preauth_transaction = 724,  // "Pre-auth transaction"
    #[cfg(feature = "universal_fw")]
    stellar__price_per_template = 725,  // "Price per {0}:"
    #[cfg(feature = "universal_fw")]
    stellar__remove_signer = 727,  // "Remove Signer"
    #[cfg(feature = "universal_fw")]
    stellar__revoke_trust = 728,  // "Revoke trust"
    #[cfg(feature = "universal_fw")]
    stellar__selling = 729,  // "Selling:"
    #[cfg(feature = "universal_fw")]
    stellar__set_data = 730,  // "Set data"
    #[cfg(feature = "universal_fw")]
    stellar__set_flags = 731,  // "Set flags"
    #[cfg(feature = "universal_fw")]
    stellar__set_sequence_to_template = 732,  // "Set sequence to {0}?"
    #[cfg(feature = "universal_fw")]
    stellar__sign_tx_count_template = 733,  // "Sign this transaction made up of {0}"
    #[cfg(feature = "universal_fw")]
    stellar__sign_tx_fee_template = 734,  // "and pay {0}\nfor fee?"
    #[cfg(feature = "universal_fw")]
    stellar__source_account = 735,  // "Source account"
    #[cfg(feature = "universal_fw")]
    stellar__trusted_account = 737,  // "Trusted Account"
    #[cfg(feature = "universal_fw")]
    stellar__update = 738,  // "Update"
    #[cfg(feature = "universal_fw")]
    stellar__valid_from = 739,  // "Valid from (UTC)"
    #[cfg(feature = "universal_fw")]
    stellar__valid_to = 740,  // "Valid to (UTC)"
    #[cfg(feature = "universal_fw")]
    stellar__value_sha256 = 741,  // "Value (SHA-256):"
    #[cfg(feature = "universal_fw")]
    stellar__wanna_clean_value_key_template = 742,  // "Do you want to clear value key {0}?"
    #[cfg(feature = "universal_fw")]
    tezos__baker_address = 744,  // "Baker address"
    #[cfg(feature = "universal_fw")]
    tezos__balance = 745,  // "Balance:"
    #[cfg(feature = "universal_fw")]
    tezos__ballot = 746,  // "Ballot:"
    #[cfg(feature = "universal_fw")]
    tezos__confirm_delegation = 747,  // "Confirm delegation"
    #[cfg(feature = "universal_fw")]
    tezos__confirm_origination = 748,  // "Confirm origination"
    #[cfg(feature = "universal_fw")]
    tezos__delegator = 749,  // "Delegator"
    #[cfg(feature = "universal_fw")]
    tezos__proposal = 750,  // "Proposal"
    #[cfg(feature = "universal_fw")]
    tezos__register_delegate = 751,  // "Register delegate"
    #[cfg(feature = "universal_fw")]
    tezos__remove_delegation = 752,  // "Remove delegation"
    #[cfg(feature = "universal_fw")]
    tezos__submit_ballot = 753,  // "Submit ballot"
    #[cfg(feature = "universal_fw")]
    tezos__submit_proposal = 754,  // "Submit proposal"
    #[cfg(feature = "universal_fw")]
    tezos__submit_proposals = 755,  // "Submit proposals"
    tutorial__middle_click = 756,  // "Press both left and right at the same\ntime to confirm."
    tutorial__press_and_hold = 757,  // "Press and hold the right button to\napprove important operations."
    tutorial__ready_to_use = 758,  // "You're ready to\nuse Trezor."
    tutorial__scroll_down = 759,  // "Press right to scroll down to read all content when text doesn't fit on one screen.\n\rPress left to scroll up."
    tutorial__sure_you_want_skip = 760,  // "Are you sure you\nwant to skip the tutorial?"
    tutorial__title_hello = 761,  // "Hello"
    tutorial__title_screen_scroll = 762,  // "Screen scroll"
    tutorial__title_skip = 763,  // "Skip tutorial"
    tutorial__title_tutorial_complete = 764,  // "Tutorial complete"
    tutorial__use_trezor = 765,  // "Use Trezor by\nclicking the left and right buttons.\n\rContinue right."
    tutorial__welcome_press_right = 766,  // "Welcome to Trezor. Press right to continue."
    #[cfg(feature = "universal_fw")]
    u2f__get = 767,  // "Increase and retrieve the U2F counter?"
    #[cfg(feature = "universal_fw")]
    u2f__set_template = 768,  // "Set the U2F counter to {0}?"
    #[cfg(feature = "universal_fw")]
    u2f__title_get = 769,  // "Get U2F counter"
    #[cfg(feature = "universal_fw")]
    u2f__title_set = 770,  // "Set U2F counter"
    wipe__info = 771,  // "All data will be erased."
    wipe__title = 772,  // "Wipe device"
    wipe__want_to_wipe = 773,  // "Do you really want to wipe the device?\n"
    wipe_code__change = 774,  // "Change wipe code"
    wipe_code__changed = 775,  // "Wipe code changed."
    wipe_code__diff_from_pin = 776,  // "The wipe code must be different from your PIN."
    wipe_code__disabled = 777,  // "Wipe code disabled."
    wipe_code__enabled = 778,  // "Wipe code enabled."
    wipe_code__enter_new = 779,  // "New wipe code"
    wipe_code__info = 780,  // "Wipe code can be used to erase all data from this device."
    wipe_code__invalid = 781,  // "Invalid wipe code"
    wipe_code__mismatch = 782,  // "The wipe codes you entered do not match."
    wipe_code__reenter = 783,  // "Re-enter wipe code"
    wipe_code__reenter_to_confirm = 784,  // "Please re-enter wipe code to confirm."
    wipe_code__title_check = 785,  // "Check wipe code"
    wipe_code__title_invalid = 786,  // "Invalid wipe code"
    wipe_code__title_settings = 787,  // "Wipe code settings"
    wipe_code__turn_off = 788,  // "Turn off wipe code protection?"
    wipe_code__turn_on = 789,  // "Turn on wipe code protection?"
    wipe_code__wipe_code_mismatch = 790,  // "Wipe code mismatch"
    word_count__title = 791,  // "Number of words"
    words__account = 792,  // "Account"
    words__account_colon = 793,  // "Account:"
    words__address = 794,  // "Address"
    words__amount = 795,  // "Amount"
    words__are_you_sure = 796,  // "Are you sure?"
    words__array_of = 797,  // "Array of"
    words__blockhash = 798,  // "Blockhash"
    words__buying = 799,  // "Buying"
    words__confirm = 800,  // "Confirm"
    words__confirm_fee = 801,  // "Confirm fee"
    words__contains = 802,  // "Contains"
    words__continue_anyway_question = 803,  // "Continue anyway?"
    words__continue_with = 804,  // "Continue with"
    words__error = 805,  // "Error"
    words__fee = 806,  // "Fee"
    words__from = 807,  // "from"
    words__keep_it_safe = 808,  // "Keep it safe!"
    words__know_what_your_doing = 809,  // "Continue only if you know what you are doing!"
    words__my_trezor = 810,  // "My Trezor"
    words__no = 811,  // "No"
    words__outputs = 812,  // "outputs"
    words__please_check_again = 813,  // "Please check again"
    words__please_try_again = 814,  // "Please try again"
    words__really_wanna = 815,  // "Do you really want to"
    words__recipient = 816,  // "Recipient"
    words__sign = 817,  // "Sign"
    words__signer = 818,  // "Signer"
    words__title_check = 819,  // "Check"
    words__title_group = 820,  // "Group"
    words__title_information = 821,  // "Information"
    words__title_remember = 822,  // "Remember"
    words__title_share = 823,  // "Share"
    words__title_shares = 824,  // "Shares"
    words__title_success = 825,  // "Success"
    words__title_summary = 826,  // "Summary"
    words__title_threshold = 827,  // "Threshold"
    words__unknown = 828,  // "Unknown"
    words__warning = 829,  // "Warning"
    words__writable = 830,  // "Writable"
    words__yes = 831,  // "Yes"
    reboot_to_bootloader__just_a_moment = 832,  // "Just a moment..."
    inputs__previous = 833,  // {"Bolt": "", "Caesar": "PREVIOUS", "Delizia": "", "Eckhart": ""}
    #[cfg(feature = "universal_fw")]
    ethereum__staking_claim = 834,  // "Claim"
    #[cfg(feature = "universal_fw")]
    ethereum__staking_claim_address = 835,  // "Claim address"
    #[cfg(feature = "universal_fw")]
    ethereum__staking_claim_intro = 836,  // "Claim ETH from Everstake?"
    #[cfg(feature = "universal_fw")]
    ethereum__staking_stake = 837,  // "Stake"
    #[cfg(feature = "universal_fw")]
    ethereum__staking_stake_address = 838,  // "Stake address"
    #[cfg(feature = "universal_fw")]
    ethereum__staking_stake_intro = 839,  // "Stake ETH on Everstake?"
    #[cfg(feature = "universal_fw")]
    ethereum__staking_unstake = 840,  // "Unstake"
    #[cfg(feature = "universal_fw")]
    ethereum__staking_unstake_intro = 841,  // "Unstake ETH from Everstake?"
    storage_msg__starting = 842,  // "Starting up"
    storage_msg__verifying_pin = 843,  // {"Bolt": "Verifying PIN", "Caesar": "Verifying PIN", "Delizia": "Verifying PIN", "Eckhart": "Verifying PIN..."}
    storage_msg__wrong_pin = 844,  // "Wrong PIN"
    reset__create_x_of_y_multi_share_backup_template = 845,  // "Do you want to create a {0} of {1} multi-share backup?"
    reset__title_shamir_backup = 846,  // "Multi-share backup"
    #[cfg(feature = "universal_fw")]
    cardano__always_abstain = 847,  // "Always Abstain"
    #[cfg(feature = "universal_fw")]
    cardano__always_no_confidence = 848,  // "Always No Confidence"
    #[cfg(feature = "universal_fw")]
    cardano__delegating_to_key_hash = 849,  // "Delegating to key hash:"
    #[cfg(feature = "universal_fw")]
    cardano__delegating_to_script = 850,  // "Delegating to script:"
    #[cfg(feature = "universal_fw")]
    cardano__deposit = 851,  // "Deposit:"
    #[cfg(feature = "universal_fw")]
    cardano__vote_delegation = 852,  // "Vote delegation"
    instructions__tap_to_confirm = 854,  // "Tap to confirm"
    instructions__hold_to_confirm = 855,  // "Hold to confirm"
    words__important = 856,  // "Important"
    reset__words_written_down_template = 857,  // "I wrote down all {0} words in order."
    backup__create_backup_to_prevent_loss = 858,  // {"Bolt": "Create a backup to avoid losing access to your funds", "Caesar": "Create a backup to avoid losing access to your funds", "Delizia": "Create a backup to avoid losing access to your funds", "Eckhart": "Create a wallet backup to avoid losing access to your funds."}
    reset__check_backup_instructions = 859,  // "Let's do a quick check of your backup."
    words__instructions = 860,  // "Instructions"
    words__not_recommended = 861,  // "Not recommended!"
    address_details__account_info = 862,  // "Account info"
    address__cancel_contact_support = 863,  // "If receive address doesn't match, contact Trezor Support at trezor.io/support."
    address__cancel_receive = 864,  // {"Bolt": "Cancel receive", "Caesar": "Cancel receive", "Delizia": "Cancel receive", "Eckhart": "Cancel receive?"}
    address__qr_code = 865,  // "QR code"
    address_details__derivation_path = 866,  // "Derivation path"
    instructions__continue_in_app = 867,  // "Continue in the app"
    words__cancel_and_exit = 868,  // "Cancel and exit"
    address__confirmed = 869,  // "Receive address confirmed"
    pin__cancel_description = 870,  // "Continue without PIN"
    pin__cancel_info = 871,  // "Without a PIN, anyone can access this device."
    pin__cancel_setup = 872,  // {"Bolt": "Cancel PIN setup", "Caesar": "Cancel PIN setup", "Delizia": "Cancel PIN setup", "Eckhart": "Cancel PIN setup?"}
    send__cancel_sign = 873,  // "Cancel sign"
    send__send_from = 874,  // "Send from"
    instructions__hold_to_sign = 875,  // "Hold to sign"
    confirm_total__fee_rate = 876,  // "Fee rate"
    send__incl_transaction_fee = 877,  // "incl. Transaction fee"
    send__total_amount = 878,  // "Total amount"
    auto_lock__turned_on = 879,  // "Auto-lock turned on"
    backup__info_multi_share_backup = 880,  // "Your wallet backup contains multiple lists of words in a specific order (shares)."
    backup__info_single_share_backup = 881,  // "Your wallet backup contains {0} words in a specific order."
    backup__title_backup_completed = 882,  // {"Bolt": "Wallet backup completed", "Caesar": "Wallet backup completed", "Delizia": "Wallet backup completed", "Eckhart": "Wallet backup completed."}
    backup__title_create_wallet_backup = 883,  // "Create wallet backup"
    haptic_feedback__disable = 884,  // {"Bolt": "", "Caesar": "", "Delizia": "Disable haptic feedback?", "Eckhart": "Disable haptic feedback?"}
    haptic_feedback__enable = 885,  // {"Bolt": "", "Caesar": "", "Delizia": "Enable haptic feedback?", "Eckhart": "Enable haptic feedback?"}
    haptic_feedback__subtitle = 886,  // {"Bolt": "", "Caesar": "", "Delizia": "Setting", "Eckhart": "Setting"}
    haptic_feedback__title = 887,  // {"Bolt": "", "Caesar": "", "Delizia": "Haptic feedback", "Eckhart": "Haptic feedback"}
    instructions__continue_holding = 888,  // {"Bolt": "", "Caesar": "", "Delizia": "Continue\nholding", "Eckhart": "Keep holding"}
    instructions__enter_next_share = 889,  // "Enter next share"
    instructions__hold_to_continue = 890,  // "Hold to continue"
    instructions__hold_to_exit_tutorial = 891,  // "Hold to exit tutorial"
    instructions__learn_more = 893,  // "Learn more"
    instructions__shares_continue_with_x_template = 894,  // "Continue with Share #{0}"
    instructions__shares_start_with_1 = 895,  // "Start with share #1"
    passphrase__title_passphrase = 897,  // "Passphrase"
    recovery__dry_run_backup_not_on_this_device = 898,  // "Wallet backup not on this device"
    recovery__dry_run_invalid_backup_entered = 899,  // "Invalid wallet backup entered"
    recovery__dry_run_slip39_valid_all_shares = 900,  // "All shares are valid and belong to the backup in this device"
    recovery__dry_run_slip39_valid_share = 901,  // "Entered share is valid and belongs to the backup in the device"
    recovery__dry_run_verify_remaining_shares = 902,  // "Verify remaining recovery shares?"
    recovery__enter_each_word = 903,  // "Enter each word of your wallet backup in order."
    recovery__info_about_disconnect = 904,  // "It's safe to disconnect your Trezor while recovering your wallet and continue later."
    recovery__share_does_not_match = 905,  // "Share doesn't match"
    reset__cancel_create_wallet = 906,  // "Cancel create wallet"
    reset__incorrect_word_selected = 907,  // {"Bolt": "Incorrect word selected", "Caesar": "Incorrect word selected", "Delizia": "Incorrect word selected", "Eckhart": "Incorrect word selected."}
    reset__more_at = 908,  // "More at"
    reset__num_of_shares_how_many = 909,  // "How many wallet backup shares do you want to create?"
    reset__num_of_shares_long_info_template = 910,  // {"Bolt": "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.", "Caesar": "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.", "Delizia": "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.", "Eckhart": "Each backup share is a sequence of {0} words.\nStore each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet."}
    reset__select_threshold = 911,  // "Select the minimum shares required to recover your wallet."
    reset__share_completed_template = 912,  // "Share #{0} completed"
    reset__slip39_checklist_num_shares_x_template = 913,  // "Number of shares: {0}"
    reset__slip39_checklist_threshold_x_template = 914,  // "Recovery threshold: {0}"
    send__transaction_signed = 915,  // "Transaction signed"
    tutorial__continue = 916,  // "Continue tutorial"
    tutorial__exit = 917,  // "Exit tutorial"
    tutorial__menu = 920,  // "Find context-specific actions and options in the menu."
    tutorial__one_more_step = 921,  // "One more step"
    tutorial__ready_to_use_safe5 = 922,  // "You're all set to start using your device!"
    tutorial__swipe_up_and_down = 924,  // {"Bolt": "", "Caesar": "", "Delizia": "Tap the lower half of the screen to continue, or swipe down to go back.", "Eckhart": ""}
    tutorial__title_easy_navigation = 925,  // "Easy navigation"
    tutorial__welcome_safe5 = 926,  // {"Bolt": "", "Caesar": "", "Delizia": "Welcome to\nTrezor Safe 5", "Eckhart": ""}
    words__good_to_know = 927,  // "Good to know"
    words__operation_cancelled = 928,  // "Operation cancelled"
    words__settings = 929,  // "Settings"
    words__try_again = 930,  // {"Bolt": "Try again.", "Caesar": "Try again.", "Delizia": "Try again.", "Eckhart": "Try again"}
    reset__slip39_checklist_num_groups_x_template = 931,  // "Number of groups: {0}"
    brightness__title = 932,  // "Display brightness"
    recovery__title_unlock_repeated_backup = 933,  // "Multi-share backup"
    recovery__unlock_repeated_backup = 934,  // "Create additional backup?"
    recovery__unlock_repeated_backup_verb = 935,  // "Create backup"
    homescreen__set_default = 936,  // "Change wallpaper to default image?"
    reset__words_may_repeat = 937,  // "Words may repeat."
    reset__repeat_for_all_shares = 938,  // "Repeat for all shares."
    homescreen__settings_subtitle = 939,  // "Settings"
    homescreen__settings_title = 940,  // "Homescreen"
    reset__the_word_is_repeated = 941,  // {"Bolt": "The word is repeated", "Caesar": "The word is repeated", "Delizia": "The word is repeated", "Eckhart": "The word appears multiple times in the backup."}
    tutorial__title_lets_begin = 942,  // "Let's begin"
    tutorial__did_you_know = 943,  // "Did you know?"
    tutorial__first_wallet = 944,  // "The Trezor Model One, created in 2013,\nwas the world's first hardware wallet."
    tutorial__restart_tutorial = 945,  // "Restart tutorial"
    tutorial__title_handy_menu = 946,  // "Handy menu"
    tutorial__title_hold = 947,  // {"Bolt": "Hold to confirm important actions", "Caesar": "Hold to confirm important actions", "Delizia": "Hold to confirm important actions", "Eckhart": "Hold the on-screen button at the bottom to confirm important actions."}
    tutorial__title_well_done = 948,  // "Well done!"
    tutorial__lets_begin = 949,  // "Learn how to use and navigate this device with ease."
    tutorial__get_started = 950,  // "Get started!"
    instructions__swipe_horizontally = 951,  // "Swipe horizontally"
    setting__adjust = 952,  // "Adjust"
    setting__apply = 953,  // "Apply"
    brightness__changed_title = 954,  // "Display brightness changed"
    brightness__change_title = 955,  // "Change display brightness"
    words__title_done = 956,  // "Done"
    reset__slip39_checklist_more_info_threshold = 957,  // "The threshold sets the minimum number of shares needed to recover your wallet."
    reset__slip39_checklist_more_info_threshold_example_template = 958,  // "If you set {0} out of {1} shares, you'll need {2} backup shares to recover your wallet."
    passphrase__continue_with_empty_passphrase = 959,  // "Continue with empty passphrase?"
    #[cfg(feature = "universal_fw")]
    fido__more_credentials = 960,  // "More credentials"
    #[cfg(feature = "universal_fw")]
    fido__select_intro = 961,  // "Select the credential that you would like to use for authentication."
    #[cfg(feature = "universal_fw")]
    fido__title_for_authentication = 962,  // "for authentication"
    #[cfg(feature = "universal_fw")]
    fido__title_select_credential = 963,  // "Select credential"
    instructions__swipe_down = 964,  // "Swipe down"
    #[cfg(feature = "universal_fw")]
    fido__title_credential_details = 965,  // "Credential details"
    address__public_key_confirmed = 966,  // "Public key confirmed"
    words__continue_anyway = 967,  // "Continue anyway"
    #[cfg(feature = "universal_fw")]
    ethereum__unknown_contract_address = 968,  // {"Bolt": "Unknown contract address", "Caesar": "Unknown contract address", "Delizia": "Unknown contract address", "Eckhart": "Unknown token contract address."}
    #[cfg(feature = "universal_fw")]
    ethereum__token_contract = 969,  // {"Bolt": "Token contract", "Caesar": "Token contract", "Delizia": "Token contract", "Eckhart": "Token contract address"}
    buttons__view_all_data = 970,  // "View all data"
    instructions__view_all_data = 971,  // "View all data in the menu."
    #[cfg(feature = "universal_fw")]
    ethereum__interaction_contract = 972,  // {"Bolt": "Interaction contract", "Caesar": "Interaction contract", "Delizia": "Interaction contract", "Eckhart": "Interaction contract address"}
    misc__enable_labeling = 973,  // "Enable labeling?"
    #[cfg(feature = "universal_fw")]
    solana__base_fee = 975,  // "Base fee"
    #[cfg(feature = "universal_fw")]
    solana__claim = 976,  // "Claim"
    #[cfg(feature = "universal_fw")]
    solana__claim_question = 977,  // "Claim SOL from stake account?"
    #[cfg(feature = "universal_fw")]
    solana__claim_recipient_warning = 978,  // "Claiming SOL to address outside your current wallet."
    #[cfg(feature = "universal_fw")]
    solana__priority_fee = 979,  // "Priority fee"
    #[cfg(feature = "universal_fw")]
    solana__stake = 980,  // "Stake"
    #[cfg(feature = "universal_fw")]
    solana__stake_account = 981,  // "Stake account"
    words__provider = 982,  // "Provider"
    #[cfg(feature = "universal_fw")]
    solana__stake_question = 983,  // "Stake SOL?"
    #[cfg(feature = "universal_fw")]
    solana__stake_withdrawal_warning = 984,  // "The current wallet isn't the SOL staking withdraw authority."
    #[cfg(feature = "universal_fw")]
    solana__stake_withdrawal_warning_title = 985,  // "Withdraw authority address"
    #[cfg(feature = "universal_fw")]
    solana__unstake = 986,  // "Unstake"
    #[cfg(feature = "universal_fw")]
    solana__unstake_question = 987,  // "Unstake SOL from stake account?"
    #[cfg(feature = "universal_fw")]
    solana__vote_account = 988,  // "Vote account"
    #[cfg(feature = "universal_fw")]
    solana__stake_on_question = 989,  // "Stake SOL on {0}?"
    sign_message__confirm_without_review = 990,  // "Confirm without review"
    instructions__tap_to_continue = 991,  // "Tap to continue"
    #[cfg(feature = "universal_fw")]
    nostr__event_kind_template = 992,  // "Event kind: {0}"
    ble__unpair_all = 993,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Unpair all bluetooth devices"}
    ble__unpair_current = 994,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Unpair connected device"}
    ble__unpair_title = 995,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Unpair"}
    words__unlocked = 996,  // "Unlocked"
    #[cfg(feature = "universal_fw")]
    solana__max_fees_rent = 997,  // "Max fees and rent"
    #[cfg(feature = "universal_fw")]
    solana__max_rent_fee = 998,  // "Max rent fee"
    words__transaction_fee = 999,  // "Transaction fee"
    #[cfg(feature = "universal_fw")]
    ethereum__approve = 1000,  // "Approve"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_amount_allowance = 1001,  // "Amount allowance"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_chain_id = 1002,  // "Chain ID"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_intro = 1003,  // "Review details to approve token spending."
    #[cfg(feature = "universal_fw")]
    ethereum__approve_intro_title = 1004,  // "Token approval"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_to = 1005,  // "Approve to"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_unlimited_template = 1006,  // "Approving unlimited amount of {0}"
    words__unlimited = 1007,  // "Unlimited"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_intro_revoke = 1008,  // "Review details to revoke token approval."
    #[cfg(feature = "universal_fw")]
    ethereum__approve_intro_title_revoke = 1009,  // "Token revocation"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_revoke = 1010,  // "Revoke"
    #[cfg(feature = "universal_fw")]
    ethereum__approve_revoke_from = 1011,  // "Revoke from"
    words__chain = 1012,  // "Chain"
    words__token = 1013,  // "Token"
    instructions__tap = 1014,  // "Tap"
    #[cfg(feature = "universal_fw")]
    solana__unknown_token = 1015,  // "Unknown token"
    #[cfg(feature = "universal_fw")]
    solana__unknown_token_address = 1016,  // "Unknown token address"
    reset__share_words_first = 1017,  // "Write down the first word from the backup."
    backup__not_recommend = 1018,  // "We don't recommend to skip wallet backup creation."
    words__pay_attention = 1019,  // "Pay attention"
    address__check_with_source = 1020,  // "Check the address with source."
    words__receive = 1021,  // "Receive"
    reset__recovery_share_description = 1022,  // "A recovery share is a list of words you wrote down when setting up your Trezor."
    reset__recovery_share_number = 1023,  // "Your wallet backup consists of 1 to 16 shares."
    words__recovery_share = 1024,  // "Recovery share"
    send__send_in_the_app = 1025,  // "After signing, send the transaction in the app."
    send__sign_cancelled = 1026,  // "Sign cancelled."
    words__send = 1027,  // "Send"
    words__wallet = 1028,  // "Wallet"
    words__authenticate = 1029,  // "Authenticate"
    #[cfg(feature = "universal_fw")]
    ethereum__title_all_input_data_template = 1031,  // "All input data ({0} bytes)"
    auto_lock__description = 1032,  // "Set the time before your Trezor locks automatically."
    plurals__lock_after_x_days = 1033,  // "day|days"
    firmware_update__restart = 1034,  // "Trezor will restart after update."
    passphrase__access_hidden_wallet = 1035,  // "Access hidden wallet"
    passphrase__hidden_wallet = 1036,  // "Hidden wallet"
    passphrase__show = 1037,  // "Show passphrase"
    pin__reenter = 1038,  // "Re-enter PIN"
    pin__setup_completed = 1039,  // "PIN setup completed."
    instructions__shares_start_with_x_template = 1041,  // "Start with Share #{0}"
    reset__check_share_backup_template = 1042,  // "Let's do a quick check of Share #{0}."
    reset__select_word_from_share_template = 1043,  // "Select word #{0} from\nShare #{1}"
    recovery__share_from_group_entered_template = 1044,  // "Share #{0} from Group #{1} entered."
    send__cancel_transaction = 1045,  // "Cancel transaction"
    send__multisig_different_paths = 1046,  // "Using different paths for different XPUBs."
    address__xpub = 1047,  // {"Bolt": "XPUB", "Caesar": "XPUB", "Delizia": "XPUB", "Eckhart": "Public key (XPUB)"}
    words__cancel_question = 1048,  // "Cancel?"
    address__coin_address_template = 1049,  // "{0} address"
    #[cfg(feature = "universal_fw")]
    ethereum__contract_address = 1050,  // "Provider contract address"
    buttons__view = 1051,  // "View"
    words__swap = 1052,  // "Swap"
    address__title_provider_address = 1053,  // "Provider address"
    address__title_refund_address = 1054,  // "Refund address"
    words__assets = 1055,  // "Assets"
    #[cfg(feature = "universal_fw")]
    ethereum__title_confirm_message_hash = 1056,  // "Confirm message hash"
    buttons__finish = 1057,  // "Finish"
    instructions__menu_to_continue = 1058,  // "Use menu to continue"
    tutorial__last_one = 1059,  // "Last one"
    tutorial__menu_appendix = 1060,  // "View more info, quit flow, ..."
    tutorial__navigation_ts7 = 1061,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Use the on-screen buttons to navigate and confirm your actions."}
    tutorial__suite_restart = 1062,  // "Replay this tutorial anytime from the Trezor Suite app."
    tutorial__welcome_safe7 = 1067,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Welcome\nto Trezor\nSafe 7"}
    tutorial__what_is_tropic = 1068,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "What is TROPIC01?"}
    tutorial__tap_to_start = 1069,  // "Tap to start tutorial"
    tutorial__tropic_info = 1070,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "TROPIC01 is a next-gen open-source secure element chip designed for transparent and auditable hardware security."}
    #[cfg(feature = "universal_fw")]
    stellar__sign_with = 1071,  // "Sign with"
    #[cfg(feature = "universal_fw")]
    stellar__timebounds = 1072,  // "Timebounds"
    #[cfg(feature = "universal_fw")]
    stellar__token_info = 1073,  // "Token info"
    #[cfg(feature = "universal_fw")]
    stellar__transaction_source = 1074,  // "Transaction source"
    #[cfg(feature = "universal_fw")]
    stellar__transaction_source_diff_warning = 1075,  // "Transaction source does not belong to this Trezor."
    device_name__continue_with_empty_label = 1076,  // "Continue with empty device name?"
    device_name__enter = 1077,  // "Enter device name"
    regulatory__title = 1078,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Regulatory"}
    words__name = 1079,  // "Name"
    device_name__changed = 1080,  // "Device name changed."
    #[cfg(feature = "universal_fw")]
    cardano__confirm_message = 1081,  // "Confirm message"
    #[cfg(feature = "universal_fw")]
    cardano__empty_message = 1082,  // "Empty message"
    #[cfg(feature = "universal_fw")]
    cardano__message_hash = 1083,  // "Message hash:"
    #[cfg(feature = "universal_fw")]
    cardano__message_hex = 1084,  // "Message hex"
    #[cfg(feature = "universal_fw")]
    cardano__message_text = 1085,  // "Message text"
    #[cfg(feature = "universal_fw")]
    cardano__sign_message_hash_path_template = 1086,  // "Sign message hash with {0}"
    #[cfg(feature = "universal_fw")]
    cardano__sign_message_path_template = 1087,  // "Sign message with {0}"
    ble__manage_paired = 1088,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Manage paired devices"}
    ble__pair_new = 1089,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Pair new device"}
    ble__pair_title = 1090,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Pair & Connect"}
    ble__version = 1091,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Bluetooth version"}
    homescreen__firmware_type = 1092,  // "Firmware type"
    homescreen__firmware_version = 1093,  // "Firmware version"
    led__disable = 1094,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Disable LED?"}
    led__enable = 1095,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Enable LED?"}
    led__title = 1096,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "LED"}
    words__about = 1097,  // "About"
    words__connected = 1098,  // "Connected"
    words__device = 1099,  // "Device"
    words__disconnect = 1100,  // "Disconnect"
    words__led = 1101,  // "LED"
    words__manage = 1102,  // "Manage"
    words__off = 1103,  // "OFF"
    words__on = 1104,  // "ON"
    words__review = 1105,  // "Review"
    words__security = 1106,  // "Security"
    pin__change_question = 1107,  // "Change PIN?"
    pin__remove = 1108,  // "Remove PIN"
    pin__title = 1109,  // "PIN code"
    wipe_code__change_question = 1110,  // "Change wipe code?"
    wipe_code__remove = 1111,  // "Remove wipe code"
    wipe_code__title = 1112,  // "Wipe code"
    words__disabled = 1113,  // "Disabled"
    words__enabled = 1114,  // "Enabled"
    ble__disable = 1115,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Turn Bluetooth off?"}
    ble__enable = 1116,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Turn Bluetooth on?"}
    words__bluetooth = 1117,  // "Bluetooth"
    wipe__start_again = 1118,  // "Wipe your Trezor and start the setup process again."
    words__set = 1119,  // "Set"
    words__wipe = 1120,  // "Wipe"
    lockscreen__unlock = 1121,  // "Unlock"
    recovery__start_entering = 1122,  // "Start entering"
    words__disconnected = 1123,  // "Disconnected"
    ble__forget_all = 1124,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Forget all"}
    words__connect = 1125,  // "Connect"
    words__forget = 1126,  // "Forget"
    words__power = 1127,  // "Power"
    ble__limit_reached = 1128,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Limit of paired devices reached"}
    ble__forget_all_description = 1129,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "They'll be removed, and you'll need to pair them again before use."}
    ble__forget_all_devices = 1130,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Forget all devices?"}
    ble__forget_all_success = 1131,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "All connections removed."}
    ble__forget_this_description = 1132,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "It will be removed, and you'll need to pair it again before use."}
    ble__forget_this_device = 1133,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Forget this device?"}
    ble__forget_this_success = 1134,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Connection removed."}
    thp__autoconnect = 1135,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Allow {0} to connect automatically to this Trezor?"}
    thp__autoconnect_app = 1136,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Allow {0} on {1} to connect automatically to this Trezor?"}
    thp__connect = 1137,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Allow {0} to connect with this Trezor?"}
    thp__connect_app = 1138,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Allow {0} on {1} to connect with this Trezor?"}
    thp__pair = 1139,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Allow {0} to pair with this Trezor?"}
    thp__pair_app = 1140,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Allow {0} on {1} to pair with this Trezor?"}
    thp__autoconnect_title = 1141,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Autoconnect credential"}
    thp__code_entry = 1142,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Enter this one-time security code on {0}"}
    thp__code_title = 1143,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "One more step"}
    thp__connect_title = 1144,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Connection dialog"}
    thp__nfc_text = 1145,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Keep your Trezor near your phone to complete the setup."}
    thp__pair_title = 1146,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Before you continue"}
    thp__qr_title = 1147,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Scan QR code to pair"}
    ble__pairing_match = 1148,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Pairing code match?"}
    ble__pairing_title = 1149,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Bluetooth pairing"}
    thp__pair_name = 1151,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "{0} is your Trezor's name."}
    thp__pair_new_device = 1152,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Pair with new device"}
    tutorial__power = 1153,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Use the power button on the side to turn your device on or off."}
    auto_lock__on_battery = 1154,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "on battery / wireless charger"}
    auto_lock__on_usb = 1155,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "connected to USB"}
    pin__wipe_code_exists_description = 1156,  // "Wipe code must be turned off before turning off PIN protection."
    pin__wipe_code_exists_title = 1157,  // "Wipe code set"
    wipe_code__pin_not_set_description = 1158,  // "PIN must be set before enabling wipe code."
    wipe_code__cancel_setup = 1159,  // {"Bolt": "Cancel wipe code setup", "Caesar": "Cancel wipe code setup", "Delizia": "Cancel wipe code setup", "Eckhart": "Cancel wipe code setup?"}
    homescreen__backup_needed_info = 1160,  // "Open Trezor Suite and create a wallet backup. This is the only way to recover access to your assets."
    ble__host_info = 1161,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Connection info"}
    ble__mac_address = 1162,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "MAC address"}
    ble__waiting_for_host = 1163,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Waiting for connection..."}
    ble__apps_connected = 1164,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Apps connected"}
    sn__action = 1165,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Allow connected device to get serial number of your Trezor Safe 7?"}
    sn__title = 1166,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "Serial number"}
    ble__must_be_enabled = 1167,  // {"Bolt": "", "Caesar": "", "Delizia": "", "Eckhart": "The Bluetooth must be turned on to pair with a new device."}
    #[cfg(feature = "universal_fw")]
    ripple__destination_tag_missing = 1168,  // "Destination tag is not set. Typically needed when sending to exchanges."
    words__comm_trouble = 1169,  // "Your Trezor is having trouble communicating with your connected device."
    secure_sync__delegated_identity_key_no_thp = 1170,  // "Allow Trezor Suite to use Suite Sync with this Trezor?"
    secure_sync__delegated_identity_key_thp = 1171,  // "Allow {0} on {1} to use Suite Sync with this Trezor?"
    secure_sync__header = 1173,  // "Suite Sync"
    words__note = 1174,  // "Note"
}

cfg_if::cfg_if! {
    if #[cfg(feature = "layout_bolt")] {
        impl TranslatedString {
            const BTC_ONLY_BLOB: StringsBlob = StringsBlob {
                text: "Please contact Trezor support atKey mismatch?Address mismatch?trezor.io/supportWrong derivation path for selected account.XPUB mismatch?Public keyCosignerReceive addressYoursDerivation path:Receive addressReceiving toAllow connected app to check the authenticity of your {0}?Authenticate deviceAuto-lock Trezor after {0} of inactivity?Auto-lock delayYou can back up your Trezor once, at any time.You should back up your new wallet right now.It should be backed up now!Wallet created.\nWallet created successfully.You can use your backup to recover your wallet at any time.Back up walletSkip backupAre you sure you want to skip the backup?Commitment dataConfirm locktimeDo you want to create a proof of ownership?The mining fee of\n{0}\nis unexpectedly high.Locktime is set but will have no effect.Locktime set toLocktime set to blockheightA lot of change-outputs.Multiple accountsNew fee rate:Simple send ofTicket amountConfirm detailsFinalize transactionHigh mining feeMeld transactionModify amountPayjoinProof of ownershipPurchase ticketUpdate transactionUnknown pathUnknown transactionUnusually high fee.The transaction contains unverified external inputs.The signature is valid.Voting rights toAbortAccessAgainAllowBackBack upCancelChangeCheckCheck againCloseConfirmContinueDetailsEnableEnterEnter shareExportFormatGo backHold to confirmInfoInstallMore infoOk, I understandPurchaseQuitRestartRetrySelectSetShow allShow detailsShow wordsSkipTry againTurn offTurn onAccess your coinjoin account?Do not disconnect your Trezor!Max mining feeMax roundsAuthorize coinjoinCoinjoin in progressWaiting for othersFee rate:Sending from account:Fee infoSending fromChange device name to {0}?Device nameDo you really want to send entropy?Confirm entropySign transactionEnable experimental features?Only for development and beta testing!Experimental modeUpdate firmwareFW fingerprintClick to ConnectClick to UnlockBackup failedBackup neededCoinjoin authorizedExperimental modeNo USB connectionPIN not setSeedlessChange wallpaperJoint transactionTo the total amount:You are contributing:Change language to {0}?Language changed successfullyChanging languageLanguage settingsTap to connectTap to unlockLockedNot connectedDecrypt valueEncrypt valueSuite labelingDecrease amount by:Increase amount by:New amount:Modify amountDecrease fee by:Fee rate:Increase fee by:New transaction fee:Fee did not change.\nModify feeTransaction fee:Access passphrase wallet?Always enter your passphrase on Trezor?Passphrase provided by connected app will be used but will not be displayed due to the device settings.Passphrase walletHide passphrase coming from app?The next screen shows your passphrase.Please enter your passphrase.Do you want to revoke the passphrase on device setting?Confirm passphraseEnter passphraseHide passphrasePassphrase settingsPassphrase sourceTurn off passphrase protection?Turn on passphrase protection?Change PINPIN changed.Position of the cursor will change between entries for enhanced security.The new PIN must be different from your wipe code.PIN protection\nturned off.PIN protection\nturned on.Enter PINEnter new PINThe PIN you have entered is not valid.PIN will be required to access this device.Invalid PINLast attemptEntered PINs do not match!PIN mismatchPlease check again.Re-enter new PINPlease re-enter PIN to confirm.PIN should be 4-50 digits long.Check PINPIN settingsWrong PINtries leftAre you sure you want to turn off PIN protection?Turn on PIN protection?Wrong PINkey|keyshour|hoursmillisecond|millisecondsminute|minutessecond|secondsaction|actionsoperation|operationsgroup|groupsshare|sharesChecking authenticity...DoneLoading transaction...Locking the device...1 second leftPlease waitProcessingRefreshing...Signing transaction...Syncing...{0} seconds leftTrezor will restart in bootloader mode.Go to bootloaderFirmware version {0}\nby {1}Cancel backup checkCheck your backup?Position of the cursor will change between entries for enhanced security.The entered wallet backup is valid and matches the one in this device.The entered wallet backup is valid but does not match the one in the device.The entered recovery shares are valid and match what is currently in the device.The entered recovery shares are valid but do not match what is currently in the device.Enter any shareEnter your backup.Enter a different share.Enter share from a different group.Group {0}Group threshold reached.Invalid wallet backup entered.Invalid recovery share entered.More shares neededSelect the number of words in your backup.You'll only have to select the first 2-4 letters of each word.All progress will be lost.Share already enteredYou have entered a share from a different backup.Share {0}Recover walletCancel backup checkCancel recoveryBackup checkRecover walletRemaining sharesType word {0} of {1}Wallet recovery completedAre you sure you want to cancel the backup check?Are you sure you want to cancel the recovery process?({0} words)Word {0} of {1}{count} more {plural} starting{count} more {plural} needed{0} of {1} shares enteredYou have enteredThe group threshold specifies the number of groups required to recover your wallet.all {0} of {1} sharesany {0} of {1} sharesCreate walletRecover walletBy continuing you agree to Trezor Company's terms and conditions.Check backupCheck g{0} - share {1}Check wallet backupCheck share #{0}Continue with the next share.Continue with share #{0}.You have finished verifying your recovery shares for group {0}.You have finished verifying your wallet backup.You have finished verifying your recovery shares.A group is made up of recovery shares.Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds.Group {0} - Share {1} checked successfully.Group {0} - share {1}More info atFor recovery you need all {0} of the shares.For recovery you need any {0} of the shares.needed to form a group. needed to recover your wallet. Never put your backup anywhere digital.{0} people or locations will each hold one share.Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}.Each recovery share is a sequence of {0} words. Next you will choose how many shares you need to recover your wallet.The required number of shares to form Group {0}.= total number of unique word lists used for wallet backup.1 shareOnly one share will be created.Wallet backupRecovery share #{0}The required number of groups for recovery.Select the correct word for each position.Select {0} wordSelect word {0} of {1}:Set it to {0} and you will need Share #{0} checked successfully.Standard backupNumber of groupsNumber of sharesSet number of groupsSet number of sharesSet sizes and thresholdsSet size and threshold for each groupSet thresholdBackup checklistWrite down and check all sharesWrite down & check all wallet backup sharesThe threshold sets the number of shares = minimum number of unique word lists used for recovery.Backup is doneCreate walletGroup thresholdNumber of groupsNumber of sharesSet group thresholdSet number of groupsSet number of sharesSet thresholdto form Group {0}.trezor.io/tosSet the total number of shares in Group {0}.Use your backup when you need to recover your wallet.Write the following {0} words in order on your wallet backup card.Wrong word selected!For recovery you need 1 share.Your backup is done.Change display orientation to {0}?eastnorthsouthDisplay orientationwestTrezor will allow you to approve some actions which might be unsafe.Trezor will temporarily allow you to approve some actions which might be unsafe.Do you really want to enforce strict safety checks (recommended)?Safety checksSafety overrideAll data on the SD card will be lost.SD card required.Do you really want to remove SD card protection from your device?You have successfully disabled SD protection.Do you really want to secure your device with SD card protection?You have successfully enabled SD protection.SD card errorFormat SD cardPlease insert the correct SD card for this device.Please insert your SD card.Please unplug the device and insert your SD card.There was a problem accessing the SD card.Do you really want to replace the current SD card secret with a newly generated one?You have successfully refreshed SD protection.Do you want to restart Trezor in bootloader mode?SD card protectionSD card problemUnknown filesystem.Please unplug the device and insert the correct SD card.Use a different card or format the SD card to the FAT32 filesystem.Do you really want to format the SD card?Wrong SD card.Sending amountSending from multiple accounts.Including fee:Maximum feeReceiving to a multisig address.Confirm sendingJoint transactionReceiving toSendingSending amountSending toTo the total amount:Transaction IDYou are contributing: words in order.I wrote down all {0} BytesSigning addressConfirm messageMessage sizeVerify addressAssetPress both left and right at the same\ntime to confirm.Press and hold the right button to\napprove important operations.You're ready to\nuse Trezor.Press right to scroll down to read all content when text doesn't fit on one screen.\n\rPress left to scroll up.Are you sure you\nwant to skip the tutorial?HelloScreen scrollSkip tutorialTutorial completeUse Trezor by\nclicking the left and right buttons.\n\rContinue right.Welcome to Trezor. Press right to continue.All data will be erased.Wipe deviceDo you really want to wipe the device?\nChange wipe codeWipe code changed.The wipe code must be different from your PIN.Wipe code disabled.Wipe code enabled.New wipe codeWipe code can be used to erase all data from this device.Invalid wipe codeThe wipe codes you entered do not match.Re-enter wipe codePlease re-enter wipe code to confirm.Check wipe codeInvalid wipe codeWipe code settingsTurn off wipe code protection?Turn on wipe code protection?Wipe code mismatchNumber of wordsAccountAccount:AddressAmountAre you sure?Array ofBlockhashBuyingConfirmConfirm feeContainsContinue anyway?Continue withErrorFeefromKeep it safe!Continue only if you know what you are doing!My TrezorNooutputsPlease check againPlease try againDo you really want toRecipientSignSignerCheckGroupInformationRememberShareSharesSuccessSummaryThresholdUnknownWarningWritableYesJust a moment...Starting upVerifying PINWrong PINDo you want to create a {0} of {1} multi-share backup?Multi-share backupTap to confirmHold to confirmImportantI wrote down all {0} words in order.Create a backup to avoid losing access to your fundsLet's do a quick check of your backup.InstructionsNot recommended!Account infoIf receive address doesn't match, contact Trezor Support at trezor.io/support.Cancel receiveQR codeDerivation pathContinue in the appCancel and exitReceive address confirmedContinue without PINWithout a PIN, anyone can access this device.Cancel PIN setupCancel signSend fromHold to signFee rateincl. Transaction feeTotal amountAuto-lock turned onYour wallet backup contains multiple lists of words in a specific order (shares).Your wallet backup contains {0} words in a specific order.Wallet backup completedCreate wallet backupEnter next shareHold to continueHold to exit tutorialLearn moreContinue with Share #{0}Start with share #1PassphraseWallet backup not on this deviceInvalid wallet backup enteredAll shares are valid and belong to the backup in this deviceEntered share is valid and belongs to the backup in the deviceVerify remaining recovery shares?Enter each word of your wallet backup in order.It's safe to disconnect your Trezor while recovering your wallet and continue later.Share doesn't matchCancel create walletIncorrect word selectedMore atHow many wallet backup shares do you want to create?Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.Select the minimum shares required to recover your wallet.Share #{0} completedNumber of shares: {0}Recovery threshold: {0}Transaction signedContinue tutorialExit tutorialFind context-specific actions and options in the menu.One more stepYou're all set to start using your device!Easy navigationGood to knowOperation cancelledSettingsTry again.Number of groups: {0}Display brightnessMulti-share backupCreate additional backup?Create backupChange wallpaper to default image?Words may repeat.Repeat for all shares.SettingsHomescreenThe word is repeatedLet's beginDid you know?The Trezor Model One, created in 2013,\nwas the world's first hardware wallet.Restart tutorialHandy menuHold to confirm important actionsWell done!Learn how to use and navigate this device with ease.Get started!Swipe horizontallyAdjustApplyDisplay brightness changedChange display brightnessDoneThe threshold sets the minimum number of shares needed to recover your wallet.If you set {0} out of {1} shares, you'll need {2} backup shares to recover your wallet.Continue with empty passphrase?Swipe downPublic key confirmedContinue anywayView all dataView all data in the menu.Enable labeling?ProviderConfirm without reviewTap to continueUnlockedTransaction feeUnlimitedChainTokenTapWrite down the first word from the backup.We don't recommend to skip wallet backup creation.Pay attentionCheck the address with source.ReceiveA recovery share is a list of words you wrote down when setting up your Trezor.Your wallet backup consists of 1 to 16 shares.Recovery shareAfter signing, send the transaction in the app.Sign cancelled.SendWalletAuthenticateSet the time before your Trezor locks automatically.day|daysTrezor will restart after update.Access hidden walletHidden walletShow passphraseRe-enter PINPIN setup completed.Start with Share #{0}Let's do a quick check of Share #{0}.Select word #{0} from\nShare #{1}Share #{0} from Group #{1} entered.Cancel transactionUsing different paths for different XPUBs.XPUBCancel?{0} addressViewSwapProvider addressRefund addressAssetsFinishUse menu to continueLast oneView more info, quit flow, ...Replay this tutorial anytime from the Trezor Suite app.Tap to start tutorialContinue with empty device name?Enter device nameNameDevice name changed.Firmware typeFirmware versionAboutConnectedDeviceDisconnectLEDManageOFFONReviewSecurityChange PIN?Remove PINPIN codeChange wipe code?Remove wipe codeWipe codeDisabledEnabledBluetoothWipe your Trezor and start the setup process again.SetWipeUnlockStart enteringDisconnectedConnectForgetPowerWipe code must be turned off before turning off PIN protection.Wipe code setPIN must be set before enabling wipe code.Cancel wipe code setupOpen Trezor Suite and create a wallet backup. This is the only way to recover access to your assets.Your Trezor is having trouble communicating with your connected device.Allow Trezor Suite to use Suite Sync with this Trezor?Allow {0} on {1} to use Suite Sync with this Trezor?Suite SyncNote",
                offsets: &[
                    (Self::addr_mismatch__contact_support_at, 32),
                    (Self::addr_mismatch__key_mismatch, 45),
                    (Self::addr_mismatch__mismatch, 62),
                    (Self::addr_mismatch__support_url, 79),
                    (Self::addr_mismatch__wrong_derivation_path, 122),
                    (Self::addr_mismatch__xpub_mismatch, 136),
                    (Self::address__public_key, 146),
                    (Self::address__title_cosigner, 154),
                    (Self::address__title_receive_address, 169),
                    (Self::address__title_yours, 174),
                    (Self::address_details__derivation_path_colon, 190),
                    (Self::address_details__title_receive_address, 205),
                    (Self::address_details__title_receiving_to, 217),
                    (Self::authenticate__confirm_template, 275),
                    (Self::authenticate__header, 294),
                    (Self::auto_lock__change_template, 335),
                    (Self::auto_lock__title, 350),
                    (Self::backup__can_back_up_anytime, 396),
                    (Self::backup__it_should_be_backed_up, 441),
                    (Self::backup__it_should_be_backed_up_now, 468),
                    (Self::backup__new_wallet_created, 484),
                    (Self::backup__new_wallet_successfully_created, 512),
                    (Self::backup__recover_anytime, 571),
                    (Self::backup__title_backup_wallet, 585),
                    (Self::backup__title_skip, 596),
                    (Self::backup__want_to_skip, 637),
                    (Self::bitcoin__commitment_data, 652),
                    (Self::bitcoin__confirm_locktime, 668),
                    (Self::bitcoin__create_proof_of_ownership, 711),
                    (Self::bitcoin__high_mining_fee_template, 754),
                    (Self::bitcoin__locktime_no_effect, 794),
                    (Self::bitcoin__locktime_set_to, 809),
                    (Self::bitcoin__locktime_set_to_blockheight, 836),
                    (Self::bitcoin__lot_of_change_outputs, 860),
                    (Self::bitcoin__multiple_accounts, 877),
                    (Self::bitcoin__new_fee_rate, 890),
                    (Self::bitcoin__simple_send_of, 904),
                    (Self::bitcoin__ticket_amount, 917),
                    (Self::bitcoin__title_confirm_details, 932),
                    (Self::bitcoin__title_finalize_transaction, 952),
                    (Self::bitcoin__title_high_mining_fee, 967),
                    (Self::bitcoin__title_meld_transaction, 983),
                    (Self::bitcoin__title_modify_amount, 996),
                    (Self::bitcoin__title_payjoin, 1003),
                    (Self::bitcoin__title_proof_of_ownership, 1021),
                    (Self::bitcoin__title_purchase_ticket, 1036),
                    (Self::bitcoin__title_update_transaction, 1054),
                    (Self::bitcoin__unknown_path, 1066),
                    (Self::bitcoin__unknown_transaction, 1085),
                    (Self::bitcoin__unusually_high_fee, 1104),
                    (Self::bitcoin__unverified_external_inputs, 1156),
                    (Self::bitcoin__valid_signature, 1179),
                    (Self::bitcoin__voting_rights, 1195),
                    (Self::buttons__abort, 1200),
                    (Self::buttons__access, 1206),
                    (Self::buttons__again, 1211),
                    (Self::buttons__allow, 1216),
                    (Self::buttons__back, 1220),
                    (Self::buttons__back_up, 1227),
                    (Self::buttons__cancel, 1233),
                    (Self::buttons__change, 1239),
                    (Self::buttons__check, 1244),
                    (Self::buttons__check_again, 1255),
                    (Self::buttons__close, 1260),
                    (Self::buttons__confirm, 1267),
                    (Self::buttons__continue, 1275),
                    (Self::buttons__details, 1282),
                    (Self::buttons__enable, 1288),
                    (Self::buttons__enter, 1293),
                    (Self::buttons__enter_share, 1304),
                    (Self::buttons__export, 1310),
                    (Self::buttons__format, 1316),
                    (Self::buttons__go_back, 1323),
                    (Self::buttons__hold_to_confirm, 1338),
                    (Self::buttons__info, 1342),
                    (Self::buttons__install, 1349),
                    (Self::buttons__more_info, 1358),
                    (Self::buttons__ok_i_understand, 1374),
                    (Self::buttons__purchase, 1382),
                    (Self::buttons__quit, 1386),
                    (Self::buttons__restart, 1393),
                    (Self::buttons__retry, 1398),
                    (Self::buttons__select, 1404),
                    (Self::buttons__set, 1407),
                    (Self::buttons__show_all, 1415),
                    (Self::buttons__show_details, 1427),
                    (Self::buttons__show_words, 1437),
                    (Self::buttons__skip, 1441),
                    (Self::buttons__try_again, 1450),
                    (Self::buttons__turn_off, 1458),
                    (Self::buttons__turn_on, 1465),
                    (Self::coinjoin__access_account, 1494),
                    (Self::coinjoin__do_not_disconnect, 1524),
                    (Self::coinjoin__max_mining_fee, 1538),
                    (Self::coinjoin__max_rounds, 1548),
                    (Self::coinjoin__title, 1566),
                    (Self::coinjoin__title_progress, 1586),
                    (Self::coinjoin__waiting_for_others, 1604),
                    (Self::confirm_total__fee_rate_colon, 1613),
                    (Self::confirm_total__sending_from_account, 1634),
                    (Self::confirm_total__title_fee, 1642),
                    (Self::confirm_total__title_sending_from, 1654),
                    (Self::device_name__change_template, 1680),
                    (Self::device_name__title, 1691),
                    (Self::entropy__send, 1726),
                    (Self::entropy__title_confirm, 1741),
                    (Self::send__sign_transaction, 1757),
                    (Self::experimental_mode__enable, 1786),
                    (Self::experimental_mode__only_for_dev, 1824),
                    (Self::experimental_mode__title, 1841),
                    (Self::firmware_update__title, 1856),
                    (Self::firmware_update__title_fingerprint, 1870),
                    (Self::homescreen__click_to_connect, 1886),
                    (Self::homescreen__click_to_unlock, 1901),
                    (Self::homescreen__title_backup_failed, 1914),
                    (Self::homescreen__title_backup_needed, 1927),
                    (Self::homescreen__title_coinjoin_authorized, 1946),
                    (Self::homescreen__title_experimental_mode, 1963),
                    (Self::homescreen__title_no_usb_connection, 1980),
                    (Self::homescreen__title_pin_not_set, 1991),
                    (Self::homescreen__title_seedless, 1999),
                    (Self::homescreen__title_set, 2015),
                    (Self::inputs__back, 2015),
                    (Self::inputs__cancel, 2015),
                    (Self::inputs__delete, 2015),
                    (Self::inputs__enter, 2015),
                    (Self::inputs__return, 2015),
                    (Self::inputs__show, 2015),
                    (Self::inputs__space, 2015),
                    (Self::joint__title, 2032),
                    (Self::joint__to_the_total_amount, 2052),
                    (Self::joint__you_are_contributing, 2073),
                    (Self::language__change_to_template, 2096),
                    (Self::language__changed, 2125),
                    (Self::language__progress, 2142),
                    (Self::language__title, 2159),
                    (Self::lockscreen__tap_to_connect, 2173),
                    (Self::lockscreen__tap_to_unlock, 2186),
                    (Self::lockscreen__title_locked, 2192),
                    (Self::lockscreen__title_not_connected, 2205),
                    (Self::misc__decrypt_value, 2218),
                    (Self::misc__encrypt_value, 2231),
                    (Self::misc__title_suite_labeling, 2245),
                    (Self::modify_amount__decrease_amount, 2264),
                    (Self::modify_amount__increase_amount, 2283),
                    (Self::modify_amount__new_amount, 2294),
                    (Self::modify_amount__title, 2307),
                    (Self::modify_fee__decrease_fee, 2323),
                    (Self::modify_fee__fee_rate, 2332),
                    (Self::modify_fee__increase_fee, 2348),
                    (Self::modify_fee__new_transaction_fee, 2368),
                    (Self::modify_fee__no_change, 2388),
                    (Self::modify_fee__title, 2398),
                    (Self::modify_fee__transaction_fee, 2414),
                    (Self::passphrase__access_wallet, 2439),
                    (Self::passphrase__always_on_device, 2478),
                    (Self::passphrase__from_host_not_shown, 2581),
                    (Self::passphrase__wallet, 2598),
                    (Self::passphrase__hide, 2630),
                    (Self::passphrase__next_screen_will_show_passphrase, 2668),
                    (Self::passphrase__please_enter, 2697),
                    (Self::passphrase__revoke_on_device, 2752),
                    (Self::passphrase__title_confirm, 2770),
                    (Self::passphrase__title_enter, 2786),
                    (Self::passphrase__title_hide, 2801),
                    (Self::passphrase__title_settings, 2820),
                    (Self::passphrase__title_source, 2837),
                    (Self::passphrase__turn_off, 2868),
                    (Self::passphrase__turn_on, 2898),
                    (Self::pin__change, 2908),
                    (Self::pin__changed, 2920),
                    (Self::pin__cursor_will_change, 2993),
                    (Self::pin__diff_from_wipe_code, 3043),
                    (Self::pin__disabled, 3069),
                    (Self::pin__enabled, 3094),
                    (Self::pin__enter, 3103),
                    (Self::pin__enter_new, 3116),
                    (Self::pin__entered_not_valid, 3154),
                    (Self::pin__info, 3197),
                    (Self::pin__invalid_pin, 3208),
                    (Self::pin__last_attempt, 3220),
                    (Self::pin__mismatch, 3246),
                    (Self::pin__pin_mismatch, 3258),
                    (Self::pin__please_check_again, 3277),
                    (Self::pin__reenter_new, 3293),
                    (Self::pin__reenter_to_confirm, 3324),
                    (Self::pin__should_be_long, 3355),
                    (Self::pin__title_check_pin, 3364),
                    (Self::pin__title_settings, 3376),
                    (Self::pin__title_wrong_pin, 3385),
                    (Self::pin__tries_left, 3395),
                    (Self::pin__turn_off, 3444),
                    (Self::pin__turn_on, 3467),
                    (Self::pin__wrong_pin, 3476),
                    (Self::plurals__contains_x_keys, 3484),
                    (Self::plurals__lock_after_x_hours, 3494),
                    (Self::plurals__lock_after_x_milliseconds, 3518),
                    (Self::plurals__lock_after_x_minutes, 3532),
                    (Self::plurals__lock_after_x_seconds, 3546),
                    (Self::plurals__sign_x_actions, 3560),
                    (Self::plurals__transaction_of_x_operations, 3580),
                    (Self::plurals__x_groups_needed, 3592),
                    (Self::plurals__x_shares_needed, 3604),
                    (Self::progress__authenticity_check, 3628),
                    (Self::progress__done, 3632),
                    (Self::progress__loading_transaction, 3654),
                    (Self::progress__locking_device, 3675),
                    (Self::progress__one_second_left, 3688),
                    (Self::progress__please_wait, 3699),
                    (Self::storage_msg__processing, 3709),
                    (Self::progress__refreshing, 3722),
                    (Self::progress__signing_transaction, 3744),
                    (Self::progress__syncing, 3754),
                    (Self::progress__x_seconds_left_template, 3770),
                    (Self::reboot_to_bootloader__restart, 3809),
                    (Self::reboot_to_bootloader__title, 3825),
                    (Self::reboot_to_bootloader__version_by_template, 3852),
                    (Self::recovery__cancel_dry_run, 3871),
                    (Self::recovery__check_dry_run, 3889),
                    (Self::recovery__cursor_will_change, 3962),
                    (Self::recovery__dry_run_bip39_valid_match, 4032),
                    (Self::recovery__dry_run_bip39_valid_mismatch, 4108),
                    (Self::recovery__dry_run_slip39_valid_match, 4188),
                    (Self::recovery__dry_run_slip39_valid_mismatch, 4275),
                    (Self::recovery__enter_any_share, 4290),
                    (Self::recovery__enter_backup, 4308),
                    (Self::recovery__enter_different_share, 4332),
                    (Self::recovery__enter_share_from_diff_group, 4367),
                    (Self::recovery__group_num_template, 4376),
                    (Self::recovery__group_threshold_reached, 4400),
                    (Self::recovery__invalid_wallet_backup_entered, 4430),
                    (Self::recovery__invalid_share_entered, 4461),
                    (Self::recovery__more_shares_needed, 4479),
                    (Self::recovery__num_of_words, 4521),
                    (Self::recovery__only_first_n_letters, 4583),
                    (Self::recovery__progress_will_be_lost, 4609),
                    (Self::recovery__share_already_entered, 4630),
                    (Self::recovery__share_from_another_multi_share_backup, 4679),
                    (Self::recovery__share_num_template, 4688),
                    (Self::recovery__title, 4702),
                    (Self::recovery__title_cancel_dry_run, 4721),
                    (Self::recovery__title_cancel_recovery, 4736),
                    (Self::recovery__title_dry_run, 4748),
                    (Self::recovery__title_recover, 4762),
                    (Self::recovery__title_remaining_shares, 4778),
                    (Self::recovery__type_word_x_of_y_template, 4798),
                    (Self::recovery__wallet_recovered, 4823),
                    (Self::recovery__wanna_cancel_dry_run, 4872),
                    (Self::recovery__wanna_cancel_recovery, 4925),
                    (Self::recovery__word_count_template, 4936),
                    (Self::recovery__word_x_of_y_template, 4951),
                    (Self::recovery__x_more_items_starting_template_plural, 4981),
                    (Self::recovery__x_more_shares_needed_template_plural, 5009),
                    (Self::recovery__x_of_y_entered_template, 5034),
                    (Self::recovery__you_have_entered, 5050),
                    (Self::reset__advanced_group_threshold_info, 5133),
                    (Self::reset__all_x_of_y_template, 5154),
                    (Self::reset__any_x_of_y_template, 5175),
                    (Self::reset__button_create, 5188),
                    (Self::reset__button_recover, 5202),
                    (Self::reset__by_continuing, 5267),
                    (Self::reset__check_backup_title, 5279),
                    (Self::reset__check_group_share_title_template, 5301),
                    (Self::reset__check_wallet_backup_title, 5320),
                    (Self::reset__check_share_title_template, 5336),
                    (Self::reset__continue_with_next_share, 5365),
                    (Self::reset__continue_with_share_template, 5390),
                    (Self::reset__finished_verifying_group_template, 5453),
                    (Self::reset__finished_verifying_wallet_backup, 5500),
                    (Self::reset__finished_verifying_shares, 5549),
                    (Self::reset__group_description, 5587),
                    (Self::reset__group_info, 5720),
                    (Self::reset__group_share_checked_successfully_template, 5763),
                    (Self::reset__group_share_title_template, 5784),
                    (Self::reset__more_info_at, 5796),
                    (Self::reset__need_all_share_template, 5840),
                    (Self::reset__need_any_share_template, 5884),
                    (Self::reset__needed_to_form_a_group, 5908),
                    (Self::reset__needed_to_recover_your_wallet, 5939),
                    (Self::reset__never_make_digital_copy, 5978),
                    (Self::reset__num_of_share_holders_template, 6027),
                    (Self::reset__num_of_shares_advanced_info_template, 6152),
                    (Self::reset__num_of_shares_basic_info_template, 6269),
                    (Self::reset__num_shares_for_group_template, 6317),
                    (Self::reset__number_of_shares_info, 6376),
                    (Self::reset__one_share, 6383),
                    (Self::reset__only_one_share_will_be_created, 6414),
                    (Self::reset__recovery_wallet_backup_title, 6427),
                    (Self::reset__recovery_share_title_template, 6446),
                    (Self::reset__required_number_of_groups, 6489),
                    (Self::reset__select_correct_word, 6531),
                    (Self::reset__select_word_template, 6546),
                    (Self::reset__select_word_x_of_y_template, 6569),
                    (Self::reset__set_it_to_count_template, 6601),
                    (Self::reset__share_checked_successfully_template, 6633),
                    (Self::reset__share_words_title, 6648),
                    (Self::reset__slip39_checklist_num_groups, 6664),
                    (Self::reset__slip39_checklist_num_shares, 6680),
                    (Self::reset__slip39_checklist_set_num_groups, 6700),
                    (Self::reset__slip39_checklist_set_num_shares, 6720),
                    (Self::reset__slip39_checklist_set_sizes, 6744),
                    (Self::reset__slip39_checklist_set_sizes_longer, 6781),
                    (Self::reset__slip39_checklist_set_threshold, 6794),
                    (Self::reset__slip39_checklist_title, 6810),
                    (Self::reset__slip39_checklist_write_down, 6841),
                    (Self::reset__slip39_checklist_write_down_recovery, 6884),
                    (Self::reset__the_threshold_sets_the_number_of_shares, 6924),
                    (Self::reset__threshold_info, 6980),
                    (Self::reset__title_backup_is_done, 6994),
                    (Self::reset__title_create_wallet, 7007),
                    (Self::reset__title_group_threshold, 7022),
                    (Self::reset__title_number_of_groups, 7038),
                    (Self::reset__title_number_of_shares, 7054),
                    (Self::reset__title_set_group_threshold, 7073),
                    (Self::reset__title_set_number_of_groups, 7093),
                    (Self::reset__title_set_number_of_shares, 7113),
                    (Self::reset__title_set_threshold, 7126),
                    (Self::reset__to_form_group_template, 7144),
                    (Self::reset__tos_link, 7157),
                    (Self::reset__total_number_of_shares_in_group_template, 7201),
                    (Self::reset__use_your_backup, 7254),
                    (Self::reset__write_down_words_template, 7320),
                    (Self::reset__wrong_word_selected, 7340),
                    (Self::reset__you_need_one_share, 7370),
                    (Self::reset__your_backup_is_done, 7390),
                    (Self::rotation__change_template, 7424),
                    (Self::rotation__east, 7428),
                    (Self::rotation__north, 7433),
                    (Self::rotation__south, 7438),
                    (Self::rotation__title_change, 7457),
                    (Self::rotation__west, 7461),
                    (Self::safety_checks__approve_unsafe_always, 7529),
                    (Self::safety_checks__approve_unsafe_temporary, 7609),
                    (Self::safety_checks__enforce_strict, 7674),
                    (Self::safety_checks__title, 7687),
                    (Self::safety_checks__title_safety_override, 7702),
                    (Self::sd_card__all_data_will_be_lost, 7739),
                    (Self::sd_card__card_required, 7756),
                    (Self::sd_card__disable, 7821),
                    (Self::sd_card__disabled, 7866),
                    (Self::sd_card__enable, 7931),
                    (Self::sd_card__enabled, 7975),
                    (Self::sd_card__error, 7988),
                    (Self::sd_card__format_card, 8002),
                    (Self::sd_card__insert_correct_card, 8052),
                    (Self::sd_card__please_insert, 8079),
                    (Self::sd_card__please_unplug_and_insert, 8128),
                    (Self::sd_card__problem_accessing, 8170),
                    (Self::sd_card__refresh, 8254),
                    (Self::sd_card__refreshed, 8300),
                    (Self::sd_card__restart, 8349),
                    (Self::sd_card__title, 8367),
                    (Self::sd_card__title_problem, 8382),
                    (Self::sd_card__unknown_filesystem, 8401),
                    (Self::sd_card__unplug_and_insert_correct, 8457),
                    (Self::sd_card__use_different_card, 8524),
                    (Self::sd_card__wanna_format, 8565),
                    (Self::sd_card__wrong_sd_card, 8579),
                    (Self::send__confirm_sending, 8593),
                    (Self::send__from_multiple_accounts, 8624),
                    (Self::send__including_fee, 8638),
                    (Self::send__maximum_fee, 8649),
                    (Self::send__receiving_to_multisig, 8681),
                    (Self::send__title_confirm_sending, 8696),
                    (Self::send__title_joint_transaction, 8713),
                    (Self::send__title_receiving_to, 8725),
                    (Self::send__title_sending, 8732),
                    (Self::send__title_sending_amount, 8746),
                    (Self::send__title_sending_to, 8756),
                    (Self::send__to_the_total_amount, 8776),
                    (Self::send__transaction_id, 8790),
                    (Self::send__you_are_contributing, 8811),
                    (Self::share_words__words_in_order, 8827),
                    (Self::share_words__wrote_down_all, 8844),
                    (Self::sign_message__bytes_template, 8853),
                    (Self::sign_message__confirm_address, 8868),
                    (Self::sign_message__confirm_message, 8883),
                    (Self::sign_message__message_size, 8895),
                    (Self::sign_message__verify_address, 8909),
                    (Self::words__asset, 8914),
                    (Self::tutorial__middle_click, 8968),
                    (Self::tutorial__press_and_hold, 9032),
                    (Self::tutorial__ready_to_use, 9059),
                    (Self::tutorial__scroll_down, 9168),
                    (Self::tutorial__sure_you_want_skip, 9211),
                    (Self::tutorial__title_hello, 9216),
                    (Self::tutorial__title_screen_scroll, 9229),
                    (Self::tutorial__title_skip, 9242),
                    (Self::tutorial__title_tutorial_complete, 9259),
                    (Self::tutorial__use_trezor, 9326),
                    (Self::tutorial__welcome_press_right, 9369),
                    (Self::wipe__info, 9393),
                    (Self::wipe__title, 9404),
                    (Self::wipe__want_to_wipe, 9443),
                    (Self::wipe_code__change, 9459),
                    (Self::wipe_code__changed, 9477),
                    (Self::wipe_code__diff_from_pin, 9523),
                    (Self::wipe_code__disabled, 9542),
                    (Self::wipe_code__enabled, 9560),
                    (Self::wipe_code__enter_new, 9573),
                    (Self::wipe_code__info, 9630),
                    (Self::wipe_code__invalid, 9647),
                    (Self::wipe_code__mismatch, 9687),
                    (Self::wipe_code__reenter, 9705),
                    (Self::wipe_code__reenter_to_confirm, 9742),
                    (Self::wipe_code__title_check, 9757),
                    (Self::wipe_code__title_invalid, 9774),
                    (Self::wipe_code__title_settings, 9792),
                    (Self::wipe_code__turn_off, 9822),
                    (Self::wipe_code__turn_on, 9851),
                    (Self::wipe_code__wipe_code_mismatch, 9869),
                    (Self::word_count__title, 9884),
                    (Self::words__account, 9891),
                    (Self::words__account_colon, 9899),
                    (Self::words__address, 9906),
                    (Self::words__amount, 9912),
                    (Self::words__are_you_sure, 9925),
                    (Self::words__array_of, 9933),
                    (Self::words__blockhash, 9942),
                    (Self::words__buying, 9948),
                    (Self::words__confirm, 9955),
                    (Self::words__confirm_fee, 9966),
                    (Self::words__contains, 9974),
                    (Self::words__continue_anyway_question, 9990),
                    (Self::words__continue_with, 10003),
                    (Self::words__error, 10008),
                    (Self::words__fee, 10011),
                    (Self::words__from, 10015),
                    (Self::words__keep_it_safe, 10028),
                    (Self::words__know_what_your_doing, 10073),
                    (Self::words__my_trezor, 10082),
                    (Self::words__no, 10084),
                    (Self::words__outputs, 10091),
                    (Self::words__please_check_again, 10109),
                    (Self::words__please_try_again, 10125),
                    (Self::words__really_wanna, 10146),
                    (Self::words__recipient, 10155),
                    (Self::words__sign, 10159),
                    (Self::words__signer, 10165),
                    (Self::words__title_check, 10170),
                    (Self::words__title_group, 10175),
                    (Self::words__title_information, 10186),
                    (Self::words__title_remember, 10194),
                    (Self::words__title_share, 10199),
                    (Self::words__title_shares, 10205),
                    (Self::words__title_success, 10212),
                    (Self::words__title_summary, 10219),
                    (Self::words__title_threshold, 10228),
                    (Self::words__unknown, 10235),
                    (Self::words__warning, 10242),
                    (Self::words__writable, 10250),
                    (Self::words__yes, 10253),
                    (Self::reboot_to_bootloader__just_a_moment, 10269),
                    (Self::inputs__previous, 10269),
                    (Self::storage_msg__starting, 10280),
                    (Self::storage_msg__verifying_pin, 10293),
                    (Self::storage_msg__wrong_pin, 10302),
                    (Self::reset__create_x_of_y_multi_share_backup_template, 10356),
                    (Self::reset__title_shamir_backup, 10374),
                    (Self::instructions__tap_to_confirm, 10388),
                    (Self::instructions__hold_to_confirm, 10403),
                    (Self::words__important, 10412),
                    (Self::reset__words_written_down_template, 10448),
                    (Self::backup__create_backup_to_prevent_loss, 10500),
                    (Self::reset__check_backup_instructions, 10538),
                    (Self::words__instructions, 10550),
                    (Self::words__not_recommended, 10566),
                    (Self::address_details__account_info, 10578),
                    (Self::address__cancel_contact_support, 10656),
                    (Self::address__cancel_receive, 10670),
                    (Self::address__qr_code, 10677),
                    (Self::address_details__derivation_path, 10692),
                    (Self::instructions__continue_in_app, 10711),
                    (Self::words__cancel_and_exit, 10726),
                    (Self::address__confirmed, 10751),
                    (Self::pin__cancel_description, 10771),
                    (Self::pin__cancel_info, 10816),
                    (Self::pin__cancel_setup, 10832),
                    (Self::send__cancel_sign, 10843),
                    (Self::send__send_from, 10852),
                    (Self::instructions__hold_to_sign, 10864),
                    (Self::confirm_total__fee_rate, 10872),
                    (Self::send__incl_transaction_fee, 10893),
                    (Self::send__total_amount, 10905),
                    (Self::auto_lock__turned_on, 10924),
                    (Self::backup__info_multi_share_backup, 11005),
                    (Self::backup__info_single_share_backup, 11063),
                    (Self::backup__title_backup_completed, 11086),
                    (Self::backup__title_create_wallet_backup, 11106),
                    (Self::haptic_feedback__disable, 11106),
                    (Self::haptic_feedback__enable, 11106),
                    (Self::haptic_feedback__subtitle, 11106),
                    (Self::haptic_feedback__title, 11106),
                    (Self::instructions__continue_holding, 11106),
                    (Self::instructions__enter_next_share, 11122),
                    (Self::instructions__hold_to_continue, 11138),
                    (Self::instructions__hold_to_exit_tutorial, 11159),
                    (Self::instructions__learn_more, 11169),
                    (Self::instructions__shares_continue_with_x_template, 11193),
                    (Self::instructions__shares_start_with_1, 11212),
                    (Self::passphrase__title_passphrase, 11222),
                    (Self::recovery__dry_run_backup_not_on_this_device, 11254),
                    (Self::recovery__dry_run_invalid_backup_entered, 11283),
                    (Self::recovery__dry_run_slip39_valid_all_shares, 11343),
                    (Self::recovery__dry_run_slip39_valid_share, 11405),
                    (Self::recovery__dry_run_verify_remaining_shares, 11438),
                    (Self::recovery__enter_each_word, 11485),
                    (Self::recovery__info_about_disconnect, 11569),
                    (Self::recovery__share_does_not_match, 11588),
                    (Self::reset__cancel_create_wallet, 11608),
                    (Self::reset__incorrect_word_selected, 11631),
                    (Self::reset__more_at, 11638),
                    (Self::reset__num_of_shares_how_many, 11690),
                    (Self::reset__num_of_shares_long_info_template, 11861),
                    (Self::reset__select_threshold, 11919),
                    (Self::reset__share_completed_template, 11939),
                    (Self::reset__slip39_checklist_num_shares_x_template, 11960),
                    (Self::reset__slip39_checklist_threshold_x_template, 11983),
                    (Self::send__transaction_signed, 12001),
                    (Self::tutorial__continue, 12018),
                    (Self::tutorial__exit, 12031),
                    (Self::tutorial__menu, 12085),
                    (Self::tutorial__one_more_step, 12098),
                    (Self::tutorial__ready_to_use_safe5, 12140),
                    (Self::tutorial__swipe_up_and_down, 12140),
                    (Self::tutorial__title_easy_navigation, 12155),
                    (Self::tutorial__welcome_safe5, 12155),
                    (Self::words__good_to_know, 12167),
                    (Self::words__operation_cancelled, 12186),
                    (Self::words__settings, 12194),
                    (Self::words__try_again, 12204),
                    (Self::reset__slip39_checklist_num_groups_x_template, 12225),
                    (Self::brightness__title, 12243),
                    (Self::recovery__title_unlock_repeated_backup, 12261),
                    (Self::recovery__unlock_repeated_backup, 12286),
                    (Self::recovery__unlock_repeated_backup_verb, 12299),
                    (Self::homescreen__set_default, 12333),
                    (Self::reset__words_may_repeat, 12350),
                    (Self::reset__repeat_for_all_shares, 12372),
                    (Self::homescreen__settings_subtitle, 12380),
                    (Self::homescreen__settings_title, 12390),
                    (Self::reset__the_word_is_repeated, 12410),
                    (Self::tutorial__title_lets_begin, 12421),
                    (Self::tutorial__did_you_know, 12434),
                    (Self::tutorial__first_wallet, 12511),
                    (Self::tutorial__restart_tutorial, 12527),
                    (Self::tutorial__title_handy_menu, 12537),
                    (Self::tutorial__title_hold, 12570),
                    (Self::tutorial__title_well_done, 12580),
                    (Self::tutorial__lets_begin, 12632),
                    (Self::tutorial__get_started, 12644),
                    (Self::instructions__swipe_horizontally, 12662),
                    (Self::setting__adjust, 12668),
                    (Self::setting__apply, 12673),
                    (Self::brightness__changed_title, 12699),
                    (Self::brightness__change_title, 12724),
                    (Self::words__title_done, 12728),
                    (Self::reset__slip39_checklist_more_info_threshold, 12806),
                    (Self::reset__slip39_checklist_more_info_threshold_example_template, 12893),
                    (Self::passphrase__continue_with_empty_passphrase, 12924),
                    (Self::instructions__swipe_down, 12934),
                    (Self::address__public_key_confirmed, 12954),
                    (Self::words__continue_anyway, 12969),
                    (Self::buttons__view_all_data, 12982),
                    (Self::instructions__view_all_data, 13008),
                    (Self::misc__enable_labeling, 13024),
                    (Self::words__provider, 13032),
                    (Self::sign_message__confirm_without_review, 13054),
                    (Self::instructions__tap_to_continue, 13069),
                    (Self::ble__unpair_all, 13069),
                    (Self::ble__unpair_current, 13069),
                    (Self::ble__unpair_title, 13069),
                    (Self::words__unlocked, 13077),
                    (Self::words__transaction_fee, 13092),
                    (Self::words__unlimited, 13101),
                    (Self::words__chain, 13106),
                    (Self::words__token, 13111),
                    (Self::instructions__tap, 13114),
                    (Self::reset__share_words_first, 13156),
                    (Self::backup__not_recommend, 13206),
                    (Self::words__pay_attention, 13219),
                    (Self::address__check_with_source, 13249),
                    (Self::words__receive, 13256),
                    (Self::reset__recovery_share_description, 13335),
                    (Self::reset__recovery_share_number, 13381),
                    (Self::words__recovery_share, 13395),
                    (Self::send__send_in_the_app, 13442),
                    (Self::send__sign_cancelled, 13457),
                    (Self::words__send, 13461),
                    (Self::words__wallet, 13467),
                    (Self::words__authenticate, 13479),
                    (Self::auto_lock__description, 13531),
                    (Self::plurals__lock_after_x_days, 13539),
                    (Self::firmware_update__restart, 13572),
                    (Self::passphrase__access_hidden_wallet, 13592),
                    (Self::passphrase__hidden_wallet, 13605),
                    (Self::passphrase__show, 13620),
                    (Self::pin__reenter, 13632),
                    (Self::pin__setup_completed, 13652),
                    (Self::instructions__shares_start_with_x_template, 13673),
                    (Self::reset__check_share_backup_template, 13710),
                    (Self::reset__select_word_from_share_template, 13742),
                    (Self::recovery__share_from_group_entered_template, 13777),
                    (Self::send__cancel_transaction, 13795),
                    (Self::send__multisig_different_paths, 13837),
                    (Self::address__xpub, 13841),
                    (Self::words__cancel_question, 13848),
                    (Self::address__coin_address_template, 13859),
                    (Self::buttons__view, 13863),
                    (Self::words__swap, 13867),
                    (Self::address__title_provider_address, 13883),
                    (Self::address__title_refund_address, 13897),
                    (Self::words__assets, 13903),
                    (Self::buttons__finish, 13909),
                    (Self::instructions__menu_to_continue, 13929),
                    (Self::tutorial__last_one, 13937),
                    (Self::tutorial__menu_appendix, 13967),
                    (Self::tutorial__navigation_ts7, 13967),
                    (Self::tutorial__suite_restart, 14022),
                    (Self::tutorial__welcome_safe7, 14022),
                    (Self::tutorial__what_is_tropic, 14022),
                    (Self::tutorial__tap_to_start, 14043),
                    (Self::tutorial__tropic_info, 14043),
                    (Self::device_name__continue_with_empty_label, 14075),
                    (Self::device_name__enter, 14092),
                    (Self::regulatory__title, 14092),
                    (Self::words__name, 14096),
                    (Self::device_name__changed, 14116),
                    (Self::ble__manage_paired, 14116),
                    (Self::ble__pair_new, 14116),
                    (Self::ble__pair_title, 14116),
                    (Self::ble__version, 14116),
                    (Self::homescreen__firmware_type, 14129),
                    (Self::homescreen__firmware_version, 14145),
                    (Self::led__disable, 14145),
                    (Self::led__enable, 14145),
                    (Self::led__title, 14145),
                    (Self::words__about, 14150),
                    (Self::words__connected, 14159),
                    (Self::words__device, 14165),
                    (Self::words__disconnect, 14175),
                    (Self::words__led, 14178),
                    (Self::words__manage, 14184),
                    (Self::words__off, 14187),
                    (Self::words__on, 14189),
                    (Self::words__review, 14195),
                    (Self::words__security, 14203),
                    (Self::pin__change_question, 14214),
                    (Self::pin__remove, 14224),
                    (Self::pin__title, 14232),
                    (Self::wipe_code__change_question, 14249),
                    (Self::wipe_code__remove, 14265),
                    (Self::wipe_code__title, 14274),
                    (Self::words__disabled, 14282),
                    (Self::words__enabled, 14289),
                    (Self::ble__disable, 14289),
                    (Self::ble__enable, 14289),
                    (Self::words__bluetooth, 14298),
                    (Self::wipe__start_again, 14349),
                    (Self::words__set, 14352),
                    (Self::words__wipe, 14356),
                    (Self::lockscreen__unlock, 14362),
                    (Self::recovery__start_entering, 14376),
                    (Self::words__disconnected, 14388),
                    (Self::ble__forget_all, 14388),
                    (Self::words__connect, 14395),
                    (Self::words__forget, 14401),
                    (Self::words__power, 14406),
                    (Self::ble__limit_reached, 14406),
                    (Self::ble__forget_all_description, 14406),
                    (Self::ble__forget_all_devices, 14406),
                    (Self::ble__forget_all_success, 14406),
                    (Self::ble__forget_this_description, 14406),
                    (Self::ble__forget_this_device, 14406),
                    (Self::ble__forget_this_success, 14406),
                    (Self::thp__autoconnect, 14406),
                    (Self::thp__autoconnect_app, 14406),
                    (Self::thp__connect, 14406),
                    (Self::thp__connect_app, 14406),
                    (Self::thp__pair, 14406),
                    (Self::thp__pair_app, 14406),
                    (Self::thp__autoconnect_title, 14406),
                    (Self::thp__code_entry, 14406),
                    (Self::thp__code_title, 14406),
                    (Self::thp__connect_title, 14406),
                    (Self::thp__nfc_text, 14406),
                    (Self::thp__pair_title, 14406),
                    (Self::thp__qr_title, 14406),
                    (Self::ble__pairing_match, 14406),
                    (Self::ble__pairing_title, 14406),
                    (Self::thp__pair_name, 14406),
                    (Self::thp__pair_new_device, 14406),
                    (Self::tutorial__power, 14406),
                    (Self::auto_lock__on_battery, 14406),
                    (Self::auto_lock__on_usb, 14406),
                    (Self::pin__wipe_code_exists_description, 14469),
                    (Self::pin__wipe_code_exists_title, 14482),
                    (Self::wipe_code__pin_not_set_description, 14524),
                    (Self::wipe_code__cancel_setup, 14546),
                    (Self::homescreen__backup_needed_info, 14646),
                    (Self::ble__host_info, 14646),
                    (Self::ble__mac_address, 14646),
                    (Self::ble__waiting_for_host, 14646),
                    (Self::ble__apps_connected, 14646),
                    (Self::sn__action, 14646),
                    (Self::sn__title, 14646),
                    (Self::ble__must_be_enabled, 14646),
                    (Self::words__comm_trouble, 14717),
                    (Self::secure_sync__delegated_identity_key_no_thp, 14771),
                    (Self::secure_sync__delegated_identity_key_thp, 14823),
                    (Self::secure_sync__header, 14833),
                    (Self::words__note, 14837),
                ],
            };

            #[cfg(feature = "universal_fw")]
            const ALTCOIN_BLOB: StringsBlob = StringsBlob {
                text: "BaseEnterpriseLegacyPointerRewardaddress - no staking rewards.Amount burned (decimals unknown):Amount minted (decimals unknown):Amount sent (decimals unknown):Pool has no metadata (anonymous pool)Asset fingerprint:Auxiliary data hash:BlockCatalystCertificateChange outputCheck all items carefully.Choose level of details:Collateral input ID:Collateral input index:The collateral return output contains tokens.Collateral returnConfirm signing the stake pool registration as an owner.Confirm transactionConfirming a multisig transaction.Confirming a Plutus transaction.Confirming pool registration as owner.Confirming a transaction.CostCredential doesn't match payment credential.Datum hash:Delegating to:for account {0} and index {1}:for account {0}:for key hash:for script:Inline datumInput ID:Input index:The following address is a change address. ItsThe following address is owned by this device. ItsThe vote key registration payment address is owned by this device. Itskey hashMarginmulti-sig pathContains {0} nested scripts.Network:Transaction has no outputs, network cannot be verified.Nonce:otherpathPledgepointerPolicy IDPool metadata hash:Pool metadata url:Pool owner:Pool reward account:Reference input ID:Reference input index:Reference scriptRequired signerrewardAddress is a reward address.Warning: The address is not a payment address, it is not eligible for rewards.Rewards go to:scriptAllAnyScript data hash:Script hash:Invalid beforeInvalid hereafterKeyN of Kscript rewardSendingShow SimpleSign transaction with {0}Stake delegationStake key deregistrationStakepool registrationStake pool registration\nPool ID:Stake key registrationStaking key for accountto pool:token minting pathTotal collateral:TransactionThe transaction contains minting or burning of tokens.The following transaction output contains a script address, but does not contain a datum.Transaction ID:The transaction contains no collateral inputs. Plutus script will not be able to run.The transaction contains no script data hash. Plutus script will not be able to run.The following transaction output contains tokens.TTL:Unknown collateral amount.Path is unusual.Valid since:Verify scriptVote key registration (CIP-36)Vote public key:Voting purpose:WarningWeight:Confirm withdrawal for {0} address:Requires {0} out of {1} signatures.You are about to sign {0}.Action Name:Arbitrary dataBuy RAMBytes:Cancel voteChecksum:Code:Contract:CPU:Creator:DelegateDelete AuthFrom:Link AuthMemoName:NET:New accountOwner:Parent:Payer:Permission:Proxy:Receiver:RefundRequirement:Sell RAMSender:Threshold:To:Transfer:Type:UndelegateUnlink AuthUpdate AuthVote for producersVote for proxyVoter:Amount sent:Size: {0} bytesGas limitGas priceMax fee per gasName and versionNew contract will be deployedNo message fieldMax priority feeShow full arrayShow full domainShow full messageShow full structReally sign EIP-712 typed data?Input dataConfirm domainConfirm messageConfirm structConfirm typed dataSigning address{0} unitsUnknown tokenThe signature is valid.Already registeredThis device is already registered with this application.This device is already registered with {0}.This device is not registered with this application.The credential you are trying to import does\nnot belong to this authenticator.erase all credentials?Export information about the credentials stored on this device?Not registeredThis device is not registered with\n{0}.Please enable PIN protection.FIDO2 authenticateImport credentialList credentialsFIDO2 registerRemove credentialFIDO2 resetU2F authenticateU2F registerFIDO2 verify userUnable to verify user.Do you really want to erase all credentials?Confirm exportConfirm ki syncConfirm refreshConfirm unlock timeHashing inputsPayment IDPostprocessing...Processing...Processing inputsProcessing outputsSigning...Signing inputsUnlock time for this transaction is set to {0}Do you really want to export tx_der\nfor tx_proof?Do you really want to export tx_key?Do you really want to export watch-only credentials?Do you really want to\nstart refresh?Do you really want to\nsync key images?absoluteActivateAddConfirm actionConfirm addressConfirm creation feeConfirm mosaicConfirm multisig feeConfirm namespaceConfirm payloadConfirm propertiesConfirm rental feeConfirm transfer ofConvert account to multisig account?Cosign transaction for cosignatoryCreate mosaicCreate namespaceDeactivateDecreaseDescription:Divisibility and levy cannot be shown for unknown mosaicsEncryptedFinal confirmimmutableIncreaseInitial supply:Initiate transaction forLevy divisibility:Levy fee:Confirm mosaic levy fee ofLevy mosaic:Levy namespace:Levy recipient:Levy type:Modify supply forModify the number of cosignatories by mutableofpercentile{0} raw units remote harvesting?RemoveSet minimum cosignatories to Sign this transaction\nand pay {0}\nfor network fee?Supply change{0} supply by {1} whole units?Transferable?under namespaceUnencryptedUnknown mosaic!Confirm tagDestination tag:\n{0}Account indexAssociated token accountConfirm multisigExpected feeInstruction contains {0} accounts and its data is {1} bytes long.Instruction dataThe following instruction is a multisig instruction.{0} is provided via a lookup table.Lookup table addressMultiple signersTransaction contains unknown instructions.Transaction requires {0} signers which increases the fee.Account MergeAccount ThresholdsAdd SignerAdd trustAll XLM will be sent toAllow trustBalance IDBump SequenceBuying:Claim Claimable BalanceClear dataClear flagsConfirm IssuerConfirm memoConfirm operationConfirm timeboundsCreate AccountDebited amountDeleteDelete Passive OfferDelete trustDestinationMemo is not set.\nTypically needed when sending to exchanges.Final confirmHashHigh:Home DomainInflation{0} issuerKey:LimitLow:Master Weight:Medium:New OfferNew Passive OfferNo memo set![no restriction]Path PayPath Pay at leastPayPay at mostPre-auth transactionPrice per {0}:Remove SignerRevoke trustSelling:Set dataSet flagsSet sequence to {0}?Sign this transaction made up of {0}and pay {0}\nfor fee?Source accountTrusted AccountUpdateValid from (UTC)Valid to (UTC)Value (SHA-256):Do you want to clear value key {0}?Baker addressBalance:Ballot:Confirm delegationConfirm originationDelegatorProposalRegister delegateRemove delegationSubmit ballotSubmit proposalSubmit proposalsIncrease and retrieve the U2F counter?Set the U2F counter to {0}?Get U2F counterSet U2F counterClaimClaim addressClaim ETH from Everstake?StakeStake addressStake ETH on Everstake?UnstakeUnstake ETH from Everstake?Always AbstainAlways No ConfidenceDelegating to key hash:Delegating to script:Deposit:Vote delegationMore credentialsSelect the credential that you would like to use for authentication.for authenticationSelect credentialCredential detailsUnknown contract addressToken contractInteraction contractBase feeClaimClaim SOL from stake account?Claiming SOL to address outside your current wallet.Priority feeStakeStake accountStake SOL?The current wallet isn't the SOL staking withdraw authority.Withdraw authority addressUnstakeUnstake SOL from stake account?Vote accountStake SOL on {0}?Event kind: {0}Max fees and rentMax rent feeApproveAmount allowanceChain IDReview details to approve token spending.Token approvalApprove toApproving unlimited amount of {0}Review details to revoke token approval.Token revocationRevokeRevoke fromUnknown tokenUnknown token addressAll input data ({0} bytes)Provider contract addressConfirm message hashSign withTimeboundsToken infoTransaction sourceTransaction source does not belong to this Trezor.Confirm messageEmpty messageMessage hash:Message hexMessage textSign message hash with {0}Sign message with {0}Destination tag is not set. Typically needed when sending to exchanges.",
                offsets: &[
                    (Self::cardano__addr_base, 4),
                    (Self::cardano__addr_enterprise, 14),
                    (Self::cardano__addr_legacy, 20),
                    (Self::cardano__addr_pointer, 27),
                    (Self::cardano__addr_reward, 33),
                    (Self::cardano__address_no_staking, 62),
                    (Self::cardano__amount_burned_decimals_unknown, 95),
                    (Self::cardano__amount_minted_decimals_unknown, 128),
                    (Self::cardano__amount_sent_decimals_unknown, 159),
                    (Self::cardano__anonymous_pool, 196),
                    (Self::cardano__asset_fingerprint, 214),
                    (Self::cardano__auxiliary_data_hash, 234),
                    (Self::cardano__block, 239),
                    (Self::cardano__catalyst, 247),
                    (Self::cardano__certificate, 258),
                    (Self::cardano__change_output, 271),
                    (Self::cardano__check_all_items, 297),
                    (Self::cardano__choose_level_of_details, 321),
                    (Self::cardano__collateral_input_id, 341),
                    (Self::cardano__collateral_input_index, 364),
                    (Self::cardano__collateral_output_contains_tokens, 409),
                    (Self::cardano__collateral_return, 426),
                    (Self::cardano__confirm_signing_stake_pool, 482),
                    (Self::cardano__confirm_transaction, 501),
                    (Self::cardano__confirming_a_multisig_transaction, 535),
                    (Self::cardano__confirming_a_plutus_transaction, 567),
                    (Self::cardano__confirming_pool_registration, 605),
                    (Self::cardano__confirming_transaction, 630),
                    (Self::cardano__cost, 634),
                    (Self::cardano__credential_mismatch, 678),
                    (Self::cardano__datum_hash, 689),
                    (Self::cardano__delegating_to, 703),
                    (Self::cardano__for_account_and_index_template, 733),
                    (Self::cardano__for_account_template, 749),
                    (Self::cardano__for_key_hash, 762),
                    (Self::cardano__for_script, 773),
                    (Self::cardano__inline_datum, 785),
                    (Self::cardano__input_id, 794),
                    (Self::cardano__input_index, 806),
                    (Self::cardano__intro_text_change, 852),
                    (Self::cardano__intro_text_owned_by_device, 902),
                    (Self::cardano__intro_text_registration_payment, 972),
                    (Self::cardano__key_hash, 980),
                    (Self::cardano__margin, 986),
                    (Self::cardano__multisig_path, 1000),
                    (Self::cardano__nested_scripts_template, 1028),
                    (Self::cardano__network, 1036),
                    (Self::cardano__no_output_tx, 1091),
                    (Self::cardano__nonce, 1097),
                    (Self::cardano__other, 1102),
                    (Self::cardano__path, 1106),
                    (Self::cardano__pledge, 1112),
                    (Self::cardano__pointer, 1119),
                    (Self::cardano__policy_id, 1128),
                    (Self::cardano__pool_metadata_hash, 1147),
                    (Self::cardano__pool_metadata_url, 1165),
                    (Self::cardano__pool_owner, 1176),
                    (Self::cardano__pool_reward_account, 1196),
                    (Self::cardano__reference_input_id, 1215),
                    (Self::cardano__reference_input_index, 1237),
                    (Self::cardano__reference_script, 1253),
                    (Self::cardano__required_signer, 1268),
                    (Self::cardano__reward, 1274),
                    (Self::cardano__reward_address, 1302),
                    (Self::cardano__reward_eligibility_warning, 1380),
                    (Self::cardano__rewards_go_to, 1394),
                    (Self::cardano__script, 1400),
                    (Self::cardano__script_all, 1403),
                    (Self::cardano__script_any, 1406),
                    (Self::cardano__script_data_hash, 1423),
                    (Self::cardano__script_hash, 1435),
                    (Self::cardano__script_invalid_before, 1449),
                    (Self::cardano__script_invalid_hereafter, 1466),
                    (Self::cardano__script_key, 1469),
                    (Self::cardano__script_n_of_k, 1475),
                    (Self::cardano__script_reward, 1488),
                    (Self::cardano__sending, 1495),
                    (Self::cardano__show_simple, 1506),
                    (Self::cardano__sign_tx_path_template, 1531),
                    (Self::cardano__stake_delegation, 1547),
                    (Self::cardano__stake_deregistration, 1571),
                    (Self::cardano__stake_pool_registration, 1593),
                    (Self::cardano__stake_pool_registration_pool_id, 1625),
                    (Self::cardano__stake_registration, 1647),
                    (Self::cardano__staking_key_for_account, 1670),
                    (Self::cardano__to_pool, 1678),
                    (Self::cardano__token_minting_path, 1696),
                    (Self::cardano__total_collateral, 1713),
                    (Self::cardano__transaction, 1724),
                    (Self::cardano__transaction_contains_minting_or_burning, 1778),
                    (Self::cardano__transaction_contains_script_address_no_datum, 1867),
                    (Self::cardano__transaction_id, 1882),
                    (Self::cardano__transaction_no_collateral_input, 1967),
                    (Self::cardano__transaction_no_script_data_hash, 2051),
                    (Self::cardano__transaction_output_contains_tokens, 2100),
                    (Self::cardano__ttl, 2104),
                    (Self::cardano__unknown_collateral_amount, 2130),
                    (Self::cardano__unusual_path, 2146),
                    (Self::cardano__valid_since, 2158),
                    (Self::cardano__verify_script, 2171),
                    (Self::cardano__vote_key_registration, 2201),
                    (Self::cardano__vote_public_key, 2217),
                    (Self::cardano__voting_purpose, 2232),
                    (Self::cardano__warning, 2239),
                    (Self::cardano__weight, 2246),
                    (Self::cardano__withdrawal_for_address_template, 2281),
                    (Self::cardano__x_of_y_signatures_template, 2316),
                    (Self::eos__about_to_sign_template, 2342),
                    (Self::eos__action_name, 2354),
                    (Self::eos__arbitrary_data, 2368),
                    (Self::eos__buy_ram, 2375),
                    (Self::eos__bytes, 2381),
                    (Self::eos__cancel_vote, 2392),
                    (Self::eos__checksum, 2401),
                    (Self::eos__code, 2406),
                    (Self::eos__contract, 2415),
                    (Self::eos__cpu, 2419),
                    (Self::eos__creator, 2427),
                    (Self::eos__delegate, 2435),
                    (Self::eos__delete_auth, 2446),
                    (Self::eos__from, 2451),
                    (Self::eos__link_auth, 2460),
                    (Self::eos__memo, 2464),
                    (Self::eos__name, 2469),
                    (Self::eos__net, 2473),
                    (Self::eos__new_account, 2484),
                    (Self::eos__owner, 2490),
                    (Self::eos__parent, 2497),
                    (Self::eos__payer, 2503),
                    (Self::eos__permission, 2514),
                    (Self::eos__proxy, 2520),
                    (Self::eos__receiver, 2529),
                    (Self::eos__refund, 2535),
                    (Self::eos__requirement, 2547),
                    (Self::eos__sell_ram, 2555),
                    (Self::eos__sender, 2562),
                    (Self::eos__threshold, 2572),
                    (Self::eos__to, 2575),
                    (Self::eos__transfer, 2584),
                    (Self::eos__type, 2589),
                    (Self::eos__undelegate, 2599),
                    (Self::eos__unlink_auth, 2610),
                    (Self::eos__update_auth, 2621),
                    (Self::eos__vote_for_producers, 2639),
                    (Self::eos__vote_for_proxy, 2653),
                    (Self::eos__voter, 2659),
                    (Self::ethereum__amount_sent, 2671),
                    (Self::ethereum__data_size_template, 2686),
                    (Self::ethereum__gas_limit, 2695),
                    (Self::ethereum__gas_price, 2704),
                    (Self::ethereum__max_gas_price, 2719),
                    (Self::ethereum__name_and_version, 2735),
                    (Self::ethereum__new_contract, 2764),
                    (Self::ethereum__no_message_field, 2780),
                    (Self::ethereum__priority_fee, 2796),
                    (Self::ethereum__show_full_array, 2811),
                    (Self::ethereum__show_full_domain, 2827),
                    (Self::ethereum__show_full_message, 2844),
                    (Self::ethereum__show_full_struct, 2860),
                    (Self::ethereum__sign_eip712, 2891),
                    (Self::ethereum__title_input_data, 2901),
                    (Self::ethereum__title_confirm_domain, 2915),
                    (Self::ethereum__title_confirm_message, 2930),
                    (Self::ethereum__title_confirm_struct, 2944),
                    (Self::ethereum__title_confirm_typed_data, 2962),
                    (Self::ethereum__title_signing_address, 2977),
                    (Self::ethereum__units_template, 2986),
                    (Self::ethereum__unknown_token, 2999),
                    (Self::ethereum__valid_signature, 3022),
                    (Self::fido__already_registered, 3040),
                    (Self::fido__device_already_registered, 3096),
                    (Self::fido__device_already_registered_with_template, 3139),
                    (Self::fido__device_not_registered, 3191),
                    (Self::fido__does_not_belong, 3269),
                    (Self::fido__erase_credentials, 3291),
                    (Self::fido__export_credentials, 3354),
                    (Self::fido__not_registered, 3368),
                    (Self::fido__not_registered_with_template, 3407),
                    (Self::fido__please_enable_pin_protection, 3436),
                    (Self::fido__title_authenticate, 3454),
                    (Self::fido__title_import_credential, 3471),
                    (Self::fido__title_list_credentials, 3487),
                    (Self::fido__title_register, 3501),
                    (Self::fido__title_remove_credential, 3518),
                    (Self::fido__title_reset, 3529),
                    (Self::fido__title_u2f_auth, 3545),
                    (Self::fido__title_u2f_register, 3557),
                    (Self::fido__title_verify_user, 3574),
                    (Self::fido__unable_to_verify_user, 3596),
                    (Self::fido__wanna_erase_credentials, 3640),
                    (Self::monero__confirm_export, 3654),
                    (Self::monero__confirm_ki_sync, 3669),
                    (Self::monero__confirm_refresh, 3684),
                    (Self::monero__confirm_unlock_time, 3703),
                    (Self::monero__hashing_inputs, 3717),
                    (Self::monero__payment_id, 3727),
                    (Self::monero__postprocessing, 3744),
                    (Self::monero__processing, 3757),
                    (Self::monero__processing_inputs, 3774),
                    (Self::monero__processing_outputs, 3792),
                    (Self::monero__signing, 3802),
                    (Self::monero__signing_inputs, 3816),
                    (Self::monero__unlock_time_set_template, 3862),
                    (Self::monero__wanna_export_tx_der, 3911),
                    (Self::monero__wanna_export_tx_key, 3947),
                    (Self::monero__wanna_export_watchkey, 3999),
                    (Self::monero__wanna_start_refresh, 4035),
                    (Self::monero__wanna_sync_key_images, 4073),
                    (Self::nem__absolute, 4081),
                    (Self::nem__activate, 4089),
                    (Self::nem__add, 4092),
                    (Self::nem__confirm_action, 4106),
                    (Self::nem__confirm_address, 4121),
                    (Self::nem__confirm_creation_fee, 4141),
                    (Self::nem__confirm_mosaic, 4155),
                    (Self::nem__confirm_multisig_fee, 4175),
                    (Self::nem__confirm_namespace, 4192),
                    (Self::nem__confirm_payload, 4207),
                    (Self::nem__confirm_properties, 4225),
                    (Self::nem__confirm_rental_fee, 4243),
                    (Self::nem__confirm_transfer_of, 4262),
                    (Self::nem__convert_account_to_multisig, 4298),
                    (Self::nem__cosign_transaction_for, 4320),
                    (Self::nem__cosignatory, 4332),
                    (Self::nem__create_mosaic, 4345),
                    (Self::nem__create_namespace, 4361),
                    (Self::nem__deactivate, 4371),
                    (Self::nem__decrease, 4379),
                    (Self::nem__description, 4391),
                    (Self::nem__divisibility_and_levy_cannot_be_shown, 4448),
                    (Self::nem__encrypted, 4457),
                    (Self::nem__final_confirm, 4470),
                    (Self::nem__immutable, 4479),
                    (Self::nem__increase, 4487),
                    (Self::nem__initial_supply, 4502),
                    (Self::nem__initiate_transaction_for, 4526),
                    (Self::nem__levy_divisibility, 4544),
                    (Self::nem__levy_fee, 4553),
                    (Self::nem__levy_fee_of, 4579),
                    (Self::nem__levy_mosaic, 4591),
                    (Self::nem__levy_namespace, 4606),
                    (Self::nem__levy_recipient, 4621),
                    (Self::nem__levy_type, 4631),
                    (Self::nem__modify_supply_for, 4648),
                    (Self::nem__modify_the_number_of_cosignatories_by, 4686),
                    (Self::nem__mutable, 4693),
                    (Self::nem__of, 4695),
                    (Self::nem__percentile, 4705),
                    (Self::nem__raw_units_template, 4718),
                    (Self::nem__remote_harvesting, 4737),
                    (Self::nem__remove, 4743),
                    (Self::nem__set_minimum_cosignatories_to, 4772),
                    (Self::nem__sign_tx_fee_template, 4822),
                    (Self::nem__supply_change, 4835),
                    (Self::nem__supply_units_template, 4865),
                    (Self::nem__transferable, 4878),
                    (Self::nem__under_namespace, 4893),
                    (Self::nem__unencrypted, 4904),
                    (Self::nem__unknown_mosaic, 4919),
                    (Self::ripple__confirm_tag, 4930),
                    (Self::ripple__destination_tag_template, 4950),
                    (Self::solana__account_index, 4963),
                    (Self::solana__associated_token_account, 4987),
                    (Self::solana__confirm_multisig, 5003),
                    (Self::solana__expected_fee, 5015),
                    (Self::solana__instruction_accounts_template, 5080),
                    (Self::solana__instruction_data, 5096),
                    (Self::solana__instruction_is_multisig, 5148),
                    (Self::solana__is_provided_via_lookup_table_template, 5183),
                    (Self::solana__lookup_table_address, 5203),
                    (Self::solana__multiple_signers, 5219),
                    (Self::solana__transaction_contains_unknown_instructions, 5261),
                    (Self::solana__transaction_requires_x_signers_template, 5318),
                    (Self::stellar__account_merge, 5331),
                    (Self::stellar__account_thresholds, 5349),
                    (Self::stellar__add_signer, 5359),
                    (Self::stellar__add_trust, 5368),
                    (Self::stellar__all_will_be_sent_to, 5391),
                    (Self::stellar__allow_trust, 5402),
                    (Self::stellar__balance_id, 5412),
                    (Self::stellar__bump_sequence, 5425),
                    (Self::stellar__buying, 5432),
                    (Self::stellar__claim_claimable_balance, 5455),
                    (Self::stellar__clear_data, 5465),
                    (Self::stellar__clear_flags, 5476),
                    (Self::stellar__confirm_issuer, 5490),
                    (Self::stellar__confirm_memo, 5502),
                    (Self::stellar__confirm_operation, 5519),
                    (Self::stellar__confirm_timebounds, 5537),
                    (Self::stellar__create_account, 5551),
                    (Self::stellar__debited_amount, 5565),
                    (Self::stellar__delete, 5571),
                    (Self::stellar__delete_passive_offer, 5591),
                    (Self::stellar__delete_trust, 5603),
                    (Self::stellar__destination, 5614),
                    (Self::stellar__exchanges_require_memo, 5674),
                    (Self::stellar__final_confirm, 5687),
                    (Self::stellar__hash, 5691),
                    (Self::stellar__high, 5696),
                    (Self::stellar__home_domain, 5707),
                    (Self::stellar__inflation, 5716),
                    (Self::stellar__issuer_template, 5726),
                    (Self::stellar__key, 5730),
                    (Self::stellar__limit, 5735),
                    (Self::stellar__low, 5739),
                    (Self::stellar__master_weight, 5753),
                    (Self::stellar__medium, 5760),
                    (Self::stellar__new_offer, 5769),
                    (Self::stellar__new_passive_offer, 5786),
                    (Self::stellar__no_memo_set, 5798),
                    (Self::stellar__no_restriction, 5814),
                    (Self::stellar__path_pay, 5822),
                    (Self::stellar__path_pay_at_least, 5839),
                    (Self::stellar__pay, 5842),
                    (Self::stellar__pay_at_most, 5853),
                    (Self::stellar__preauth_transaction, 5873),
                    (Self::stellar__price_per_template, 5887),
                    (Self::stellar__remove_signer, 5900),
                    (Self::stellar__revoke_trust, 5912),
                    (Self::stellar__selling, 5920),
                    (Self::stellar__set_data, 5928),
                    (Self::stellar__set_flags, 5937),
                    (Self::stellar__set_sequence_to_template, 5957),
                    (Self::stellar__sign_tx_count_template, 5993),
                    (Self::stellar__sign_tx_fee_template, 6013),
                    (Self::stellar__source_account, 6027),
                    (Self::stellar__trusted_account, 6042),
                    (Self::stellar__update, 6048),
                    (Self::stellar__valid_from, 6064),
                    (Self::stellar__valid_to, 6078),
                    (Self::stellar__value_sha256, 6094),
                    (Self::stellar__wanna_clean_value_key_template, 6129),
                    (Self::tezos__baker_address, 6142),
                    (Self::tezos__balance, 6150),
                    (Self::tezos__ballot, 6157),
                    (Self::tezos__confirm_delegation, 6175),
                    (Self::tezos__confirm_origination, 6194),
                    (Self::tezos__delegator, 6203),
                    (Self::tezos__proposal, 6211),
                    (Self::tezos__register_delegate, 6228),
                    (Self::tezos__remove_delegation, 6245),
                    (Self::tezos__submit_ballot, 6258),
                    (Self::tezos__submit_proposal, 6273),
                    (Self::tezos__submit_proposals, 6289),
                    (Self::u2f__get, 6327),
                    (Self::u2f__set_template, 6354),
                    (Self::u2f__title_get, 6369),
                    (Self::u2f__title_set, 6384),
                    (Self::ethereum__staking_claim, 6389),
                    (Self::ethereum__staking_claim_address, 6402),
                    (Self::ethereum__staking_claim_intro, 6427),
                    (Self::ethereum__staking_stake, 6432),
                    (Self::ethereum__staking_stake_address, 6445),
                    (Self::ethereum__staking_stake_intro, 6468),
                    (Self::ethereum__staking_unstake, 6475),
                    (Self::ethereum__staking_unstake_intro, 6502),
                    (Self::cardano__always_abstain, 6516),
                    (Self::cardano__always_no_confidence, 6536),
                    (Self::cardano__delegating_to_key_hash, 6559),
                    (Self::cardano__delegating_to_script, 6580),
                    (Self::cardano__deposit, 6588),
                    (Self::cardano__vote_delegation, 6603),
                    (Self::fido__more_credentials, 6619),
                    (Self::fido__select_intro, 6687),
                    (Self::fido__title_for_authentication, 6705),
                    (Self::fido__title_select_credential, 6722),
                    (Self::fido__title_credential_details, 6740),
                    (Self::ethereum__unknown_contract_address, 6764),
                    (Self::ethereum__token_contract, 6778),
                    (Self::ethereum__interaction_contract, 6798),
                    (Self::solana__base_fee, 6806),
                    (Self::solana__claim, 6811),
                    (Self::solana__claim_question, 6840),
                    (Self::solana__claim_recipient_warning, 6892),
                    (Self::solana__priority_fee, 6904),
                    (Self::solana__stake, 6909),
                    (Self::solana__stake_account, 6922),
                    (Self::solana__stake_question, 6932),
                    (Self::solana__stake_withdrawal_warning, 6992),
                    (Self::solana__stake_withdrawal_warning_title, 7018),
                    (Self::solana__unstake, 7025),
                    (Self::solana__unstake_question, 7056),
                    (Self::solana__vote_account, 7068),
                    (Self::solana__stake_on_question, 7085),
                    (Self::nostr__event_kind_template, 7100),
                    (Self::solana__max_fees_rent, 7117),
                    (Self::solana__max_rent_fee, 7129),
                    (Self::ethereum__approve, 7136),
                    (Self::ethereum__approve_amount_allowance, 7152),
                    (Self::ethereum__approve_chain_id, 7160),
                    (Self::ethereum__approve_intro, 7201),
                    (Self::ethereum__approve_intro_title, 7215),
                    (Self::ethereum__approve_to, 7225),
                    (Self::ethereum__approve_unlimited_template, 7258),
                    (Self::ethereum__approve_intro_revoke, 7298),
                    (Self::ethereum__approve_intro_title_revoke, 7314),
                    (Self::ethereum__approve_revoke, 7320),
                    (Self::ethereum__approve_revoke_from, 7331),
                    (Self::solana__unknown_token, 7344),
                    (Self::solana__unknown_token_address, 7365),
                    (Self::ethereum__title_all_input_data_template, 7391),
                    (Self::ethereum__contract_address, 7416),
                    (Self::ethereum__title_confirm_message_hash, 7436),
                    (Self::stellar__sign_with, 7445),
                    (Self::stellar__timebounds, 7455),
                    (Self::stellar__token_info, 7465),
                    (Self::stellar__transaction_source, 7483),
                    (Self::stellar__transaction_source_diff_warning, 7533),
                    (Self::cardano__confirm_message, 7548),
                    (Self::cardano__empty_message, 7561),
                    (Self::cardano__message_hash, 7574),
                    (Self::cardano__message_hex, 7585),
                    (Self::cardano__message_text, 7597),
                    (Self::cardano__sign_message_hash_path_template, 7623),
                    (Self::cardano__sign_message_path_template, 7644),
                    (Self::ripple__destination_tag_missing, 7715),
                ],
            };

            #[cfg(feature = "debug")]
            const DEBUG_BLOB: StringsBlob = StringsBlob {
                text: "Loading seedLoading private seed is not recommended.",
                offsets: &[
                    (Self::debug__loading_seed, 12),
                    (Self::debug__loading_seed_not_recommended, 52),
                ],
            };

            pub const BLOBS: &'static [StringsBlob] = &[
                Self::BTC_ONLY_BLOB,
                #[cfg(feature = "universal_fw")]
                Self::ALTCOIN_BLOB,
                #[cfg(feature = "debug")]
                Self::DEBUG_BLOB,
            ];
        }
    } else if #[cfg(feature = "layout_caesar")] {
        impl TranslatedString {
            const BTC_ONLY_BLOB: StringsBlob = StringsBlob {
                text: "Please contact Trezor support atKey mismatch?Address mismatch?trezor.io/supportWrong derivation path for selected account.XPUB mismatch?Public keyCosignerReceive addressYoursDerivation path:Receive addressReceiving toAllow connected app to check the authenticity of your {0}?Authenticate deviceAuto-lock Trezor after {0} of inactivity?Auto-lock delayYou can back up your Trezor once, at any time.You should back up your new wallet right now.It should be backed up now!Wallet created.\nWallet created successfully.You can use your backup to recover your wallet at any time.Back up walletSkip backupAre you sure you want to skip the backup?Commitment dataConfirm locktimeDo you want to create a proof of ownership?The mining fee of\n{0}\nis unexpectedly high.Locktime is set but will have no effect.Locktime set toLocktime set to blockheightA lot of change-outputs.Multiple accountsNew fee rate:Simple send ofTicket amountConfirm detailsFinalize transactionHigh mining feeMeld transactionModify amountPayjoinProof of ownershipPurchase ticketUpdate transactionUnknown pathUnknown transactionUnusually high fee.The transaction contains unverified external inputs.The signature is valid.Voting rights toAbortAccessAgainAllowBackBack upCancelChangeCheckCheck againCloseConfirmContinueDetailsEnableEnterEnter shareExportFormatGo backHold to confirmInfoInstallMore infoOk, I understandPurchaseQuitRestartRetrySelectSetShow allShow detailsShow wordsSkipTry againTurn offTurn onAccess your coinjoin account?Do not disconnect your Trezor!Max mining feeMax roundsAuthorize coinjoinCoinjoin in progressWaiting for othersFee rate:Sending from account:Fee infoSending fromChange device name to {0}?Device nameDo you really want to send entropy?Confirm entropySign transactionEnable experimental features?Only for development and beta testing!Experimental modeUpdate firmwareFW fingerprintClick to ConnectClick to UnlockBackup failedBackup neededCoinjoin authorizedExperimental modeNo USB connectionPIN not setSeedlessChange wallpaperBACKCANCELDELETEENTERRETURNSHOWSPACEJoint transactionTo the total amount:You are contributing:Change language to {0}?Language changed successfullyChanging languageLanguage settingsTap to connectTap to unlockLockedNot connectedDecrypt valueEncrypt valueSuite labelingDecrease amount by:Increase amount by:New amount:Modify amountDecrease fee by:Fee rate:Increase fee by:New transaction fee:Fee did not change.\nModify feeTransaction fee:Access passphrase wallet?Always enter your passphrase on Trezor?Passphrase provided by connected app will be used but will not be displayed due to the device settings.Passphrase walletHide passphrase coming from app?The next screen shows your passphrase.Please enter your passphrase.Do you want to revoke the passphrase on device setting?Confirm passphraseEnter passphraseHide passphrasePassphrase settingsPassphrase sourceTurn off passphrase protection?Turn on passphrase protection?Change PINPIN changed.Position of the cursor will change between entries for enhanced security.The new PIN must be different from your wipe code.PIN protection\nturned off.PIN protection\nturned on.Enter PINEnter new PINThe PIN you have entered is not valid.PIN will be required to access this device.Invalid PINLast attemptEntered PINs do not match!PIN mismatchPlease check again.Re-enter new PINPlease re-enter PIN to confirm.PIN should be 4-50 digits long.Check PINPIN settingsWrong PINtries leftAre you sure you want to turn off PIN protection?Turn on PIN protection?Wrong PINkey|keyshour|hoursmillisecond|millisecondsminute|minutessecond|secondsaction|actionsoperation|operationsgroup|groupsshare|sharesChecking authenticity...DoneLoading transaction...Locking the device...1 second leftPlease waitProcessingRefreshing...Signing transaction...Syncing...{0} seconds leftTrezor will restart in bootloader mode.Go to bootloaderFirmware version {0}\nby {1}Cancel backup checkCheck your backup?Position of the cursor will change between entries for enhanced security.The entered wallet backup is valid and matches the one in this device.The entered wallet backup is valid but does not match the one in the device.The entered recovery shares are valid and match what is currently in the device.The entered recovery shares are valid but do not match what is currently in the device.Enter any shareEnter your backup.Enter a different share.Enter share from a different group.Group {0}Group threshold reached.Invalid wallet backup entered.Invalid recovery share entered.More shares neededSelect the number of words in your backup.You'll only have to select the first 2-4 letters of each word.All progress will be lost.Share already enteredYou have entered a share from a different backup.Share {0}Recover walletCancel backup checkCancel recoveryBackup checkRecover walletRemaining sharesType word {0} of {1}Wallet recovery completedAre you sure you want to cancel the backup check?Are you sure you want to cancel the recovery process?({0} words)Word {0} of {1}{count} more {plural} starting{count} more {plural} needed{0} of {1} shares enteredYou have enteredThe group threshold specifies the number of groups required to recover your wallet.Create walletRecover walletBy continuing you agree to Trezor Company's terms and conditions.Check backupCheck g{0} - share {1}Check wallet backupCheck share #{0}Continue with the next share.Continue with share #{0}.You have finished verifying your recovery shares for group {0}.You have finished verifying your wallet backup.You have finished verifying your recovery shares.A group is made up of recovery shares.Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds.Group {0} - Share {1} checked successfully.Group {0} - share {1}More info atNever put your backup anywhere digital.{0} people or locations will each hold one share.Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}.The required number of shares to form Group {0}.= total number of unique word lists used for wallet backup.Only one share will be created.Wallet backupRecovery share #{0}The required number of groups for recovery.Select the correct word for each position.Select {0} wordSelect word {0} of {1}:Share #{0} checked successfully.Standard backupNumber of groupsNumber of sharesSet number of groupsSet number of sharesSet sizes and thresholdsSet size and threshold for each groupSet thresholdBackup checklistWrite down and check all sharesWrite down & check all wallet backup shares= minimum number of unique word lists used for recovery.Backup is doneCreate walletGroup thresholdNumber of groupsNumber of sharesSet group thresholdSet number of groupsSet number of sharesSet thresholdtrezor.io/tosSet the total number of shares in Group {0}.Use your backup when you need to recover your wallet.Write the following {0} words in order on your wallet backup card.Wrong word selected!Your backup is done.Change display orientation to {0}?eastnorthsouthDisplay orientationwestTrezor will allow you to approve some actions which might be unsafe.Trezor will temporarily allow you to approve some actions which might be unsafe.Do you really want to enforce strict safety checks (recommended)?Safety checksSafety overrideSending amountSending from multiple accounts.Including fee:Maximum feeReceiving to a multisig address.Confirm sendingJoint transactionReceiving toSendingSending amountSending toTo the total amount:Transaction IDYou are contributing: words in order.I wrote down all {0} BytesSigning addressConfirm messageMessage sizeVerify addressAssetPress both left and right at the same\ntime to confirm.Press and hold the right button to\napprove important operations.You're ready to\nuse Trezor.Press right to scroll down to read all content when text doesn't fit on one screen.\n\rPress left to scroll up.Are you sure you\nwant to skip the tutorial?HelloScreen scrollSkip tutorialTutorial completeUse Trezor by\nclicking the left and right buttons.\n\rContinue right.Welcome to Trezor. Press right to continue.All data will be erased.Wipe deviceDo you really want to wipe the device?\nChange wipe codeWipe code changed.The wipe code must be different from your PIN.Wipe code disabled.Wipe code enabled.New wipe codeWipe code can be used to erase all data from this device.Invalid wipe codeThe wipe codes you entered do not match.Re-enter wipe codePlease re-enter wipe code to confirm.Check wipe codeInvalid wipe codeWipe code settingsTurn off wipe code protection?Turn on wipe code protection?Wipe code mismatchNumber of wordsAccountAccount:AddressAmountAre you sure?Array ofBlockhashBuyingConfirmConfirm feeContainsContinue anyway?Continue withErrorFeefromKeep it safe!Continue only if you know what you are doing!My TrezorNooutputsPlease check againPlease try againDo you really want toRecipientSignSignerCheckGroupInformationRememberShareSharesSuccessSummaryThresholdUnknownWarningWritableYesJust a moment...PREVIOUSStarting upVerifying PINWrong PINDo you want to create a {0} of {1} multi-share backup?Multi-share backupTap to confirmHold to confirmImportantI wrote down all {0} words in order.Create a backup to avoid losing access to your fundsLet's do a quick check of your backup.InstructionsNot recommended!Account infoIf receive address doesn't match, contact Trezor Support at trezor.io/support.Cancel receiveQR codeDerivation pathContinue in the appCancel and exitReceive address confirmedContinue without PINWithout a PIN, anyone can access this device.Cancel PIN setupCancel signSend fromHold to signFee rateincl. Transaction feeTotal amountAuto-lock turned onYour wallet backup contains multiple lists of words in a specific order (shares).Your wallet backup contains {0} words in a specific order.Wallet backup completedCreate wallet backupEnter next shareHold to continueHold to exit tutorialLearn moreContinue with Share #{0}Start with share #1PassphraseWallet backup not on this deviceInvalid wallet backup enteredAll shares are valid and belong to the backup in this deviceEntered share is valid and belongs to the backup in the deviceVerify remaining recovery shares?Enter each word of your wallet backup in order.It's safe to disconnect your Trezor while recovering your wallet and continue later.Share doesn't matchCancel create walletIncorrect word selectedMore atHow many wallet backup shares do you want to create?Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.Select the minimum shares required to recover your wallet.Share #{0} completedNumber of shares: {0}Recovery threshold: {0}Transaction signedContinue tutorialExit tutorialFind context-specific actions and options in the menu.One more stepYou're all set to start using your device!Easy navigationGood to knowOperation cancelledSettingsTry again.Number of groups: {0}Display brightnessMulti-share backupCreate additional backup?Create backupChange wallpaper to default image?Words may repeat.Repeat for all shares.SettingsHomescreenThe word is repeatedLet's beginDid you know?The Trezor Model One, created in 2013,\nwas the world's first hardware wallet.Restart tutorialHandy menuHold to confirm important actionsWell done!Learn how to use and navigate this device with ease.Get started!Swipe horizontallyAdjustApplyDisplay brightness changedChange display brightnessDoneThe threshold sets the minimum number of shares needed to recover your wallet.If you set {0} out of {1} shares, you'll need {2} backup shares to recover your wallet.Continue with empty passphrase?Swipe downPublic key confirmedContinue anywayView all dataView all data in the menu.Enable labeling?ProviderConfirm without reviewTap to continueUnlockedTransaction feeUnlimitedChainTokenTapWrite down the first word from the backup.We don't recommend to skip wallet backup creation.Pay attentionCheck the address with source.ReceiveA recovery share is a list of words you wrote down when setting up your Trezor.Your wallet backup consists of 1 to 16 shares.Recovery shareAfter signing, send the transaction in the app.Sign cancelled.SendWalletAuthenticateSet the time before your Trezor locks automatically.day|daysTrezor will restart after update.Access hidden walletHidden walletShow passphraseRe-enter PINPIN setup completed.Start with Share #{0}Let's do a quick check of Share #{0}.Select word #{0} from\nShare #{1}Share #{0} from Group #{1} entered.Cancel transactionUsing different paths for different XPUBs.XPUBCancel?{0} addressViewSwapProvider addressRefund addressAssetsFinishUse menu to continueLast oneView more info, quit flow, ...Replay this tutorial anytime from the Trezor Suite app.Tap to start tutorialContinue with empty device name?Enter device nameNameDevice name changed.Firmware typeFirmware versionAboutConnectedDeviceDisconnectLEDManageOFFONReviewSecurityChange PIN?Remove PINPIN codeChange wipe code?Remove wipe codeWipe codeDisabledEnabledBluetoothWipe your Trezor and start the setup process again.SetWipeUnlockStart enteringDisconnectedConnectForgetPowerWipe code must be turned off before turning off PIN protection.Wipe code setPIN must be set before enabling wipe code.Cancel wipe code setupOpen Trezor Suite and create a wallet backup. This is the only way to recover access to your assets.Your Trezor is having trouble communicating with your connected device.Allow Trezor Suite to use Suite Sync with this Trezor?Allow {0} on {1} to use Suite Sync with this Trezor?Suite SyncNote",
                offsets: &[
                    (Self::addr_mismatch__contact_support_at, 32),
                    (Self::addr_mismatch__key_mismatch, 45),
                    (Self::addr_mismatch__mismatch, 62),
                    (Self::addr_mismatch__support_url, 79),
                    (Self::addr_mismatch__wrong_derivation_path, 122),
                    (Self::addr_mismatch__xpub_mismatch, 136),
                    (Self::address__public_key, 146),
                    (Self::address__title_cosigner, 154),
                    (Self::address__title_receive_address, 169),
                    (Self::address__title_yours, 174),
                    (Self::address_details__derivation_path_colon, 190),
                    (Self::address_details__title_receive_address, 205),
                    (Self::address_details__title_receiving_to, 217),
                    (Self::authenticate__confirm_template, 275),
                    (Self::authenticate__header, 294),
                    (Self::auto_lock__change_template, 335),
                    (Self::auto_lock__title, 350),
                    (Self::backup__can_back_up_anytime, 396),
                    (Self::backup__it_should_be_backed_up, 441),
                    (Self::backup__it_should_be_backed_up_now, 468),
                    (Self::backup__new_wallet_created, 484),
                    (Self::backup__new_wallet_successfully_created, 512),
                    (Self::backup__recover_anytime, 571),
                    (Self::backup__title_backup_wallet, 585),
                    (Self::backup__title_skip, 596),
                    (Self::backup__want_to_skip, 637),
                    (Self::bitcoin__commitment_data, 652),
                    (Self::bitcoin__confirm_locktime, 668),
                    (Self::bitcoin__create_proof_of_ownership, 711),
                    (Self::bitcoin__high_mining_fee_template, 754),
                    (Self::bitcoin__locktime_no_effect, 794),
                    (Self::bitcoin__locktime_set_to, 809),
                    (Self::bitcoin__locktime_set_to_blockheight, 836),
                    (Self::bitcoin__lot_of_change_outputs, 860),
                    (Self::bitcoin__multiple_accounts, 877),
                    (Self::bitcoin__new_fee_rate, 890),
                    (Self::bitcoin__simple_send_of, 904),
                    (Self::bitcoin__ticket_amount, 917),
                    (Self::bitcoin__title_confirm_details, 932),
                    (Self::bitcoin__title_finalize_transaction, 952),
                    (Self::bitcoin__title_high_mining_fee, 967),
                    (Self::bitcoin__title_meld_transaction, 983),
                    (Self::bitcoin__title_modify_amount, 996),
                    (Self::bitcoin__title_payjoin, 1003),
                    (Self::bitcoin__title_proof_of_ownership, 1021),
                    (Self::bitcoin__title_purchase_ticket, 1036),
                    (Self::bitcoin__title_update_transaction, 1054),
                    (Self::bitcoin__unknown_path, 1066),
                    (Self::bitcoin__unknown_transaction, 1085),
                    (Self::bitcoin__unusually_high_fee, 1104),
                    (Self::bitcoin__unverified_external_inputs, 1156),
                    (Self::bitcoin__valid_signature, 1179),
                    (Self::bitcoin__voting_rights, 1195),
                    (Self::buttons__abort, 1200),
                    (Self::buttons__access, 1206),
                    (Self::buttons__again, 1211),
                    (Self::buttons__allow, 1216),
                    (Self::buttons__back, 1220),
                    (Self::buttons__back_up, 1227),
                    (Self::buttons__cancel, 1233),
                    (Self::buttons__change, 1239),
                    (Self::buttons__check, 1244),
                    (Self::buttons__check_again, 1255),
                    (Self::buttons__close, 1260),
                    (Self::buttons__confirm, 1267),
                    (Self::buttons__continue, 1275),
                    (Self::buttons__details, 1282),
                    (Self::buttons__enable, 1288),
                    (Self::buttons__enter, 1293),
                    (Self::buttons__enter_share, 1304),
                    (Self::buttons__export, 1310),
                    (Self::buttons__format, 1316),
                    (Self::buttons__go_back, 1323),
                    (Self::buttons__hold_to_confirm, 1338),
                    (Self::buttons__info, 1342),
                    (Self::buttons__install, 1349),
                    (Self::buttons__more_info, 1358),
                    (Self::buttons__ok_i_understand, 1374),
                    (Self::buttons__purchase, 1382),
                    (Self::buttons__quit, 1386),
                    (Self::buttons__restart, 1393),
                    (Self::buttons__retry, 1398),
                    (Self::buttons__select, 1404),
                    (Self::buttons__set, 1407),
                    (Self::buttons__show_all, 1415),
                    (Self::buttons__show_details, 1427),
                    (Self::buttons__show_words, 1437),
                    (Self::buttons__skip, 1441),
                    (Self::buttons__try_again, 1450),
                    (Self::buttons__turn_off, 1458),
                    (Self::buttons__turn_on, 1465),
                    (Self::coinjoin__access_account, 1494),
                    (Self::coinjoin__do_not_disconnect, 1524),
                    (Self::coinjoin__max_mining_fee, 1538),
                    (Self::coinjoin__max_rounds, 1548),
                    (Self::coinjoin__title, 1566),
                    (Self::coinjoin__title_progress, 1586),
                    (Self::coinjoin__waiting_for_others, 1604),
                    (Self::confirm_total__fee_rate_colon, 1613),
                    (Self::confirm_total__sending_from_account, 1634),
                    (Self::confirm_total__title_fee, 1642),
                    (Self::confirm_total__title_sending_from, 1654),
                    (Self::device_name__change_template, 1680),
                    (Self::device_name__title, 1691),
                    (Self::entropy__send, 1726),
                    (Self::entropy__title_confirm, 1741),
                    (Self::send__sign_transaction, 1757),
                    (Self::experimental_mode__enable, 1786),
                    (Self::experimental_mode__only_for_dev, 1824),
                    (Self::experimental_mode__title, 1841),
                    (Self::firmware_update__title, 1856),
                    (Self::firmware_update__title_fingerprint, 1870),
                    (Self::homescreen__click_to_connect, 1886),
                    (Self::homescreen__click_to_unlock, 1901),
                    (Self::homescreen__title_backup_failed, 1914),
                    (Self::homescreen__title_backup_needed, 1927),
                    (Self::homescreen__title_coinjoin_authorized, 1946),
                    (Self::homescreen__title_experimental_mode, 1963),
                    (Self::homescreen__title_no_usb_connection, 1980),
                    (Self::homescreen__title_pin_not_set, 1991),
                    (Self::homescreen__title_seedless, 1999),
                    (Self::homescreen__title_set, 2015),
                    (Self::inputs__back, 2019),
                    (Self::inputs__cancel, 2025),
                    (Self::inputs__delete, 2031),
                    (Self::inputs__enter, 2036),
                    (Self::inputs__return, 2042),
                    (Self::inputs__show, 2046),
                    (Self::inputs__space, 2051),
                    (Self::joint__title, 2068),
                    (Self::joint__to_the_total_amount, 2088),
                    (Self::joint__you_are_contributing, 2109),
                    (Self::language__change_to_template, 2132),
                    (Self::language__changed, 2161),
                    (Self::language__progress, 2178),
                    (Self::language__title, 2195),
                    (Self::lockscreen__tap_to_connect, 2209),
                    (Self::lockscreen__tap_to_unlock, 2222),
                    (Self::lockscreen__title_locked, 2228),
                    (Self::lockscreen__title_not_connected, 2241),
                    (Self::misc__decrypt_value, 2254),
                    (Self::misc__encrypt_value, 2267),
                    (Self::misc__title_suite_labeling, 2281),
                    (Self::modify_amount__decrease_amount, 2300),
                    (Self::modify_amount__increase_amount, 2319),
                    (Self::modify_amount__new_amount, 2330),
                    (Self::modify_amount__title, 2343),
                    (Self::modify_fee__decrease_fee, 2359),
                    (Self::modify_fee__fee_rate, 2368),
                    (Self::modify_fee__increase_fee, 2384),
                    (Self::modify_fee__new_transaction_fee, 2404),
                    (Self::modify_fee__no_change, 2424),
                    (Self::modify_fee__title, 2434),
                    (Self::modify_fee__transaction_fee, 2450),
                    (Self::passphrase__access_wallet, 2475),
                    (Self::passphrase__always_on_device, 2514),
                    (Self::passphrase__from_host_not_shown, 2617),
                    (Self::passphrase__wallet, 2634),
                    (Self::passphrase__hide, 2666),
                    (Self::passphrase__next_screen_will_show_passphrase, 2704),
                    (Self::passphrase__please_enter, 2733),
                    (Self::passphrase__revoke_on_device, 2788),
                    (Self::passphrase__title_confirm, 2806),
                    (Self::passphrase__title_enter, 2822),
                    (Self::passphrase__title_hide, 2837),
                    (Self::passphrase__title_settings, 2856),
                    (Self::passphrase__title_source, 2873),
                    (Self::passphrase__turn_off, 2904),
                    (Self::passphrase__turn_on, 2934),
                    (Self::pin__change, 2944),
                    (Self::pin__changed, 2956),
                    (Self::pin__cursor_will_change, 3029),
                    (Self::pin__diff_from_wipe_code, 3079),
                    (Self::pin__disabled, 3105),
                    (Self::pin__enabled, 3130),
                    (Self::pin__enter, 3139),
                    (Self::pin__enter_new, 3152),
                    (Self::pin__entered_not_valid, 3190),
                    (Self::pin__info, 3233),
                    (Self::pin__invalid_pin, 3244),
                    (Self::pin__last_attempt, 3256),
                    (Self::pin__mismatch, 3282),
                    (Self::pin__pin_mismatch, 3294),
                    (Self::pin__please_check_again, 3313),
                    (Self::pin__reenter_new, 3329),
                    (Self::pin__reenter_to_confirm, 3360),
                    (Self::pin__should_be_long, 3391),
                    (Self::pin__title_check_pin, 3400),
                    (Self::pin__title_settings, 3412),
                    (Self::pin__title_wrong_pin, 3421),
                    (Self::pin__tries_left, 3431),
                    (Self::pin__turn_off, 3480),
                    (Self::pin__turn_on, 3503),
                    (Self::pin__wrong_pin, 3512),
                    (Self::plurals__contains_x_keys, 3520),
                    (Self::plurals__lock_after_x_hours, 3530),
                    (Self::plurals__lock_after_x_milliseconds, 3554),
                    (Self::plurals__lock_after_x_minutes, 3568),
                    (Self::plurals__lock_after_x_seconds, 3582),
                    (Self::plurals__sign_x_actions, 3596),
                    (Self::plurals__transaction_of_x_operations, 3616),
                    (Self::plurals__x_groups_needed, 3628),
                    (Self::plurals__x_shares_needed, 3640),
                    (Self::progress__authenticity_check, 3664),
                    (Self::progress__done, 3668),
                    (Self::progress__loading_transaction, 3690),
                    (Self::progress__locking_device, 3711),
                    (Self::progress__one_second_left, 3724),
                    (Self::progress__please_wait, 3735),
                    (Self::storage_msg__processing, 3745),
                    (Self::progress__refreshing, 3758),
                    (Self::progress__signing_transaction, 3780),
                    (Self::progress__syncing, 3790),
                    (Self::progress__x_seconds_left_template, 3806),
                    (Self::reboot_to_bootloader__restart, 3845),
                    (Self::reboot_to_bootloader__title, 3861),
                    (Self::reboot_to_bootloader__version_by_template, 3888),
                    (Self::recovery__cancel_dry_run, 3907),
                    (Self::recovery__check_dry_run, 3925),
                    (Self::recovery__cursor_will_change, 3998),
                    (Self::recovery__dry_run_bip39_valid_match, 4068),
                    (Self::recovery__dry_run_bip39_valid_mismatch, 4144),
                    (Self::recovery__dry_run_slip39_valid_match, 4224),
                    (Self::recovery__dry_run_slip39_valid_mismatch, 4311),
                    (Self::recovery__enter_any_share, 4326),
                    (Self::recovery__enter_backup, 4344),
                    (Self::recovery__enter_different_share, 4368),
                    (Self::recovery__enter_share_from_diff_group, 4403),
                    (Self::recovery__group_num_template, 4412),
                    (Self::recovery__group_threshold_reached, 4436),
                    (Self::recovery__invalid_wallet_backup_entered, 4466),
                    (Self::recovery__invalid_share_entered, 4497),
                    (Self::recovery__more_shares_needed, 4515),
                    (Self::recovery__num_of_words, 4557),
                    (Self::recovery__only_first_n_letters, 4619),
                    (Self::recovery__progress_will_be_lost, 4645),
                    (Self::recovery__share_already_entered, 4666),
                    (Self::recovery__share_from_another_multi_share_backup, 4715),
                    (Self::recovery__share_num_template, 4724),
                    (Self::recovery__title, 4738),
                    (Self::recovery__title_cancel_dry_run, 4757),
                    (Self::recovery__title_cancel_recovery, 4772),
                    (Self::recovery__title_dry_run, 4784),
                    (Self::recovery__title_recover, 4798),
                    (Self::recovery__title_remaining_shares, 4814),
                    (Self::recovery__type_word_x_of_y_template, 4834),
                    (Self::recovery__wallet_recovered, 4859),
                    (Self::recovery__wanna_cancel_dry_run, 4908),
                    (Self::recovery__wanna_cancel_recovery, 4961),
                    (Self::recovery__word_count_template, 4972),
                    (Self::recovery__word_x_of_y_template, 4987),
                    (Self::recovery__x_more_items_starting_template_plural, 5017),
                    (Self::recovery__x_more_shares_needed_template_plural, 5045),
                    (Self::recovery__x_of_y_entered_template, 5070),
                    (Self::recovery__you_have_entered, 5086),
                    (Self::reset__advanced_group_threshold_info, 5169),
                    (Self::reset__all_x_of_y_template, 5169),
                    (Self::reset__any_x_of_y_template, 5169),
                    (Self::reset__button_create, 5182),
                    (Self::reset__button_recover, 5196),
                    (Self::reset__by_continuing, 5261),
                    (Self::reset__check_backup_title, 5273),
                    (Self::reset__check_group_share_title_template, 5295),
                    (Self::reset__check_wallet_backup_title, 5314),
                    (Self::reset__check_share_title_template, 5330),
                    (Self::reset__continue_with_next_share, 5359),
                    (Self::reset__continue_with_share_template, 5384),
                    (Self::reset__finished_verifying_group_template, 5447),
                    (Self::reset__finished_verifying_wallet_backup, 5494),
                    (Self::reset__finished_verifying_shares, 5543),
                    (Self::reset__group_description, 5581),
                    (Self::reset__group_info, 5714),
                    (Self::reset__group_share_checked_successfully_template, 5757),
                    (Self::reset__group_share_title_template, 5778),
                    (Self::reset__more_info_at, 5790),
                    (Self::reset__need_all_share_template, 5790),
                    (Self::reset__need_any_share_template, 5790),
                    (Self::reset__needed_to_form_a_group, 5790),
                    (Self::reset__needed_to_recover_your_wallet, 5790),
                    (Self::reset__never_make_digital_copy, 5829),
                    (Self::reset__num_of_share_holders_template, 5878),
                    (Self::reset__num_of_shares_advanced_info_template, 6003),
                    (Self::reset__num_of_shares_basic_info_template, 6003),
                    (Self::reset__num_shares_for_group_template, 6051),
                    (Self::reset__number_of_shares_info, 6110),
                    (Self::reset__one_share, 6110),
                    (Self::reset__only_one_share_will_be_created, 6141),
                    (Self::reset__recovery_wallet_backup_title, 6154),
                    (Self::reset__recovery_share_title_template, 6173),
                    (Self::reset__required_number_of_groups, 6216),
                    (Self::reset__select_correct_word, 6258),
                    (Self::reset__select_word_template, 6273),
                    (Self::reset__select_word_x_of_y_template, 6296),
                    (Self::reset__set_it_to_count_template, 6296),
                    (Self::reset__share_checked_successfully_template, 6328),
                    (Self::reset__share_words_title, 6343),
                    (Self::reset__slip39_checklist_num_groups, 6359),
                    (Self::reset__slip39_checklist_num_shares, 6375),
                    (Self::reset__slip39_checklist_set_num_groups, 6395),
                    (Self::reset__slip39_checklist_set_num_shares, 6415),
                    (Self::reset__slip39_checklist_set_sizes, 6439),
                    (Self::reset__slip39_checklist_set_sizes_longer, 6476),
                    (Self::reset__slip39_checklist_set_threshold, 6489),
                    (Self::reset__slip39_checklist_title, 6505),
                    (Self::reset__slip39_checklist_write_down, 6536),
                    (Self::reset__slip39_checklist_write_down_recovery, 6579),
                    (Self::reset__the_threshold_sets_the_number_of_shares, 6579),
                    (Self::reset__threshold_info, 6635),
                    (Self::reset__title_backup_is_done, 6649),
                    (Self::reset__title_create_wallet, 6662),
                    (Self::reset__title_group_threshold, 6677),
                    (Self::reset__title_number_of_groups, 6693),
                    (Self::reset__title_number_of_shares, 6709),
                    (Self::reset__title_set_group_threshold, 6728),
                    (Self::reset__title_set_number_of_groups, 6748),
                    (Self::reset__title_set_number_of_shares, 6768),
                    (Self::reset__title_set_threshold, 6781),
                    (Self::reset__to_form_group_template, 6781),
                    (Self::reset__tos_link, 6794),
                    (Self::reset__total_number_of_shares_in_group_template, 6838),
                    (Self::reset__use_your_backup, 6891),
                    (Self::reset__write_down_words_template, 6957),
                    (Self::reset__wrong_word_selected, 6977),
                    (Self::reset__you_need_one_share, 6977),
                    (Self::reset__your_backup_is_done, 6997),
                    (Self::rotation__change_template, 7031),
                    (Self::rotation__east, 7035),
                    (Self::rotation__north, 7040),
                    (Self::rotation__south, 7045),
                    (Self::rotation__title_change, 7064),
                    (Self::rotation__west, 7068),
                    (Self::safety_checks__approve_unsafe_always, 7136),
                    (Self::safety_checks__approve_unsafe_temporary, 7216),
                    (Self::safety_checks__enforce_strict, 7281),
                    (Self::safety_checks__title, 7294),
                    (Self::safety_checks__title_safety_override, 7309),
                    (Self::sd_card__all_data_will_be_lost, 7309),
                    (Self::sd_card__card_required, 7309),
                    (Self::sd_card__disable, 7309),
                    (Self::sd_card__disabled, 7309),
                    (Self::sd_card__enable, 7309),
                    (Self::sd_card__enabled, 7309),
                    (Self::sd_card__error, 7309),
                    (Self::sd_card__format_card, 7309),
                    (Self::sd_card__insert_correct_card, 7309),
                    (Self::sd_card__please_insert, 7309),
                    (Self::sd_card__please_unplug_and_insert, 7309),
                    (Self::sd_card__problem_accessing, 7309),
                    (Self::sd_card__refresh, 7309),
                    (Self::sd_card__refreshed, 7309),
                    (Self::sd_card__restart, 7309),
                    (Self::sd_card__title, 7309),
                    (Self::sd_card__title_problem, 7309),
                    (Self::sd_card__unknown_filesystem, 7309),
                    (Self::sd_card__unplug_and_insert_correct, 7309),
                    (Self::sd_card__use_different_card, 7309),
                    (Self::sd_card__wanna_format, 7309),
                    (Self::sd_card__wrong_sd_card, 7309),
                    (Self::send__confirm_sending, 7323),
                    (Self::send__from_multiple_accounts, 7354),
                    (Self::send__including_fee, 7368),
                    (Self::send__maximum_fee, 7379),
                    (Self::send__receiving_to_multisig, 7411),
                    (Self::send__title_confirm_sending, 7426),
                    (Self::send__title_joint_transaction, 7443),
                    (Self::send__title_receiving_to, 7455),
                    (Self::send__title_sending, 7462),
                    (Self::send__title_sending_amount, 7476),
                    (Self::send__title_sending_to, 7486),
                    (Self::send__to_the_total_amount, 7506),
                    (Self::send__transaction_id, 7520),
                    (Self::send__you_are_contributing, 7541),
                    (Self::share_words__words_in_order, 7557),
                    (Self::share_words__wrote_down_all, 7574),
                    (Self::sign_message__bytes_template, 7583),
                    (Self::sign_message__confirm_address, 7598),
                    (Self::sign_message__confirm_message, 7613),
                    (Self::sign_message__message_size, 7625),
                    (Self::sign_message__verify_address, 7639),
                    (Self::words__asset, 7644),
                    (Self::tutorial__middle_click, 7698),
                    (Self::tutorial__press_and_hold, 7762),
                    (Self::tutorial__ready_to_use, 7789),
                    (Self::tutorial__scroll_down, 7898),
                    (Self::tutorial__sure_you_want_skip, 7941),
                    (Self::tutorial__title_hello, 7946),
                    (Self::tutorial__title_screen_scroll, 7959),
                    (Self::tutorial__title_skip, 7972),
                    (Self::tutorial__title_tutorial_complete, 7989),
                    (Self::tutorial__use_trezor, 8056),
                    (Self::tutorial__welcome_press_right, 8099),
                    (Self::wipe__info, 8123),
                    (Self::wipe__title, 8134),
                    (Self::wipe__want_to_wipe, 8173),
                    (Self::wipe_code__change, 8189),
                    (Self::wipe_code__changed, 8207),
                    (Self::wipe_code__diff_from_pin, 8253),
                    (Self::wipe_code__disabled, 8272),
                    (Self::wipe_code__enabled, 8290),
                    (Self::wipe_code__enter_new, 8303),
                    (Self::wipe_code__info, 8360),
                    (Self::wipe_code__invalid, 8377),
                    (Self::wipe_code__mismatch, 8417),
                    (Self::wipe_code__reenter, 8435),
                    (Self::wipe_code__reenter_to_confirm, 8472),
                    (Self::wipe_code__title_check, 8487),
                    (Self::wipe_code__title_invalid, 8504),
                    (Self::wipe_code__title_settings, 8522),
                    (Self::wipe_code__turn_off, 8552),
                    (Self::wipe_code__turn_on, 8581),
                    (Self::wipe_code__wipe_code_mismatch, 8599),
                    (Self::word_count__title, 8614),
                    (Self::words__account, 8621),
                    (Self::words__account_colon, 8629),
                    (Self::words__address, 8636),
                    (Self::words__amount, 8642),
                    (Self::words__are_you_sure, 8655),
                    (Self::words__array_of, 8663),
                    (Self::words__blockhash, 8672),
                    (Self::words__buying, 8678),
                    (Self::words__confirm, 8685),
                    (Self::words__confirm_fee, 8696),
                    (Self::words__contains, 8704),
                    (Self::words__continue_anyway_question, 8720),
                    (Self::words__continue_with, 8733),
                    (Self::words__error, 8738),
                    (Self::words__fee, 8741),
                    (Self::words__from, 8745),
                    (Self::words__keep_it_safe, 8758),
                    (Self::words__know_what_your_doing, 8803),
                    (Self::words__my_trezor, 8812),
                    (Self::words__no, 8814),
                    (Self::words__outputs, 8821),
                    (Self::words__please_check_again, 8839),
                    (Self::words__please_try_again, 8855),
                    (Self::words__really_wanna, 8876),
                    (Self::words__recipient, 8885),
                    (Self::words__sign, 8889),
                    (Self::words__signer, 8895),
                    (Self::words__title_check, 8900),
                    (Self::words__title_group, 8905),
                    (Self::words__title_information, 8916),
                    (Self::words__title_remember, 8924),
                    (Self::words__title_share, 8929),
                    (Self::words__title_shares, 8935),
                    (Self::words__title_success, 8942),
                    (Self::words__title_summary, 8949),
                    (Self::words__title_threshold, 8958),
                    (Self::words__unknown, 8965),
                    (Self::words__warning, 8972),
                    (Self::words__writable, 8980),
                    (Self::words__yes, 8983),
                    (Self::reboot_to_bootloader__just_a_moment, 8999),
                    (Self::inputs__previous, 9007),
                    (Self::storage_msg__starting, 9018),
                    (Self::storage_msg__verifying_pin, 9031),
                    (Self::storage_msg__wrong_pin, 9040),
                    (Self::reset__create_x_of_y_multi_share_backup_template, 9094),
                    (Self::reset__title_shamir_backup, 9112),
                    (Self::instructions__tap_to_confirm, 9126),
                    (Self::instructions__hold_to_confirm, 9141),
                    (Self::words__important, 9150),
                    (Self::reset__words_written_down_template, 9186),
                    (Self::backup__create_backup_to_prevent_loss, 9238),
                    (Self::reset__check_backup_instructions, 9276),
                    (Self::words__instructions, 9288),
                    (Self::words__not_recommended, 9304),
                    (Self::address_details__account_info, 9316),
                    (Self::address__cancel_contact_support, 9394),
                    (Self::address__cancel_receive, 9408),
                    (Self::address__qr_code, 9415),
                    (Self::address_details__derivation_path, 9430),
                    (Self::instructions__continue_in_app, 9449),
                    (Self::words__cancel_and_exit, 9464),
                    (Self::address__confirmed, 9489),
                    (Self::pin__cancel_description, 9509),
                    (Self::pin__cancel_info, 9554),
                    (Self::pin__cancel_setup, 9570),
                    (Self::send__cancel_sign, 9581),
                    (Self::send__send_from, 9590),
                    (Self::instructions__hold_to_sign, 9602),
                    (Self::confirm_total__fee_rate, 9610),
                    (Self::send__incl_transaction_fee, 9631),
                    (Self::send__total_amount, 9643),
                    (Self::auto_lock__turned_on, 9662),
                    (Self::backup__info_multi_share_backup, 9743),
                    (Self::backup__info_single_share_backup, 9801),
                    (Self::backup__title_backup_completed, 9824),
                    (Self::backup__title_create_wallet_backup, 9844),
                    (Self::haptic_feedback__disable, 9844),
                    (Self::haptic_feedback__enable, 9844),
                    (Self::haptic_feedback__subtitle, 9844),
                    (Self::haptic_feedback__title, 9844),
                    (Self::instructions__continue_holding, 9844),
                    (Self::instructions__enter_next_share, 9860),
                    (Self::instructions__hold_to_continue, 9876),
                    (Self::instructions__hold_to_exit_tutorial, 9897),
                    (Self::instructions__learn_more, 9907),
                    (Self::instructions__shares_continue_with_x_template, 9931),
                    (Self::instructions__shares_start_with_1, 9950),
                    (Self::passphrase__title_passphrase, 9960),
                    (Self::recovery__dry_run_backup_not_on_this_device, 9992),
                    (Self::recovery__dry_run_invalid_backup_entered, 10021),
                    (Self::recovery__dry_run_slip39_valid_all_shares, 10081),
                    (Self::recovery__dry_run_slip39_valid_share, 10143),
                    (Self::recovery__dry_run_verify_remaining_shares, 10176),
                    (Self::recovery__enter_each_word, 10223),
                    (Self::recovery__info_about_disconnect, 10307),
                    (Self::recovery__share_does_not_match, 10326),
                    (Self::reset__cancel_create_wallet, 10346),
                    (Self::reset__incorrect_word_selected, 10369),
                    (Self::reset__more_at, 10376),
                    (Self::reset__num_of_shares_how_many, 10428),
                    (Self::reset__num_of_shares_long_info_template, 10599),
                    (Self::reset__select_threshold, 10657),
                    (Self::reset__share_completed_template, 10677),
                    (Self::reset__slip39_checklist_num_shares_x_template, 10698),
                    (Self::reset__slip39_checklist_threshold_x_template, 10721),
                    (Self::send__transaction_signed, 10739),
                    (Self::tutorial__continue, 10756),
                    (Self::tutorial__exit, 10769),
                    (Self::tutorial__menu, 10823),
                    (Self::tutorial__one_more_step, 10836),
                    (Self::tutorial__ready_to_use_safe5, 10878),
                    (Self::tutorial__swipe_up_and_down, 10878),
                    (Self::tutorial__title_easy_navigation, 10893),
                    (Self::tutorial__welcome_safe5, 10893),
                    (Self::words__good_to_know, 10905),
                    (Self::words__operation_cancelled, 10924),
                    (Self::words__settings, 10932),
                    (Self::words__try_again, 10942),
                    (Self::reset__slip39_checklist_num_groups_x_template, 10963),
                    (Self::brightness__title, 10981),
                    (Self::recovery__title_unlock_repeated_backup, 10999),
                    (Self::recovery__unlock_repeated_backup, 11024),
                    (Self::recovery__unlock_repeated_backup_verb, 11037),
                    (Self::homescreen__set_default, 11071),
                    (Self::reset__words_may_repeat, 11088),
                    (Self::reset__repeat_for_all_shares, 11110),
                    (Self::homescreen__settings_subtitle, 11118),
                    (Self::homescreen__settings_title, 11128),
                    (Self::reset__the_word_is_repeated, 11148),
                    (Self::tutorial__title_lets_begin, 11159),
                    (Self::tutorial__did_you_know, 11172),
                    (Self::tutorial__first_wallet, 11249),
                    (Self::tutorial__restart_tutorial, 11265),
                    (Self::tutorial__title_handy_menu, 11275),
                    (Self::tutorial__title_hold, 11308),
                    (Self::tutorial__title_well_done, 11318),
                    (Self::tutorial__lets_begin, 11370),
                    (Self::tutorial__get_started, 11382),
                    (Self::instructions__swipe_horizontally, 11400),
                    (Self::setting__adjust, 11406),
                    (Self::setting__apply, 11411),
                    (Self::brightness__changed_title, 11437),
                    (Self::brightness__change_title, 11462),
                    (Self::words__title_done, 11466),
                    (Self::reset__slip39_checklist_more_info_threshold, 11544),
                    (Self::reset__slip39_checklist_more_info_threshold_example_template, 11631),
                    (Self::passphrase__continue_with_empty_passphrase, 11662),
                    (Self::instructions__swipe_down, 11672),
                    (Self::address__public_key_confirmed, 11692),
                    (Self::words__continue_anyway, 11707),
                    (Self::buttons__view_all_data, 11720),
                    (Self::instructions__view_all_data, 11746),
                    (Self::misc__enable_labeling, 11762),
                    (Self::words__provider, 11770),
                    (Self::sign_message__confirm_without_review, 11792),
                    (Self::instructions__tap_to_continue, 11807),
                    (Self::ble__unpair_all, 11807),
                    (Self::ble__unpair_current, 11807),
                    (Self::ble__unpair_title, 11807),
                    (Self::words__unlocked, 11815),
                    (Self::words__transaction_fee, 11830),
                    (Self::words__unlimited, 11839),
                    (Self::words__chain, 11844),
                    (Self::words__token, 11849),
                    (Self::instructions__tap, 11852),
                    (Self::reset__share_words_first, 11894),
                    (Self::backup__not_recommend, 11944),
                    (Self::words__pay_attention, 11957),
                    (Self::address__check_with_source, 11987),
                    (Self::words__receive, 11994),
                    (Self::reset__recovery_share_description, 12073),
                    (Self::reset__recovery_share_number, 12119),
                    (Self::words__recovery_share, 12133),
                    (Self::send__send_in_the_app, 12180),
                    (Self::send__sign_cancelled, 12195),
                    (Self::words__send, 12199),
                    (Self::words__wallet, 12205),
                    (Self::words__authenticate, 12217),
                    (Self::auto_lock__description, 12269),
                    (Self::plurals__lock_after_x_days, 12277),
                    (Self::firmware_update__restart, 12310),
                    (Self::passphrase__access_hidden_wallet, 12330),
                    (Self::passphrase__hidden_wallet, 12343),
                    (Self::passphrase__show, 12358),
                    (Self::pin__reenter, 12370),
                    (Self::pin__setup_completed, 12390),
                    (Self::instructions__shares_start_with_x_template, 12411),
                    (Self::reset__check_share_backup_template, 12448),
                    (Self::reset__select_word_from_share_template, 12480),
                    (Self::recovery__share_from_group_entered_template, 12515),
                    (Self::send__cancel_transaction, 12533),
                    (Self::send__multisig_different_paths, 12575),
                    (Self::address__xpub, 12579),
                    (Self::words__cancel_question, 12586),
                    (Self::address__coin_address_template, 12597),
                    (Self::buttons__view, 12601),
                    (Self::words__swap, 12605),
                    (Self::address__title_provider_address, 12621),
                    (Self::address__title_refund_address, 12635),
                    (Self::words__assets, 12641),
                    (Self::buttons__finish, 12647),
                    (Self::instructions__menu_to_continue, 12667),
                    (Self::tutorial__last_one, 12675),
                    (Self::tutorial__menu_appendix, 12705),
                    (Self::tutorial__navigation_ts7, 12705),
                    (Self::tutorial__suite_restart, 12760),
                    (Self::tutorial__welcome_safe7, 12760),
                    (Self::tutorial__what_is_tropic, 12760),
                    (Self::tutorial__tap_to_start, 12781),
                    (Self::tutorial__tropic_info, 12781),
                    (Self::device_name__continue_with_empty_label, 12813),
                    (Self::device_name__enter, 12830),
                    (Self::regulatory__title, 12830),
                    (Self::words__name, 12834),
                    (Self::device_name__changed, 12854),
                    (Self::ble__manage_paired, 12854),
                    (Self::ble__pair_new, 12854),
                    (Self::ble__pair_title, 12854),
                    (Self::ble__version, 12854),
                    (Self::homescreen__firmware_type, 12867),
                    (Self::homescreen__firmware_version, 12883),
                    (Self::led__disable, 12883),
                    (Self::led__enable, 12883),
                    (Self::led__title, 12883),
                    (Self::words__about, 12888),
                    (Self::words__connected, 12897),
                    (Self::words__device, 12903),
                    (Self::words__disconnect, 12913),
                    (Self::words__led, 12916),
                    (Self::words__manage, 12922),
                    (Self::words__off, 12925),
                    (Self::words__on, 12927),
                    (Self::words__review, 12933),
                    (Self::words__security, 12941),
                    (Self::pin__change_question, 12952),
                    (Self::pin__remove, 12962),
                    (Self::pin__title, 12970),
                    (Self::wipe_code__change_question, 12987),
                    (Self::wipe_code__remove, 13003),
                    (Self::wipe_code__title, 13012),
                    (Self::words__disabled, 13020),
                    (Self::words__enabled, 13027),
                    (Self::ble__disable, 13027),
                    (Self::ble__enable, 13027),
                    (Self::words__bluetooth, 13036),
                    (Self::wipe__start_again, 13087),
                    (Self::words__set, 13090),
                    (Self::words__wipe, 13094),
                    (Self::lockscreen__unlock, 13100),
                    (Self::recovery__start_entering, 13114),
                    (Self::words__disconnected, 13126),
                    (Self::ble__forget_all, 13126),
                    (Self::words__connect, 13133),
                    (Self::words__forget, 13139),
                    (Self::words__power, 13144),
                    (Self::ble__limit_reached, 13144),
                    (Self::ble__forget_all_description, 13144),
                    (Self::ble__forget_all_devices, 13144),
                    (Self::ble__forget_all_success, 13144),
                    (Self::ble__forget_this_description, 13144),
                    (Self::ble__forget_this_device, 13144),
                    (Self::ble__forget_this_success, 13144),
                    (Self::thp__autoconnect, 13144),
                    (Self::thp__autoconnect_app, 13144),
                    (Self::thp__connect, 13144),
                    (Self::thp__connect_app, 13144),
                    (Self::thp__pair, 13144),
                    (Self::thp__pair_app, 13144),
                    (Self::thp__autoconnect_title, 13144),
                    (Self::thp__code_entry, 13144),
                    (Self::thp__code_title, 13144),
                    (Self::thp__connect_title, 13144),
                    (Self::thp__nfc_text, 13144),
                    (Self::thp__pair_title, 13144),
                    (Self::thp__qr_title, 13144),
                    (Self::ble__pairing_match, 13144),
                    (Self::ble__pairing_title, 13144),
                    (Self::thp__pair_name, 13144),
                    (Self::thp__pair_new_device, 13144),
                    (Self::tutorial__power, 13144),
                    (Self::auto_lock__on_battery, 13144),
                    (Self::auto_lock__on_usb, 13144),
                    (Self::pin__wipe_code_exists_description, 13207),
                    (Self::pin__wipe_code_exists_title, 13220),
                    (Self::wipe_code__pin_not_set_description, 13262),
                    (Self::wipe_code__cancel_setup, 13284),
                    (Self::homescreen__backup_needed_info, 13384),
                    (Self::ble__host_info, 13384),
                    (Self::ble__mac_address, 13384),
                    (Self::ble__waiting_for_host, 13384),
                    (Self::ble__apps_connected, 13384),
                    (Self::sn__action, 13384),
                    (Self::sn__title, 13384),
                    (Self::ble__must_be_enabled, 13384),
                    (Self::words__comm_trouble, 13455),
                    (Self::secure_sync__delegated_identity_key_no_thp, 13509),
                    (Self::secure_sync__delegated_identity_key_thp, 13561),
                    (Self::secure_sync__header, 13571),
                    (Self::words__note, 13575),
                ],
            };

            #[cfg(feature = "universal_fw")]
            const ALTCOIN_BLOB: StringsBlob = StringsBlob {
                text: "BaseEnterpriseLegacyPointerRewardaddress - no staking rewards.Amount burned (decimals unknown):Amount minted (decimals unknown):Amount sent (decimals unknown):Pool has no metadata (anonymous pool)Asset fingerprint:Auxiliary data hash:BlockCatalystCertificateChange outputCheck all items carefully.Choose level of details:Collateral input ID:Collateral input index:The collateral return output contains tokens.Collateral returnConfirm signing the stake pool registration as an owner.Confirm transactionConfirming a multisig transaction.Confirming a Plutus transaction.Confirming pool registration as owner.Confirming a transaction.CostCredential doesn't match payment credential.Datum hash:Delegating to:for account {0} and index {1}:for account {0}:for key hash:for script:Inline datumInput ID:Input index:The following address is a change address. ItsThe following address is owned by this device. ItsThe vote key registration payment address is owned by this device. Itskey hashMarginmulti-sig pathContains {0} nested scripts.Network:Transaction has no outputs, network cannot be verified.Nonce:otherpathPledgepointerPolicy IDPool metadata hash:Pool metadata url:Pool owner:Pool reward account:Reference input ID:Reference input index:Reference scriptRequired signerrewardAddress is a reward address.Warning: The address is not a payment address, it is not eligible for rewards.Rewards go to:scriptAllAnyScript data hash:Script hash:Invalid beforeInvalid hereafterKeyN of Kscript rewardSendingShow SimpleSign transaction with {0}Stake delegationStake key deregistrationStakepool registrationStake pool registration\nPool ID:Stake key registrationStaking key for accountto pool:token minting pathTotal collateral:TransactionThe transaction contains minting or burning of tokens.The following transaction output contains a script address, but does not contain a datum.Transaction ID:The transaction contains no collateral inputs. Plutus script will not be able to run.The transaction contains no script data hash. Plutus script will not be able to run.The following transaction output contains tokens.TTL:Unknown collateral amount.Path is unusual.Valid since:Verify scriptVote key registration (CIP-36)Vote public key:Voting purpose:WarningWeight:Confirm withdrawal for {0} address:Requires {0} out of {1} signatures.Amount sent:Size: {0} bytesGas limitGas priceMax fee per gasName and versionNew contract will be deployedNo message fieldMax priority feeShow full arrayShow full domainShow full messageShow full structReally sign EIP-712 typed data?Input dataConfirm domainConfirm messageConfirm structConfirm typed dataSigning address{0} unitsUnknown tokenThe signature is valid.Already registeredThis device is already registered with this application.This device is already registered with {0}.This device is not registered with this application.The credential you are trying to import does\nnot belong to this authenticator.erase all credentials?Export information about the credentials stored on this device?Not registeredThis device is not registered with\n{0}.Please enable PIN protection.FIDO2 authenticateImport credentialList credentialsFIDO2 registerRemove credentialFIDO2 resetU2F authenticateU2F registerFIDO2 verify userUnable to verify user.Do you really want to erase all credentials?Confirm exportConfirm ki syncConfirm refreshConfirm unlock timeHashing inputsPayment IDPostprocessing...Processing...Processing inputsProcessing outputsSigning...Signing inputsUnlock time for this transaction is set to {0}Do you really want to export tx_der\nfor tx_proof?Do you really want to export tx_key?Do you really want to export watch-only credentials?Do you really want to\nstart refresh?Do you really want to\nsync key images?Confirm tagDestination tag:\n{0}Account indexAssociated token accountConfirm multisigExpected feeInstruction contains {0} accounts and its data is {1} bytes long.Instruction dataThe following instruction is a multisig instruction.{0} is provided via a lookup table.Lookup table addressMultiple signersTransaction contains unknown instructions.Transaction requires {0} signers which increases the fee.Account MergeAccount ThresholdsAdd SignerAdd trustAll XLM will be sent toAllow trustBalance IDBump SequenceBuying:Claim Claimable BalanceClear dataClear flagsConfirm IssuerConfirm memoConfirm operationConfirm timeboundsCreate AccountDebited amountDeleteDelete Passive OfferDelete trustDestinationMemo is not set.\nTypically needed when sending to exchanges.Final confirmHashHigh:Home DomainInflation{0} issuerKey:LimitLow:Master Weight:Medium:New OfferNew Passive OfferNo memo set![no restriction]Path PayPath Pay at leastPayPay at mostPre-auth transactionPrice per {0}:Remove SignerRevoke trustSelling:Set dataSet flagsSet sequence to {0}?Sign this transaction made up of {0}and pay {0}\nfor fee?Source accountTrusted AccountUpdateValid from (UTC)Valid to (UTC)Value (SHA-256):Do you want to clear value key {0}?Baker addressBalance:Ballot:Confirm delegationConfirm originationDelegatorProposalRegister delegateRemove delegationSubmit ballotSubmit proposalSubmit proposalsIncrease and retrieve the U2F counter?Set the U2F counter to {0}?Get U2F counterSet U2F counterClaimClaim addressClaim ETH from Everstake?StakeStake addressStake ETH on Everstake?UnstakeUnstake ETH from Everstake?Always AbstainAlways No ConfidenceDelegating to key hash:Delegating to script:Deposit:Vote delegationMore credentialsSelect the credential that you would like to use for authentication.for authenticationSelect credentialCredential detailsUnknown contract addressToken contractInteraction contractBase feeClaimClaim SOL from stake account?Claiming SOL to address outside your current wallet.Priority feeStakeStake accountStake SOL?The current wallet isn't the SOL staking withdraw authority.Withdraw authority addressUnstakeUnstake SOL from stake account?Vote accountStake SOL on {0}?Event kind: {0}Max fees and rentMax rent feeApproveAmount allowanceChain IDReview details to approve token spending.Token approvalApprove toApproving unlimited amount of {0}Review details to revoke token approval.Token revocationRevokeRevoke fromUnknown tokenUnknown token addressAll input data ({0} bytes)Provider contract addressConfirm message hashSign withTimeboundsToken infoTransaction sourceTransaction source does not belong to this Trezor.Confirm messageEmpty messageMessage hash:Message hexMessage textSign message hash with {0}Sign message with {0}Destination tag is not set. Typically needed when sending to exchanges.",
                offsets: &[
                    (Self::cardano__addr_base, 4),
                    (Self::cardano__addr_enterprise, 14),
                    (Self::cardano__addr_legacy, 20),
                    (Self::cardano__addr_pointer, 27),
                    (Self::cardano__addr_reward, 33),
                    (Self::cardano__address_no_staking, 62),
                    (Self::cardano__amount_burned_decimals_unknown, 95),
                    (Self::cardano__amount_minted_decimals_unknown, 128),
                    (Self::cardano__amount_sent_decimals_unknown, 159),
                    (Self::cardano__anonymous_pool, 196),
                    (Self::cardano__asset_fingerprint, 214),
                    (Self::cardano__auxiliary_data_hash, 234),
                    (Self::cardano__block, 239),
                    (Self::cardano__catalyst, 247),
                    (Self::cardano__certificate, 258),
                    (Self::cardano__change_output, 271),
                    (Self::cardano__check_all_items, 297),
                    (Self::cardano__choose_level_of_details, 321),
                    (Self::cardano__collateral_input_id, 341),
                    (Self::cardano__collateral_input_index, 364),
                    (Self::cardano__collateral_output_contains_tokens, 409),
                    (Self::cardano__collateral_return, 426),
                    (Self::cardano__confirm_signing_stake_pool, 482),
                    (Self::cardano__confirm_transaction, 501),
                    (Self::cardano__confirming_a_multisig_transaction, 535),
                    (Self::cardano__confirming_a_plutus_transaction, 567),
                    (Self::cardano__confirming_pool_registration, 605),
                    (Self::cardano__confirming_transaction, 630),
                    (Self::cardano__cost, 634),
                    (Self::cardano__credential_mismatch, 678),
                    (Self::cardano__datum_hash, 689),
                    (Self::cardano__delegating_to, 703),
                    (Self::cardano__for_account_and_index_template, 733),
                    (Self::cardano__for_account_template, 749),
                    (Self::cardano__for_key_hash, 762),
                    (Self::cardano__for_script, 773),
                    (Self::cardano__inline_datum, 785),
                    (Self::cardano__input_id, 794),
                    (Self::cardano__input_index, 806),
                    (Self::cardano__intro_text_change, 852),
                    (Self::cardano__intro_text_owned_by_device, 902),
                    (Self::cardano__intro_text_registration_payment, 972),
                    (Self::cardano__key_hash, 980),
                    (Self::cardano__margin, 986),
                    (Self::cardano__multisig_path, 1000),
                    (Self::cardano__nested_scripts_template, 1028),
                    (Self::cardano__network, 1036),
                    (Self::cardano__no_output_tx, 1091),
                    (Self::cardano__nonce, 1097),
                    (Self::cardano__other, 1102),
                    (Self::cardano__path, 1106),
                    (Self::cardano__pledge, 1112),
                    (Self::cardano__pointer, 1119),
                    (Self::cardano__policy_id, 1128),
                    (Self::cardano__pool_metadata_hash, 1147),
                    (Self::cardano__pool_metadata_url, 1165),
                    (Self::cardano__pool_owner, 1176),
                    (Self::cardano__pool_reward_account, 1196),
                    (Self::cardano__reference_input_id, 1215),
                    (Self::cardano__reference_input_index, 1237),
                    (Self::cardano__reference_script, 1253),
                    (Self::cardano__required_signer, 1268),
                    (Self::cardano__reward, 1274),
                    (Self::cardano__reward_address, 1302),
                    (Self::cardano__reward_eligibility_warning, 1380),
                    (Self::cardano__rewards_go_to, 1394),
                    (Self::cardano__script, 1400),
                    (Self::cardano__script_all, 1403),
                    (Self::cardano__script_any, 1406),
                    (Self::cardano__script_data_hash, 1423),
                    (Self::cardano__script_hash, 1435),
                    (Self::cardano__script_invalid_before, 1449),
                    (Self::cardano__script_invalid_hereafter, 1466),
                    (Self::cardano__script_key, 1469),
                    (Self::cardano__script_n_of_k, 1475),
                    (Self::cardano__script_reward, 1488),
                    (Self::cardano__sending, 1495),
                    (Self::cardano__show_simple, 1506),
                    (Self::cardano__sign_tx_path_template, 1531),
                    (Self::cardano__stake_delegation, 1547),
                    (Self::cardano__stake_deregistration, 1571),
                    (Self::cardano__stake_pool_registration, 1593),
                    (Self::cardano__stake_pool_registration_pool_id, 1625),
                    (Self::cardano__stake_registration, 1647),
                    (Self::cardano__staking_key_for_account, 1670),
                    (Self::cardano__to_pool, 1678),
                    (Self::cardano__token_minting_path, 1696),
                    (Self::cardano__total_collateral, 1713),
                    (Self::cardano__transaction, 1724),
                    (Self::cardano__transaction_contains_minting_or_burning, 1778),
                    (Self::cardano__transaction_contains_script_address_no_datum, 1867),
                    (Self::cardano__transaction_id, 1882),
                    (Self::cardano__transaction_no_collateral_input, 1967),
                    (Self::cardano__transaction_no_script_data_hash, 2051),
                    (Self::cardano__transaction_output_contains_tokens, 2100),
                    (Self::cardano__ttl, 2104),
                    (Self::cardano__unknown_collateral_amount, 2130),
                    (Self::cardano__unusual_path, 2146),
                    (Self::cardano__valid_since, 2158),
                    (Self::cardano__verify_script, 2171),
                    (Self::cardano__vote_key_registration, 2201),
                    (Self::cardano__vote_public_key, 2217),
                    (Self::cardano__voting_purpose, 2232),
                    (Self::cardano__warning, 2239),
                    (Self::cardano__weight, 2246),
                    (Self::cardano__withdrawal_for_address_template, 2281),
                    (Self::cardano__x_of_y_signatures_template, 2316),
                    (Self::eos__about_to_sign_template, 2316),
                    (Self::eos__action_name, 2316),
                    (Self::eos__arbitrary_data, 2316),
                    (Self::eos__buy_ram, 2316),
                    (Self::eos__bytes, 2316),
                    (Self::eos__cancel_vote, 2316),
                    (Self::eos__checksum, 2316),
                    (Self::eos__code, 2316),
                    (Self::eos__contract, 2316),
                    (Self::eos__cpu, 2316),
                    (Self::eos__creator, 2316),
                    (Self::eos__delegate, 2316),
                    (Self::eos__delete_auth, 2316),
                    (Self::eos__from, 2316),
                    (Self::eos__link_auth, 2316),
                    (Self::eos__memo, 2316),
                    (Self::eos__name, 2316),
                    (Self::eos__net, 2316),
                    (Self::eos__new_account, 2316),
                    (Self::eos__owner, 2316),
                    (Self::eos__parent, 2316),
                    (Self::eos__payer, 2316),
                    (Self::eos__permission, 2316),
                    (Self::eos__proxy, 2316),
                    (Self::eos__receiver, 2316),
                    (Self::eos__refund, 2316),
                    (Self::eos__requirement, 2316),
                    (Self::eos__sell_ram, 2316),
                    (Self::eos__sender, 2316),
                    (Self::eos__threshold, 2316),
                    (Self::eos__to, 2316),
                    (Self::eos__transfer, 2316),
                    (Self::eos__type, 2316),
                    (Self::eos__undelegate, 2316),
                    (Self::eos__unlink_auth, 2316),
                    (Self::eos__update_auth, 2316),
                    (Self::eos__vote_for_producers, 2316),
                    (Self::eos__vote_for_proxy, 2316),
                    (Self::eos__voter, 2316),
                    (Self::ethereum__amount_sent, 2328),
                    (Self::ethereum__data_size_template, 2343),
                    (Self::ethereum__gas_limit, 2352),
                    (Self::ethereum__gas_price, 2361),
                    (Self::ethereum__max_gas_price, 2376),
                    (Self::ethereum__name_and_version, 2392),
                    (Self::ethereum__new_contract, 2421),
                    (Self::ethereum__no_message_field, 2437),
                    (Self::ethereum__priority_fee, 2453),
                    (Self::ethereum__show_full_array, 2468),
                    (Self::ethereum__show_full_domain, 2484),
                    (Self::ethereum__show_full_message, 2501),
                    (Self::ethereum__show_full_struct, 2517),
                    (Self::ethereum__sign_eip712, 2548),
                    (Self::ethereum__title_input_data, 2558),
                    (Self::ethereum__title_confirm_domain, 2572),
                    (Self::ethereum__title_confirm_message, 2587),
                    (Self::ethereum__title_confirm_struct, 2601),
                    (Self::ethereum__title_confirm_typed_data, 2619),
                    (Self::ethereum__title_signing_address, 2634),
                    (Self::ethereum__units_template, 2643),
                    (Self::ethereum__unknown_token, 2656),
                    (Self::ethereum__valid_signature, 2679),
                    (Self::fido__already_registered, 2697),
                    (Self::fido__device_already_registered, 2753),
                    (Self::fido__device_already_registered_with_template, 2796),
                    (Self::fido__device_not_registered, 2848),
                    (Self::fido__does_not_belong, 2926),
                    (Self::fido__erase_credentials, 2948),
                    (Self::fido__export_credentials, 3011),
                    (Self::fido__not_registered, 3025),
                    (Self::fido__not_registered_with_template, 3064),
                    (Self::fido__please_enable_pin_protection, 3093),
                    (Self::fido__title_authenticate, 3111),
                    (Self::fido__title_import_credential, 3128),
                    (Self::fido__title_list_credentials, 3144),
                    (Self::fido__title_register, 3158),
                    (Self::fido__title_remove_credential, 3175),
                    (Self::fido__title_reset, 3186),
                    (Self::fido__title_u2f_auth, 3202),
                    (Self::fido__title_u2f_register, 3214),
                    (Self::fido__title_verify_user, 3231),
                    (Self::fido__unable_to_verify_user, 3253),
                    (Self::fido__wanna_erase_credentials, 3297),
                    (Self::monero__confirm_export, 3311),
                    (Self::monero__confirm_ki_sync, 3326),
                    (Self::monero__confirm_refresh, 3341),
                    (Self::monero__confirm_unlock_time, 3360),
                    (Self::monero__hashing_inputs, 3374),
                    (Self::monero__payment_id, 3384),
                    (Self::monero__postprocessing, 3401),
                    (Self::monero__processing, 3414),
                    (Self::monero__processing_inputs, 3431),
                    (Self::monero__processing_outputs, 3449),
                    (Self::monero__signing, 3459),
                    (Self::monero__signing_inputs, 3473),
                    (Self::monero__unlock_time_set_template, 3519),
                    (Self::monero__wanna_export_tx_der, 3568),
                    (Self::monero__wanna_export_tx_key, 3604),
                    (Self::monero__wanna_export_watchkey, 3656),
                    (Self::monero__wanna_start_refresh, 3692),
                    (Self::monero__wanna_sync_key_images, 3730),
                    (Self::nem__absolute, 3730),
                    (Self::nem__activate, 3730),
                    (Self::nem__add, 3730),
                    (Self::nem__confirm_action, 3730),
                    (Self::nem__confirm_address, 3730),
                    (Self::nem__confirm_creation_fee, 3730),
                    (Self::nem__confirm_mosaic, 3730),
                    (Self::nem__confirm_multisig_fee, 3730),
                    (Self::nem__confirm_namespace, 3730),
                    (Self::nem__confirm_payload, 3730),
                    (Self::nem__confirm_properties, 3730),
                    (Self::nem__confirm_rental_fee, 3730),
                    (Self::nem__confirm_transfer_of, 3730),
                    (Self::nem__convert_account_to_multisig, 3730),
                    (Self::nem__cosign_transaction_for, 3730),
                    (Self::nem__cosignatory, 3730),
                    (Self::nem__create_mosaic, 3730),
                    (Self::nem__create_namespace, 3730),
                    (Self::nem__deactivate, 3730),
                    (Self::nem__decrease, 3730),
                    (Self::nem__description, 3730),
                    (Self::nem__divisibility_and_levy_cannot_be_shown, 3730),
                    (Self::nem__encrypted, 3730),
                    (Self::nem__final_confirm, 3730),
                    (Self::nem__immutable, 3730),
                    (Self::nem__increase, 3730),
                    (Self::nem__initial_supply, 3730),
                    (Self::nem__initiate_transaction_for, 3730),
                    (Self::nem__levy_divisibility, 3730),
                    (Self::nem__levy_fee, 3730),
                    (Self::nem__levy_fee_of, 3730),
                    (Self::nem__levy_mosaic, 3730),
                    (Self::nem__levy_namespace, 3730),
                    (Self::nem__levy_recipient, 3730),
                    (Self::nem__levy_type, 3730),
                    (Self::nem__modify_supply_for, 3730),
                    (Self::nem__modify_the_number_of_cosignatories_by, 3730),
                    (Self::nem__mutable, 3730),
                    (Self::nem__of, 3730),
                    (Self::nem__percentile, 3730),
                    (Self::nem__raw_units_template, 3730),
                    (Self::nem__remote_harvesting, 3730),
                    (Self::nem__remove, 3730),
                    (Self::nem__set_minimum_cosignatories_to, 3730),
                    (Self::nem__sign_tx_fee_template, 3730),
                    (Self::nem__supply_change, 3730),
                    (Self::nem__supply_units_template, 3730),
                    (Self::nem__transferable, 3730),
                    (Self::nem__under_namespace, 3730),
                    (Self::nem__unencrypted, 3730),
                    (Self::nem__unknown_mosaic, 3730),
                    (Self::ripple__confirm_tag, 3741),
                    (Self::ripple__destination_tag_template, 3761),
                    (Self::solana__account_index, 3774),
                    (Self::solana__associated_token_account, 3798),
                    (Self::solana__confirm_multisig, 3814),
                    (Self::solana__expected_fee, 3826),
                    (Self::solana__instruction_accounts_template, 3891),
                    (Self::solana__instruction_data, 3907),
                    (Self::solana__instruction_is_multisig, 3959),
                    (Self::solana__is_provided_via_lookup_table_template, 3994),
                    (Self::solana__lookup_table_address, 4014),
                    (Self::solana__multiple_signers, 4030),
                    (Self::solana__transaction_contains_unknown_instructions, 4072),
                    (Self::solana__transaction_requires_x_signers_template, 4129),
                    (Self::stellar__account_merge, 4142),
                    (Self::stellar__account_thresholds, 4160),
                    (Self::stellar__add_signer, 4170),
                    (Self::stellar__add_trust, 4179),
                    (Self::stellar__all_will_be_sent_to, 4202),
                    (Self::stellar__allow_trust, 4213),
                    (Self::stellar__balance_id, 4223),
                    (Self::stellar__bump_sequence, 4236),
                    (Self::stellar__buying, 4243),
                    (Self::stellar__claim_claimable_balance, 4266),
                    (Self::stellar__clear_data, 4276),
                    (Self::stellar__clear_flags, 4287),
                    (Self::stellar__confirm_issuer, 4301),
                    (Self::stellar__confirm_memo, 4313),
                    (Self::stellar__confirm_operation, 4330),
                    (Self::stellar__confirm_timebounds, 4348),
                    (Self::stellar__create_account, 4362),
                    (Self::stellar__debited_amount, 4376),
                    (Self::stellar__delete, 4382),
                    (Self::stellar__delete_passive_offer, 4402),
                    (Self::stellar__delete_trust, 4414),
                    (Self::stellar__destination, 4425),
                    (Self::stellar__exchanges_require_memo, 4485),
                    (Self::stellar__final_confirm, 4498),
                    (Self::stellar__hash, 4502),
                    (Self::stellar__high, 4507),
                    (Self::stellar__home_domain, 4518),
                    (Self::stellar__inflation, 4527),
                    (Self::stellar__issuer_template, 4537),
                    (Self::stellar__key, 4541),
                    (Self::stellar__limit, 4546),
                    (Self::stellar__low, 4550),
                    (Self::stellar__master_weight, 4564),
                    (Self::stellar__medium, 4571),
                    (Self::stellar__new_offer, 4580),
                    (Self::stellar__new_passive_offer, 4597),
                    (Self::stellar__no_memo_set, 4609),
                    (Self::stellar__no_restriction, 4625),
                    (Self::stellar__path_pay, 4633),
                    (Self::stellar__path_pay_at_least, 4650),
                    (Self::stellar__pay, 4653),
                    (Self::stellar__pay_at_most, 4664),
                    (Self::stellar__preauth_transaction, 4684),
                    (Self::stellar__price_per_template, 4698),
                    (Self::stellar__remove_signer, 4711),
                    (Self::stellar__revoke_trust, 4723),
                    (Self::stellar__selling, 4731),
                    (Self::stellar__set_data, 4739),
                    (Self::stellar__set_flags, 4748),
                    (Self::stellar__set_sequence_to_template, 4768),
                    (Self::stellar__sign_tx_count_template, 4804),
                    (Self::stellar__sign_tx_fee_template, 4824),
                    (Self::stellar__source_account, 4838),
                    (Self::stellar__trusted_account, 4853),
                    (Self::stellar__update, 4859),
                    (Self::stellar__valid_from, 4875),
                    (Self::stellar__valid_to, 4889),
                    (Self::stellar__value_sha256, 4905),
                    (Self::stellar__wanna_clean_value_key_template, 4940),
                    (Self::tezos__baker_address, 4953),
                    (Self::tezos__balance, 4961),
                    (Self::tezos__ballot, 4968),
                    (Self::tezos__confirm_delegation, 4986),
                    (Self::tezos__confirm_origination, 5005),
                    (Self::tezos__delegator, 5014),
                    (Self::tezos__proposal, 5022),
                    (Self::tezos__register_delegate, 5039),
                    (Self::tezos__remove_delegation, 5056),
                    (Self::tezos__submit_ballot, 5069),
                    (Self::tezos__submit_proposal, 5084),
                    (Self::tezos__submit_proposals, 5100),
                    (Self::u2f__get, 5138),
                    (Self::u2f__set_template, 5165),
                    (Self::u2f__title_get, 5180),
                    (Self::u2f__title_set, 5195),
                    (Self::ethereum__staking_claim, 5200),
                    (Self::ethereum__staking_claim_address, 5213),
                    (Self::ethereum__staking_claim_intro, 5238),
                    (Self::ethereum__staking_stake, 5243),
                    (Self::ethereum__staking_stake_address, 5256),
                    (Self::ethereum__staking_stake_intro, 5279),
                    (Self::ethereum__staking_unstake, 5286),
                    (Self::ethereum__staking_unstake_intro, 5313),
                    (Self::cardano__always_abstain, 5327),
                    (Self::cardano__always_no_confidence, 5347),
                    (Self::cardano__delegating_to_key_hash, 5370),
                    (Self::cardano__delegating_to_script, 5391),
                    (Self::cardano__deposit, 5399),
                    (Self::cardano__vote_delegation, 5414),
                    (Self::fido__more_credentials, 5430),
                    (Self::fido__select_intro, 5498),
                    (Self::fido__title_for_authentication, 5516),
                    (Self::fido__title_select_credential, 5533),
                    (Self::fido__title_credential_details, 5551),
                    (Self::ethereum__unknown_contract_address, 5575),
                    (Self::ethereum__token_contract, 5589),
                    (Self::ethereum__interaction_contract, 5609),
                    (Self::solana__base_fee, 5617),
                    (Self::solana__claim, 5622),
                    (Self::solana__claim_question, 5651),
                    (Self::solana__claim_recipient_warning, 5703),
                    (Self::solana__priority_fee, 5715),
                    (Self::solana__stake, 5720),
                    (Self::solana__stake_account, 5733),
                    (Self::solana__stake_question, 5743),
                    (Self::solana__stake_withdrawal_warning, 5803),
                    (Self::solana__stake_withdrawal_warning_title, 5829),
                    (Self::solana__unstake, 5836),
                    (Self::solana__unstake_question, 5867),
                    (Self::solana__vote_account, 5879),
                    (Self::solana__stake_on_question, 5896),
                    (Self::nostr__event_kind_template, 5911),
                    (Self::solana__max_fees_rent, 5928),
                    (Self::solana__max_rent_fee, 5940),
                    (Self::ethereum__approve, 5947),
                    (Self::ethereum__approve_amount_allowance, 5963),
                    (Self::ethereum__approve_chain_id, 5971),
                    (Self::ethereum__approve_intro, 6012),
                    (Self::ethereum__approve_intro_title, 6026),
                    (Self::ethereum__approve_to, 6036),
                    (Self::ethereum__approve_unlimited_template, 6069),
                    (Self::ethereum__approve_intro_revoke, 6109),
                    (Self::ethereum__approve_intro_title_revoke, 6125),
                    (Self::ethereum__approve_revoke, 6131),
                    (Self::ethereum__approve_revoke_from, 6142),
                    (Self::solana__unknown_token, 6155),
                    (Self::solana__unknown_token_address, 6176),
                    (Self::ethereum__title_all_input_data_template, 6202),
                    (Self::ethereum__contract_address, 6227),
                    (Self::ethereum__title_confirm_message_hash, 6247),
                    (Self::stellar__sign_with, 6256),
                    (Self::stellar__timebounds, 6266),
                    (Self::stellar__token_info, 6276),
                    (Self::stellar__transaction_source, 6294),
                    (Self::stellar__transaction_source_diff_warning, 6344),
                    (Self::cardano__confirm_message, 6359),
                    (Self::cardano__empty_message, 6372),
                    (Self::cardano__message_hash, 6385),
                    (Self::cardano__message_hex, 6396),
                    (Self::cardano__message_text, 6408),
                    (Self::cardano__sign_message_hash_path_template, 6434),
                    (Self::cardano__sign_message_path_template, 6455),
                    (Self::ripple__destination_tag_missing, 6526),
                ],
            };

            #[cfg(feature = "debug")]
            const DEBUG_BLOB: StringsBlob = StringsBlob {
                text: "Loading seedLoading private seed is not recommended.",
                offsets: &[
                    (Self::debug__loading_seed, 12),
                    (Self::debug__loading_seed_not_recommended, 52),
                ],
            };

            pub const BLOBS: &'static [StringsBlob] = &[
                Self::BTC_ONLY_BLOB,
                #[cfg(feature = "universal_fw")]
                Self::ALTCOIN_BLOB,
                #[cfg(feature = "debug")]
                Self::DEBUG_BLOB,
            ];
        }
    } else if #[cfg(feature = "layout_delizia")] {
        impl TranslatedString {
            const BTC_ONLY_BLOB: StringsBlob = StringsBlob {
                text: "Please contact Trezor support atKey mismatch?Address mismatch?trezor.io/supportWrong derivation path for selected account.XPUB mismatch?Public keyCosignerReceive addressYoursDerivation path:Receive addressReceiving toAllow connected app to check the authenticity of your {0}?Authenticate deviceAuto-lock Trezor after {0} of inactivity?Auto-lock delayYou can back up your Trezor once, at any time.You should back up your new wallet right now.It should be backed up now!Wallet created.\nWallet created successfully.You can use your backup to recover your wallet at any time.Back up walletSkip backupAre you sure you want to skip the backup?Commitment dataConfirm locktimeDo you want to create a proof of ownership?The mining fee of\n{0}\nis unexpectedly high.Locktime is set but will have no effect.Locktime set toLocktime set to blockheightA lot of change-outputs.Multiple accountsNew fee rate:Simple send ofTicket amountConfirm detailsFinalize transactionHigh mining feeMeld transactionModify amountPayjoinProof of ownershipPurchase ticketUpdate transactionUnknown pathUnknown transactionUnusually high fee.The transaction contains unverified external inputs.The signature is valid.Voting rights toAbortAccessAgainAllowBackBack upCancelChangeCheckCheck againCloseConfirmContinueDetailsEnableEnterEnter shareExportFormatGo backHold to confirmInfoInstallMore infoOk, I understandPurchaseQuitRestartRetrySelectSetShow allShow detailsShow wordsSkipTry againTurn offTurn onAccess your coinjoin account?Do not disconnect your Trezor!Max mining feeMax roundsAuthorize coinjoinCoinjoin in progressWaiting for othersFee rate:Sending from account:Fee infoSending fromChange device name to {0}?Device nameDo you really want to send entropy?Confirm entropySign transactionEnable experimental features?Only for development and beta testing!Experimental modeUpdate firmwareFW fingerprintClick to ConnectClick to UnlockBackup failedBackup neededCoinjoin authorizedExperimental modeNo USB connectionPIN not setSeedlessChange wallpaperJoint transactionTo the total amount:You are contributing:Change language to {0}?Language changed successfullyChanging languageLanguage settingsTap to connectTap to unlockLockedNot connectedDecrypt valueEncrypt valueSuite labelingDecrease amount by:Increase amount by:New amount:Modify amountDecrease fee by:Fee rate:Increase fee by:New transaction fee:Fee did not change.\nModify feeTransaction fee:Access passphrase wallet?Always enter your passphrase on Trezor?Passphrase provided by connected app will be used but will not be displayed due to the device settings.Passphrase walletHide passphrase coming from app?The next screen shows your passphrase.Please enter your passphrase.Do you want to revoke the passphrase on device setting?Confirm passphraseEnter passphraseHide passphrasePassphrase settingsPassphrase sourceTurn off passphrase protection?Turn on passphrase protection?Change PINPIN changed.Position of the cursor will change between entries for enhanced security.The new PIN must be different from your wipe code.PIN protection\nturned off.PIN protection\nturned on.Enter PINEnter new PINThe PIN you have entered is not valid.PIN will be required to access this device.Invalid PINLast attemptEntered PINs do not match!PIN mismatchPlease check again.Re-enter new PINPlease re-enter PIN to confirm.PIN should be 4-50 digits long.Check PINPIN settingsWrong PINtries leftAre you sure you want to turn off PIN protection?Turn on PIN protection?Wrong PINkey|keyshour|hoursmillisecond|millisecondsminute|minutessecond|secondsaction|actionsoperation|operationsgroup|groupsshare|sharesChecking authenticity...DoneLoading transaction...Locking the device...1 second leftPlease waitProcessingRefreshing...Signing transaction...Syncing...{0} seconds leftTrezor will restart in bootloader mode.Go to bootloaderFirmware version {0}\nby {1}Cancel backup checkCheck your backup?Position of the cursor will change between entries for enhanced security.The entered wallet backup is valid and matches the one in this device.The entered wallet backup is valid but does not match the one in the device.The entered recovery shares are valid and match what is currently in the device.The entered wallet backup is valid but doesn't match the one on this device.Enter any shareEnter your backup.Enter a different share.Enter share from a different group.Group {0}Group threshold reached.Invalid wallet backup entered.Invalid recovery share entered.More shares neededSelect the number of words in your backup.You'll only have to select the first 2-4 letters of each word.All progress will be lost.Share already enteredYou have entered a share from a different backup.Share {0}Recover walletCancel backup checkCancel recoveryBackup checkRecover walletRemaining sharesType word {0} of {1}Wallet recovery completedAre you sure you want to cancel the backup check?Are you sure you want to cancel the recovery process?({0} words)Word {0} of {1}{count} more {plural} starting{count} more {plural} needed{0} of {1} shares enteredYou have enteredThe group threshold specifies the number of groups required to recover your wallet.Create walletRecover walletBy continuing you agree to Trezor Company's terms and conditions.Check backupCheck g{0} - share {1}Check wallet backupCheck share #{0}Continue with the next share.Continue with share #{0}.You have finished verifying your recovery shares for group {0}.You have finished verifying your wallet backup.You have finished verifying your recovery shares.A group is made up of recovery shares.Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds.Group {0} - Share {1} checked successfully.Group {0} - share {1}More info atNever put your backup anywhere digital.{0} people or locations will each hold one share.Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}.The required number of shares to form Group {0}.= total number of unique word lists used for wallet backup.Only one share will be created.Wallet backupRecovery share #{0}The required number of groups for recovery.Select the correct word for each position.Select {0} wordSelect word {0} of {1}:Share #{0} checked successfully.Standard backupNumber of groupsNumber of sharesSet number of groupsSet number of sharesSet sizes and thresholdsSet size and threshold for each groupSet thresholdBackup checklistWrite down and check all sharesWrite down & check all wallet backup shares= minimum number of unique word lists used for recovery.Backup is doneCreate walletGroup thresholdNumber of groupsNumber of sharesSet group thresholdSet number of groupsSet number of sharesSet thresholdtrezor.io/tosSet the total number of shares in Group {0}.Use your backup when you need to recover your wallet.Write the following {0} words in order on your wallet backup card.Wrong word selected!Your backup is done.Change display orientation to {0}?eastnorthsouthDisplay orientationwestTrezor will allow you to approve some actions which might be unsafe.Trezor will temporarily allow you to approve some actions which might be unsafe.Do you really want to enforce strict safety checks (recommended)?Safety checksSafety overrideAll data on the SD card will be lost.SD card required.Do you really want to remove SD card protection from your device?You have successfully disabled SD protection.Do you really want to secure your device with SD card protection?You have successfully enabled SD protection.SD card errorFormat SD cardPlease insert the correct SD card for this device.Please insert your SD card.Please unplug the device and insert your SD card.There was a problem accessing the SD card.Do you really want to replace the current SD card secret with a newly generated one?You have successfully refreshed SD protection.Do you want to restart Trezor in bootloader mode?SD card protectionSD card problemUnknown filesystem.Please unplug the device and insert the correct SD card.Use a different card or format the SD card to the FAT32 filesystem.Do you really want to format the SD card?Wrong SD card.Sending amountSending from multiple accounts.Including fee:Maximum feeReceiving to a multisig address.Confirm sendingJoint transactionReceiving toSendingSending amountSending toTo the total amount:Transaction IDYou are contributing: words in order.I wrote down all {0} BytesSigning addressConfirm messageMessage sizeVerify addressAssetPress both left and right at the same\ntime to confirm.Press and hold the right button to\napprove important operations.You're ready to\nuse Trezor.Press right to scroll down to read all content when text doesn't fit on one screen.\n\rPress left to scroll up.Are you sure you\nwant to skip the tutorial?HelloScreen scrollSkip tutorialTutorial completeUse Trezor by\nclicking the left and right buttons.\n\rContinue right.Welcome to Trezor. Press right to continue.All data will be erased.Wipe deviceDo you really want to wipe the device?\nChange wipe codeWipe code changed.The wipe code must be different from your PIN.Wipe code disabled.Wipe code enabled.New wipe codeWipe code can be used to erase all data from this device.Invalid wipe codeThe wipe codes you entered do not match.Re-enter wipe codePlease re-enter wipe code to confirm.Check wipe codeInvalid wipe codeWipe code settingsTurn off wipe code protection?Turn on wipe code protection?Wipe code mismatchNumber of wordsAccountAccount:AddressAmountAre you sure?Array ofBlockhashBuyingConfirmConfirm feeContainsContinue anyway?Continue withErrorFeefromKeep it safe!Continue only if you know what you are doing!My TrezorNooutputsPlease check againPlease try againDo you really want toRecipientSignSignerCheckGroupInformationRememberShareSharesSuccessSummaryThresholdUnknownWarningWritableYesJust a moment...Starting upVerifying PINWrong PINDo you want to create a {0} of {1} multi-share backup?Multi-share backupTap to confirmHold to confirmImportantI wrote down all {0} words in order.Create a backup to avoid losing access to your fundsLet's do a quick check of your backup.InstructionsNot recommended!Account infoIf receive address doesn't match, contact Trezor Support at trezor.io/support.Cancel receiveQR codeDerivation pathContinue in the appCancel and exitReceive address confirmedContinue without PINWithout a PIN, anyone can access this device.Cancel PIN setupCancel signSend fromHold to signFee rateincl. Transaction feeTotal amountAuto-lock turned onYour wallet backup contains multiple lists of words in a specific order (shares).Your wallet backup contains {0} words in a specific order.Wallet backup completedCreate wallet backupDisable haptic feedback?Enable haptic feedback?SettingHaptic feedbackContinue\nholdingEnter next shareHold to continueHold to exit tutorialLearn moreContinue with Share #{0}Start with share #1PassphraseWallet backup not on this deviceInvalid wallet backup enteredAll shares are valid and belong to the backup in this deviceEntered share is valid and belongs to the backup in the deviceVerify remaining recovery shares?Enter each word of your wallet backup in order.It's safe to disconnect your Trezor while recovering your wallet and continue later.Share doesn't matchCancel create walletIncorrect word selectedMore atHow many wallet backup shares do you want to create?Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.Select the minimum shares required to recover your wallet.Share #{0} completedNumber of shares: {0}Recovery threshold: {0}Transaction signedContinue tutorialExit tutorialFind context-specific actions and options in the menu.One more stepYou're all set to start using your device!Tap the lower half of the screen to continue, or swipe down to go back.Easy navigationWelcome to\nTrezor Safe 5Good to knowOperation cancelledSettingsTry again.Number of groups: {0}Display brightnessMulti-share backupCreate additional backup?Create backupChange wallpaper to default image?Words may repeat.Repeat for all shares.SettingsHomescreenThe word is repeatedLet's beginDid you know?The Trezor Model One, created in 2013,\nwas the world's first hardware wallet.Restart tutorialHandy menuHold to confirm important actionsWell done!Learn how to use and navigate this device with ease.Get started!Swipe horizontallyAdjustApplyDisplay brightness changedChange display brightnessDoneThe threshold sets the minimum number of shares needed to recover your wallet.If you set {0} out of {1} shares, you'll need {2} backup shares to recover your wallet.Continue with empty passphrase?Swipe downPublic key confirmedContinue anywayView all dataView all data in the menu.Enable labeling?ProviderConfirm without reviewTap to continueUnlockedTransaction feeUnlimitedChainTokenTapWrite down the first word from the backup.We don't recommend to skip wallet backup creation.Pay attentionCheck the address with source.ReceiveA recovery share is a list of words you wrote down when setting up your Trezor.Your wallet backup consists of 1 to 16 shares.Recovery shareAfter signing, send the transaction in the app.Sign cancelled.SendWalletAuthenticateSet the time before your Trezor locks automatically.day|daysTrezor will restart after update.Access hidden walletHidden walletShow passphraseRe-enter PINPIN setup completed.Start with Share #{0}Let's do a quick check of Share #{0}.Select word #{0} from\nShare #{1}Share #{0} from Group #{1} entered.Cancel transactionUsing different paths for different XPUBs.XPUBCancel?{0} addressViewSwapProvider addressRefund addressAssetsFinishUse menu to continueLast oneView more info, quit flow, ...Replay this tutorial anytime from the Trezor Suite app.Tap to start tutorialContinue with empty device name?Enter device nameNameDevice name changed.Firmware typeFirmware versionAboutConnectedDeviceDisconnectLEDManageOFFONReviewSecurityChange PIN?Remove PINPIN codeChange wipe code?Remove wipe codeWipe codeDisabledEnabledBluetoothWipe your Trezor and start the setup process again.SetWipeUnlockStart enteringDisconnectedConnectForgetPowerWipe code must be turned off before turning off PIN protection.Wipe code setPIN must be set before enabling wipe code.Cancel wipe code setupOpen Trezor Suite and create a wallet backup. This is the only way to recover access to your assets.Your Trezor is having trouble communicating with your connected device.Allow Trezor Suite to use Suite Sync with this Trezor?Allow {0} on {1} to use Suite Sync with this Trezor?Suite SyncNote",
                offsets: &[
                    (Self::addr_mismatch__contact_support_at, 32),
                    (Self::addr_mismatch__key_mismatch, 45),
                    (Self::addr_mismatch__mismatch, 62),
                    (Self::addr_mismatch__support_url, 79),
                    (Self::addr_mismatch__wrong_derivation_path, 122),
                    (Self::addr_mismatch__xpub_mismatch, 136),
                    (Self::address__public_key, 146),
                    (Self::address__title_cosigner, 154),
                    (Self::address__title_receive_address, 169),
                    (Self::address__title_yours, 174),
                    (Self::address_details__derivation_path_colon, 190),
                    (Self::address_details__title_receive_address, 205),
                    (Self::address_details__title_receiving_to, 217),
                    (Self::authenticate__confirm_template, 275),
                    (Self::authenticate__header, 294),
                    (Self::auto_lock__change_template, 335),
                    (Self::auto_lock__title, 350),
                    (Self::backup__can_back_up_anytime, 396),
                    (Self::backup__it_should_be_backed_up, 441),
                    (Self::backup__it_should_be_backed_up_now, 468),
                    (Self::backup__new_wallet_created, 484),
                    (Self::backup__new_wallet_successfully_created, 512),
                    (Self::backup__recover_anytime, 571),
                    (Self::backup__title_backup_wallet, 585),
                    (Self::backup__title_skip, 596),
                    (Self::backup__want_to_skip, 637),
                    (Self::bitcoin__commitment_data, 652),
                    (Self::bitcoin__confirm_locktime, 668),
                    (Self::bitcoin__create_proof_of_ownership, 711),
                    (Self::bitcoin__high_mining_fee_template, 754),
                    (Self::bitcoin__locktime_no_effect, 794),
                    (Self::bitcoin__locktime_set_to, 809),
                    (Self::bitcoin__locktime_set_to_blockheight, 836),
                    (Self::bitcoin__lot_of_change_outputs, 860),
                    (Self::bitcoin__multiple_accounts, 877),
                    (Self::bitcoin__new_fee_rate, 890),
                    (Self::bitcoin__simple_send_of, 904),
                    (Self::bitcoin__ticket_amount, 917),
                    (Self::bitcoin__title_confirm_details, 932),
                    (Self::bitcoin__title_finalize_transaction, 952),
                    (Self::bitcoin__title_high_mining_fee, 967),
                    (Self::bitcoin__title_meld_transaction, 983),
                    (Self::bitcoin__title_modify_amount, 996),
                    (Self::bitcoin__title_payjoin, 1003),
                    (Self::bitcoin__title_proof_of_ownership, 1021),
                    (Self::bitcoin__title_purchase_ticket, 1036),
                    (Self::bitcoin__title_update_transaction, 1054),
                    (Self::bitcoin__unknown_path, 1066),
                    (Self::bitcoin__unknown_transaction, 1085),
                    (Self::bitcoin__unusually_high_fee, 1104),
                    (Self::bitcoin__unverified_external_inputs, 1156),
                    (Self::bitcoin__valid_signature, 1179),
                    (Self::bitcoin__voting_rights, 1195),
                    (Self::buttons__abort, 1200),
                    (Self::buttons__access, 1206),
                    (Self::buttons__again, 1211),
                    (Self::buttons__allow, 1216),
                    (Self::buttons__back, 1220),
                    (Self::buttons__back_up, 1227),
                    (Self::buttons__cancel, 1233),
                    (Self::buttons__change, 1239),
                    (Self::buttons__check, 1244),
                    (Self::buttons__check_again, 1255),
                    (Self::buttons__close, 1260),
                    (Self::buttons__confirm, 1267),
                    (Self::buttons__continue, 1275),
                    (Self::buttons__details, 1282),
                    (Self::buttons__enable, 1288),
                    (Self::buttons__enter, 1293),
                    (Self::buttons__enter_share, 1304),
                    (Self::buttons__export, 1310),
                    (Self::buttons__format, 1316),
                    (Self::buttons__go_back, 1323),
                    (Self::buttons__hold_to_confirm, 1338),
                    (Self::buttons__info, 1342),
                    (Self::buttons__install, 1349),
                    (Self::buttons__more_info, 1358),
                    (Self::buttons__ok_i_understand, 1374),
                    (Self::buttons__purchase, 1382),
                    (Self::buttons__quit, 1386),
                    (Self::buttons__restart, 1393),
                    (Self::buttons__retry, 1398),
                    (Self::buttons__select, 1404),
                    (Self::buttons__set, 1407),
                    (Self::buttons__show_all, 1415),
                    (Self::buttons__show_details, 1427),
                    (Self::buttons__show_words, 1437),
                    (Self::buttons__skip, 1441),
                    (Self::buttons__try_again, 1450),
                    (Self::buttons__turn_off, 1458),
                    (Self::buttons__turn_on, 1465),
                    (Self::coinjoin__access_account, 1494),
                    (Self::coinjoin__do_not_disconnect, 1524),
                    (Self::coinjoin__max_mining_fee, 1538),
                    (Self::coinjoin__max_rounds, 1548),
                    (Self::coinjoin__title, 1566),
                    (Self::coinjoin__title_progress, 1586),
                    (Self::coinjoin__waiting_for_others, 1604),
                    (Self::confirm_total__fee_rate_colon, 1613),
                    (Self::confirm_total__sending_from_account, 1634),
                    (Self::confirm_total__title_fee, 1642),
                    (Self::confirm_total__title_sending_from, 1654),
                    (Self::device_name__change_template, 1680),
                    (Self::device_name__title, 1691),
                    (Self::entropy__send, 1726),
                    (Self::entropy__title_confirm, 1741),
                    (Self::send__sign_transaction, 1757),
                    (Self::experimental_mode__enable, 1786),
                    (Self::experimental_mode__only_for_dev, 1824),
                    (Self::experimental_mode__title, 1841),
                    (Self::firmware_update__title, 1856),
                    (Self::firmware_update__title_fingerprint, 1870),
                    (Self::homescreen__click_to_connect, 1886),
                    (Self::homescreen__click_to_unlock, 1901),
                    (Self::homescreen__title_backup_failed, 1914),
                    (Self::homescreen__title_backup_needed, 1927),
                    (Self::homescreen__title_coinjoin_authorized, 1946),
                    (Self::homescreen__title_experimental_mode, 1963),
                    (Self::homescreen__title_no_usb_connection, 1980),
                    (Self::homescreen__title_pin_not_set, 1991),
                    (Self::homescreen__title_seedless, 1999),
                    (Self::homescreen__title_set, 2015),
                    (Self::inputs__back, 2015),
                    (Self::inputs__cancel, 2015),
                    (Self::inputs__delete, 2015),
                    (Self::inputs__enter, 2015),
                    (Self::inputs__return, 2015),
                    (Self::inputs__show, 2015),
                    (Self::inputs__space, 2015),
                    (Self::joint__title, 2032),
                    (Self::joint__to_the_total_amount, 2052),
                    (Self::joint__you_are_contributing, 2073),
                    (Self::language__change_to_template, 2096),
                    (Self::language__changed, 2125),
                    (Self::language__progress, 2142),
                    (Self::language__title, 2159),
                    (Self::lockscreen__tap_to_connect, 2173),
                    (Self::lockscreen__tap_to_unlock, 2186),
                    (Self::lockscreen__title_locked, 2192),
                    (Self::lockscreen__title_not_connected, 2205),
                    (Self::misc__decrypt_value, 2218),
                    (Self::misc__encrypt_value, 2231),
                    (Self::misc__title_suite_labeling, 2245),
                    (Self::modify_amount__decrease_amount, 2264),
                    (Self::modify_amount__increase_amount, 2283),
                    (Self::modify_amount__new_amount, 2294),
                    (Self::modify_amount__title, 2307),
                    (Self::modify_fee__decrease_fee, 2323),
                    (Self::modify_fee__fee_rate, 2332),
                    (Self::modify_fee__increase_fee, 2348),
                    (Self::modify_fee__new_transaction_fee, 2368),
                    (Self::modify_fee__no_change, 2388),
                    (Self::modify_fee__title, 2398),
                    (Self::modify_fee__transaction_fee, 2414),
                    (Self::passphrase__access_wallet, 2439),
                    (Self::passphrase__always_on_device, 2478),
                    (Self::passphrase__from_host_not_shown, 2581),
                    (Self::passphrase__wallet, 2598),
                    (Self::passphrase__hide, 2630),
                    (Self::passphrase__next_screen_will_show_passphrase, 2668),
                    (Self::passphrase__please_enter, 2697),
                    (Self::passphrase__revoke_on_device, 2752),
                    (Self::passphrase__title_confirm, 2770),
                    (Self::passphrase__title_enter, 2786),
                    (Self::passphrase__title_hide, 2801),
                    (Self::passphrase__title_settings, 2820),
                    (Self::passphrase__title_source, 2837),
                    (Self::passphrase__turn_off, 2868),
                    (Self::passphrase__turn_on, 2898),
                    (Self::pin__change, 2908),
                    (Self::pin__changed, 2920),
                    (Self::pin__cursor_will_change, 2993),
                    (Self::pin__diff_from_wipe_code, 3043),
                    (Self::pin__disabled, 3069),
                    (Self::pin__enabled, 3094),
                    (Self::pin__enter, 3103),
                    (Self::pin__enter_new, 3116),
                    (Self::pin__entered_not_valid, 3154),
                    (Self::pin__info, 3197),
                    (Self::pin__invalid_pin, 3208),
                    (Self::pin__last_attempt, 3220),
                    (Self::pin__mismatch, 3246),
                    (Self::pin__pin_mismatch, 3258),
                    (Self::pin__please_check_again, 3277),
                    (Self::pin__reenter_new, 3293),
                    (Self::pin__reenter_to_confirm, 3324),
                    (Self::pin__should_be_long, 3355),
                    (Self::pin__title_check_pin, 3364),
                    (Self::pin__title_settings, 3376),
                    (Self::pin__title_wrong_pin, 3385),
                    (Self::pin__tries_left, 3395),
                    (Self::pin__turn_off, 3444),
                    (Self::pin__turn_on, 3467),
                    (Self::pin__wrong_pin, 3476),
                    (Self::plurals__contains_x_keys, 3484),
                    (Self::plurals__lock_after_x_hours, 3494),
                    (Self::plurals__lock_after_x_milliseconds, 3518),
                    (Self::plurals__lock_after_x_minutes, 3532),
                    (Self::plurals__lock_after_x_seconds, 3546),
                    (Self::plurals__sign_x_actions, 3560),
                    (Self::plurals__transaction_of_x_operations, 3580),
                    (Self::plurals__x_groups_needed, 3592),
                    (Self::plurals__x_shares_needed, 3604),
                    (Self::progress__authenticity_check, 3628),
                    (Self::progress__done, 3632),
                    (Self::progress__loading_transaction, 3654),
                    (Self::progress__locking_device, 3675),
                    (Self::progress__one_second_left, 3688),
                    (Self::progress__please_wait, 3699),
                    (Self::storage_msg__processing, 3709),
                    (Self::progress__refreshing, 3722),
                    (Self::progress__signing_transaction, 3744),
                    (Self::progress__syncing, 3754),
                    (Self::progress__x_seconds_left_template, 3770),
                    (Self::reboot_to_bootloader__restart, 3809),
                    (Self::reboot_to_bootloader__title, 3825),
                    (Self::reboot_to_bootloader__version_by_template, 3852),
                    (Self::recovery__cancel_dry_run, 3871),
                    (Self::recovery__check_dry_run, 3889),
                    (Self::recovery__cursor_will_change, 3962),
                    (Self::recovery__dry_run_bip39_valid_match, 4032),
                    (Self::recovery__dry_run_bip39_valid_mismatch, 4108),
                    (Self::recovery__dry_run_slip39_valid_match, 4188),
                    (Self::recovery__dry_run_slip39_valid_mismatch, 4264),
                    (Self::recovery__enter_any_share, 4279),
                    (Self::recovery__enter_backup, 4297),
                    (Self::recovery__enter_different_share, 4321),
                    (Self::recovery__enter_share_from_diff_group, 4356),
                    (Self::recovery__group_num_template, 4365),
                    (Self::recovery__group_threshold_reached, 4389),
                    (Self::recovery__invalid_wallet_backup_entered, 4419),
                    (Self::recovery__invalid_share_entered, 4450),
                    (Self::recovery__more_shares_needed, 4468),
                    (Self::recovery__num_of_words, 4510),
                    (Self::recovery__only_first_n_letters, 4572),
                    (Self::recovery__progress_will_be_lost, 4598),
                    (Self::recovery__share_already_entered, 4619),
                    (Self::recovery__share_from_another_multi_share_backup, 4668),
                    (Self::recovery__share_num_template, 4677),
                    (Self::recovery__title, 4691),
                    (Self::recovery__title_cancel_dry_run, 4710),
                    (Self::recovery__title_cancel_recovery, 4725),
                    (Self::recovery__title_dry_run, 4737),
                    (Self::recovery__title_recover, 4751),
                    (Self::recovery__title_remaining_shares, 4767),
                    (Self::recovery__type_word_x_of_y_template, 4787),
                    (Self::recovery__wallet_recovered, 4812),
                    (Self::recovery__wanna_cancel_dry_run, 4861),
                    (Self::recovery__wanna_cancel_recovery, 4914),
                    (Self::recovery__word_count_template, 4925),
                    (Self::recovery__word_x_of_y_template, 4940),
                    (Self::recovery__x_more_items_starting_template_plural, 4970),
                    (Self::recovery__x_more_shares_needed_template_plural, 4998),
                    (Self::recovery__x_of_y_entered_template, 5023),
                    (Self::recovery__you_have_entered, 5039),
                    (Self::reset__advanced_group_threshold_info, 5122),
                    (Self::reset__all_x_of_y_template, 5122),
                    (Self::reset__any_x_of_y_template, 5122),
                    (Self::reset__button_create, 5135),
                    (Self::reset__button_recover, 5149),
                    (Self::reset__by_continuing, 5214),
                    (Self::reset__check_backup_title, 5226),
                    (Self::reset__check_group_share_title_template, 5248),
                    (Self::reset__check_wallet_backup_title, 5267),
                    (Self::reset__check_share_title_template, 5283),
                    (Self::reset__continue_with_next_share, 5312),
                    (Self::reset__continue_with_share_template, 5337),
                    (Self::reset__finished_verifying_group_template, 5400),
                    (Self::reset__finished_verifying_wallet_backup, 5447),
                    (Self::reset__finished_verifying_shares, 5496),
                    (Self::reset__group_description, 5534),
                    (Self::reset__group_info, 5667),
                    (Self::reset__group_share_checked_successfully_template, 5710),
                    (Self::reset__group_share_title_template, 5731),
                    (Self::reset__more_info_at, 5743),
                    (Self::reset__need_all_share_template, 5743),
                    (Self::reset__need_any_share_template, 5743),
                    (Self::reset__needed_to_form_a_group, 5743),
                    (Self::reset__needed_to_recover_your_wallet, 5743),
                    (Self::reset__never_make_digital_copy, 5782),
                    (Self::reset__num_of_share_holders_template, 5831),
                    (Self::reset__num_of_shares_advanced_info_template, 5956),
                    (Self::reset__num_of_shares_basic_info_template, 5956),
                    (Self::reset__num_shares_for_group_template, 6004),
                    (Self::reset__number_of_shares_info, 6063),
                    (Self::reset__one_share, 6063),
                    (Self::reset__only_one_share_will_be_created, 6094),
                    (Self::reset__recovery_wallet_backup_title, 6107),
                    (Self::reset__recovery_share_title_template, 6126),
                    (Self::reset__required_number_of_groups, 6169),
                    (Self::reset__select_correct_word, 6211),
                    (Self::reset__select_word_template, 6226),
                    (Self::reset__select_word_x_of_y_template, 6249),
                    (Self::reset__set_it_to_count_template, 6249),
                    (Self::reset__share_checked_successfully_template, 6281),
                    (Self::reset__share_words_title, 6296),
                    (Self::reset__slip39_checklist_num_groups, 6312),
                    (Self::reset__slip39_checklist_num_shares, 6328),
                    (Self::reset__slip39_checklist_set_num_groups, 6348),
                    (Self::reset__slip39_checklist_set_num_shares, 6368),
                    (Self::reset__slip39_checklist_set_sizes, 6392),
                    (Self::reset__slip39_checklist_set_sizes_longer, 6429),
                    (Self::reset__slip39_checklist_set_threshold, 6442),
                    (Self::reset__slip39_checklist_title, 6458),
                    (Self::reset__slip39_checklist_write_down, 6489),
                    (Self::reset__slip39_checklist_write_down_recovery, 6532),
                    (Self::reset__the_threshold_sets_the_number_of_shares, 6532),
                    (Self::reset__threshold_info, 6588),
                    (Self::reset__title_backup_is_done, 6602),
                    (Self::reset__title_create_wallet, 6615),
                    (Self::reset__title_group_threshold, 6630),
                    (Self::reset__title_number_of_groups, 6646),
                    (Self::reset__title_number_of_shares, 6662),
                    (Self::reset__title_set_group_threshold, 6681),
                    (Self::reset__title_set_number_of_groups, 6701),
                    (Self::reset__title_set_number_of_shares, 6721),
                    (Self::reset__title_set_threshold, 6734),
                    (Self::reset__to_form_group_template, 6734),
                    (Self::reset__tos_link, 6747),
                    (Self::reset__total_number_of_shares_in_group_template, 6791),
                    (Self::reset__use_your_backup, 6844),
                    (Self::reset__write_down_words_template, 6910),
                    (Self::reset__wrong_word_selected, 6930),
                    (Self::reset__you_need_one_share, 6930),
                    (Self::reset__your_backup_is_done, 6950),
                    (Self::rotation__change_template, 6984),
                    (Self::rotation__east, 6988),
                    (Self::rotation__north, 6993),
                    (Self::rotation__south, 6998),
                    (Self::rotation__title_change, 7017),
                    (Self::rotation__west, 7021),
                    (Self::safety_checks__approve_unsafe_always, 7089),
                    (Self::safety_checks__approve_unsafe_temporary, 7169),
                    (Self::safety_checks__enforce_strict, 7234),
                    (Self::safety_checks__title, 7247),
                    (Self::safety_checks__title_safety_override, 7262),
                    (Self::sd_card__all_data_will_be_lost, 7299),
                    (Self::sd_card__card_required, 7316),
                    (Self::sd_card__disable, 7381),
                    (Self::sd_card__disabled, 7426),
                    (Self::sd_card__enable, 7491),
                    (Self::sd_card__enabled, 7535),
                    (Self::sd_card__error, 7548),
                    (Self::sd_card__format_card, 7562),
                    (Self::sd_card__insert_correct_card, 7612),
                    (Self::sd_card__please_insert, 7639),
                    (Self::sd_card__please_unplug_and_insert, 7688),
                    (Self::sd_card__problem_accessing, 7730),
                    (Self::sd_card__refresh, 7814),
                    (Self::sd_card__refreshed, 7860),
                    (Self::sd_card__restart, 7909),
                    (Self::sd_card__title, 7927),
                    (Self::sd_card__title_problem, 7942),
                    (Self::sd_card__unknown_filesystem, 7961),
                    (Self::sd_card__unplug_and_insert_correct, 8017),
                    (Self::sd_card__use_different_card, 8084),
                    (Self::sd_card__wanna_format, 8125),
                    (Self::sd_card__wrong_sd_card, 8139),
                    (Self::send__confirm_sending, 8153),
                    (Self::send__from_multiple_accounts, 8184),
                    (Self::send__including_fee, 8198),
                    (Self::send__maximum_fee, 8209),
                    (Self::send__receiving_to_multisig, 8241),
                    (Self::send__title_confirm_sending, 8256),
                    (Self::send__title_joint_transaction, 8273),
                    (Self::send__title_receiving_to, 8285),
                    (Self::send__title_sending, 8292),
                    (Self::send__title_sending_amount, 8306),
                    (Self::send__title_sending_to, 8316),
                    (Self::send__to_the_total_amount, 8336),
                    (Self::send__transaction_id, 8350),
                    (Self::send__you_are_contributing, 8371),
                    (Self::share_words__words_in_order, 8387),
                    (Self::share_words__wrote_down_all, 8404),
                    (Self::sign_message__bytes_template, 8413),
                    (Self::sign_message__confirm_address, 8428),
                    (Self::sign_message__confirm_message, 8443),
                    (Self::sign_message__message_size, 8455),
                    (Self::sign_message__verify_address, 8469),
                    (Self::words__asset, 8474),
                    (Self::tutorial__middle_click, 8528),
                    (Self::tutorial__press_and_hold, 8592),
                    (Self::tutorial__ready_to_use, 8619),
                    (Self::tutorial__scroll_down, 8728),
                    (Self::tutorial__sure_you_want_skip, 8771),
                    (Self::tutorial__title_hello, 8776),
                    (Self::tutorial__title_screen_scroll, 8789),
                    (Self::tutorial__title_skip, 8802),
                    (Self::tutorial__title_tutorial_complete, 8819),
                    (Self::tutorial__use_trezor, 8886),
                    (Self::tutorial__welcome_press_right, 8929),
                    (Self::wipe__info, 8953),
                    (Self::wipe__title, 8964),
                    (Self::wipe__want_to_wipe, 9003),
                    (Self::wipe_code__change, 9019),
                    (Self::wipe_code__changed, 9037),
                    (Self::wipe_code__diff_from_pin, 9083),
                    (Self::wipe_code__disabled, 9102),
                    (Self::wipe_code__enabled, 9120),
                    (Self::wipe_code__enter_new, 9133),
                    (Self::wipe_code__info, 9190),
                    (Self::wipe_code__invalid, 9207),
                    (Self::wipe_code__mismatch, 9247),
                    (Self::wipe_code__reenter, 9265),
                    (Self::wipe_code__reenter_to_confirm, 9302),
                    (Self::wipe_code__title_check, 9317),
                    (Self::wipe_code__title_invalid, 9334),
                    (Self::wipe_code__title_settings, 9352),
                    (Self::wipe_code__turn_off, 9382),
                    (Self::wipe_code__turn_on, 9411),
                    (Self::wipe_code__wipe_code_mismatch, 9429),
                    (Self::word_count__title, 9444),
                    (Self::words__account, 9451),
                    (Self::words__account_colon, 9459),
                    (Self::words__address, 9466),
                    (Self::words__amount, 9472),
                    (Self::words__are_you_sure, 9485),
                    (Self::words__array_of, 9493),
                    (Self::words__blockhash, 9502),
                    (Self::words__buying, 9508),
                    (Self::words__confirm, 9515),
                    (Self::words__confirm_fee, 9526),
                    (Self::words__contains, 9534),
                    (Self::words__continue_anyway_question, 9550),
                    (Self::words__continue_with, 9563),
                    (Self::words__error, 9568),
                    (Self::words__fee, 9571),
                    (Self::words__from, 9575),
                    (Self::words__keep_it_safe, 9588),
                    (Self::words__know_what_your_doing, 9633),
                    (Self::words__my_trezor, 9642),
                    (Self::words__no, 9644),
                    (Self::words__outputs, 9651),
                    (Self::words__please_check_again, 9669),
                    (Self::words__please_try_again, 9685),
                    (Self::words__really_wanna, 9706),
                    (Self::words__recipient, 9715),
                    (Self::words__sign, 9719),
                    (Self::words__signer, 9725),
                    (Self::words__title_check, 9730),
                    (Self::words__title_group, 9735),
                    (Self::words__title_information, 9746),
                    (Self::words__title_remember, 9754),
                    (Self::words__title_share, 9759),
                    (Self::words__title_shares, 9765),
                    (Self::words__title_success, 9772),
                    (Self::words__title_summary, 9779),
                    (Self::words__title_threshold, 9788),
                    (Self::words__unknown, 9795),
                    (Self::words__warning, 9802),
                    (Self::words__writable, 9810),
                    (Self::words__yes, 9813),
                    (Self::reboot_to_bootloader__just_a_moment, 9829),
                    (Self::inputs__previous, 9829),
                    (Self::storage_msg__starting, 9840),
                    (Self::storage_msg__verifying_pin, 9853),
                    (Self::storage_msg__wrong_pin, 9862),
                    (Self::reset__create_x_of_y_multi_share_backup_template, 9916),
                    (Self::reset__title_shamir_backup, 9934),
                    (Self::instructions__tap_to_confirm, 9948),
                    (Self::instructions__hold_to_confirm, 9963),
                    (Self::words__important, 9972),
                    (Self::reset__words_written_down_template, 10008),
                    (Self::backup__create_backup_to_prevent_loss, 10060),
                    (Self::reset__check_backup_instructions, 10098),
                    (Self::words__instructions, 10110),
                    (Self::words__not_recommended, 10126),
                    (Self::address_details__account_info, 10138),
                    (Self::address__cancel_contact_support, 10216),
                    (Self::address__cancel_receive, 10230),
                    (Self::address__qr_code, 10237),
                    (Self::address_details__derivation_path, 10252),
                    (Self::instructions__continue_in_app, 10271),
                    (Self::words__cancel_and_exit, 10286),
                    (Self::address__confirmed, 10311),
                    (Self::pin__cancel_description, 10331),
                    (Self::pin__cancel_info, 10376),
                    (Self::pin__cancel_setup, 10392),
                    (Self::send__cancel_sign, 10403),
                    (Self::send__send_from, 10412),
                    (Self::instructions__hold_to_sign, 10424),
                    (Self::confirm_total__fee_rate, 10432),
                    (Self::send__incl_transaction_fee, 10453),
                    (Self::send__total_amount, 10465),
                    (Self::auto_lock__turned_on, 10484),
                    (Self::backup__info_multi_share_backup, 10565),
                    (Self::backup__info_single_share_backup, 10623),
                    (Self::backup__title_backup_completed, 10646),
                    (Self::backup__title_create_wallet_backup, 10666),
                    (Self::haptic_feedback__disable, 10690),
                    (Self::haptic_feedback__enable, 10713),
                    (Self::haptic_feedback__subtitle, 10720),
                    (Self::haptic_feedback__title, 10735),
                    (Self::instructions__continue_holding, 10751),
                    (Self::instructions__enter_next_share, 10767),
                    (Self::instructions__hold_to_continue, 10783),
                    (Self::instructions__hold_to_exit_tutorial, 10804),
                    (Self::instructions__learn_more, 10814),
                    (Self::instructions__shares_continue_with_x_template, 10838),
                    (Self::instructions__shares_start_with_1, 10857),
                    (Self::passphrase__title_passphrase, 10867),
                    (Self::recovery__dry_run_backup_not_on_this_device, 10899),
                    (Self::recovery__dry_run_invalid_backup_entered, 10928),
                    (Self::recovery__dry_run_slip39_valid_all_shares, 10988),
                    (Self::recovery__dry_run_slip39_valid_share, 11050),
                    (Self::recovery__dry_run_verify_remaining_shares, 11083),
                    (Self::recovery__enter_each_word, 11130),
                    (Self::recovery__info_about_disconnect, 11214),
                    (Self::recovery__share_does_not_match, 11233),
                    (Self::reset__cancel_create_wallet, 11253),
                    (Self::reset__incorrect_word_selected, 11276),
                    (Self::reset__more_at, 11283),
                    (Self::reset__num_of_shares_how_many, 11335),
                    (Self::reset__num_of_shares_long_info_template, 11506),
                    (Self::reset__select_threshold, 11564),
                    (Self::reset__share_completed_template, 11584),
                    (Self::reset__slip39_checklist_num_shares_x_template, 11605),
                    (Self::reset__slip39_checklist_threshold_x_template, 11628),
                    (Self::send__transaction_signed, 11646),
                    (Self::tutorial__continue, 11663),
                    (Self::tutorial__exit, 11676),
                    (Self::tutorial__menu, 11730),
                    (Self::tutorial__one_more_step, 11743),
                    (Self::tutorial__ready_to_use_safe5, 11785),
                    (Self::tutorial__swipe_up_and_down, 11856),
                    (Self::tutorial__title_easy_navigation, 11871),
                    (Self::tutorial__welcome_safe5, 11895),
                    (Self::words__good_to_know, 11907),
                    (Self::words__operation_cancelled, 11926),
                    (Self::words__settings, 11934),
                    (Self::words__try_again, 11944),
                    (Self::reset__slip39_checklist_num_groups_x_template, 11965),
                    (Self::brightness__title, 11983),
                    (Self::recovery__title_unlock_repeated_backup, 12001),
                    (Self::recovery__unlock_repeated_backup, 12026),
                    (Self::recovery__unlock_repeated_backup_verb, 12039),
                    (Self::homescreen__set_default, 12073),
                    (Self::reset__words_may_repeat, 12090),
                    (Self::reset__repeat_for_all_shares, 12112),
                    (Self::homescreen__settings_subtitle, 12120),
                    (Self::homescreen__settings_title, 12130),
                    (Self::reset__the_word_is_repeated, 12150),
                    (Self::tutorial__title_lets_begin, 12161),
                    (Self::tutorial__did_you_know, 12174),
                    (Self::tutorial__first_wallet, 12251),
                    (Self::tutorial__restart_tutorial, 12267),
                    (Self::tutorial__title_handy_menu, 12277),
                    (Self::tutorial__title_hold, 12310),
                    (Self::tutorial__title_well_done, 12320),
                    (Self::tutorial__lets_begin, 12372),
                    (Self::tutorial__get_started, 12384),
                    (Self::instructions__swipe_horizontally, 12402),
                    (Self::setting__adjust, 12408),
                    (Self::setting__apply, 12413),
                    (Self::brightness__changed_title, 12439),
                    (Self::brightness__change_title, 12464),
                    (Self::words__title_done, 12468),
                    (Self::reset__slip39_checklist_more_info_threshold, 12546),
                    (Self::reset__slip39_checklist_more_info_threshold_example_template, 12633),
                    (Self::passphrase__continue_with_empty_passphrase, 12664),
                    (Self::instructions__swipe_down, 12674),
                    (Self::address__public_key_confirmed, 12694),
                    (Self::words__continue_anyway, 12709),
                    (Self::buttons__view_all_data, 12722),
                    (Self::instructions__view_all_data, 12748),
                    (Self::misc__enable_labeling, 12764),
                    (Self::words__provider, 12772),
                    (Self::sign_message__confirm_without_review, 12794),
                    (Self::instructions__tap_to_continue, 12809),
                    (Self::ble__unpair_all, 12809),
                    (Self::ble__unpair_current, 12809),
                    (Self::ble__unpair_title, 12809),
                    (Self::words__unlocked, 12817),
                    (Self::words__transaction_fee, 12832),
                    (Self::words__unlimited, 12841),
                    (Self::words__chain, 12846),
                    (Self::words__token, 12851),
                    (Self::instructions__tap, 12854),
                    (Self::reset__share_words_first, 12896),
                    (Self::backup__not_recommend, 12946),
                    (Self::words__pay_attention, 12959),
                    (Self::address__check_with_source, 12989),
                    (Self::words__receive, 12996),
                    (Self::reset__recovery_share_description, 13075),
                    (Self::reset__recovery_share_number, 13121),
                    (Self::words__recovery_share, 13135),
                    (Self::send__send_in_the_app, 13182),
                    (Self::send__sign_cancelled, 13197),
                    (Self::words__send, 13201),
                    (Self::words__wallet, 13207),
                    (Self::words__authenticate, 13219),
                    (Self::auto_lock__description, 13271),
                    (Self::plurals__lock_after_x_days, 13279),
                    (Self::firmware_update__restart, 13312),
                    (Self::passphrase__access_hidden_wallet, 13332),
                    (Self::passphrase__hidden_wallet, 13345),
                    (Self::passphrase__show, 13360),
                    (Self::pin__reenter, 13372),
                    (Self::pin__setup_completed, 13392),
                    (Self::instructions__shares_start_with_x_template, 13413),
                    (Self::reset__check_share_backup_template, 13450),
                    (Self::reset__select_word_from_share_template, 13482),
                    (Self::recovery__share_from_group_entered_template, 13517),
                    (Self::send__cancel_transaction, 13535),
                    (Self::send__multisig_different_paths, 13577),
                    (Self::address__xpub, 13581),
                    (Self::words__cancel_question, 13588),
                    (Self::address__coin_address_template, 13599),
                    (Self::buttons__view, 13603),
                    (Self::words__swap, 13607),
                    (Self::address__title_provider_address, 13623),
                    (Self::address__title_refund_address, 13637),
                    (Self::words__assets, 13643),
                    (Self::buttons__finish, 13649),
                    (Self::instructions__menu_to_continue, 13669),
                    (Self::tutorial__last_one, 13677),
                    (Self::tutorial__menu_appendix, 13707),
                    (Self::tutorial__navigation_ts7, 13707),
                    (Self::tutorial__suite_restart, 13762),
                    (Self::tutorial__welcome_safe7, 13762),
                    (Self::tutorial__what_is_tropic, 13762),
                    (Self::tutorial__tap_to_start, 13783),
                    (Self::tutorial__tropic_info, 13783),
                    (Self::device_name__continue_with_empty_label, 13815),
                    (Self::device_name__enter, 13832),
                    (Self::regulatory__title, 13832),
                    (Self::words__name, 13836),
                    (Self::device_name__changed, 13856),
                    (Self::ble__manage_paired, 13856),
                    (Self::ble__pair_new, 13856),
                    (Self::ble__pair_title, 13856),
                    (Self::ble__version, 13856),
                    (Self::homescreen__firmware_type, 13869),
                    (Self::homescreen__firmware_version, 13885),
                    (Self::led__disable, 13885),
                    (Self::led__enable, 13885),
                    (Self::led__title, 13885),
                    (Self::words__about, 13890),
                    (Self::words__connected, 13899),
                    (Self::words__device, 13905),
                    (Self::words__disconnect, 13915),
                    (Self::words__led, 13918),
                    (Self::words__manage, 13924),
                    (Self::words__off, 13927),
                    (Self::words__on, 13929),
                    (Self::words__review, 13935),
                    (Self::words__security, 13943),
                    (Self::pin__change_question, 13954),
                    (Self::pin__remove, 13964),
                    (Self::pin__title, 13972),
                    (Self::wipe_code__change_question, 13989),
                    (Self::wipe_code__remove, 14005),
                    (Self::wipe_code__title, 14014),
                    (Self::words__disabled, 14022),
                    (Self::words__enabled, 14029),
                    (Self::ble__disable, 14029),
                    (Self::ble__enable, 14029),
                    (Self::words__bluetooth, 14038),
                    (Self::wipe__start_again, 14089),
                    (Self::words__set, 14092),
                    (Self::words__wipe, 14096),
                    (Self::lockscreen__unlock, 14102),
                    (Self::recovery__start_entering, 14116),
                    (Self::words__disconnected, 14128),
                    (Self::ble__forget_all, 14128),
                    (Self::words__connect, 14135),
                    (Self::words__forget, 14141),
                    (Self::words__power, 14146),
                    (Self::ble__limit_reached, 14146),
                    (Self::ble__forget_all_description, 14146),
                    (Self::ble__forget_all_devices, 14146),
                    (Self::ble__forget_all_success, 14146),
                    (Self::ble__forget_this_description, 14146),
                    (Self::ble__forget_this_device, 14146),
                    (Self::ble__forget_this_success, 14146),
                    (Self::thp__autoconnect, 14146),
                    (Self::thp__autoconnect_app, 14146),
                    (Self::thp__connect, 14146),
                    (Self::thp__connect_app, 14146),
                    (Self::thp__pair, 14146),
                    (Self::thp__pair_app, 14146),
                    (Self::thp__autoconnect_title, 14146),
                    (Self::thp__code_entry, 14146),
                    (Self::thp__code_title, 14146),
                    (Self::thp__connect_title, 14146),
                    (Self::thp__nfc_text, 14146),
                    (Self::thp__pair_title, 14146),
                    (Self::thp__qr_title, 14146),
                    (Self::ble__pairing_match, 14146),
                    (Self::ble__pairing_title, 14146),
                    (Self::thp__pair_name, 14146),
                    (Self::thp__pair_new_device, 14146),
                    (Self::tutorial__power, 14146),
                    (Self::auto_lock__on_battery, 14146),
                    (Self::auto_lock__on_usb, 14146),
                    (Self::pin__wipe_code_exists_description, 14209),
                    (Self::pin__wipe_code_exists_title, 14222),
                    (Self::wipe_code__pin_not_set_description, 14264),
                    (Self::wipe_code__cancel_setup, 14286),
                    (Self::homescreen__backup_needed_info, 14386),
                    (Self::ble__host_info, 14386),
                    (Self::ble__mac_address, 14386),
                    (Self::ble__waiting_for_host, 14386),
                    (Self::ble__apps_connected, 14386),
                    (Self::sn__action, 14386),
                    (Self::sn__title, 14386),
                    (Self::ble__must_be_enabled, 14386),
                    (Self::words__comm_trouble, 14457),
                    (Self::secure_sync__delegated_identity_key_no_thp, 14511),
                    (Self::secure_sync__delegated_identity_key_thp, 14563),
                    (Self::secure_sync__header, 14573),
                    (Self::words__note, 14577),
                ],
            };

            #[cfg(feature = "universal_fw")]
            const ALTCOIN_BLOB: StringsBlob = StringsBlob {
                text: "BaseEnterpriseLegacyPointerRewardaddress - no staking rewards.Amount burned (decimals unknown):Amount minted (decimals unknown):Amount sent (decimals unknown):Pool has no metadata (anonymous pool)Asset fingerprint:Auxiliary data hash:BlockCatalystCertificateChange outputCheck all items carefully.Choose level of details:Collateral input ID:Collateral input index:The collateral return output contains tokens.Collateral returnConfirm signing the stake pool registration as an owner.Confirm transactionConfirming a multisig transaction.Confirming a Plutus transaction.Confirming pool registration as owner.Confirming a transaction.CostCredential doesn't match payment credential.Datum hash:Delegating to:for account {0} and index {1}:for account {0}:for key hash:for script:Inline datumInput ID:Input index:The following address is a change address. ItsThe following address is owned by this device. ItsThe vote key registration payment address is owned by this device. Itskey hashMarginmulti-sig pathContains {0} nested scripts.Network:Transaction has no outputs, network cannot be verified.Nonce:otherpathPledgepointerPolicy IDPool metadata hash:Pool metadata url:Pool owner:Pool reward account:Reference input ID:Reference input index:Reference scriptRequired signerrewardAddress is a reward address.Warning: The address is not a payment address, it is not eligible for rewards.Rewards go to:scriptAllAnyScript data hash:Script hash:Invalid beforeInvalid hereafterKeyN of Kscript rewardSendingShow SimpleSign transaction with {0}Stake delegationStake key deregistrationStakepool registrationStake pool registration\nPool ID:Stake key registrationStaking key for accountto pool:token minting pathTotal collateral:TransactionThe transaction contains minting or burning of tokens.The following transaction output contains a script address, but does not contain a datum.Transaction ID:The transaction contains no collateral inputs. Plutus script will not be able to run.The transaction contains no script data hash. Plutus script will not be able to run.The following transaction output contains tokens.TTL:Unknown collateral amount.Path is unusual.Valid since:Verify scriptVote key registration (CIP-36)Vote public key:Voting purpose:WarningWeight:Confirm withdrawal for {0} address:Requires {0} out of {1} signatures.Amount sent:Size: {0} bytesGas limitGas priceMax fee per gasName and versionNew contract will be deployedNo message fieldMax priority feeShow full arrayShow full domainShow full messageShow full structReally sign EIP-712 typed data?Input dataConfirm domainConfirm messageConfirm structConfirm typed dataSigning address{0} unitsUnknown tokenThe signature is valid.Already registeredThis device is already registered with this application.This device is already registered with {0}.This device is not registered with this application.The credential you are trying to import does\nnot belong to this authenticator.erase all credentials?Export information about the credentials stored on this device?Not registeredThis device is not registered with\n{0}.Please enable PIN protection.FIDO2 authenticateImport credentialList credentialsFIDO2 registerRemove credentialFIDO2 resetU2F authenticateU2F registerFIDO2 verify userUnable to verify user.Do you really want to erase all credentials?Confirm exportConfirm ki syncConfirm refreshConfirm unlock timeHashing inputsPayment IDPostprocessing...Processing...Processing inputsProcessing outputsSigning...Signing inputsUnlock time for this transaction is set to {0}Do you really want to export tx_der\nfor tx_proof?Do you really want to export tx_key?Do you really want to export watch-only credentials?Do you really want to\nstart refresh?Do you really want to\nsync key images?Confirm tagDestination tag:\n{0}Account indexAssociated token accountConfirm multisigExpected feeInstruction contains {0} accounts and its data is {1} bytes long.Instruction dataThe following instruction is a multisig instruction.{0} is provided via a lookup table.Lookup table addressMultiple signersTransaction contains unknown instructions.Transaction requires {0} signers which increases the fee.Account MergeAccount ThresholdsAdd SignerAdd trustAll XLM will be sent toAllow trustBalance IDBump SequenceBuying:Claim Claimable BalanceClear dataClear flagsConfirm IssuerConfirm memoConfirm operationConfirm timeboundsCreate AccountDebited amountDeleteDelete Passive OfferDelete trustDestinationMemo is not set.\nTypically needed when sending to exchanges.Final confirmHashHigh:Home DomainInflation{0} issuerKey:LimitLow:Master Weight:Medium:New OfferNew Passive OfferNo memo set![no restriction]Path PayPath Pay at leastPayPay at mostPre-auth transactionPrice per {0}:Remove SignerRevoke trustSelling:Set dataSet flagsSet sequence to {0}?Sign this transaction made up of {0}and pay {0}\nfor fee?Source accountTrusted AccountUpdateValid from (UTC)Valid to (UTC)Value (SHA-256):Do you want to clear value key {0}?Baker addressBalance:Ballot:Confirm delegationConfirm originationDelegatorProposalRegister delegateRemove delegationSubmit ballotSubmit proposalSubmit proposalsIncrease and retrieve the U2F counter?Set the U2F counter to {0}?Get U2F counterSet U2F counterClaimClaim addressClaim ETH from Everstake?StakeStake addressStake ETH on Everstake?UnstakeUnstake ETH from Everstake?Always AbstainAlways No ConfidenceDelegating to key hash:Delegating to script:Deposit:Vote delegationMore credentialsSelect the credential that you would like to use for authentication.for authenticationSelect credentialCredential detailsUnknown contract addressToken contractInteraction contractBase feeClaimClaim SOL from stake account?Claiming SOL to address outside your current wallet.Priority feeStakeStake accountStake SOL?The current wallet isn't the SOL staking withdraw authority.Withdraw authority addressUnstakeUnstake SOL from stake account?Vote accountStake SOL on {0}?Event kind: {0}Max fees and rentMax rent feeApproveAmount allowanceChain IDReview details to approve token spending.Token approvalApprove toApproving unlimited amount of {0}Review details to revoke token approval.Token revocationRevokeRevoke fromUnknown tokenUnknown token addressAll input data ({0} bytes)Provider contract addressConfirm message hashSign withTimeboundsToken infoTransaction sourceTransaction source does not belong to this Trezor.Confirm messageEmpty messageMessage hash:Message hexMessage textSign message hash with {0}Sign message with {0}Destination tag is not set. Typically needed when sending to exchanges.",
                offsets: &[
                    (Self::cardano__addr_base, 4),
                    (Self::cardano__addr_enterprise, 14),
                    (Self::cardano__addr_legacy, 20),
                    (Self::cardano__addr_pointer, 27),
                    (Self::cardano__addr_reward, 33),
                    (Self::cardano__address_no_staking, 62),
                    (Self::cardano__amount_burned_decimals_unknown, 95),
                    (Self::cardano__amount_minted_decimals_unknown, 128),
                    (Self::cardano__amount_sent_decimals_unknown, 159),
                    (Self::cardano__anonymous_pool, 196),
                    (Self::cardano__asset_fingerprint, 214),
                    (Self::cardano__auxiliary_data_hash, 234),
                    (Self::cardano__block, 239),
                    (Self::cardano__catalyst, 247),
                    (Self::cardano__certificate, 258),
                    (Self::cardano__change_output, 271),
                    (Self::cardano__check_all_items, 297),
                    (Self::cardano__choose_level_of_details, 321),
                    (Self::cardano__collateral_input_id, 341),
                    (Self::cardano__collateral_input_index, 364),
                    (Self::cardano__collateral_output_contains_tokens, 409),
                    (Self::cardano__collateral_return, 426),
                    (Self::cardano__confirm_signing_stake_pool, 482),
                    (Self::cardano__confirm_transaction, 501),
                    (Self::cardano__confirming_a_multisig_transaction, 535),
                    (Self::cardano__confirming_a_plutus_transaction, 567),
                    (Self::cardano__confirming_pool_registration, 605),
                    (Self::cardano__confirming_transaction, 630),
                    (Self::cardano__cost, 634),
                    (Self::cardano__credential_mismatch, 678),
                    (Self::cardano__datum_hash, 689),
                    (Self::cardano__delegating_to, 703),
                    (Self::cardano__for_account_and_index_template, 733),
                    (Self::cardano__for_account_template, 749),
                    (Self::cardano__for_key_hash, 762),
                    (Self::cardano__for_script, 773),
                    (Self::cardano__inline_datum, 785),
                    (Self::cardano__input_id, 794),
                    (Self::cardano__input_index, 806),
                    (Self::cardano__intro_text_change, 852),
                    (Self::cardano__intro_text_owned_by_device, 902),
                    (Self::cardano__intro_text_registration_payment, 972),
                    (Self::cardano__key_hash, 980),
                    (Self::cardano__margin, 986),
                    (Self::cardano__multisig_path, 1000),
                    (Self::cardano__nested_scripts_template, 1028),
                    (Self::cardano__network, 1036),
                    (Self::cardano__no_output_tx, 1091),
                    (Self::cardano__nonce, 1097),
                    (Self::cardano__other, 1102),
                    (Self::cardano__path, 1106),
                    (Self::cardano__pledge, 1112),
                    (Self::cardano__pointer, 1119),
                    (Self::cardano__policy_id, 1128),
                    (Self::cardano__pool_metadata_hash, 1147),
                    (Self::cardano__pool_metadata_url, 1165),
                    (Self::cardano__pool_owner, 1176),
                    (Self::cardano__pool_reward_account, 1196),
                    (Self::cardano__reference_input_id, 1215),
                    (Self::cardano__reference_input_index, 1237),
                    (Self::cardano__reference_script, 1253),
                    (Self::cardano__required_signer, 1268),
                    (Self::cardano__reward, 1274),
                    (Self::cardano__reward_address, 1302),
                    (Self::cardano__reward_eligibility_warning, 1380),
                    (Self::cardano__rewards_go_to, 1394),
                    (Self::cardano__script, 1400),
                    (Self::cardano__script_all, 1403),
                    (Self::cardano__script_any, 1406),
                    (Self::cardano__script_data_hash, 1423),
                    (Self::cardano__script_hash, 1435),
                    (Self::cardano__script_invalid_before, 1449),
                    (Self::cardano__script_invalid_hereafter, 1466),
                    (Self::cardano__script_key, 1469),
                    (Self::cardano__script_n_of_k, 1475),
                    (Self::cardano__script_reward, 1488),
                    (Self::cardano__sending, 1495),
                    (Self::cardano__show_simple, 1506),
                    (Self::cardano__sign_tx_path_template, 1531),
                    (Self::cardano__stake_delegation, 1547),
                    (Self::cardano__stake_deregistration, 1571),
                    (Self::cardano__stake_pool_registration, 1593),
                    (Self::cardano__stake_pool_registration_pool_id, 1625),
                    (Self::cardano__stake_registration, 1647),
                    (Self::cardano__staking_key_for_account, 1670),
                    (Self::cardano__to_pool, 1678),
                    (Self::cardano__token_minting_path, 1696),
                    (Self::cardano__total_collateral, 1713),
                    (Self::cardano__transaction, 1724),
                    (Self::cardano__transaction_contains_minting_or_burning, 1778),
                    (Self::cardano__transaction_contains_script_address_no_datum, 1867),
                    (Self::cardano__transaction_id, 1882),
                    (Self::cardano__transaction_no_collateral_input, 1967),
                    (Self::cardano__transaction_no_script_data_hash, 2051),
                    (Self::cardano__transaction_output_contains_tokens, 2100),
                    (Self::cardano__ttl, 2104),
                    (Self::cardano__unknown_collateral_amount, 2130),
                    (Self::cardano__unusual_path, 2146),
                    (Self::cardano__valid_since, 2158),
                    (Self::cardano__verify_script, 2171),
                    (Self::cardano__vote_key_registration, 2201),
                    (Self::cardano__vote_public_key, 2217),
                    (Self::cardano__voting_purpose, 2232),
                    (Self::cardano__warning, 2239),
                    (Self::cardano__weight, 2246),
                    (Self::cardano__withdrawal_for_address_template, 2281),
                    (Self::cardano__x_of_y_signatures_template, 2316),
                    (Self::eos__about_to_sign_template, 2316),
                    (Self::eos__action_name, 2316),
                    (Self::eos__arbitrary_data, 2316),
                    (Self::eos__buy_ram, 2316),
                    (Self::eos__bytes, 2316),
                    (Self::eos__cancel_vote, 2316),
                    (Self::eos__checksum, 2316),
                    (Self::eos__code, 2316),
                    (Self::eos__contract, 2316),
                    (Self::eos__cpu, 2316),
                    (Self::eos__creator, 2316),
                    (Self::eos__delegate, 2316),
                    (Self::eos__delete_auth, 2316),
                    (Self::eos__from, 2316),
                    (Self::eos__link_auth, 2316),
                    (Self::eos__memo, 2316),
                    (Self::eos__name, 2316),
                    (Self::eos__net, 2316),
                    (Self::eos__new_account, 2316),
                    (Self::eos__owner, 2316),
                    (Self::eos__parent, 2316),
                    (Self::eos__payer, 2316),
                    (Self::eos__permission, 2316),
                    (Self::eos__proxy, 2316),
                    (Self::eos__receiver, 2316),
                    (Self::eos__refund, 2316),
                    (Self::eos__requirement, 2316),
                    (Self::eos__sell_ram, 2316),
                    (Self::eos__sender, 2316),
                    (Self::eos__threshold, 2316),
                    (Self::eos__to, 2316),
                    (Self::eos__transfer, 2316),
                    (Self::eos__type, 2316),
                    (Self::eos__undelegate, 2316),
                    (Self::eos__unlink_auth, 2316),
                    (Self::eos__update_auth, 2316),
                    (Self::eos__vote_for_producers, 2316),
                    (Self::eos__vote_for_proxy, 2316),
                    (Self::eos__voter, 2316),
                    (Self::ethereum__amount_sent, 2328),
                    (Self::ethereum__data_size_template, 2343),
                    (Self::ethereum__gas_limit, 2352),
                    (Self::ethereum__gas_price, 2361),
                    (Self::ethereum__max_gas_price, 2376),
                    (Self::ethereum__name_and_version, 2392),
                    (Self::ethereum__new_contract, 2421),
                    (Self::ethereum__no_message_field, 2437),
                    (Self::ethereum__priority_fee, 2453),
                    (Self::ethereum__show_full_array, 2468),
                    (Self::ethereum__show_full_domain, 2484),
                    (Self::ethereum__show_full_message, 2501),
                    (Self::ethereum__show_full_struct, 2517),
                    (Self::ethereum__sign_eip712, 2548),
                    (Self::ethereum__title_input_data, 2558),
                    (Self::ethereum__title_confirm_domain, 2572),
                    (Self::ethereum__title_confirm_message, 2587),
                    (Self::ethereum__title_confirm_struct, 2601),
                    (Self::ethereum__title_confirm_typed_data, 2619),
                    (Self::ethereum__title_signing_address, 2634),
                    (Self::ethereum__units_template, 2643),
                    (Self::ethereum__unknown_token, 2656),
                    (Self::ethereum__valid_signature, 2679),
                    (Self::fido__already_registered, 2697),
                    (Self::fido__device_already_registered, 2753),
                    (Self::fido__device_already_registered_with_template, 2796),
                    (Self::fido__device_not_registered, 2848),
                    (Self::fido__does_not_belong, 2926),
                    (Self::fido__erase_credentials, 2948),
                    (Self::fido__export_credentials, 3011),
                    (Self::fido__not_registered, 3025),
                    (Self::fido__not_registered_with_template, 3064),
                    (Self::fido__please_enable_pin_protection, 3093),
                    (Self::fido__title_authenticate, 3111),
                    (Self::fido__title_import_credential, 3128),
                    (Self::fido__title_list_credentials, 3144),
                    (Self::fido__title_register, 3158),
                    (Self::fido__title_remove_credential, 3175),
                    (Self::fido__title_reset, 3186),
                    (Self::fido__title_u2f_auth, 3202),
                    (Self::fido__title_u2f_register, 3214),
                    (Self::fido__title_verify_user, 3231),
                    (Self::fido__unable_to_verify_user, 3253),
                    (Self::fido__wanna_erase_credentials, 3297),
                    (Self::monero__confirm_export, 3311),
                    (Self::monero__confirm_ki_sync, 3326),
                    (Self::monero__confirm_refresh, 3341),
                    (Self::monero__confirm_unlock_time, 3360),
                    (Self::monero__hashing_inputs, 3374),
                    (Self::monero__payment_id, 3384),
                    (Self::monero__postprocessing, 3401),
                    (Self::monero__processing, 3414),
                    (Self::monero__processing_inputs, 3431),
                    (Self::monero__processing_outputs, 3449),
                    (Self::monero__signing, 3459),
                    (Self::monero__signing_inputs, 3473),
                    (Self::monero__unlock_time_set_template, 3519),
                    (Self::monero__wanna_export_tx_der, 3568),
                    (Self::monero__wanna_export_tx_key, 3604),
                    (Self::monero__wanna_export_watchkey, 3656),
                    (Self::monero__wanna_start_refresh, 3692),
                    (Self::monero__wanna_sync_key_images, 3730),
                    (Self::nem__absolute, 3730),
                    (Self::nem__activate, 3730),
                    (Self::nem__add, 3730),
                    (Self::nem__confirm_action, 3730),
                    (Self::nem__confirm_address, 3730),
                    (Self::nem__confirm_creation_fee, 3730),
                    (Self::nem__confirm_mosaic, 3730),
                    (Self::nem__confirm_multisig_fee, 3730),
                    (Self::nem__confirm_namespace, 3730),
                    (Self::nem__confirm_payload, 3730),
                    (Self::nem__confirm_properties, 3730),
                    (Self::nem__confirm_rental_fee, 3730),
                    (Self::nem__confirm_transfer_of, 3730),
                    (Self::nem__convert_account_to_multisig, 3730),
                    (Self::nem__cosign_transaction_for, 3730),
                    (Self::nem__cosignatory, 3730),
                    (Self::nem__create_mosaic, 3730),
                    (Self::nem__create_namespace, 3730),
                    (Self::nem__deactivate, 3730),
                    (Self::nem__decrease, 3730),
                    (Self::nem__description, 3730),
                    (Self::nem__divisibility_and_levy_cannot_be_shown, 3730),
                    (Self::nem__encrypted, 3730),
                    (Self::nem__final_confirm, 3730),
                    (Self::nem__immutable, 3730),
                    (Self::nem__increase, 3730),
                    (Self::nem__initial_supply, 3730),
                    (Self::nem__initiate_transaction_for, 3730),
                    (Self::nem__levy_divisibility, 3730),
                    (Self::nem__levy_fee, 3730),
                    (Self::nem__levy_fee_of, 3730),
                    (Self::nem__levy_mosaic, 3730),
                    (Self::nem__levy_namespace, 3730),
                    (Self::nem__levy_recipient, 3730),
                    (Self::nem__levy_type, 3730),
                    (Self::nem__modify_supply_for, 3730),
                    (Self::nem__modify_the_number_of_cosignatories_by, 3730),
                    (Self::nem__mutable, 3730),
                    (Self::nem__of, 3730),
                    (Self::nem__percentile, 3730),
                    (Self::nem__raw_units_template, 3730),
                    (Self::nem__remote_harvesting, 3730),
                    (Self::nem__remove, 3730),
                    (Self::nem__set_minimum_cosignatories_to, 3730),
                    (Self::nem__sign_tx_fee_template, 3730),
                    (Self::nem__supply_change, 3730),
                    (Self::nem__supply_units_template, 3730),
                    (Self::nem__transferable, 3730),
                    (Self::nem__under_namespace, 3730),
                    (Self::nem__unencrypted, 3730),
                    (Self::nem__unknown_mosaic, 3730),
                    (Self::ripple__confirm_tag, 3741),
                    (Self::ripple__destination_tag_template, 3761),
                    (Self::solana__account_index, 3774),
                    (Self::solana__associated_token_account, 3798),
                    (Self::solana__confirm_multisig, 3814),
                    (Self::solana__expected_fee, 3826),
                    (Self::solana__instruction_accounts_template, 3891),
                    (Self::solana__instruction_data, 3907),
                    (Self::solana__instruction_is_multisig, 3959),
                    (Self::solana__is_provided_via_lookup_table_template, 3994),
                    (Self::solana__lookup_table_address, 4014),
                    (Self::solana__multiple_signers, 4030),
                    (Self::solana__transaction_contains_unknown_instructions, 4072),
                    (Self::solana__transaction_requires_x_signers_template, 4129),
                    (Self::stellar__account_merge, 4142),
                    (Self::stellar__account_thresholds, 4160),
                    (Self::stellar__add_signer, 4170),
                    (Self::stellar__add_trust, 4179),
                    (Self::stellar__all_will_be_sent_to, 4202),
                    (Self::stellar__allow_trust, 4213),
                    (Self::stellar__balance_id, 4223),
                    (Self::stellar__bump_sequence, 4236),
                    (Self::stellar__buying, 4243),
                    (Self::stellar__claim_claimable_balance, 4266),
                    (Self::stellar__clear_data, 4276),
                    (Self::stellar__clear_flags, 4287),
                    (Self::stellar__confirm_issuer, 4301),
                    (Self::stellar__confirm_memo, 4313),
                    (Self::stellar__confirm_operation, 4330),
                    (Self::stellar__confirm_timebounds, 4348),
                    (Self::stellar__create_account, 4362),
                    (Self::stellar__debited_amount, 4376),
                    (Self::stellar__delete, 4382),
                    (Self::stellar__delete_passive_offer, 4402),
                    (Self::stellar__delete_trust, 4414),
                    (Self::stellar__destination, 4425),
                    (Self::stellar__exchanges_require_memo, 4485),
                    (Self::stellar__final_confirm, 4498),
                    (Self::stellar__hash, 4502),
                    (Self::stellar__high, 4507),
                    (Self::stellar__home_domain, 4518),
                    (Self::stellar__inflation, 4527),
                    (Self::stellar__issuer_template, 4537),
                    (Self::stellar__key, 4541),
                    (Self::stellar__limit, 4546),
                    (Self::stellar__low, 4550),
                    (Self::stellar__master_weight, 4564),
                    (Self::stellar__medium, 4571),
                    (Self::stellar__new_offer, 4580),
                    (Self::stellar__new_passive_offer, 4597),
                    (Self::stellar__no_memo_set, 4609),
                    (Self::stellar__no_restriction, 4625),
                    (Self::stellar__path_pay, 4633),
                    (Self::stellar__path_pay_at_least, 4650),
                    (Self::stellar__pay, 4653),
                    (Self::stellar__pay_at_most, 4664),
                    (Self::stellar__preauth_transaction, 4684),
                    (Self::stellar__price_per_template, 4698),
                    (Self::stellar__remove_signer, 4711),
                    (Self::stellar__revoke_trust, 4723),
                    (Self::stellar__selling, 4731),
                    (Self::stellar__set_data, 4739),
                    (Self::stellar__set_flags, 4748),
                    (Self::stellar__set_sequence_to_template, 4768),
                    (Self::stellar__sign_tx_count_template, 4804),
                    (Self::stellar__sign_tx_fee_template, 4824),
                    (Self::stellar__source_account, 4838),
                    (Self::stellar__trusted_account, 4853),
                    (Self::stellar__update, 4859),
                    (Self::stellar__valid_from, 4875),
                    (Self::stellar__valid_to, 4889),
                    (Self::stellar__value_sha256, 4905),
                    (Self::stellar__wanna_clean_value_key_template, 4940),
                    (Self::tezos__baker_address, 4953),
                    (Self::tezos__balance, 4961),
                    (Self::tezos__ballot, 4968),
                    (Self::tezos__confirm_delegation, 4986),
                    (Self::tezos__confirm_origination, 5005),
                    (Self::tezos__delegator, 5014),
                    (Self::tezos__proposal, 5022),
                    (Self::tezos__register_delegate, 5039),
                    (Self::tezos__remove_delegation, 5056),
                    (Self::tezos__submit_ballot, 5069),
                    (Self::tezos__submit_proposal, 5084),
                    (Self::tezos__submit_proposals, 5100),
                    (Self::u2f__get, 5138),
                    (Self::u2f__set_template, 5165),
                    (Self::u2f__title_get, 5180),
                    (Self::u2f__title_set, 5195),
                    (Self::ethereum__staking_claim, 5200),
                    (Self::ethereum__staking_claim_address, 5213),
                    (Self::ethereum__staking_claim_intro, 5238),
                    (Self::ethereum__staking_stake, 5243),
                    (Self::ethereum__staking_stake_address, 5256),
                    (Self::ethereum__staking_stake_intro, 5279),
                    (Self::ethereum__staking_unstake, 5286),
                    (Self::ethereum__staking_unstake_intro, 5313),
                    (Self::cardano__always_abstain, 5327),
                    (Self::cardano__always_no_confidence, 5347),
                    (Self::cardano__delegating_to_key_hash, 5370),
                    (Self::cardano__delegating_to_script, 5391),
                    (Self::cardano__deposit, 5399),
                    (Self::cardano__vote_delegation, 5414),
                    (Self::fido__more_credentials, 5430),
                    (Self::fido__select_intro, 5498),
                    (Self::fido__title_for_authentication, 5516),
                    (Self::fido__title_select_credential, 5533),
                    (Self::fido__title_credential_details, 5551),
                    (Self::ethereum__unknown_contract_address, 5575),
                    (Self::ethereum__token_contract, 5589),
                    (Self::ethereum__interaction_contract, 5609),
                    (Self::solana__base_fee, 5617),
                    (Self::solana__claim, 5622),
                    (Self::solana__claim_question, 5651),
                    (Self::solana__claim_recipient_warning, 5703),
                    (Self::solana__priority_fee, 5715),
                    (Self::solana__stake, 5720),
                    (Self::solana__stake_account, 5733),
                    (Self::solana__stake_question, 5743),
                    (Self::solana__stake_withdrawal_warning, 5803),
                    (Self::solana__stake_withdrawal_warning_title, 5829),
                    (Self::solana__unstake, 5836),
                    (Self::solana__unstake_question, 5867),
                    (Self::solana__vote_account, 5879),
                    (Self::solana__stake_on_question, 5896),
                    (Self::nostr__event_kind_template, 5911),
                    (Self::solana__max_fees_rent, 5928),
                    (Self::solana__max_rent_fee, 5940),
                    (Self::ethereum__approve, 5947),
                    (Self::ethereum__approve_amount_allowance, 5963),
                    (Self::ethereum__approve_chain_id, 5971),
                    (Self::ethereum__approve_intro, 6012),
                    (Self::ethereum__approve_intro_title, 6026),
                    (Self::ethereum__approve_to, 6036),
                    (Self::ethereum__approve_unlimited_template, 6069),
                    (Self::ethereum__approve_intro_revoke, 6109),
                    (Self::ethereum__approve_intro_title_revoke, 6125),
                    (Self::ethereum__approve_revoke, 6131),
                    (Self::ethereum__approve_revoke_from, 6142),
                    (Self::solana__unknown_token, 6155),
                    (Self::solana__unknown_token_address, 6176),
                    (Self::ethereum__title_all_input_data_template, 6202),
                    (Self::ethereum__contract_address, 6227),
                    (Self::ethereum__title_confirm_message_hash, 6247),
                    (Self::stellar__sign_with, 6256),
                    (Self::stellar__timebounds, 6266),
                    (Self::stellar__token_info, 6276),
                    (Self::stellar__transaction_source, 6294),
                    (Self::stellar__transaction_source_diff_warning, 6344),
                    (Self::cardano__confirm_message, 6359),
                    (Self::cardano__empty_message, 6372),
                    (Self::cardano__message_hash, 6385),
                    (Self::cardano__message_hex, 6396),
                    (Self::cardano__message_text, 6408),
                    (Self::cardano__sign_message_hash_path_template, 6434),
                    (Self::cardano__sign_message_path_template, 6455),
                    (Self::ripple__destination_tag_missing, 6526),
                ],
            };

            #[cfg(feature = "debug")]
            const DEBUG_BLOB: StringsBlob = StringsBlob {
                text: "Loading seedLoading private seed is not recommended.",
                offsets: &[
                    (Self::debug__loading_seed, 12),
                    (Self::debug__loading_seed_not_recommended, 52),
                ],
            };

            pub const BLOBS: &'static [StringsBlob] = &[
                Self::BTC_ONLY_BLOB,
                #[cfg(feature = "universal_fw")]
                Self::ALTCOIN_BLOB,
                #[cfg(feature = "debug")]
                Self::DEBUG_BLOB,
            ];
        }
    } else if #[cfg(feature = "layout_eckhart")] {
        impl TranslatedString {
            const BTC_ONLY_BLOB: StringsBlob = StringsBlob {
                text: "Please contact Trezor support atKey mismatch?Address mismatch?trezor.io/supportWrong derivation path for selected account.XPUB mismatch?Public keyCosignerReceive addressYoursDerivation path:Receive addressReceiving toAllow connected app to check the authenticity of your {0}?Authenticate deviceAuto-lock Trezor after {0} of inactivity?Auto-lockYou can back up your Trezor once, at any time.Back up your new wallet now.It should be backed up now!Wallet created.\nWallet created successfully.You can use your backup to recover your wallet at any time.Back up walletSkip backupAre you sure you want to skip the backup?Commitment dataConfirm locktimeDo you want to create a proof of ownership?The mining fee of\n{0}\nis unexpectedly high.Locktime is set but will have no effect.Locktime set toLocktime set to blockheightA lot of change-outputs.Multiple accountsNew fee rate:Simple send ofTicket amountConfirm detailsFinalize transactionHigh mining feeMeld transactionModify amountPayjoinProof of ownershipPurchase ticketUpdate transactionUnknown pathUnknown transactionUnusually high fee.The transaction contains unverified external inputs.The signature is valid.Voting rights toAbortAccessAgainAllowBackBack upCancelChangeCheckCheck againCloseConfirmContinueDetailsEnableEnterEnter shareExportFormatGo backHold to confirmInfoInstallMore infoOk, I understandPurchaseQuitRestartRetrySelectSetShow allShow detailsShow wordsSkipTry againTurn offTurn onAccess your coinjoin account?Do not disconnect your Trezor!Max mining feeMax roundsAuthorize coinjoinCoinjoin in progress...Waiting for othersFee rate:Sending from account:Fee infoSending fromChange device name to {0}?Device nameDo you really want to send entropy?Confirm entropySign transactionEnable experimental features?Only for development and beta testing!Experimental modeUpdate firmwareFW fingerprintClick to ConnectClick to UnlockBackup failedBackup neededCoinjoin authorizedExperimental modeNo USB connectionPIN not setSeedlessChange wallpaperJoint transactionTo the total amount:You are contributing:Change language to {0}?Language changed successfullyChanging language...Language settingsTap to connectTap to unlockLockedNot connectedDecrypt valueEncrypt valueSuite labelingDecrease amount byIncrease amount byNew amountModify amountDecrease fee byFee rate:Increase fee byNew transaction feeFee did not changeModify feeTransaction feeAccess passphrase wallet?Always enter your passphrase on Trezor?Passphrase provided by connected app will be used but will not be displayed due to the device settings.Passphrase walletHide your passphrase on Trezor entered on connected app?The next screen shows your passphrase.Please enter your passphrase.Do you want to revoke the passphrase on device setting?Confirm passphraseEnter passphraseHide passphrasePassphrase settingsPassphrase sourceTurn off passphrase protection?Turn on passphrase protection?Change PINPIN changed.Position of the cursor will change between entries for enhanced security.The new PIN must be different from your wipe code.PIN protection\nturned off.PIN protection\nturned on.Enter PINEnter new PINThe PIN you have entered is not valid.The PIN will be required to access this device.Invalid PINLast attemptEntered PINs do not match!PIN mismatchPlease check again.Re-enter new PINPlease re-enter PIN to confirm.PIN should be 4-50 digits long.Check PINPIN settingsWrong PINtries leftAre you sure you want to turn off PIN protection?Turn on PIN protection?Wrong PINkey|keyshour|hoursmillisecond|millisecondsminute|minutessecond|secondsaction|actionsoperation|operationsgroup|groupsshare|sharesChecking authenticity...DoneLoading transaction...Locking the device...1 second leftPlease wait...Processing...Refreshing...Signing transaction...Syncing...{0} seconds leftTrezor will restart in bootloader mode.Go to bootloaderFirmware version {0}\nby {1}Cancel backup checkLet's do a wallet backup check.Position of the cursor will change between entries for enhanced security.The entered wallet backup is valid and matches the one in this device.The entered wallet backup is valid but does not match the one in the device.The entered recovery shares are valid and match what is currently in the device.The entered wallet backup is valid but doesn't match the one on this device.Enter any shareEnter your backup.Enter a different share.Enter share from a different group.Group #{0}Group threshold reached.Invalid wallet backup entered.Invalid recovery share entered.More shares needed.Select the number of words in your backup.You'll only have to select the first 2-4 letters of each word.All progress will be lost.Share already entered.You have entered a share from a different backup.Share #{0}Recover walletCancel backup checkCancel recoveryBackup checkRecover walletRemaining sharesType word {0} of {1}Wallet recovery completed.Are you sure you want to cancel the backup check?Are you sure you want to cancel the recovery process?({0} words)Word {0}\nof {1}You need {count} more {plural} starting{count} more {plural} needed.{0} of {1} shares entered.You have enteredThe group threshold specifies the number of groups required to recover your wallet.Create walletRecover walletBy continuing, you agree to Trezor Company's Terms of Use.Check backupCheck g{0} - share {1}Check wallet backupCheck share #{0}Continue with the next share.Continue with share #{0}.You have finished verifying your recovery shares for group {0}.You have finished verifying your wallet backup.You have finished verifying your recovery shares.A group is made up of recovery shares.Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds.Group {0} - Share {1} checked successfully.Group #{0} - Share #{1}More info atNever put your backup anywhere digital.{0} people or locations will each hold one share.Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}.The required number of shares to form Group {0}.= total number of unique word lists used for wallet backup.Only one share will be created.Wallet backupRecovery share #{0}The required number of groups for recovery.Select the correct word for each position.Select word #{0} from your wallet backupSelect word {0} of {1}:Share #{0} checked successfully.Standard backupNumber of groupsNumber of sharesSet number of groupsSet number of sharesSet sizes and thresholdsSet size and threshold for each groupSet recovery thresholdBackup checklistWrite down and check all sharesWrite down & check all wallet backup shares= minimum number of unique word lists used for recovery.Backup is doneCreate walletGroup thresholdNumber of groupsNumber of sharesSet group thresholdSet number of groupsSet number of sharesSet thresholdMore at trezor.io/tosSet the total number of shares in Group {0}.Use your backup when you need to recover your wallet.Write the following {0} words in order on your wallet backup card.Wrong word selected!Your backup is done.Change display orientation to {0}?eastnorthsouthDisplay orientationwestTrezor will allow you to approve some actions which might be unsafe.Trezor will temporarily allow you to approve some actions which might be unsafe.Do you really want to enforce strict safety checks (recommended)?Safety checksSafety overrideSending amountSending from multiple accounts.Including fee:Maximum feeReceiving to a multisig address.Confirm sendingJoint transactionReceiving toSendingSending amountSending toTo the total amount:Transaction IDYou are contributing: words in order.I wrote down all {0} BytesSigning addressConfirm messageMessage sizeVerify addressAssetPress both left and right at the same\ntime to confirm.Press and hold the right button to\napprove important operations.You're ready to\nuse Trezor.Press right to scroll down to read all content when text doesn't fit on one screen.\n\rPress left to scroll up.Are you sure you\nwant to skip the tutorial?HelloScreen scrollSkip tutorialTutorial completeUse Trezor by\nclicking the left and right buttons.\n\rContinue right.Welcome to Trezor. Press right to continue.All data will be erased.Wipe deviceDo you really want to wipe the device?\nChange wipe codeWipe code changed.The wipe code must be different from your PIN.Wipe code disabled.Wipe code enabled.New wipe codeWipe code can be used to erase all data from this device.Invalid wipe codeThe wipe codes you entered do not match.Re-enter wipe codePlease re-enter wipe code to confirm.Check wipe codeInvalid wipe codeWipe code settingsTurn off wipe code protection?Turn on wipe code protection?Wipe code mismatchNumber of wordsAccountAccount:AddressAmountAre you sure?Array ofBlockhashBuyingConfirmConfirm feeContainsContinue anyway?Continue withErrorFeefromKeep it safe!Continue only if you know what you are doing!My TrezorNooutputsPlease check againPlease try againDo you really want toRecipientSignSignerCheckGroupInformationRememberShareSharesSuccessSummaryThresholdUnknownWarningWritableYesJust a moment...Starting upVerifying PIN...Wrong PINDo you want to create a {0} of {1} multi-share backup?Multi-share backupTap to confirmHold to confirmImportantI wrote down all {0} words in order.Create a wallet backup to avoid losing access to your funds.Let's do a quick check of your backup.InstructionsNot recommended!Account infoIf receive address doesn't match, contact Trezor Support at trezor.io/support.Cancel receive?QR codeDerivation pathContinue in the appCancel and exitReceive address confirmedContinue without PINWithout a PIN, anyone can access this device.Cancel PIN setup?Cancel signSend fromHold to signFee rateincl. Transaction feeTotal amountAuto-lock turned onYour wallet backup contains multiple lists of words in a specific order (shares).Your wallet backup contains {0} words in a specific order.Wallet backup completed.Create wallet backupDisable haptic feedback?Enable haptic feedback?SettingHaptic feedbackKeep holdingEnter next shareHold to continueHold to exit tutorialLearn moreContinue with Share #{0}Start with share #1PassphraseWallet backup not on this deviceInvalid wallet backup enteredAll shares are valid and belong to the backup in this deviceEntered share is valid and belongs to the backup in the deviceVerify remaining recovery shares?Enter each word of your wallet backup in order.It's safe to disconnect your Trezor while recovering your wallet and continue later.Share doesn't matchCancel create walletIncorrect word selected.More atHow many wallet backup shares do you want to create?Each backup share is a sequence of {0} words.\nStore each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.Select the minimum shares required to recover your wallet.Share #{0} completedNumber of shares: {0}Recovery threshold: {0}Transaction signedContinue tutorialExit tutorialFind context-specific actions and options in the menu.One more stepYou're all set to start using your device!Easy navigationGood to knowOperation cancelledSettingsTry againNumber of groups: {0}Display brightnessMulti-share backupCreate additional backup?Create backupChange wallpaper to default image?Words may repeat.Repeat for all shares.SettingsHomescreenThe word appears multiple times in the backup.Let's beginDid you know?The Trezor Model One, created in 2013,\nwas the world's first hardware wallet.Restart tutorialHandy menuHold the on-screen button at the bottom to confirm important actions.Well done!Learn how to use and navigate this device with ease.Get started!Swipe horizontallyAdjustApplyDisplay brightness changedChange display brightnessDoneThe threshold sets the minimum number of shares needed to recover your wallet.If you set {0} out of {1} shares, you'll need {2} backup shares to recover your wallet.Continue with empty passphrase?Swipe downPublic key confirmedContinue anywayView all dataView all data in the menu.Enable labeling?ProviderConfirm without reviewTap to continueUnpair all bluetooth devicesUnpair connected deviceUnpairUnlockedTransaction feeUnlimitedChainTokenTapWrite down the first word from the backup.We don't recommend to skip wallet backup creation.Pay attentionCheck the address with source.ReceiveA recovery share is a list of words you wrote down when setting up your Trezor.Your wallet backup consists of 1 to 16 shares.Recovery shareAfter signing, send the transaction in the app.Sign cancelled.SendWalletAuthenticateSet the time before your Trezor locks automatically.day|daysTrezor will restart after update.Access hidden walletHidden walletShow passphraseRe-enter PINPIN setup completed.Start with Share #{0}Let's do a quick check of Share #{0}.Select word #{0} from\nShare #{1}Share #{0} from Group #{1} entered.Cancel transactionUsing different paths for different XPUBs.Public key (XPUB)Cancel?{0} addressViewSwapProvider addressRefund addressAssetsFinishUse menu to continueLast oneView more info, quit flow, ...Use the on-screen buttons to navigate and confirm your actions.Replay this tutorial anytime from the Trezor Suite app.Welcome\nto Trezor\nSafe 7What is TROPIC01?Tap to start tutorialTROPIC01 is a next-gen open-source secure element chip designed for transparent and auditable hardware security.Continue with empty device name?Enter device nameRegulatoryNameDevice name changed.Manage paired devicesPair new devicePair & ConnectBluetooth versionFirmware typeFirmware versionDisable LED?Enable LED?LEDAboutConnectedDeviceDisconnectLEDManageOFFONReviewSecurityChange PIN?Remove PINPIN codeChange wipe code?Remove wipe codeWipe codeDisabledEnabledTurn Bluetooth off?Turn Bluetooth on?BluetoothWipe your Trezor and start the setup process again.SetWipeUnlockStart enteringDisconnectedForget allConnectForgetPowerLimit of paired devices reachedThey'll be removed, and you'll need to pair them again before use.Forget all devices?All connections removed.It will be removed, and you'll need to pair it again before use.Forget this device?Connection removed.Allow {0} to connect automatically to this Trezor?Allow {0} on {1} to connect automatically to this Trezor?Allow {0} to connect with this Trezor?Allow {0} on {1} to connect with this Trezor?Allow {0} to pair with this Trezor?Allow {0} on {1} to pair with this Trezor?Autoconnect credentialEnter this one-time security code on {0}One more stepConnection dialogKeep your Trezor near your phone to complete the setup.Before you continueScan QR code to pairPairing code match?Bluetooth pairing{0} is your Trezor's name.Pair with new deviceUse the power button on the side to turn your device on or off.on battery / wireless chargerconnected to USBWipe code must be turned off before turning off PIN protection.Wipe code setPIN must be set before enabling wipe code.Cancel wipe code setup?Open Trezor Suite and create a wallet backup. This is the only way to recover access to your assets.Connection infoMAC addressWaiting for connection...Apps connectedAllow connected device to get serial number of your Trezor Safe 7?Serial numberThe Bluetooth must be turned on to pair with a new device.Your Trezor is having trouble communicating with your connected device.Allow Trezor Suite to use Suite Sync with this Trezor?Allow {0} on {1} to use Suite Sync with this Trezor?Suite SyncNote",
                offsets: &[
                    (Self::addr_mismatch__contact_support_at, 32),
                    (Self::addr_mismatch__key_mismatch, 45),
                    (Self::addr_mismatch__mismatch, 62),
                    (Self::addr_mismatch__support_url, 79),
                    (Self::addr_mismatch__wrong_derivation_path, 122),
                    (Self::addr_mismatch__xpub_mismatch, 136),
                    (Self::address__public_key, 146),
                    (Self::address__title_cosigner, 154),
                    (Self::address__title_receive_address, 169),
                    (Self::address__title_yours, 174),
                    (Self::address_details__derivation_path_colon, 190),
                    (Self::address_details__title_receive_address, 205),
                    (Self::address_details__title_receiving_to, 217),
                    (Self::authenticate__confirm_template, 275),
                    (Self::authenticate__header, 294),
                    (Self::auto_lock__change_template, 335),
                    (Self::auto_lock__title, 344),
                    (Self::backup__can_back_up_anytime, 390),
                    (Self::backup__it_should_be_backed_up, 418),
                    (Self::backup__it_should_be_backed_up_now, 445),
                    (Self::backup__new_wallet_created, 461),
                    (Self::backup__new_wallet_successfully_created, 489),
                    (Self::backup__recover_anytime, 548),
                    (Self::backup__title_backup_wallet, 562),
                    (Self::backup__title_skip, 573),
                    (Self::backup__want_to_skip, 614),
                    (Self::bitcoin__commitment_data, 629),
                    (Self::bitcoin__confirm_locktime, 645),
                    (Self::bitcoin__create_proof_of_ownership, 688),
                    (Self::bitcoin__high_mining_fee_template, 731),
                    (Self::bitcoin__locktime_no_effect, 771),
                    (Self::bitcoin__locktime_set_to, 786),
                    (Self::bitcoin__locktime_set_to_blockheight, 813),
                    (Self::bitcoin__lot_of_change_outputs, 837),
                    (Self::bitcoin__multiple_accounts, 854),
                    (Self::bitcoin__new_fee_rate, 867),
                    (Self::bitcoin__simple_send_of, 881),
                    (Self::bitcoin__ticket_amount, 894),
                    (Self::bitcoin__title_confirm_details, 909),
                    (Self::bitcoin__title_finalize_transaction, 929),
                    (Self::bitcoin__title_high_mining_fee, 944),
                    (Self::bitcoin__title_meld_transaction, 960),
                    (Self::bitcoin__title_modify_amount, 973),
                    (Self::bitcoin__title_payjoin, 980),
                    (Self::bitcoin__title_proof_of_ownership, 998),
                    (Self::bitcoin__title_purchase_ticket, 1013),
                    (Self::bitcoin__title_update_transaction, 1031),
                    (Self::bitcoin__unknown_path, 1043),
                    (Self::bitcoin__unknown_transaction, 1062),
                    (Self::bitcoin__unusually_high_fee, 1081),
                    (Self::bitcoin__unverified_external_inputs, 1133),
                    (Self::bitcoin__valid_signature, 1156),
                    (Self::bitcoin__voting_rights, 1172),
                    (Self::buttons__abort, 1177),
                    (Self::buttons__access, 1183),
                    (Self::buttons__again, 1188),
                    (Self::buttons__allow, 1193),
                    (Self::buttons__back, 1197),
                    (Self::buttons__back_up, 1204),
                    (Self::buttons__cancel, 1210),
                    (Self::buttons__change, 1216),
                    (Self::buttons__check, 1221),
                    (Self::buttons__check_again, 1232),
                    (Self::buttons__close, 1237),
                    (Self::buttons__confirm, 1244),
                    (Self::buttons__continue, 1252),
                    (Self::buttons__details, 1259),
                    (Self::buttons__enable, 1265),
                    (Self::buttons__enter, 1270),
                    (Self::buttons__enter_share, 1281),
                    (Self::buttons__export, 1287),
                    (Self::buttons__format, 1293),
                    (Self::buttons__go_back, 1300),
                    (Self::buttons__hold_to_confirm, 1315),
                    (Self::buttons__info, 1319),
                    (Self::buttons__install, 1326),
                    (Self::buttons__more_info, 1335),
                    (Self::buttons__ok_i_understand, 1351),
                    (Self::buttons__purchase, 1359),
                    (Self::buttons__quit, 1363),
                    (Self::buttons__restart, 1370),
                    (Self::buttons__retry, 1375),
                    (Self::buttons__select, 1381),
                    (Self::buttons__set, 1384),
                    (Self::buttons__show_all, 1392),
                    (Self::buttons__show_details, 1404),
                    (Self::buttons__show_words, 1414),
                    (Self::buttons__skip, 1418),
                    (Self::buttons__try_again, 1427),
                    (Self::buttons__turn_off, 1435),
                    (Self::buttons__turn_on, 1442),
                    (Self::coinjoin__access_account, 1471),
                    (Self::coinjoin__do_not_disconnect, 1501),
                    (Self::coinjoin__max_mining_fee, 1515),
                    (Self::coinjoin__max_rounds, 1525),
                    (Self::coinjoin__title, 1543),
                    (Self::coinjoin__title_progress, 1566),
                    (Self::coinjoin__waiting_for_others, 1584),
                    (Self::confirm_total__fee_rate_colon, 1593),
                    (Self::confirm_total__sending_from_account, 1614),
                    (Self::confirm_total__title_fee, 1622),
                    (Self::confirm_total__title_sending_from, 1634),
                    (Self::device_name__change_template, 1660),
                    (Self::device_name__title, 1671),
                    (Self::entropy__send, 1706),
                    (Self::entropy__title_confirm, 1721),
                    (Self::send__sign_transaction, 1737),
                    (Self::experimental_mode__enable, 1766),
                    (Self::experimental_mode__only_for_dev, 1804),
                    (Self::experimental_mode__title, 1821),
                    (Self::firmware_update__title, 1836),
                    (Self::firmware_update__title_fingerprint, 1850),
                    (Self::homescreen__click_to_connect, 1866),
                    (Self::homescreen__click_to_unlock, 1881),
                    (Self::homescreen__title_backup_failed, 1894),
                    (Self::homescreen__title_backup_needed, 1907),
                    (Self::homescreen__title_coinjoin_authorized, 1926),
                    (Self::homescreen__title_experimental_mode, 1943),
                    (Self::homescreen__title_no_usb_connection, 1960),
                    (Self::homescreen__title_pin_not_set, 1971),
                    (Self::homescreen__title_seedless, 1979),
                    (Self::homescreen__title_set, 1995),
                    (Self::inputs__back, 1995),
                    (Self::inputs__cancel, 1995),
                    (Self::inputs__delete, 1995),
                    (Self::inputs__enter, 1995),
                    (Self::inputs__return, 1995),
                    (Self::inputs__show, 1995),
                    (Self::inputs__space, 1995),
                    (Self::joint__title, 2012),
                    (Self::joint__to_the_total_amount, 2032),
                    (Self::joint__you_are_contributing, 2053),
                    (Self::language__change_to_template, 2076),
                    (Self::language__changed, 2105),
                    (Self::language__progress, 2125),
                    (Self::language__title, 2142),
                    (Self::lockscreen__tap_to_connect, 2156),
                    (Self::lockscreen__tap_to_unlock, 2169),
                    (Self::lockscreen__title_locked, 2175),
                    (Self::lockscreen__title_not_connected, 2188),
                    (Self::misc__decrypt_value, 2201),
                    (Self::misc__encrypt_value, 2214),
                    (Self::misc__title_suite_labeling, 2228),
                    (Self::modify_amount__decrease_amount, 2246),
                    (Self::modify_amount__increase_amount, 2264),
                    (Self::modify_amount__new_amount, 2274),
                    (Self::modify_amount__title, 2287),
                    (Self::modify_fee__decrease_fee, 2302),
                    (Self::modify_fee__fee_rate, 2311),
                    (Self::modify_fee__increase_fee, 2326),
                    (Self::modify_fee__new_transaction_fee, 2345),
                    (Self::modify_fee__no_change, 2363),
                    (Self::modify_fee__title, 2373),
                    (Self::modify_fee__transaction_fee, 2388),
                    (Self::passphrase__access_wallet, 2413),
                    (Self::passphrase__always_on_device, 2452),
                    (Self::passphrase__from_host_not_shown, 2555),
                    (Self::passphrase__wallet, 2572),
                    (Self::passphrase__hide, 2628),
                    (Self::passphrase__next_screen_will_show_passphrase, 2666),
                    (Self::passphrase__please_enter, 2695),
                    (Self::passphrase__revoke_on_device, 2750),
                    (Self::passphrase__title_confirm, 2768),
                    (Self::passphrase__title_enter, 2784),
                    (Self::passphrase__title_hide, 2799),
                    (Self::passphrase__title_settings, 2818),
                    (Self::passphrase__title_source, 2835),
                    (Self::passphrase__turn_off, 2866),
                    (Self::passphrase__turn_on, 2896),
                    (Self::pin__change, 2906),
                    (Self::pin__changed, 2918),
                    (Self::pin__cursor_will_change, 2991),
                    (Self::pin__diff_from_wipe_code, 3041),
                    (Self::pin__disabled, 3067),
                    (Self::pin__enabled, 3092),
                    (Self::pin__enter, 3101),
                    (Self::pin__enter_new, 3114),
                    (Self::pin__entered_not_valid, 3152),
                    (Self::pin__info, 3199),
                    (Self::pin__invalid_pin, 3210),
                    (Self::pin__last_attempt, 3222),
                    (Self::pin__mismatch, 3248),
                    (Self::pin__pin_mismatch, 3260),
                    (Self::pin__please_check_again, 3279),
                    (Self::pin__reenter_new, 3295),
                    (Self::pin__reenter_to_confirm, 3326),
                    (Self::pin__should_be_long, 3357),
                    (Self::pin__title_check_pin, 3366),
                    (Self::pin__title_settings, 3378),
                    (Self::pin__title_wrong_pin, 3387),
                    (Self::pin__tries_left, 3397),
                    (Self::pin__turn_off, 3446),
                    (Self::pin__turn_on, 3469),
                    (Self::pin__wrong_pin, 3478),
                    (Self::plurals__contains_x_keys, 3486),
                    (Self::plurals__lock_after_x_hours, 3496),
                    (Self::plurals__lock_after_x_milliseconds, 3520),
                    (Self::plurals__lock_after_x_minutes, 3534),
                    (Self::plurals__lock_after_x_seconds, 3548),
                    (Self::plurals__sign_x_actions, 3562),
                    (Self::plurals__transaction_of_x_operations, 3582),
                    (Self::plurals__x_groups_needed, 3594),
                    (Self::plurals__x_shares_needed, 3606),
                    (Self::progress__authenticity_check, 3630),
                    (Self::progress__done, 3634),
                    (Self::progress__loading_transaction, 3656),
                    (Self::progress__locking_device, 3677),
                    (Self::progress__one_second_left, 3690),
                    (Self::progress__please_wait, 3704),
                    (Self::storage_msg__processing, 3717),
                    (Self::progress__refreshing, 3730),
                    (Self::progress__signing_transaction, 3752),
                    (Self::progress__syncing, 3762),
                    (Self::progress__x_seconds_left_template, 3778),
                    (Self::reboot_to_bootloader__restart, 3817),
                    (Self::reboot_to_bootloader__title, 3833),
                    (Self::reboot_to_bootloader__version_by_template, 3860),
                    (Self::recovery__cancel_dry_run, 3879),
                    (Self::recovery__check_dry_run, 3910),
                    (Self::recovery__cursor_will_change, 3983),
                    (Self::recovery__dry_run_bip39_valid_match, 4053),
                    (Self::recovery__dry_run_bip39_valid_mismatch, 4129),
                    (Self::recovery__dry_run_slip39_valid_match, 4209),
                    (Self::recovery__dry_run_slip39_valid_mismatch, 4285),
                    (Self::recovery__enter_any_share, 4300),
                    (Self::recovery__enter_backup, 4318),
                    (Self::recovery__enter_different_share, 4342),
                    (Self::recovery__enter_share_from_diff_group, 4377),
                    (Self::recovery__group_num_template, 4387),
                    (Self::recovery__group_threshold_reached, 4411),
                    (Self::recovery__invalid_wallet_backup_entered, 4441),
                    (Self::recovery__invalid_share_entered, 4472),
                    (Self::recovery__more_shares_needed, 4491),
                    (Self::recovery__num_of_words, 4533),
                    (Self::recovery__only_first_n_letters, 4595),
                    (Self::recovery__progress_will_be_lost, 4621),
                    (Self::recovery__share_already_entered, 4643),
                    (Self::recovery__share_from_another_multi_share_backup, 4692),
                    (Self::recovery__share_num_template, 4702),
                    (Self::recovery__title, 4716),
                    (Self::recovery__title_cancel_dry_run, 4735),
                    (Self::recovery__title_cancel_recovery, 4750),
                    (Self::recovery__title_dry_run, 4762),
                    (Self::recovery__title_recover, 4776),
                    (Self::recovery__title_remaining_shares, 4792),
                    (Self::recovery__type_word_x_of_y_template, 4812),
                    (Self::recovery__wallet_recovered, 4838),
                    (Self::recovery__wanna_cancel_dry_run, 4887),
                    (Self::recovery__wanna_cancel_recovery, 4940),
                    (Self::recovery__word_count_template, 4951),
                    (Self::recovery__word_x_of_y_template, 4966),
                    (Self::recovery__x_more_items_starting_template_plural, 5005),
                    (Self::recovery__x_more_shares_needed_template_plural, 5034),
                    (Self::recovery__x_of_y_entered_template, 5060),
                    (Self::recovery__you_have_entered, 5076),
                    (Self::reset__advanced_group_threshold_info, 5159),
                    (Self::reset__all_x_of_y_template, 5159),
                    (Self::reset__any_x_of_y_template, 5159),
                    (Self::reset__button_create, 5172),
                    (Self::reset__button_recover, 5186),
                    (Self::reset__by_continuing, 5244),
                    (Self::reset__check_backup_title, 5256),
                    (Self::reset__check_group_share_title_template, 5278),
                    (Self::reset__check_wallet_backup_title, 5297),
                    (Self::reset__check_share_title_template, 5313),
                    (Self::reset__continue_with_next_share, 5342),
                    (Self::reset__continue_with_share_template, 5367),
                    (Self::reset__finished_verifying_group_template, 5430),
                    (Self::reset__finished_verifying_wallet_backup, 5477),
                    (Self::reset__finished_verifying_shares, 5526),
                    (Self::reset__group_description, 5564),
                    (Self::reset__group_info, 5697),
                    (Self::reset__group_share_checked_successfully_template, 5740),
                    (Self::reset__group_share_title_template, 5763),
                    (Self::reset__more_info_at, 5775),
                    (Self::reset__need_all_share_template, 5775),
                    (Self::reset__need_any_share_template, 5775),
                    (Self::reset__needed_to_form_a_group, 5775),
                    (Self::reset__needed_to_recover_your_wallet, 5775),
                    (Self::reset__never_make_digital_copy, 5814),
                    (Self::reset__num_of_share_holders_template, 5863),
                    (Self::reset__num_of_shares_advanced_info_template, 5988),
                    (Self::reset__num_of_shares_basic_info_template, 5988),
                    (Self::reset__num_shares_for_group_template, 6036),
                    (Self::reset__number_of_shares_info, 6095),
                    (Self::reset__one_share, 6095),
                    (Self::reset__only_one_share_will_be_created, 6126),
                    (Self::reset__recovery_wallet_backup_title, 6139),
                    (Self::reset__recovery_share_title_template, 6158),
                    (Self::reset__required_number_of_groups, 6201),
                    (Self::reset__select_correct_word, 6243),
                    (Self::reset__select_word_template, 6283),
                    (Self::reset__select_word_x_of_y_template, 6306),
                    (Self::reset__set_it_to_count_template, 6306),
                    (Self::reset__share_checked_successfully_template, 6338),
                    (Self::reset__share_words_title, 6353),
                    (Self::reset__slip39_checklist_num_groups, 6369),
                    (Self::reset__slip39_checklist_num_shares, 6385),
                    (Self::reset__slip39_checklist_set_num_groups, 6405),
                    (Self::reset__slip39_checklist_set_num_shares, 6425),
                    (Self::reset__slip39_checklist_set_sizes, 6449),
                    (Self::reset__slip39_checklist_set_sizes_longer, 6486),
                    (Self::reset__slip39_checklist_set_threshold, 6508),
                    (Self::reset__slip39_checklist_title, 6524),
                    (Self::reset__slip39_checklist_write_down, 6555),
                    (Self::reset__slip39_checklist_write_down_recovery, 6598),
                    (Self::reset__the_threshold_sets_the_number_of_shares, 6598),
                    (Self::reset__threshold_info, 6654),
                    (Self::reset__title_backup_is_done, 6668),
                    (Self::reset__title_create_wallet, 6681),
                    (Self::reset__title_group_threshold, 6696),
                    (Self::reset__title_number_of_groups, 6712),
                    (Self::reset__title_number_of_shares, 6728),
                    (Self::reset__title_set_group_threshold, 6747),
                    (Self::reset__title_set_number_of_groups, 6767),
                    (Self::reset__title_set_number_of_shares, 6787),
                    (Self::reset__title_set_threshold, 6800),
                    (Self::reset__to_form_group_template, 6800),
                    (Self::reset__tos_link, 6821),
                    (Self::reset__total_number_of_shares_in_group_template, 6865),
                    (Self::reset__use_your_backup, 6918),
                    (Self::reset__write_down_words_template, 6984),
                    (Self::reset__wrong_word_selected, 7004),
                    (Self::reset__you_need_one_share, 7004),
                    (Self::reset__your_backup_is_done, 7024),
                    (Self::rotation__change_template, 7058),
                    (Self::rotation__east, 7062),
                    (Self::rotation__north, 7067),
                    (Self::rotation__south, 7072),
                    (Self::rotation__title_change, 7091),
                    (Self::rotation__west, 7095),
                    (Self::safety_checks__approve_unsafe_always, 7163),
                    (Self::safety_checks__approve_unsafe_temporary, 7243),
                    (Self::safety_checks__enforce_strict, 7308),
                    (Self::safety_checks__title, 7321),
                    (Self::safety_checks__title_safety_override, 7336),
                    (Self::sd_card__all_data_will_be_lost, 7336),
                    (Self::sd_card__card_required, 7336),
                    (Self::sd_card__disable, 7336),
                    (Self::sd_card__disabled, 7336),
                    (Self::sd_card__enable, 7336),
                    (Self::sd_card__enabled, 7336),
                    (Self::sd_card__error, 7336),
                    (Self::sd_card__format_card, 7336),
                    (Self::sd_card__insert_correct_card, 7336),
                    (Self::sd_card__please_insert, 7336),
                    (Self::sd_card__please_unplug_and_insert, 7336),
                    (Self::sd_card__problem_accessing, 7336),
                    (Self::sd_card__refresh, 7336),
                    (Self::sd_card__refreshed, 7336),
                    (Self::sd_card__restart, 7336),
                    (Self::sd_card__title, 7336),
                    (Self::sd_card__title_problem, 7336),
                    (Self::sd_card__unknown_filesystem, 7336),
                    (Self::sd_card__unplug_and_insert_correct, 7336),
                    (Self::sd_card__use_different_card, 7336),
                    (Self::sd_card__wanna_format, 7336),
                    (Self::sd_card__wrong_sd_card, 7336),
                    (Self::send__confirm_sending, 7350),
                    (Self::send__from_multiple_accounts, 7381),
                    (Self::send__including_fee, 7395),
                    (Self::send__maximum_fee, 7406),
                    (Self::send__receiving_to_multisig, 7438),
                    (Self::send__title_confirm_sending, 7453),
                    (Self::send__title_joint_transaction, 7470),
                    (Self::send__title_receiving_to, 7482),
                    (Self::send__title_sending, 7489),
                    (Self::send__title_sending_amount, 7503),
                    (Self::send__title_sending_to, 7513),
                    (Self::send__to_the_total_amount, 7533),
                    (Self::send__transaction_id, 7547),
                    (Self::send__you_are_contributing, 7568),
                    (Self::share_words__words_in_order, 7584),
                    (Self::share_words__wrote_down_all, 7601),
                    (Self::sign_message__bytes_template, 7610),
                    (Self::sign_message__confirm_address, 7625),
                    (Self::sign_message__confirm_message, 7640),
                    (Self::sign_message__message_size, 7652),
                    (Self::sign_message__verify_address, 7666),
                    (Self::words__asset, 7671),
                    (Self::tutorial__middle_click, 7725),
                    (Self::tutorial__press_and_hold, 7789),
                    (Self::tutorial__ready_to_use, 7816),
                    (Self::tutorial__scroll_down, 7925),
                    (Self::tutorial__sure_you_want_skip, 7968),
                    (Self::tutorial__title_hello, 7973),
                    (Self::tutorial__title_screen_scroll, 7986),
                    (Self::tutorial__title_skip, 7999),
                    (Self::tutorial__title_tutorial_complete, 8016),
                    (Self::tutorial__use_trezor, 8083),
                    (Self::tutorial__welcome_press_right, 8126),
                    (Self::wipe__info, 8150),
                    (Self::wipe__title, 8161),
                    (Self::wipe__want_to_wipe, 8200),
                    (Self::wipe_code__change, 8216),
                    (Self::wipe_code__changed, 8234),
                    (Self::wipe_code__diff_from_pin, 8280),
                    (Self::wipe_code__disabled, 8299),
                    (Self::wipe_code__enabled, 8317),
                    (Self::wipe_code__enter_new, 8330),
                    (Self::wipe_code__info, 8387),
                    (Self::wipe_code__invalid, 8404),
                    (Self::wipe_code__mismatch, 8444),
                    (Self::wipe_code__reenter, 8462),
                    (Self::wipe_code__reenter_to_confirm, 8499),
                    (Self::wipe_code__title_check, 8514),
                    (Self::wipe_code__title_invalid, 8531),
                    (Self::wipe_code__title_settings, 8549),
                    (Self::wipe_code__turn_off, 8579),
                    (Self::wipe_code__turn_on, 8608),
                    (Self::wipe_code__wipe_code_mismatch, 8626),
                    (Self::word_count__title, 8641),
                    (Self::words__account, 8648),
                    (Self::words__account_colon, 8656),
                    (Self::words__address, 8663),
                    (Self::words__amount, 8669),
                    (Self::words__are_you_sure, 8682),
                    (Self::words__array_of, 8690),
                    (Self::words__blockhash, 8699),
                    (Self::words__buying, 8705),
                    (Self::words__confirm, 8712),
                    (Self::words__confirm_fee, 8723),
                    (Self::words__contains, 8731),
                    (Self::words__continue_anyway_question, 8747),
                    (Self::words__continue_with, 8760),
                    (Self::words__error, 8765),
                    (Self::words__fee, 8768),
                    (Self::words__from, 8772),
                    (Self::words__keep_it_safe, 8785),
                    (Self::words__know_what_your_doing, 8830),
                    (Self::words__my_trezor, 8839),
                    (Self::words__no, 8841),
                    (Self::words__outputs, 8848),
                    (Self::words__please_check_again, 8866),
                    (Self::words__please_try_again, 8882),
                    (Self::words__really_wanna, 8903),
                    (Self::words__recipient, 8912),
                    (Self::words__sign, 8916),
                    (Self::words__signer, 8922),
                    (Self::words__title_check, 8927),
                    (Self::words__title_group, 8932),
                    (Self::words__title_information, 8943),
                    (Self::words__title_remember, 8951),
                    (Self::words__title_share, 8956),
                    (Self::words__title_shares, 8962),
                    (Self::words__title_success, 8969),
                    (Self::words__title_summary, 8976),
                    (Self::words__title_threshold, 8985),
                    (Self::words__unknown, 8992),
                    (Self::words__warning, 8999),
                    (Self::words__writable, 9007),
                    (Self::words__yes, 9010),
                    (Self::reboot_to_bootloader__just_a_moment, 9026),
                    (Self::inputs__previous, 9026),
                    (Self::storage_msg__starting, 9037),
                    (Self::storage_msg__verifying_pin, 9053),
                    (Self::storage_msg__wrong_pin, 9062),
                    (Self::reset__create_x_of_y_multi_share_backup_template, 9116),
                    (Self::reset__title_shamir_backup, 9134),
                    (Self::instructions__tap_to_confirm, 9148),
                    (Self::instructions__hold_to_confirm, 9163),
                    (Self::words__important, 9172),
                    (Self::reset__words_written_down_template, 9208),
                    (Self::backup__create_backup_to_prevent_loss, 9268),
                    (Self::reset__check_backup_instructions, 9306),
                    (Self::words__instructions, 9318),
                    (Self::words__not_recommended, 9334),
                    (Self::address_details__account_info, 9346),
                    (Self::address__cancel_contact_support, 9424),
                    (Self::address__cancel_receive, 9439),
                    (Self::address__qr_code, 9446),
                    (Self::address_details__derivation_path, 9461),
                    (Self::instructions__continue_in_app, 9480),
                    (Self::words__cancel_and_exit, 9495),
                    (Self::address__confirmed, 9520),
                    (Self::pin__cancel_description, 9540),
                    (Self::pin__cancel_info, 9585),
                    (Self::pin__cancel_setup, 9602),
                    (Self::send__cancel_sign, 9613),
                    (Self::send__send_from, 9622),
                    (Self::instructions__hold_to_sign, 9634),
                    (Self::confirm_total__fee_rate, 9642),
                    (Self::send__incl_transaction_fee, 9663),
                    (Self::send__total_amount, 9675),
                    (Self::auto_lock__turned_on, 9694),
                    (Self::backup__info_multi_share_backup, 9775),
                    (Self::backup__info_single_share_backup, 9833),
                    (Self::backup__title_backup_completed, 9857),
                    (Self::backup__title_create_wallet_backup, 9877),
                    (Self::haptic_feedback__disable, 9901),
                    (Self::haptic_feedback__enable, 9924),
                    (Self::haptic_feedback__subtitle, 9931),
                    (Self::haptic_feedback__title, 9946),
                    (Self::instructions__continue_holding, 9958),
                    (Self::instructions__enter_next_share, 9974),
                    (Self::instructions__hold_to_continue, 9990),
                    (Self::instructions__hold_to_exit_tutorial, 10011),
                    (Self::instructions__learn_more, 10021),
                    (Self::instructions__shares_continue_with_x_template, 10045),
                    (Self::instructions__shares_start_with_1, 10064),
                    (Self::passphrase__title_passphrase, 10074),
                    (Self::recovery__dry_run_backup_not_on_this_device, 10106),
                    (Self::recovery__dry_run_invalid_backup_entered, 10135),
                    (Self::recovery__dry_run_slip39_valid_all_shares, 10195),
                    (Self::recovery__dry_run_slip39_valid_share, 10257),
                    (Self::recovery__dry_run_verify_remaining_shares, 10290),
                    (Self::recovery__enter_each_word, 10337),
                    (Self::recovery__info_about_disconnect, 10421),
                    (Self::recovery__share_does_not_match, 10440),
                    (Self::reset__cancel_create_wallet, 10460),
                    (Self::reset__incorrect_word_selected, 10484),
                    (Self::reset__more_at, 10491),
                    (Self::reset__num_of_shares_how_many, 10543),
                    (Self::reset__num_of_shares_long_info_template, 10714),
                    (Self::reset__select_threshold, 10772),
                    (Self::reset__share_completed_template, 10792),
                    (Self::reset__slip39_checklist_num_shares_x_template, 10813),
                    (Self::reset__slip39_checklist_threshold_x_template, 10836),
                    (Self::send__transaction_signed, 10854),
                    (Self::tutorial__continue, 10871),
                    (Self::tutorial__exit, 10884),
                    (Self::tutorial__menu, 10938),
                    (Self::tutorial__one_more_step, 10951),
                    (Self::tutorial__ready_to_use_safe5, 10993),
                    (Self::tutorial__swipe_up_and_down, 10993),
                    (Self::tutorial__title_easy_navigation, 11008),
                    (Self::tutorial__welcome_safe5, 11008),
                    (Self::words__good_to_know, 11020),
                    (Self::words__operation_cancelled, 11039),
                    (Self::words__settings, 11047),
                    (Self::words__try_again, 11056),
                    (Self::reset__slip39_checklist_num_groups_x_template, 11077),
                    (Self::brightness__title, 11095),
                    (Self::recovery__title_unlock_repeated_backup, 11113),
                    (Self::recovery__unlock_repeated_backup, 11138),
                    (Self::recovery__unlock_repeated_backup_verb, 11151),
                    (Self::homescreen__set_default, 11185),
                    (Self::reset__words_may_repeat, 11202),
                    (Self::reset__repeat_for_all_shares, 11224),
                    (Self::homescreen__settings_subtitle, 11232),
                    (Self::homescreen__settings_title, 11242),
                    (Self::reset__the_word_is_repeated, 11288),
                    (Self::tutorial__title_lets_begin, 11299),
                    (Self::tutorial__did_you_know, 11312),
                    (Self::tutorial__first_wallet, 11389),
                    (Self::tutorial__restart_tutorial, 11405),
                    (Self::tutorial__title_handy_menu, 11415),
                    (Self::tutorial__title_hold, 11484),
                    (Self::tutorial__title_well_done, 11494),
                    (Self::tutorial__lets_begin, 11546),
                    (Self::tutorial__get_started, 11558),
                    (Self::instructions__swipe_horizontally, 11576),
                    (Self::setting__adjust, 11582),
                    (Self::setting__apply, 11587),
                    (Self::brightness__changed_title, 11613),
                    (Self::brightness__change_title, 11638),
                    (Self::words__title_done, 11642),
                    (Self::reset__slip39_checklist_more_info_threshold, 11720),
                    (Self::reset__slip39_checklist_more_info_threshold_example_template, 11807),
                    (Self::passphrase__continue_with_empty_passphrase, 11838),
                    (Self::instructions__swipe_down, 11848),
                    (Self::address__public_key_confirmed, 11868),
                    (Self::words__continue_anyway, 11883),
                    (Self::buttons__view_all_data, 11896),
                    (Self::instructions__view_all_data, 11922),
                    (Self::misc__enable_labeling, 11938),
                    (Self::words__provider, 11946),
                    (Self::sign_message__confirm_without_review, 11968),
                    (Self::instructions__tap_to_continue, 11983),
                    (Self::ble__unpair_all, 12011),
                    (Self::ble__unpair_current, 12034),
                    (Self::ble__unpair_title, 12040),
                    (Self::words__unlocked, 12048),
                    (Self::words__transaction_fee, 12063),
                    (Self::words__unlimited, 12072),
                    (Self::words__chain, 12077),
                    (Self::words__token, 12082),
                    (Self::instructions__tap, 12085),
                    (Self::reset__share_words_first, 12127),
                    (Self::backup__not_recommend, 12177),
                    (Self::words__pay_attention, 12190),
                    (Self::address__check_with_source, 12220),
                    (Self::words__receive, 12227),
                    (Self::reset__recovery_share_description, 12306),
                    (Self::reset__recovery_share_number, 12352),
                    (Self::words__recovery_share, 12366),
                    (Self::send__send_in_the_app, 12413),
                    (Self::send__sign_cancelled, 12428),
                    (Self::words__send, 12432),
                    (Self::words__wallet, 12438),
                    (Self::words__authenticate, 12450),
                    (Self::auto_lock__description, 12502),
                    (Self::plurals__lock_after_x_days, 12510),
                    (Self::firmware_update__restart, 12543),
                    (Self::passphrase__access_hidden_wallet, 12563),
                    (Self::passphrase__hidden_wallet, 12576),
                    (Self::passphrase__show, 12591),
                    (Self::pin__reenter, 12603),
                    (Self::pin__setup_completed, 12623),
                    (Self::instructions__shares_start_with_x_template, 12644),
                    (Self::reset__check_share_backup_template, 12681),
                    (Self::reset__select_word_from_share_template, 12713),
                    (Self::recovery__share_from_group_entered_template, 12748),
                    (Self::send__cancel_transaction, 12766),
                    (Self::send__multisig_different_paths, 12808),
                    (Self::address__xpub, 12825),
                    (Self::words__cancel_question, 12832),
                    (Self::address__coin_address_template, 12843),
                    (Self::buttons__view, 12847),
                    (Self::words__swap, 12851),
                    (Self::address__title_provider_address, 12867),
                    (Self::address__title_refund_address, 12881),
                    (Self::words__assets, 12887),
                    (Self::buttons__finish, 12893),
                    (Self::instructions__menu_to_continue, 12913),
                    (Self::tutorial__last_one, 12921),
                    (Self::tutorial__menu_appendix, 12951),
                    (Self::tutorial__navigation_ts7, 13014),
                    (Self::tutorial__suite_restart, 13069),
                    (Self::tutorial__welcome_safe7, 13093),
                    (Self::tutorial__what_is_tropic, 13110),
                    (Self::tutorial__tap_to_start, 13131),
                    (Self::tutorial__tropic_info, 13243),
                    (Self::device_name__continue_with_empty_label, 13275),
                    (Self::device_name__enter, 13292),
                    (Self::regulatory__title, 13302),
                    (Self::words__name, 13306),
                    (Self::device_name__changed, 13326),
                    (Self::ble__manage_paired, 13347),
                    (Self::ble__pair_new, 13362),
                    (Self::ble__pair_title, 13376),
                    (Self::ble__version, 13393),
                    (Self::homescreen__firmware_type, 13406),
                    (Self::homescreen__firmware_version, 13422),
                    (Self::led__disable, 13434),
                    (Self::led__enable, 13445),
                    (Self::led__title, 13448),
                    (Self::words__about, 13453),
                    (Self::words__connected, 13462),
                    (Self::words__device, 13468),
                    (Self::words__disconnect, 13478),
                    (Self::words__led, 13481),
                    (Self::words__manage, 13487),
                    (Self::words__off, 13490),
                    (Self::words__on, 13492),
                    (Self::words__review, 13498),
                    (Self::words__security, 13506),
                    (Self::pin__change_question, 13517),
                    (Self::pin__remove, 13527),
                    (Self::pin__title, 13535),
                    (Self::wipe_code__change_question, 13552),
                    (Self::wipe_code__remove, 13568),
                    (Self::wipe_code__title, 13577),
                    (Self::words__disabled, 13585),
                    (Self::words__enabled, 13592),
                    (Self::ble__disable, 13611),
                    (Self::ble__enable, 13629),
                    (Self::words__bluetooth, 13638),
                    (Self::wipe__start_again, 13689),
                    (Self::words__set, 13692),
                    (Self::words__wipe, 13696),
                    (Self::lockscreen__unlock, 13702),
                    (Self::recovery__start_entering, 13716),
                    (Self::words__disconnected, 13728),
                    (Self::ble__forget_all, 13738),
                    (Self::words__connect, 13745),
                    (Self::words__forget, 13751),
                    (Self::words__power, 13756),
                    (Self::ble__limit_reached, 13787),
                    (Self::ble__forget_all_description, 13853),
                    (Self::ble__forget_all_devices, 13872),
                    (Self::ble__forget_all_success, 13896),
                    (Self::ble__forget_this_description, 13960),
                    (Self::ble__forget_this_device, 13979),
                    (Self::ble__forget_this_success, 13998),
                    (Self::thp__autoconnect, 14048),
                    (Self::thp__autoconnect_app, 14105),
                    (Self::thp__connect, 14143),
                    (Self::thp__connect_app, 14188),
                    (Self::thp__pair, 14223),
                    (Self::thp__pair_app, 14265),
                    (Self::thp__autoconnect_title, 14287),
                    (Self::thp__code_entry, 14327),
                    (Self::thp__code_title, 14340),
                    (Self::thp__connect_title, 14357),
                    (Self::thp__nfc_text, 14412),
                    (Self::thp__pair_title, 14431),
                    (Self::thp__qr_title, 14451),
                    (Self::ble__pairing_match, 14470),
                    (Self::ble__pairing_title, 14487),
                    (Self::thp__pair_name, 14513),
                    (Self::thp__pair_new_device, 14533),
                    (Self::tutorial__power, 14596),
                    (Self::auto_lock__on_battery, 14625),
                    (Self::auto_lock__on_usb, 14641),
                    (Self::pin__wipe_code_exists_description, 14704),
                    (Self::pin__wipe_code_exists_title, 14717),
                    (Self::wipe_code__pin_not_set_description, 14759),
                    (Self::wipe_code__cancel_setup, 14782),
                    (Self::homescreen__backup_needed_info, 14882),
                    (Self::ble__host_info, 14897),
                    (Self::ble__mac_address, 14908),
                    (Self::ble__waiting_for_host, 14933),
                    (Self::ble__apps_connected, 14947),
                    (Self::sn__action, 15013),
                    (Self::sn__title, 15026),
                    (Self::ble__must_be_enabled, 15084),
                    (Self::words__comm_trouble, 15155),
                    (Self::secure_sync__delegated_identity_key_no_thp, 15209),
                    (Self::secure_sync__delegated_identity_key_thp, 15261),
                    (Self::secure_sync__header, 15271),
                    (Self::words__note, 15275),
                ],
            };

            #[cfg(feature = "universal_fw")]
            const ALTCOIN_BLOB: StringsBlob = StringsBlob {
                text: "BaseEnterpriseLegacyPointerRewardaddress - no staking rewards.Amount burned (decimals unknown):Amount minted (decimals unknown):Amount sent (decimals unknown):Pool has no metadata (anonymous pool)Asset fingerprint:Auxiliary data hash:BlockCatalystCertificateChange outputCheck all items carefully.Choose level of details:Collateral input ID:Collateral input index:The collateral return output contains tokens.Collateral returnConfirm signing the stake pool registration as an owner.Confirm transactionConfirming a multisig transaction.Confirming a Plutus transaction.Confirming pool registration as owner.Confirming a transaction.CostCredential doesn't match payment credential.Datum hash:Delegating to:for account {0} and index {1}:for account {0}:for key hash:for script:Inline datumInput ID:Input index:The following address is a change address. ItsThe following address is owned by this device. ItsThe vote key registration payment address is owned by this device. Itskey hashMarginmulti-sig pathContains {0} nested scripts.Network:Transaction has no outputs, network cannot be verified.Nonce:otherpathPledgepointerPolicy IDPool metadata hash:Pool metadata url:Pool owner:Pool reward account:Reference input ID:Reference input index:Reference scriptRequired signerrewardAddress is a reward address.Warning: The address is not a payment address, it is not eligible for rewards.Rewards go to:scriptAllAnyScript data hash:Script hash:Invalid beforeInvalid hereafterKeyN of Kscript rewardSendingShow SimpleSign transaction with {0}Stake delegationStake key deregistrationStakepool registrationStake pool registration\nPool ID:Stake key registrationStaking key for accountto pool:token minting pathTotal collateral:TransactionThe transaction contains minting or burning of tokens.The following transaction output contains a script address, but does not contain a datum.Transaction ID:The transaction contains no collateral inputs. Plutus script will not be able to run.The transaction contains no script data hash. Plutus script will not be able to run.The following transaction output contains tokens.TTL:Unknown collateral amount.Path is unusual.Valid since:Verify scriptVote key registration (CIP-36)Vote public key:Voting purpose:WarningWeight:Confirm withdrawal for {0} address:Requires {0} out of {1} signatures.Amount sent:Size: {0} bytesGas limitGas priceMax fee per gasName and versionNew contract will be deployedNo message fieldMax priority feeShow full arrayShow full domainShow full messageShow full structReally sign EIP-712 typed data?Input dataConfirm domainConfirm messageConfirm structConfirm typed dataSigning address{0} unitsUnknown tokenThe signature is valid.Already registeredThis device is already registered with this application.This device is already registered with {0}.This device is not registered with this application.The credential you are trying to import does not belong to this authenticator.Delete all of the saved credentials?Export information about the credentials stored on this device?Not registeredThis device is not registered with\n{0}.Please enable PIN protection.FIDO2 authenticateImport credentialList credentialsFIDO2 registerRemove credentialFIDO2 resetU2F authenticateU2F registerFIDO2 verify userUnable to verify user.Do you really want to erase all credentials?Confirm exportConfirm ki syncConfirm refreshConfirm unlock timeHashing inputsPayment IDPostprocessing...Processing...Processing inputsProcessing outputsSigning...Signing inputsUnlock time for this transaction is set to {0}Do you really want to export tx_der\nfor tx_proof?Do you really want to export tx_key?Do you really want to export watch-only credentials?Do you really want to\nstart refresh?Do you really want to\nsync key images?Confirm tagDestination tag:\n{0}Account indexAssociated token accountConfirm multisigExpected feeInstruction contains {0} accounts and its data is {1} bytes long.Instruction dataThe following instruction is a multisig instruction.{0} is provided via a lookup table.Lookup table addressMultiple signersTransaction contains unknown instructions.Transaction requires {0} signers which increases the fee.Account MergeAccount ThresholdsAdd SignerAdd trustAll XLM will be sent toAllow trustBalance IDBump SequenceBuying:Claim Claimable BalanceClear dataClear flagsConfirm IssuerConfirm memoConfirm operationConfirm timeboundsCreate AccountDebited amountDeleteDelete Passive OfferDelete trustDestinationMemo is not set.\nTypically needed when sending to exchanges.Final confirmHashHigh:Home DomainInflation{0} issuerKey:LimitLow:Master Weight:Medium:New OfferNew Passive OfferNo memo set![no restriction]Path PayPath Pay at leastPayPay at mostPre-auth transactionPrice per {0}:Remove SignerRevoke trustSelling:Set dataSet flagsSet sequence to {0}?Sign this transaction made up of {0}and pay {0}\nfor fee?Source accountTrusted AccountUpdateValid from (UTC)Valid to (UTC)Value (SHA-256):Do you want to clear value key {0}?Baker addressBalance:Ballot:Confirm delegationConfirm originationDelegatorProposalRegister delegateRemove delegationSubmit ballotSubmit proposalSubmit proposalsIncrease and retrieve the U2F counter?Set the U2F counter to {0}?Get U2F counterSet U2F counterClaimClaim addressClaim ETH from Everstake?StakeStake addressStake ETH on Everstake?UnstakeUnstake ETH from Everstake?Always AbstainAlways No ConfidenceDelegating to key hash:Delegating to script:Deposit:Vote delegationMore credentialsSelect the credential that you would like to use for authentication.for authenticationSelect credentialCredential detailsUnknown token contract address.Token contract addressInteraction contract addressBase feeClaimClaim SOL from stake account?Claiming SOL to address outside your current wallet.Priority feeStakeStake accountStake SOL?The current wallet isn't the SOL staking withdraw authority.Withdraw authority addressUnstakeUnstake SOL from stake account?Vote accountStake SOL on {0}?Event kind: {0}Max fees and rentMax rent feeApproveAmount allowanceChain IDReview details to approve token spending.Token approvalApprove toApproving unlimited amount of {0}Review details to revoke token approval.Token revocationRevokeRevoke fromUnknown tokenUnknown token addressAll input data ({0} bytes)Provider contract addressConfirm message hashSign withTimeboundsToken infoTransaction sourceTransaction source does not belong to this Trezor.Confirm messageEmpty messageMessage hash:Message hexMessage textSign message hash with {0}Sign message with {0}Destination tag is not set. Typically needed when sending to exchanges.",
                offsets: &[
                    (Self::cardano__addr_base, 4),
                    (Self::cardano__addr_enterprise, 14),
                    (Self::cardano__addr_legacy, 20),
                    (Self::cardano__addr_pointer, 27),
                    (Self::cardano__addr_reward, 33),
                    (Self::cardano__address_no_staking, 62),
                    (Self::cardano__amount_burned_decimals_unknown, 95),
                    (Self::cardano__amount_minted_decimals_unknown, 128),
                    (Self::cardano__amount_sent_decimals_unknown, 159),
                    (Self::cardano__anonymous_pool, 196),
                    (Self::cardano__asset_fingerprint, 214),
                    (Self::cardano__auxiliary_data_hash, 234),
                    (Self::cardano__block, 239),
                    (Self::cardano__catalyst, 247),
                    (Self::cardano__certificate, 258),
                    (Self::cardano__change_output, 271),
                    (Self::cardano__check_all_items, 297),
                    (Self::cardano__choose_level_of_details, 321),
                    (Self::cardano__collateral_input_id, 341),
                    (Self::cardano__collateral_input_index, 364),
                    (Self::cardano__collateral_output_contains_tokens, 409),
                    (Self::cardano__collateral_return, 426),
                    (Self::cardano__confirm_signing_stake_pool, 482),
                    (Self::cardano__confirm_transaction, 501),
                    (Self::cardano__confirming_a_multisig_transaction, 535),
                    (Self::cardano__confirming_a_plutus_transaction, 567),
                    (Self::cardano__confirming_pool_registration, 605),
                    (Self::cardano__confirming_transaction, 630),
                    (Self::cardano__cost, 634),
                    (Self::cardano__credential_mismatch, 678),
                    (Self::cardano__datum_hash, 689),
                    (Self::cardano__delegating_to, 703),
                    (Self::cardano__for_account_and_index_template, 733),
                    (Self::cardano__for_account_template, 749),
                    (Self::cardano__for_key_hash, 762),
                    (Self::cardano__for_script, 773),
                    (Self::cardano__inline_datum, 785),
                    (Self::cardano__input_id, 794),
                    (Self::cardano__input_index, 806),
                    (Self::cardano__intro_text_change, 852),
                    (Self::cardano__intro_text_owned_by_device, 902),
                    (Self::cardano__intro_text_registration_payment, 972),
                    (Self::cardano__key_hash, 980),
                    (Self::cardano__margin, 986),
                    (Self::cardano__multisig_path, 1000),
                    (Self::cardano__nested_scripts_template, 1028),
                    (Self::cardano__network, 1036),
                    (Self::cardano__no_output_tx, 1091),
                    (Self::cardano__nonce, 1097),
                    (Self::cardano__other, 1102),
                    (Self::cardano__path, 1106),
                    (Self::cardano__pledge, 1112),
                    (Self::cardano__pointer, 1119),
                    (Self::cardano__policy_id, 1128),
                    (Self::cardano__pool_metadata_hash, 1147),
                    (Self::cardano__pool_metadata_url, 1165),
                    (Self::cardano__pool_owner, 1176),
                    (Self::cardano__pool_reward_account, 1196),
                    (Self::cardano__reference_input_id, 1215),
                    (Self::cardano__reference_input_index, 1237),
                    (Self::cardano__reference_script, 1253),
                    (Self::cardano__required_signer, 1268),
                    (Self::cardano__reward, 1274),
                    (Self::cardano__reward_address, 1302),
                    (Self::cardano__reward_eligibility_warning, 1380),
                    (Self::cardano__rewards_go_to, 1394),
                    (Self::cardano__script, 1400),
                    (Self::cardano__script_all, 1403),
                    (Self::cardano__script_any, 1406),
                    (Self::cardano__script_data_hash, 1423),
                    (Self::cardano__script_hash, 1435),
                    (Self::cardano__script_invalid_before, 1449),
                    (Self::cardano__script_invalid_hereafter, 1466),
                    (Self::cardano__script_key, 1469),
                    (Self::cardano__script_n_of_k, 1475),
                    (Self::cardano__script_reward, 1488),
                    (Self::cardano__sending, 1495),
                    (Self::cardano__show_simple, 1506),
                    (Self::cardano__sign_tx_path_template, 1531),
                    (Self::cardano__stake_delegation, 1547),
                    (Self::cardano__stake_deregistration, 1571),
                    (Self::cardano__stake_pool_registration, 1593),
                    (Self::cardano__stake_pool_registration_pool_id, 1625),
                    (Self::cardano__stake_registration, 1647),
                    (Self::cardano__staking_key_for_account, 1670),
                    (Self::cardano__to_pool, 1678),
                    (Self::cardano__token_minting_path, 1696),
                    (Self::cardano__total_collateral, 1713),
                    (Self::cardano__transaction, 1724),
                    (Self::cardano__transaction_contains_minting_or_burning, 1778),
                    (Self::cardano__transaction_contains_script_address_no_datum, 1867),
                    (Self::cardano__transaction_id, 1882),
                    (Self::cardano__transaction_no_collateral_input, 1967),
                    (Self::cardano__transaction_no_script_data_hash, 2051),
                    (Self::cardano__transaction_output_contains_tokens, 2100),
                    (Self::cardano__ttl, 2104),
                    (Self::cardano__unknown_collateral_amount, 2130),
                    (Self::cardano__unusual_path, 2146),
                    (Self::cardano__valid_since, 2158),
                    (Self::cardano__verify_script, 2171),
                    (Self::cardano__vote_key_registration, 2201),
                    (Self::cardano__vote_public_key, 2217),
                    (Self::cardano__voting_purpose, 2232),
                    (Self::cardano__warning, 2239),
                    (Self::cardano__weight, 2246),
                    (Self::cardano__withdrawal_for_address_template, 2281),
                    (Self::cardano__x_of_y_signatures_template, 2316),
                    (Self::eos__about_to_sign_template, 2316),
                    (Self::eos__action_name, 2316),
                    (Self::eos__arbitrary_data, 2316),
                    (Self::eos__buy_ram, 2316),
                    (Self::eos__bytes, 2316),
                    (Self::eos__cancel_vote, 2316),
                    (Self::eos__checksum, 2316),
                    (Self::eos__code, 2316),
                    (Self::eos__contract, 2316),
                    (Self::eos__cpu, 2316),
                    (Self::eos__creator, 2316),
                    (Self::eos__delegate, 2316),
                    (Self::eos__delete_auth, 2316),
                    (Self::eos__from, 2316),
                    (Self::eos__link_auth, 2316),
                    (Self::eos__memo, 2316),
                    (Self::eos__name, 2316),
                    (Self::eos__net, 2316),
                    (Self::eos__new_account, 2316),
                    (Self::eos__owner, 2316),
                    (Self::eos__parent, 2316),
                    (Self::eos__payer, 2316),
                    (Self::eos__permission, 2316),
                    (Self::eos__proxy, 2316),
                    (Self::eos__receiver, 2316),
                    (Self::eos__refund, 2316),
                    (Self::eos__requirement, 2316),
                    (Self::eos__sell_ram, 2316),
                    (Self::eos__sender, 2316),
                    (Self::eos__threshold, 2316),
                    (Self::eos__to, 2316),
                    (Self::eos__transfer, 2316),
                    (Self::eos__type, 2316),
                    (Self::eos__undelegate, 2316),
                    (Self::eos__unlink_auth, 2316),
                    (Self::eos__update_auth, 2316),
                    (Self::eos__vote_for_producers, 2316),
                    (Self::eos__vote_for_proxy, 2316),
                    (Self::eos__voter, 2316),
                    (Self::ethereum__amount_sent, 2328),
                    (Self::ethereum__data_size_template, 2343),
                    (Self::ethereum__gas_limit, 2352),
                    (Self::ethereum__gas_price, 2361),
                    (Self::ethereum__max_gas_price, 2376),
                    (Self::ethereum__name_and_version, 2392),
                    (Self::ethereum__new_contract, 2421),
                    (Self::ethereum__no_message_field, 2437),
                    (Self::ethereum__priority_fee, 2453),
                    (Self::ethereum__show_full_array, 2468),
                    (Self::ethereum__show_full_domain, 2484),
                    (Self::ethereum__show_full_message, 2501),
                    (Self::ethereum__show_full_struct, 2517),
                    (Self::ethereum__sign_eip712, 2548),
                    (Self::ethereum__title_input_data, 2558),
                    (Self::ethereum__title_confirm_domain, 2572),
                    (Self::ethereum__title_confirm_message, 2587),
                    (Self::ethereum__title_confirm_struct, 2601),
                    (Self::ethereum__title_confirm_typed_data, 2619),
                    (Self::ethereum__title_signing_address, 2634),
                    (Self::ethereum__units_template, 2643),
                    (Self::ethereum__unknown_token, 2656),
                    (Self::ethereum__valid_signature, 2679),
                    (Self::fido__already_registered, 2697),
                    (Self::fido__device_already_registered, 2753),
                    (Self::fido__device_already_registered_with_template, 2796),
                    (Self::fido__device_not_registered, 2848),
                    (Self::fido__does_not_belong, 2926),
                    (Self::fido__erase_credentials, 2962),
                    (Self::fido__export_credentials, 3025),
                    (Self::fido__not_registered, 3039),
                    (Self::fido__not_registered_with_template, 3078),
                    (Self::fido__please_enable_pin_protection, 3107),
                    (Self::fido__title_authenticate, 3125),
                    (Self::fido__title_import_credential, 3142),
                    (Self::fido__title_list_credentials, 3158),
                    (Self::fido__title_register, 3172),
                    (Self::fido__title_remove_credential, 3189),
                    (Self::fido__title_reset, 3200),
                    (Self::fido__title_u2f_auth, 3216),
                    (Self::fido__title_u2f_register, 3228),
                    (Self::fido__title_verify_user, 3245),
                    (Self::fido__unable_to_verify_user, 3267),
                    (Self::fido__wanna_erase_credentials, 3311),
                    (Self::monero__confirm_export, 3325),
                    (Self::monero__confirm_ki_sync, 3340),
                    (Self::monero__confirm_refresh, 3355),
                    (Self::monero__confirm_unlock_time, 3374),
                    (Self::monero__hashing_inputs, 3388),
                    (Self::monero__payment_id, 3398),
                    (Self::monero__postprocessing, 3415),
                    (Self::monero__processing, 3428),
                    (Self::monero__processing_inputs, 3445),
                    (Self::monero__processing_outputs, 3463),
                    (Self::monero__signing, 3473),
                    (Self::monero__signing_inputs, 3487),
                    (Self::monero__unlock_time_set_template, 3533),
                    (Self::monero__wanna_export_tx_der, 3582),
                    (Self::monero__wanna_export_tx_key, 3618),
                    (Self::monero__wanna_export_watchkey, 3670),
                    (Self::monero__wanna_start_refresh, 3706),
                    (Self::monero__wanna_sync_key_images, 3744),
                    (Self::nem__absolute, 3744),
                    (Self::nem__activate, 3744),
                    (Self::nem__add, 3744),
                    (Self::nem__confirm_action, 3744),
                    (Self::nem__confirm_address, 3744),
                    (Self::nem__confirm_creation_fee, 3744),
                    (Self::nem__confirm_mosaic, 3744),
                    (Self::nem__confirm_multisig_fee, 3744),
                    (Self::nem__confirm_namespace, 3744),
                    (Self::nem__confirm_payload, 3744),
                    (Self::nem__confirm_properties, 3744),
                    (Self::nem__confirm_rental_fee, 3744),
                    (Self::nem__confirm_transfer_of, 3744),
                    (Self::nem__convert_account_to_multisig, 3744),
                    (Self::nem__cosign_transaction_for, 3744),
                    (Self::nem__cosignatory, 3744),
                    (Self::nem__create_mosaic, 3744),
                    (Self::nem__create_namespace, 3744),
                    (Self::nem__deactivate, 3744),
                    (Self::nem__decrease, 3744),
                    (Self::nem__description, 3744),
                    (Self::nem__divisibility_and_levy_cannot_be_shown, 3744),
                    (Self::nem__encrypted, 3744),
                    (Self::nem__final_confirm, 3744),
                    (Self::nem__immutable, 3744),
                    (Self::nem__increase, 3744),
                    (Self::nem__initial_supply, 3744),
                    (Self::nem__initiate_transaction_for, 3744),
                    (Self::nem__levy_divisibility, 3744),
                    (Self::nem__levy_fee, 3744),
                    (Self::nem__levy_fee_of, 3744),
                    (Self::nem__levy_mosaic, 3744),
                    (Self::nem__levy_namespace, 3744),
                    (Self::nem__levy_recipient, 3744),
                    (Self::nem__levy_type, 3744),
                    (Self::nem__modify_supply_for, 3744),
                    (Self::nem__modify_the_number_of_cosignatories_by, 3744),
                    (Self::nem__mutable, 3744),
                    (Self::nem__of, 3744),
                    (Self::nem__percentile, 3744),
                    (Self::nem__raw_units_template, 3744),
                    (Self::nem__remote_harvesting, 3744),
                    (Self::nem__remove, 3744),
                    (Self::nem__set_minimum_cosignatories_to, 3744),
                    (Self::nem__sign_tx_fee_template, 3744),
                    (Self::nem__supply_change, 3744),
                    (Self::nem__supply_units_template, 3744),
                    (Self::nem__transferable, 3744),
                    (Self::nem__under_namespace, 3744),
                    (Self::nem__unencrypted, 3744),
                    (Self::nem__unknown_mosaic, 3744),
                    (Self::ripple__confirm_tag, 3755),
                    (Self::ripple__destination_tag_template, 3775),
                    (Self::solana__account_index, 3788),
                    (Self::solana__associated_token_account, 3812),
                    (Self::solana__confirm_multisig, 3828),
                    (Self::solana__expected_fee, 3840),
                    (Self::solana__instruction_accounts_template, 3905),
                    (Self::solana__instruction_data, 3921),
                    (Self::solana__instruction_is_multisig, 3973),
                    (Self::solana__is_provided_via_lookup_table_template, 4008),
                    (Self::solana__lookup_table_address, 4028),
                    (Self::solana__multiple_signers, 4044),
                    (Self::solana__transaction_contains_unknown_instructions, 4086),
                    (Self::solana__transaction_requires_x_signers_template, 4143),
                    (Self::stellar__account_merge, 4156),
                    (Self::stellar__account_thresholds, 4174),
                    (Self::stellar__add_signer, 4184),
                    (Self::stellar__add_trust, 4193),
                    (Self::stellar__all_will_be_sent_to, 4216),
                    (Self::stellar__allow_trust, 4227),
                    (Self::stellar__balance_id, 4237),
                    (Self::stellar__bump_sequence, 4250),
                    (Self::stellar__buying, 4257),
                    (Self::stellar__claim_claimable_balance, 4280),
                    (Self::stellar__clear_data, 4290),
                    (Self::stellar__clear_flags, 4301),
                    (Self::stellar__confirm_issuer, 4315),
                    (Self::stellar__confirm_memo, 4327),
                    (Self::stellar__confirm_operation, 4344),
                    (Self::stellar__confirm_timebounds, 4362),
                    (Self::stellar__create_account, 4376),
                    (Self::stellar__debited_amount, 4390),
                    (Self::stellar__delete, 4396),
                    (Self::stellar__delete_passive_offer, 4416),
                    (Self::stellar__delete_trust, 4428),
                    (Self::stellar__destination, 4439),
                    (Self::stellar__exchanges_require_memo, 4499),
                    (Self::stellar__final_confirm, 4512),
                    (Self::stellar__hash, 4516),
                    (Self::stellar__high, 4521),
                    (Self::stellar__home_domain, 4532),
                    (Self::stellar__inflation, 4541),
                    (Self::stellar__issuer_template, 4551),
                    (Self::stellar__key, 4555),
                    (Self::stellar__limit, 4560),
                    (Self::stellar__low, 4564),
                    (Self::stellar__master_weight, 4578),
                    (Self::stellar__medium, 4585),
                    (Self::stellar__new_offer, 4594),
                    (Self::stellar__new_passive_offer, 4611),
                    (Self::stellar__no_memo_set, 4623),
                    (Self::stellar__no_restriction, 4639),
                    (Self::stellar__path_pay, 4647),
                    (Self::stellar__path_pay_at_least, 4664),
                    (Self::stellar__pay, 4667),
                    (Self::stellar__pay_at_most, 4678),
                    (Self::stellar__preauth_transaction, 4698),
                    (Self::stellar__price_per_template, 4712),
                    (Self::stellar__remove_signer, 4725),
                    (Self::stellar__revoke_trust, 4737),
                    (Self::stellar__selling, 4745),
                    (Self::stellar__set_data, 4753),
                    (Self::stellar__set_flags, 4762),
                    (Self::stellar__set_sequence_to_template, 4782),
                    (Self::stellar__sign_tx_count_template, 4818),
                    (Self::stellar__sign_tx_fee_template, 4838),
                    (Self::stellar__source_account, 4852),
                    (Self::stellar__trusted_account, 4867),
                    (Self::stellar__update, 4873),
                    (Self::stellar__valid_from, 4889),
                    (Self::stellar__valid_to, 4903),
                    (Self::stellar__value_sha256, 4919),
                    (Self::stellar__wanna_clean_value_key_template, 4954),
                    (Self::tezos__baker_address, 4967),
                    (Self::tezos__balance, 4975),
                    (Self::tezos__ballot, 4982),
                    (Self::tezos__confirm_delegation, 5000),
                    (Self::tezos__confirm_origination, 5019),
                    (Self::tezos__delegator, 5028),
                    (Self::tezos__proposal, 5036),
                    (Self::tezos__register_delegate, 5053),
                    (Self::tezos__remove_delegation, 5070),
                    (Self::tezos__submit_ballot, 5083),
                    (Self::tezos__submit_proposal, 5098),
                    (Self::tezos__submit_proposals, 5114),
                    (Self::u2f__get, 5152),
                    (Self::u2f__set_template, 5179),
                    (Self::u2f__title_get, 5194),
                    (Self::u2f__title_set, 5209),
                    (Self::ethereum__staking_claim, 5214),
                    (Self::ethereum__staking_claim_address, 5227),
                    (Self::ethereum__staking_claim_intro, 5252),
                    (Self::ethereum__staking_stake, 5257),
                    (Self::ethereum__staking_stake_address, 5270),
                    (Self::ethereum__staking_stake_intro, 5293),
                    (Self::ethereum__staking_unstake, 5300),
                    (Self::ethereum__staking_unstake_intro, 5327),
                    (Self::cardano__always_abstain, 5341),
                    (Self::cardano__always_no_confidence, 5361),
                    (Self::cardano__delegating_to_key_hash, 5384),
                    (Self::cardano__delegating_to_script, 5405),
                    (Self::cardano__deposit, 5413),
                    (Self::cardano__vote_delegation, 5428),
                    (Self::fido__more_credentials, 5444),
                    (Self::fido__select_intro, 5512),
                    (Self::fido__title_for_authentication, 5530),
                    (Self::fido__title_select_credential, 5547),
                    (Self::fido__title_credential_details, 5565),
                    (Self::ethereum__unknown_contract_address, 5596),
                    (Self::ethereum__token_contract, 5618),
                    (Self::ethereum__interaction_contract, 5646),
                    (Self::solana__base_fee, 5654),
                    (Self::solana__claim, 5659),
                    (Self::solana__claim_question, 5688),
                    (Self::solana__claim_recipient_warning, 5740),
                    (Self::solana__priority_fee, 5752),
                    (Self::solana__stake, 5757),
                    (Self::solana__stake_account, 5770),
                    (Self::solana__stake_question, 5780),
                    (Self::solana__stake_withdrawal_warning, 5840),
                    (Self::solana__stake_withdrawal_warning_title, 5866),
                    (Self::solana__unstake, 5873),
                    (Self::solana__unstake_question, 5904),
                    (Self::solana__vote_account, 5916),
                    (Self::solana__stake_on_question, 5933),
                    (Self::nostr__event_kind_template, 5948),
                    (Self::solana__max_fees_rent, 5965),
                    (Self::solana__max_rent_fee, 5977),
                    (Self::ethereum__approve, 5984),
                    (Self::ethereum__approve_amount_allowance, 6000),
                    (Self::ethereum__approve_chain_id, 6008),
                    (Self::ethereum__approve_intro, 6049),
                    (Self::ethereum__approve_intro_title, 6063),
                    (Self::ethereum__approve_to, 6073),
                    (Self::ethereum__approve_unlimited_template, 6106),
                    (Self::ethereum__approve_intro_revoke, 6146),
                    (Self::ethereum__approve_intro_title_revoke, 6162),
                    (Self::ethereum__approve_revoke, 6168),
                    (Self::ethereum__approve_revoke_from, 6179),
                    (Self::solana__unknown_token, 6192),
                    (Self::solana__unknown_token_address, 6213),
                    (Self::ethereum__title_all_input_data_template, 6239),
                    (Self::ethereum__contract_address, 6264),
                    (Self::ethereum__title_confirm_message_hash, 6284),
                    (Self::stellar__sign_with, 6293),
                    (Self::stellar__timebounds, 6303),
                    (Self::stellar__token_info, 6313),
                    (Self::stellar__transaction_source, 6331),
                    (Self::stellar__transaction_source_diff_warning, 6381),
                    (Self::cardano__confirm_message, 6396),
                    (Self::cardano__empty_message, 6409),
                    (Self::cardano__message_hash, 6422),
                    (Self::cardano__message_hex, 6433),
                    (Self::cardano__message_text, 6445),
                    (Self::cardano__sign_message_hash_path_template, 6471),
                    (Self::cardano__sign_message_path_template, 6492),
                    (Self::ripple__destination_tag_missing, 6563),
                ],
            };

            #[cfg(feature = "debug")]
            const DEBUG_BLOB: StringsBlob = StringsBlob {
                text: "Loading seedLoading private seed is not recommended.",
                offsets: &[
                    (Self::debug__loading_seed, 12),
                    (Self::debug__loading_seed_not_recommended, 52),
                ],
            };

            pub const BLOBS: &'static [StringsBlob] = &[
                Self::BTC_ONLY_BLOB,
                #[cfg(feature = "universal_fw")]
                Self::ALTCOIN_BLOB,
                #[cfg(feature = "debug")]
                Self::DEBUG_BLOB,
            ];
        }
    }
}

#[cfg(feature = "micropython")]
impl TranslatedString {
    pub const QSTR_MAP: &'static [(Qstr, Self)] = &[
        (Qstr::MP_QSTR_addr_mismatch__contact_support_at, Self::addr_mismatch__contact_support_at),
        (Qstr::MP_QSTR_addr_mismatch__key_mismatch, Self::addr_mismatch__key_mismatch),
        (Qstr::MP_QSTR_addr_mismatch__mismatch, Self::addr_mismatch__mismatch),
        (Qstr::MP_QSTR_addr_mismatch__support_url, Self::addr_mismatch__support_url),
        (Qstr::MP_QSTR_addr_mismatch__wrong_derivation_path, Self::addr_mismatch__wrong_derivation_path),
        (Qstr::MP_QSTR_addr_mismatch__xpub_mismatch, Self::addr_mismatch__xpub_mismatch),
        (Qstr::MP_QSTR_address__cancel_contact_support, Self::address__cancel_contact_support),
        (Qstr::MP_QSTR_address__cancel_receive, Self::address__cancel_receive),
        (Qstr::MP_QSTR_address__check_with_source, Self::address__check_with_source),
        (Qstr::MP_QSTR_address__coin_address_template, Self::address__coin_address_template),
        (Qstr::MP_QSTR_address__confirmed, Self::address__confirmed),
        (Qstr::MP_QSTR_address__public_key, Self::address__public_key),
        (Qstr::MP_QSTR_address__public_key_confirmed, Self::address__public_key_confirmed),
        (Qstr::MP_QSTR_address__qr_code, Self::address__qr_code),
        (Qstr::MP_QSTR_address__title_cosigner, Self::address__title_cosigner),
        (Qstr::MP_QSTR_address__title_provider_address, Self::address__title_provider_address),
        (Qstr::MP_QSTR_address__title_receive_address, Self::address__title_receive_address),
        (Qstr::MP_QSTR_address__title_refund_address, Self::address__title_refund_address),
        (Qstr::MP_QSTR_address__title_yours, Self::address__title_yours),
        (Qstr::MP_QSTR_address__xpub, Self::address__xpub),
        (Qstr::MP_QSTR_address_details__account_info, Self::address_details__account_info),
        (Qstr::MP_QSTR_address_details__derivation_path, Self::address_details__derivation_path),
        (Qstr::MP_QSTR_address_details__derivation_path_colon, Self::address_details__derivation_path_colon),
        (Qstr::MP_QSTR_address_details__title_receive_address, Self::address_details__title_receive_address),
        (Qstr::MP_QSTR_address_details__title_receiving_to, Self::address_details__title_receiving_to),
        (Qstr::MP_QSTR_authenticate__confirm_template, Self::authenticate__confirm_template),
        (Qstr::MP_QSTR_authenticate__header, Self::authenticate__header),
        (Qstr::MP_QSTR_auto_lock__change_template, Self::auto_lock__change_template),
        (Qstr::MP_QSTR_auto_lock__description, Self::auto_lock__description),
        (Qstr::MP_QSTR_auto_lock__on_battery, Self::auto_lock__on_battery),
        (Qstr::MP_QSTR_auto_lock__on_usb, Self::auto_lock__on_usb),
        (Qstr::MP_QSTR_auto_lock__title, Self::auto_lock__title),
        (Qstr::MP_QSTR_auto_lock__turned_on, Self::auto_lock__turned_on),
        (Qstr::MP_QSTR_backup__can_back_up_anytime, Self::backup__can_back_up_anytime),
        (Qstr::MP_QSTR_backup__create_backup_to_prevent_loss, Self::backup__create_backup_to_prevent_loss),
        (Qstr::MP_QSTR_backup__info_multi_share_backup, Self::backup__info_multi_share_backup),
        (Qstr::MP_QSTR_backup__info_single_share_backup, Self::backup__info_single_share_backup),
        (Qstr::MP_QSTR_backup__it_should_be_backed_up, Self::backup__it_should_be_backed_up),
        (Qstr::MP_QSTR_backup__it_should_be_backed_up_now, Self::backup__it_should_be_backed_up_now),
        (Qstr::MP_QSTR_backup__new_wallet_created, Self::backup__new_wallet_created),
        (Qstr::MP_QSTR_backup__new_wallet_successfully_created, Self::backup__new_wallet_successfully_created),
        (Qstr::MP_QSTR_backup__not_recommend, Self::backup__not_recommend),
        (Qstr::MP_QSTR_backup__recover_anytime, Self::backup__recover_anytime),
        (Qstr::MP_QSTR_backup__title_backup_completed, Self::backup__title_backup_completed),
        (Qstr::MP_QSTR_backup__title_backup_wallet, Self::backup__title_backup_wallet),
        (Qstr::MP_QSTR_backup__title_create_wallet_backup, Self::backup__title_create_wallet_backup),
        (Qstr::MP_QSTR_backup__title_skip, Self::backup__title_skip),
        (Qstr::MP_QSTR_backup__want_to_skip, Self::backup__want_to_skip),
        (Qstr::MP_QSTR_bitcoin__commitment_data, Self::bitcoin__commitment_data),
        (Qstr::MP_QSTR_bitcoin__confirm_locktime, Self::bitcoin__confirm_locktime),
        (Qstr::MP_QSTR_bitcoin__create_proof_of_ownership, Self::bitcoin__create_proof_of_ownership),
        (Qstr::MP_QSTR_bitcoin__high_mining_fee_template, Self::bitcoin__high_mining_fee_template),
        (Qstr::MP_QSTR_bitcoin__locktime_no_effect, Self::bitcoin__locktime_no_effect),
        (Qstr::MP_QSTR_bitcoin__locktime_set_to, Self::bitcoin__locktime_set_to),
        (Qstr::MP_QSTR_bitcoin__locktime_set_to_blockheight, Self::bitcoin__locktime_set_to_blockheight),
        (Qstr::MP_QSTR_bitcoin__lot_of_change_outputs, Self::bitcoin__lot_of_change_outputs),
        (Qstr::MP_QSTR_bitcoin__multiple_accounts, Self::bitcoin__multiple_accounts),
        (Qstr::MP_QSTR_bitcoin__new_fee_rate, Self::bitcoin__new_fee_rate),
        (Qstr::MP_QSTR_bitcoin__simple_send_of, Self::bitcoin__simple_send_of),
        (Qstr::MP_QSTR_bitcoin__ticket_amount, Self::bitcoin__ticket_amount),
        (Qstr::MP_QSTR_bitcoin__title_confirm_details, Self::bitcoin__title_confirm_details),
        (Qstr::MP_QSTR_bitcoin__title_finalize_transaction, Self::bitcoin__title_finalize_transaction),
        (Qstr::MP_QSTR_bitcoin__title_high_mining_fee, Self::bitcoin__title_high_mining_fee),
        (Qstr::MP_QSTR_bitcoin__title_meld_transaction, Self::bitcoin__title_meld_transaction),
        (Qstr::MP_QSTR_bitcoin__title_modify_amount, Self::bitcoin__title_modify_amount),
        (Qstr::MP_QSTR_bitcoin__title_payjoin, Self::bitcoin__title_payjoin),
        (Qstr::MP_QSTR_bitcoin__title_proof_of_ownership, Self::bitcoin__title_proof_of_ownership),
        (Qstr::MP_QSTR_bitcoin__title_purchase_ticket, Self::bitcoin__title_purchase_ticket),
        (Qstr::MP_QSTR_bitcoin__title_update_transaction, Self::bitcoin__title_update_transaction),
        (Qstr::MP_QSTR_bitcoin__unknown_path, Self::bitcoin__unknown_path),
        (Qstr::MP_QSTR_bitcoin__unknown_transaction, Self::bitcoin__unknown_transaction),
        (Qstr::MP_QSTR_bitcoin__unusually_high_fee, Self::bitcoin__unusually_high_fee),
        (Qstr::MP_QSTR_bitcoin__unverified_external_inputs, Self::bitcoin__unverified_external_inputs),
        (Qstr::MP_QSTR_bitcoin__valid_signature, Self::bitcoin__valid_signature),
        (Qstr::MP_QSTR_bitcoin__voting_rights, Self::bitcoin__voting_rights),
        (Qstr::MP_QSTR_ble__apps_connected, Self::ble__apps_connected),
        (Qstr::MP_QSTR_ble__disable, Self::ble__disable),
        (Qstr::MP_QSTR_ble__enable, Self::ble__enable),
        (Qstr::MP_QSTR_ble__forget_all, Self::ble__forget_all),
        (Qstr::MP_QSTR_ble__forget_all_description, Self::ble__forget_all_description),
        (Qstr::MP_QSTR_ble__forget_all_devices, Self::ble__forget_all_devices),
        (Qstr::MP_QSTR_ble__forget_all_success, Self::ble__forget_all_success),
        (Qstr::MP_QSTR_ble__forget_this_description, Self::ble__forget_this_description),
        (Qstr::MP_QSTR_ble__forget_this_device, Self::ble__forget_this_device),
        (Qstr::MP_QSTR_ble__forget_this_success, Self::ble__forget_this_success),
        (Qstr::MP_QSTR_ble__host_info, Self::ble__host_info),
        (Qstr::MP_QSTR_ble__limit_reached, Self::ble__limit_reached),
        (Qstr::MP_QSTR_ble__mac_address, Self::ble__mac_address),
        (Qstr::MP_QSTR_ble__manage_paired, Self::ble__manage_paired),
        (Qstr::MP_QSTR_ble__must_be_enabled, Self::ble__must_be_enabled),
        (Qstr::MP_QSTR_ble__pair_new, Self::ble__pair_new),
        (Qstr::MP_QSTR_ble__pair_title, Self::ble__pair_title),
        (Qstr::MP_QSTR_ble__pairing_match, Self::ble__pairing_match),
        (Qstr::MP_QSTR_ble__pairing_title, Self::ble__pairing_title),
        (Qstr::MP_QSTR_ble__unpair_all, Self::ble__unpair_all),
        (Qstr::MP_QSTR_ble__unpair_current, Self::ble__unpair_current),
        (Qstr::MP_QSTR_ble__unpair_title, Self::ble__unpair_title),
        (Qstr::MP_QSTR_ble__version, Self::ble__version),
        (Qstr::MP_QSTR_ble__waiting_for_host, Self::ble__waiting_for_host),
        (Qstr::MP_QSTR_brightness__change_title, Self::brightness__change_title),
        (Qstr::MP_QSTR_brightness__changed_title, Self::brightness__changed_title),
        (Qstr::MP_QSTR_brightness__title, Self::brightness__title),
        (Qstr::MP_QSTR_buttons__abort, Self::buttons__abort),
        (Qstr::MP_QSTR_buttons__access, Self::buttons__access),
        (Qstr::MP_QSTR_buttons__again, Self::buttons__again),
        (Qstr::MP_QSTR_buttons__allow, Self::buttons__allow),
        (Qstr::MP_QSTR_buttons__back, Self::buttons__back),
        (Qstr::MP_QSTR_buttons__back_up, Self::buttons__back_up),
        (Qstr::MP_QSTR_buttons__cancel, Self::buttons__cancel),
        (Qstr::MP_QSTR_buttons__change, Self::buttons__change),
        (Qstr::MP_QSTR_buttons__check, Self::buttons__check),
        (Qstr::MP_QSTR_buttons__check_again, Self::buttons__check_again),
        (Qstr::MP_QSTR_buttons__close, Self::buttons__close),
        (Qstr::MP_QSTR_buttons__confirm, Self::buttons__confirm),
        (Qstr::MP_QSTR_buttons__continue, Self::buttons__continue),
        (Qstr::MP_QSTR_buttons__details, Self::buttons__details),
        (Qstr::MP_QSTR_buttons__enable, Self::buttons__enable),
        (Qstr::MP_QSTR_buttons__enter, Self::buttons__enter),
        (Qstr::MP_QSTR_buttons__enter_share, Self::buttons__enter_share),
        (Qstr::MP_QSTR_buttons__export, Self::buttons__export),
        (Qstr::MP_QSTR_buttons__finish, Self::buttons__finish),
        (Qstr::MP_QSTR_buttons__format, Self::buttons__format),
        (Qstr::MP_QSTR_buttons__go_back, Self::buttons__go_back),
        (Qstr::MP_QSTR_buttons__hold_to_confirm, Self::buttons__hold_to_confirm),
        (Qstr::MP_QSTR_buttons__info, Self::buttons__info),
        (Qstr::MP_QSTR_buttons__install, Self::buttons__install),
        (Qstr::MP_QSTR_buttons__more_info, Self::buttons__more_info),
        (Qstr::MP_QSTR_buttons__ok_i_understand, Self::buttons__ok_i_understand),
        (Qstr::MP_QSTR_buttons__purchase, Self::buttons__purchase),
        (Qstr::MP_QSTR_buttons__quit, Self::buttons__quit),
        (Qstr::MP_QSTR_buttons__restart, Self::buttons__restart),
        (Qstr::MP_QSTR_buttons__retry, Self::buttons__retry),
        (Qstr::MP_QSTR_buttons__select, Self::buttons__select),
        (Qstr::MP_QSTR_buttons__set, Self::buttons__set),
        (Qstr::MP_QSTR_buttons__show_all, Self::buttons__show_all),
        (Qstr::MP_QSTR_buttons__show_details, Self::buttons__show_details),
        (Qstr::MP_QSTR_buttons__show_words, Self::buttons__show_words),
        (Qstr::MP_QSTR_buttons__skip, Self::buttons__skip),
        (Qstr::MP_QSTR_buttons__try_again, Self::buttons__try_again),
        (Qstr::MP_QSTR_buttons__turn_off, Self::buttons__turn_off),
        (Qstr::MP_QSTR_buttons__turn_on, Self::buttons__turn_on),
        (Qstr::MP_QSTR_buttons__view, Self::buttons__view),
        (Qstr::MP_QSTR_buttons__view_all_data, Self::buttons__view_all_data),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__addr_base, Self::cardano__addr_base),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__addr_enterprise, Self::cardano__addr_enterprise),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__addr_legacy, Self::cardano__addr_legacy),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__addr_pointer, Self::cardano__addr_pointer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__addr_reward, Self::cardano__addr_reward),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__address_no_staking, Self::cardano__address_no_staking),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__always_abstain, Self::cardano__always_abstain),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__always_no_confidence, Self::cardano__always_no_confidence),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__amount_burned_decimals_unknown, Self::cardano__amount_burned_decimals_unknown),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__amount_minted_decimals_unknown, Self::cardano__amount_minted_decimals_unknown),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__amount_sent_decimals_unknown, Self::cardano__amount_sent_decimals_unknown),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__anonymous_pool, Self::cardano__anonymous_pool),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__asset_fingerprint, Self::cardano__asset_fingerprint),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__auxiliary_data_hash, Self::cardano__auxiliary_data_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__block, Self::cardano__block),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__catalyst, Self::cardano__catalyst),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__certificate, Self::cardano__certificate),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__change_output, Self::cardano__change_output),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__check_all_items, Self::cardano__check_all_items),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__choose_level_of_details, Self::cardano__choose_level_of_details),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__collateral_input_id, Self::cardano__collateral_input_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__collateral_input_index, Self::cardano__collateral_input_index),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__collateral_output_contains_tokens, Self::cardano__collateral_output_contains_tokens),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__collateral_return, Self::cardano__collateral_return),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__confirm_message, Self::cardano__confirm_message),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__confirm_signing_stake_pool, Self::cardano__confirm_signing_stake_pool),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__confirm_transaction, Self::cardano__confirm_transaction),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__confirming_a_multisig_transaction, Self::cardano__confirming_a_multisig_transaction),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__confirming_a_plutus_transaction, Self::cardano__confirming_a_plutus_transaction),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__confirming_pool_registration, Self::cardano__confirming_pool_registration),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__confirming_transaction, Self::cardano__confirming_transaction),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__cost, Self::cardano__cost),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__credential_mismatch, Self::cardano__credential_mismatch),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__datum_hash, Self::cardano__datum_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__delegating_to, Self::cardano__delegating_to),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__delegating_to_key_hash, Self::cardano__delegating_to_key_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__delegating_to_script, Self::cardano__delegating_to_script),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__deposit, Self::cardano__deposit),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__empty_message, Self::cardano__empty_message),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__for_account_and_index_template, Self::cardano__for_account_and_index_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__for_account_template, Self::cardano__for_account_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__for_key_hash, Self::cardano__for_key_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__for_script, Self::cardano__for_script),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__inline_datum, Self::cardano__inline_datum),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__input_id, Self::cardano__input_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__input_index, Self::cardano__input_index),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__intro_text_change, Self::cardano__intro_text_change),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__intro_text_owned_by_device, Self::cardano__intro_text_owned_by_device),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__intro_text_registration_payment, Self::cardano__intro_text_registration_payment),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__key_hash, Self::cardano__key_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__margin, Self::cardano__margin),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__message_hash, Self::cardano__message_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__message_hex, Self::cardano__message_hex),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__message_text, Self::cardano__message_text),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__multisig_path, Self::cardano__multisig_path),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__nested_scripts_template, Self::cardano__nested_scripts_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__network, Self::cardano__network),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__no_output_tx, Self::cardano__no_output_tx),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__nonce, Self::cardano__nonce),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__other, Self::cardano__other),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__path, Self::cardano__path),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__pledge, Self::cardano__pledge),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__pointer, Self::cardano__pointer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__policy_id, Self::cardano__policy_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__pool_metadata_hash, Self::cardano__pool_metadata_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__pool_metadata_url, Self::cardano__pool_metadata_url),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__pool_owner, Self::cardano__pool_owner),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__pool_reward_account, Self::cardano__pool_reward_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__reference_input_id, Self::cardano__reference_input_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__reference_input_index, Self::cardano__reference_input_index),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__reference_script, Self::cardano__reference_script),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__required_signer, Self::cardano__required_signer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__reward, Self::cardano__reward),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__reward_address, Self::cardano__reward_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__reward_eligibility_warning, Self::cardano__reward_eligibility_warning),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__rewards_go_to, Self::cardano__rewards_go_to),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script, Self::cardano__script),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_all, Self::cardano__script_all),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_any, Self::cardano__script_any),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_data_hash, Self::cardano__script_data_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_hash, Self::cardano__script_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_invalid_before, Self::cardano__script_invalid_before),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_invalid_hereafter, Self::cardano__script_invalid_hereafter),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_key, Self::cardano__script_key),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_n_of_k, Self::cardano__script_n_of_k),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__script_reward, Self::cardano__script_reward),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__sending, Self::cardano__sending),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__show_simple, Self::cardano__show_simple),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__sign_message_hash_path_template, Self::cardano__sign_message_hash_path_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__sign_message_path_template, Self::cardano__sign_message_path_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__sign_tx_path_template, Self::cardano__sign_tx_path_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__stake_delegation, Self::cardano__stake_delegation),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__stake_deregistration, Self::cardano__stake_deregistration),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__stake_pool_registration, Self::cardano__stake_pool_registration),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__stake_pool_registration_pool_id, Self::cardano__stake_pool_registration_pool_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__stake_registration, Self::cardano__stake_registration),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__staking_key_for_account, Self::cardano__staking_key_for_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__to_pool, Self::cardano__to_pool),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__token_minting_path, Self::cardano__token_minting_path),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__total_collateral, Self::cardano__total_collateral),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__transaction, Self::cardano__transaction),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__transaction_contains_minting_or_burning, Self::cardano__transaction_contains_minting_or_burning),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__transaction_contains_script_address_no_datum, Self::cardano__transaction_contains_script_address_no_datum),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__transaction_id, Self::cardano__transaction_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__transaction_no_collateral_input, Self::cardano__transaction_no_collateral_input),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__transaction_no_script_data_hash, Self::cardano__transaction_no_script_data_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__transaction_output_contains_tokens, Self::cardano__transaction_output_contains_tokens),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__ttl, Self::cardano__ttl),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__unknown_collateral_amount, Self::cardano__unknown_collateral_amount),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__unusual_path, Self::cardano__unusual_path),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__valid_since, Self::cardano__valid_since),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__verify_script, Self::cardano__verify_script),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__vote_delegation, Self::cardano__vote_delegation),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__vote_key_registration, Self::cardano__vote_key_registration),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__vote_public_key, Self::cardano__vote_public_key),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__voting_purpose, Self::cardano__voting_purpose),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__warning, Self::cardano__warning),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__weight, Self::cardano__weight),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__withdrawal_for_address_template, Self::cardano__withdrawal_for_address_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_cardano__x_of_y_signatures_template, Self::cardano__x_of_y_signatures_template),
        (Qstr::MP_QSTR_coinjoin__access_account, Self::coinjoin__access_account),
        (Qstr::MP_QSTR_coinjoin__do_not_disconnect, Self::coinjoin__do_not_disconnect),
        (Qstr::MP_QSTR_coinjoin__max_mining_fee, Self::coinjoin__max_mining_fee),
        (Qstr::MP_QSTR_coinjoin__max_rounds, Self::coinjoin__max_rounds),
        (Qstr::MP_QSTR_coinjoin__title, Self::coinjoin__title),
        (Qstr::MP_QSTR_coinjoin__title_progress, Self::coinjoin__title_progress),
        (Qstr::MP_QSTR_coinjoin__waiting_for_others, Self::coinjoin__waiting_for_others),
        (Qstr::MP_QSTR_confirm_total__fee_rate, Self::confirm_total__fee_rate),
        (Qstr::MP_QSTR_confirm_total__fee_rate_colon, Self::confirm_total__fee_rate_colon),
        (Qstr::MP_QSTR_confirm_total__sending_from_account, Self::confirm_total__sending_from_account),
        (Qstr::MP_QSTR_confirm_total__title_fee, Self::confirm_total__title_fee),
        (Qstr::MP_QSTR_confirm_total__title_sending_from, Self::confirm_total__title_sending_from),
        #[cfg(feature = "debug")]
        (Qstr::MP_QSTR_debug__loading_seed, Self::debug__loading_seed),
        #[cfg(feature = "debug")]
        (Qstr::MP_QSTR_debug__loading_seed_not_recommended, Self::debug__loading_seed_not_recommended),
        (Qstr::MP_QSTR_device_name__change_template, Self::device_name__change_template),
        (Qstr::MP_QSTR_device_name__changed, Self::device_name__changed),
        (Qstr::MP_QSTR_device_name__continue_with_empty_label, Self::device_name__continue_with_empty_label),
        (Qstr::MP_QSTR_device_name__enter, Self::device_name__enter),
        (Qstr::MP_QSTR_device_name__title, Self::device_name__title),
        (Qstr::MP_QSTR_entropy__send, Self::entropy__send),
        (Qstr::MP_QSTR_entropy__title_confirm, Self::entropy__title_confirm),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__about_to_sign_template, Self::eos__about_to_sign_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__action_name, Self::eos__action_name),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__arbitrary_data, Self::eos__arbitrary_data),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__buy_ram, Self::eos__buy_ram),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__bytes, Self::eos__bytes),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__cancel_vote, Self::eos__cancel_vote),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__checksum, Self::eos__checksum),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__code, Self::eos__code),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__contract, Self::eos__contract),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__cpu, Self::eos__cpu),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__creator, Self::eos__creator),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__delegate, Self::eos__delegate),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__delete_auth, Self::eos__delete_auth),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__from, Self::eos__from),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__link_auth, Self::eos__link_auth),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__memo, Self::eos__memo),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__name, Self::eos__name),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__net, Self::eos__net),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__new_account, Self::eos__new_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__owner, Self::eos__owner),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__parent, Self::eos__parent),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__payer, Self::eos__payer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__permission, Self::eos__permission),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__proxy, Self::eos__proxy),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__receiver, Self::eos__receiver),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__refund, Self::eos__refund),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__requirement, Self::eos__requirement),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__sell_ram, Self::eos__sell_ram),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__sender, Self::eos__sender),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__threshold, Self::eos__threshold),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__to, Self::eos__to),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__transfer, Self::eos__transfer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__type, Self::eos__type),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__undelegate, Self::eos__undelegate),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__unlink_auth, Self::eos__unlink_auth),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__update_auth, Self::eos__update_auth),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__vote_for_producers, Self::eos__vote_for_producers),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__vote_for_proxy, Self::eos__vote_for_proxy),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_eos__voter, Self::eos__voter),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__amount_sent, Self::ethereum__amount_sent),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve, Self::ethereum__approve),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_amount_allowance, Self::ethereum__approve_amount_allowance),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_chain_id, Self::ethereum__approve_chain_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_intro, Self::ethereum__approve_intro),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_intro_revoke, Self::ethereum__approve_intro_revoke),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_intro_title, Self::ethereum__approve_intro_title),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_intro_title_revoke, Self::ethereum__approve_intro_title_revoke),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_revoke, Self::ethereum__approve_revoke),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_revoke_from, Self::ethereum__approve_revoke_from),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_to, Self::ethereum__approve_to),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__approve_unlimited_template, Self::ethereum__approve_unlimited_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__contract_address, Self::ethereum__contract_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__data_size_template, Self::ethereum__data_size_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__gas_limit, Self::ethereum__gas_limit),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__gas_price, Self::ethereum__gas_price),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__interaction_contract, Self::ethereum__interaction_contract),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__max_gas_price, Self::ethereum__max_gas_price),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__name_and_version, Self::ethereum__name_and_version),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__new_contract, Self::ethereum__new_contract),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__no_message_field, Self::ethereum__no_message_field),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__priority_fee, Self::ethereum__priority_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__show_full_array, Self::ethereum__show_full_array),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__show_full_domain, Self::ethereum__show_full_domain),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__show_full_message, Self::ethereum__show_full_message),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__show_full_struct, Self::ethereum__show_full_struct),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__sign_eip712, Self::ethereum__sign_eip712),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_claim, Self::ethereum__staking_claim),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_claim_address, Self::ethereum__staking_claim_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_claim_intro, Self::ethereum__staking_claim_intro),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_stake, Self::ethereum__staking_stake),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_stake_address, Self::ethereum__staking_stake_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_stake_intro, Self::ethereum__staking_stake_intro),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_unstake, Self::ethereum__staking_unstake),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__staking_unstake_intro, Self::ethereum__staking_unstake_intro),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_all_input_data_template, Self::ethereum__title_all_input_data_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_confirm_domain, Self::ethereum__title_confirm_domain),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_confirm_message, Self::ethereum__title_confirm_message),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_confirm_message_hash, Self::ethereum__title_confirm_message_hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_confirm_struct, Self::ethereum__title_confirm_struct),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_confirm_typed_data, Self::ethereum__title_confirm_typed_data),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_input_data, Self::ethereum__title_input_data),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_signing_address, Self::ethereum__title_signing_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__token_contract, Self::ethereum__token_contract),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__units_template, Self::ethereum__units_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__unknown_contract_address, Self::ethereum__unknown_contract_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__unknown_token, Self::ethereum__unknown_token),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__valid_signature, Self::ethereum__valid_signature),
        (Qstr::MP_QSTR_experimental_mode__enable, Self::experimental_mode__enable),
        (Qstr::MP_QSTR_experimental_mode__only_for_dev, Self::experimental_mode__only_for_dev),
        (Qstr::MP_QSTR_experimental_mode__title, Self::experimental_mode__title),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__already_registered, Self::fido__already_registered),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__device_already_registered, Self::fido__device_already_registered),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__device_already_registered_with_template, Self::fido__device_already_registered_with_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__device_not_registered, Self::fido__device_not_registered),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__does_not_belong, Self::fido__does_not_belong),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__erase_credentials, Self::fido__erase_credentials),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__export_credentials, Self::fido__export_credentials),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__more_credentials, Self::fido__more_credentials),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__not_registered, Self::fido__not_registered),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__not_registered_with_template, Self::fido__not_registered_with_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__please_enable_pin_protection, Self::fido__please_enable_pin_protection),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__select_intro, Self::fido__select_intro),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_authenticate, Self::fido__title_authenticate),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_credential_details, Self::fido__title_credential_details),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_for_authentication, Self::fido__title_for_authentication),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_import_credential, Self::fido__title_import_credential),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_list_credentials, Self::fido__title_list_credentials),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_register, Self::fido__title_register),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_remove_credential, Self::fido__title_remove_credential),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_reset, Self::fido__title_reset),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_select_credential, Self::fido__title_select_credential),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_u2f_auth, Self::fido__title_u2f_auth),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_u2f_register, Self::fido__title_u2f_register),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__title_verify_user, Self::fido__title_verify_user),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__unable_to_verify_user, Self::fido__unable_to_verify_user),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_fido__wanna_erase_credentials, Self::fido__wanna_erase_credentials),
        (Qstr::MP_QSTR_firmware_update__restart, Self::firmware_update__restart),
        (Qstr::MP_QSTR_firmware_update__title, Self::firmware_update__title),
        (Qstr::MP_QSTR_firmware_update__title_fingerprint, Self::firmware_update__title_fingerprint),
        (Qstr::MP_QSTR_haptic_feedback__disable, Self::haptic_feedback__disable),
        (Qstr::MP_QSTR_haptic_feedback__enable, Self::haptic_feedback__enable),
        (Qstr::MP_QSTR_haptic_feedback__subtitle, Self::haptic_feedback__subtitle),
        (Qstr::MP_QSTR_haptic_feedback__title, Self::haptic_feedback__title),
        (Qstr::MP_QSTR_homescreen__backup_needed_info, Self::homescreen__backup_needed_info),
        (Qstr::MP_QSTR_homescreen__click_to_connect, Self::homescreen__click_to_connect),
        (Qstr::MP_QSTR_homescreen__click_to_unlock, Self::homescreen__click_to_unlock),
        (Qstr::MP_QSTR_homescreen__firmware_type, Self::homescreen__firmware_type),
        (Qstr::MP_QSTR_homescreen__firmware_version, Self::homescreen__firmware_version),
        (Qstr::MP_QSTR_homescreen__set_default, Self::homescreen__set_default),
        (Qstr::MP_QSTR_homescreen__settings_subtitle, Self::homescreen__settings_subtitle),
        (Qstr::MP_QSTR_homescreen__settings_title, Self::homescreen__settings_title),
        (Qstr::MP_QSTR_homescreen__title_backup_failed, Self::homescreen__title_backup_failed),
        (Qstr::MP_QSTR_homescreen__title_backup_needed, Self::homescreen__title_backup_needed),
        (Qstr::MP_QSTR_homescreen__title_coinjoin_authorized, Self::homescreen__title_coinjoin_authorized),
        (Qstr::MP_QSTR_homescreen__title_experimental_mode, Self::homescreen__title_experimental_mode),
        (Qstr::MP_QSTR_homescreen__title_no_usb_connection, Self::homescreen__title_no_usb_connection),
        (Qstr::MP_QSTR_homescreen__title_pin_not_set, Self::homescreen__title_pin_not_set),
        (Qstr::MP_QSTR_homescreen__title_seedless, Self::homescreen__title_seedless),
        (Qstr::MP_QSTR_homescreen__title_set, Self::homescreen__title_set),
        (Qstr::MP_QSTR_inputs__back, Self::inputs__back),
        (Qstr::MP_QSTR_inputs__cancel, Self::inputs__cancel),
        (Qstr::MP_QSTR_inputs__delete, Self::inputs__delete),
        (Qstr::MP_QSTR_inputs__enter, Self::inputs__enter),
        (Qstr::MP_QSTR_inputs__previous, Self::inputs__previous),
        (Qstr::MP_QSTR_inputs__return, Self::inputs__return),
        (Qstr::MP_QSTR_inputs__show, Self::inputs__show),
        (Qstr::MP_QSTR_inputs__space, Self::inputs__space),
        (Qstr::MP_QSTR_instructions__continue_holding, Self::instructions__continue_holding),
        (Qstr::MP_QSTR_instructions__continue_in_app, Self::instructions__continue_in_app),
        (Qstr::MP_QSTR_instructions__enter_next_share, Self::instructions__enter_next_share),
        (Qstr::MP_QSTR_instructions__hold_to_confirm, Self::instructions__hold_to_confirm),
        (Qstr::MP_QSTR_instructions__hold_to_continue, Self::instructions__hold_to_continue),
        (Qstr::MP_QSTR_instructions__hold_to_exit_tutorial, Self::instructions__hold_to_exit_tutorial),
        (Qstr::MP_QSTR_instructions__hold_to_sign, Self::instructions__hold_to_sign),
        (Qstr::MP_QSTR_instructions__learn_more, Self::instructions__learn_more),
        (Qstr::MP_QSTR_instructions__menu_to_continue, Self::instructions__menu_to_continue),
        (Qstr::MP_QSTR_instructions__shares_continue_with_x_template, Self::instructions__shares_continue_with_x_template),
        (Qstr::MP_QSTR_instructions__shares_start_with_1, Self::instructions__shares_start_with_1),
        (Qstr::MP_QSTR_instructions__shares_start_with_x_template, Self::instructions__shares_start_with_x_template),
        (Qstr::MP_QSTR_instructions__swipe_down, Self::instructions__swipe_down),
        (Qstr::MP_QSTR_instructions__swipe_horizontally, Self::instructions__swipe_horizontally),
        (Qstr::MP_QSTR_instructions__tap, Self::instructions__tap),
        (Qstr::MP_QSTR_instructions__tap_to_confirm, Self::instructions__tap_to_confirm),
        (Qstr::MP_QSTR_instructions__tap_to_continue, Self::instructions__tap_to_continue),
        (Qstr::MP_QSTR_instructions__view_all_data, Self::instructions__view_all_data),
        (Qstr::MP_QSTR_joint__title, Self::joint__title),
        (Qstr::MP_QSTR_joint__to_the_total_amount, Self::joint__to_the_total_amount),
        (Qstr::MP_QSTR_joint__you_are_contributing, Self::joint__you_are_contributing),
        (Qstr::MP_QSTR_language__change_to_template, Self::language__change_to_template),
        (Qstr::MP_QSTR_language__changed, Self::language__changed),
        (Qstr::MP_QSTR_language__progress, Self::language__progress),
        (Qstr::MP_QSTR_language__title, Self::language__title),
        (Qstr::MP_QSTR_led__disable, Self::led__disable),
        (Qstr::MP_QSTR_led__enable, Self::led__enable),
        (Qstr::MP_QSTR_led__title, Self::led__title),
        (Qstr::MP_QSTR_lockscreen__tap_to_connect, Self::lockscreen__tap_to_connect),
        (Qstr::MP_QSTR_lockscreen__tap_to_unlock, Self::lockscreen__tap_to_unlock),
        (Qstr::MP_QSTR_lockscreen__title_locked, Self::lockscreen__title_locked),
        (Qstr::MP_QSTR_lockscreen__title_not_connected, Self::lockscreen__title_not_connected),
        (Qstr::MP_QSTR_lockscreen__unlock, Self::lockscreen__unlock),
        (Qstr::MP_QSTR_misc__decrypt_value, Self::misc__decrypt_value),
        (Qstr::MP_QSTR_misc__enable_labeling, Self::misc__enable_labeling),
        (Qstr::MP_QSTR_misc__encrypt_value, Self::misc__encrypt_value),
        (Qstr::MP_QSTR_misc__title_suite_labeling, Self::misc__title_suite_labeling),
        (Qstr::MP_QSTR_modify_amount__decrease_amount, Self::modify_amount__decrease_amount),
        (Qstr::MP_QSTR_modify_amount__increase_amount, Self::modify_amount__increase_amount),
        (Qstr::MP_QSTR_modify_amount__new_amount, Self::modify_amount__new_amount),
        (Qstr::MP_QSTR_modify_amount__title, Self::modify_amount__title),
        (Qstr::MP_QSTR_modify_fee__decrease_fee, Self::modify_fee__decrease_fee),
        (Qstr::MP_QSTR_modify_fee__fee_rate, Self::modify_fee__fee_rate),
        (Qstr::MP_QSTR_modify_fee__increase_fee, Self::modify_fee__increase_fee),
        (Qstr::MP_QSTR_modify_fee__new_transaction_fee, Self::modify_fee__new_transaction_fee),
        (Qstr::MP_QSTR_modify_fee__no_change, Self::modify_fee__no_change),
        (Qstr::MP_QSTR_modify_fee__title, Self::modify_fee__title),
        (Qstr::MP_QSTR_modify_fee__transaction_fee, Self::modify_fee__transaction_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__confirm_export, Self::monero__confirm_export),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__confirm_ki_sync, Self::monero__confirm_ki_sync),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__confirm_refresh, Self::monero__confirm_refresh),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__confirm_unlock_time, Self::monero__confirm_unlock_time),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__hashing_inputs, Self::monero__hashing_inputs),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__payment_id, Self::monero__payment_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__postprocessing, Self::monero__postprocessing),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__processing, Self::monero__processing),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__processing_inputs, Self::monero__processing_inputs),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__processing_outputs, Self::monero__processing_outputs),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__signing, Self::monero__signing),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__signing_inputs, Self::monero__signing_inputs),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__unlock_time_set_template, Self::monero__unlock_time_set_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__wanna_export_tx_der, Self::monero__wanna_export_tx_der),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__wanna_export_tx_key, Self::monero__wanna_export_tx_key),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__wanna_export_watchkey, Self::monero__wanna_export_watchkey),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__wanna_start_refresh, Self::monero__wanna_start_refresh),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_monero__wanna_sync_key_images, Self::monero__wanna_sync_key_images),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__absolute, Self::nem__absolute),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__activate, Self::nem__activate),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__add, Self::nem__add),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_action, Self::nem__confirm_action),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_address, Self::nem__confirm_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_creation_fee, Self::nem__confirm_creation_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_mosaic, Self::nem__confirm_mosaic),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_multisig_fee, Self::nem__confirm_multisig_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_namespace, Self::nem__confirm_namespace),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_payload, Self::nem__confirm_payload),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_properties, Self::nem__confirm_properties),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_rental_fee, Self::nem__confirm_rental_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__confirm_transfer_of, Self::nem__confirm_transfer_of),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__convert_account_to_multisig, Self::nem__convert_account_to_multisig),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__cosign_transaction_for, Self::nem__cosign_transaction_for),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__cosignatory, Self::nem__cosignatory),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__create_mosaic, Self::nem__create_mosaic),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__create_namespace, Self::nem__create_namespace),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__deactivate, Self::nem__deactivate),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__decrease, Self::nem__decrease),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__description, Self::nem__description),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__divisibility_and_levy_cannot_be_shown, Self::nem__divisibility_and_levy_cannot_be_shown),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__encrypted, Self::nem__encrypted),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__final_confirm, Self::nem__final_confirm),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__immutable, Self::nem__immutable),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__increase, Self::nem__increase),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__initial_supply, Self::nem__initial_supply),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__initiate_transaction_for, Self::nem__initiate_transaction_for),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__levy_divisibility, Self::nem__levy_divisibility),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__levy_fee, Self::nem__levy_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__levy_fee_of, Self::nem__levy_fee_of),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__levy_mosaic, Self::nem__levy_mosaic),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__levy_namespace, Self::nem__levy_namespace),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__levy_recipient, Self::nem__levy_recipient),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__levy_type, Self::nem__levy_type),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__modify_supply_for, Self::nem__modify_supply_for),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__modify_the_number_of_cosignatories_by, Self::nem__modify_the_number_of_cosignatories_by),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__mutable, Self::nem__mutable),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__of, Self::nem__of),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__percentile, Self::nem__percentile),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__raw_units_template, Self::nem__raw_units_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__remote_harvesting, Self::nem__remote_harvesting),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__remove, Self::nem__remove),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__set_minimum_cosignatories_to, Self::nem__set_minimum_cosignatories_to),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__sign_tx_fee_template, Self::nem__sign_tx_fee_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__supply_change, Self::nem__supply_change),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__supply_units_template, Self::nem__supply_units_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__transferable, Self::nem__transferable),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__under_namespace, Self::nem__under_namespace),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__unencrypted, Self::nem__unencrypted),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nem__unknown_mosaic, Self::nem__unknown_mosaic),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_nostr__event_kind_template, Self::nostr__event_kind_template),
        (Qstr::MP_QSTR_passphrase__access_hidden_wallet, Self::passphrase__access_hidden_wallet),
        (Qstr::MP_QSTR_passphrase__access_wallet, Self::passphrase__access_wallet),
        (Qstr::MP_QSTR_passphrase__always_on_device, Self::passphrase__always_on_device),
        (Qstr::MP_QSTR_passphrase__continue_with_empty_passphrase, Self::passphrase__continue_with_empty_passphrase),
        (Qstr::MP_QSTR_passphrase__from_host_not_shown, Self::passphrase__from_host_not_shown),
        (Qstr::MP_QSTR_passphrase__hidden_wallet, Self::passphrase__hidden_wallet),
        (Qstr::MP_QSTR_passphrase__hide, Self::passphrase__hide),
        (Qstr::MP_QSTR_passphrase__next_screen_will_show_passphrase, Self::passphrase__next_screen_will_show_passphrase),
        (Qstr::MP_QSTR_passphrase__please_enter, Self::passphrase__please_enter),
        (Qstr::MP_QSTR_passphrase__revoke_on_device, Self::passphrase__revoke_on_device),
        (Qstr::MP_QSTR_passphrase__show, Self::passphrase__show),
        (Qstr::MP_QSTR_passphrase__title_confirm, Self::passphrase__title_confirm),
        (Qstr::MP_QSTR_passphrase__title_enter, Self::passphrase__title_enter),
        (Qstr::MP_QSTR_passphrase__title_hide, Self::passphrase__title_hide),
        (Qstr::MP_QSTR_passphrase__title_passphrase, Self::passphrase__title_passphrase),
        (Qstr::MP_QSTR_passphrase__title_settings, Self::passphrase__title_settings),
        (Qstr::MP_QSTR_passphrase__title_source, Self::passphrase__title_source),
        (Qstr::MP_QSTR_passphrase__turn_off, Self::passphrase__turn_off),
        (Qstr::MP_QSTR_passphrase__turn_on, Self::passphrase__turn_on),
        (Qstr::MP_QSTR_passphrase__wallet, Self::passphrase__wallet),
        (Qstr::MP_QSTR_pin__cancel_description, Self::pin__cancel_description),
        (Qstr::MP_QSTR_pin__cancel_info, Self::pin__cancel_info),
        (Qstr::MP_QSTR_pin__cancel_setup, Self::pin__cancel_setup),
        (Qstr::MP_QSTR_pin__change, Self::pin__change),
        (Qstr::MP_QSTR_pin__change_question, Self::pin__change_question),
        (Qstr::MP_QSTR_pin__changed, Self::pin__changed),
        (Qstr::MP_QSTR_pin__cursor_will_change, Self::pin__cursor_will_change),
        (Qstr::MP_QSTR_pin__diff_from_wipe_code, Self::pin__diff_from_wipe_code),
        (Qstr::MP_QSTR_pin__disabled, Self::pin__disabled),
        (Qstr::MP_QSTR_pin__enabled, Self::pin__enabled),
        (Qstr::MP_QSTR_pin__enter, Self::pin__enter),
        (Qstr::MP_QSTR_pin__enter_new, Self::pin__enter_new),
        (Qstr::MP_QSTR_pin__entered_not_valid, Self::pin__entered_not_valid),
        (Qstr::MP_QSTR_pin__info, Self::pin__info),
        (Qstr::MP_QSTR_pin__invalid_pin, Self::pin__invalid_pin),
        (Qstr::MP_QSTR_pin__last_attempt, Self::pin__last_attempt),
        (Qstr::MP_QSTR_pin__mismatch, Self::pin__mismatch),
        (Qstr::MP_QSTR_pin__pin_mismatch, Self::pin__pin_mismatch),
        (Qstr::MP_QSTR_pin__please_check_again, Self::pin__please_check_again),
        (Qstr::MP_QSTR_pin__reenter, Self::pin__reenter),
        (Qstr::MP_QSTR_pin__reenter_new, Self::pin__reenter_new),
        (Qstr::MP_QSTR_pin__reenter_to_confirm, Self::pin__reenter_to_confirm),
        (Qstr::MP_QSTR_pin__remove, Self::pin__remove),
        (Qstr::MP_QSTR_pin__setup_completed, Self::pin__setup_completed),
        (Qstr::MP_QSTR_pin__should_be_long, Self::pin__should_be_long),
        (Qstr::MP_QSTR_pin__title, Self::pin__title),
        (Qstr::MP_QSTR_pin__title_check_pin, Self::pin__title_check_pin),
        (Qstr::MP_QSTR_pin__title_settings, Self::pin__title_settings),
        (Qstr::MP_QSTR_pin__title_wrong_pin, Self::pin__title_wrong_pin),
        (Qstr::MP_QSTR_pin__tries_left, Self::pin__tries_left),
        (Qstr::MP_QSTR_pin__turn_off, Self::pin__turn_off),
        (Qstr::MP_QSTR_pin__turn_on, Self::pin__turn_on),
        (Qstr::MP_QSTR_pin__wipe_code_exists_description, Self::pin__wipe_code_exists_description),
        (Qstr::MP_QSTR_pin__wipe_code_exists_title, Self::pin__wipe_code_exists_title),
        (Qstr::MP_QSTR_pin__wrong_pin, Self::pin__wrong_pin),
        (Qstr::MP_QSTR_plurals__contains_x_keys, Self::plurals__contains_x_keys),
        (Qstr::MP_QSTR_plurals__lock_after_x_days, Self::plurals__lock_after_x_days),
        (Qstr::MP_QSTR_plurals__lock_after_x_hours, Self::plurals__lock_after_x_hours),
        (Qstr::MP_QSTR_plurals__lock_after_x_milliseconds, Self::plurals__lock_after_x_milliseconds),
        (Qstr::MP_QSTR_plurals__lock_after_x_minutes, Self::plurals__lock_after_x_minutes),
        (Qstr::MP_QSTR_plurals__lock_after_x_seconds, Self::plurals__lock_after_x_seconds),
        (Qstr::MP_QSTR_plurals__sign_x_actions, Self::plurals__sign_x_actions),
        (Qstr::MP_QSTR_plurals__transaction_of_x_operations, Self::plurals__transaction_of_x_operations),
        (Qstr::MP_QSTR_plurals__x_groups_needed, Self::plurals__x_groups_needed),
        (Qstr::MP_QSTR_plurals__x_shares_needed, Self::plurals__x_shares_needed),
        (Qstr::MP_QSTR_progress__authenticity_check, Self::progress__authenticity_check),
        (Qstr::MP_QSTR_progress__done, Self::progress__done),
        (Qstr::MP_QSTR_progress__loading_transaction, Self::progress__loading_transaction),
        (Qstr::MP_QSTR_progress__locking_device, Self::progress__locking_device),
        (Qstr::MP_QSTR_progress__one_second_left, Self::progress__one_second_left),
        (Qstr::MP_QSTR_progress__please_wait, Self::progress__please_wait),
        (Qstr::MP_QSTR_progress__refreshing, Self::progress__refreshing),
        (Qstr::MP_QSTR_progress__signing_transaction, Self::progress__signing_transaction),
        (Qstr::MP_QSTR_progress__syncing, Self::progress__syncing),
        (Qstr::MP_QSTR_progress__x_seconds_left_template, Self::progress__x_seconds_left_template),
        (Qstr::MP_QSTR_reboot_to_bootloader__just_a_moment, Self::reboot_to_bootloader__just_a_moment),
        (Qstr::MP_QSTR_reboot_to_bootloader__restart, Self::reboot_to_bootloader__restart),
        (Qstr::MP_QSTR_reboot_to_bootloader__title, Self::reboot_to_bootloader__title),
        (Qstr::MP_QSTR_reboot_to_bootloader__version_by_template, Self::reboot_to_bootloader__version_by_template),
        (Qstr::MP_QSTR_recovery__cancel_dry_run, Self::recovery__cancel_dry_run),
        (Qstr::MP_QSTR_recovery__check_dry_run, Self::recovery__check_dry_run),
        (Qstr::MP_QSTR_recovery__cursor_will_change, Self::recovery__cursor_will_change),
        (Qstr::MP_QSTR_recovery__dry_run_backup_not_on_this_device, Self::recovery__dry_run_backup_not_on_this_device),
        (Qstr::MP_QSTR_recovery__dry_run_bip39_valid_match, Self::recovery__dry_run_bip39_valid_match),
        (Qstr::MP_QSTR_recovery__dry_run_bip39_valid_mismatch, Self::recovery__dry_run_bip39_valid_mismatch),
        (Qstr::MP_QSTR_recovery__dry_run_invalid_backup_entered, Self::recovery__dry_run_invalid_backup_entered),
        (Qstr::MP_QSTR_recovery__dry_run_slip39_valid_all_shares, Self::recovery__dry_run_slip39_valid_all_shares),
        (Qstr::MP_QSTR_recovery__dry_run_slip39_valid_match, Self::recovery__dry_run_slip39_valid_match),
        (Qstr::MP_QSTR_recovery__dry_run_slip39_valid_mismatch, Self::recovery__dry_run_slip39_valid_mismatch),
        (Qstr::MP_QSTR_recovery__dry_run_slip39_valid_share, Self::recovery__dry_run_slip39_valid_share),
        (Qstr::MP_QSTR_recovery__dry_run_verify_remaining_shares, Self::recovery__dry_run_verify_remaining_shares),
        (Qstr::MP_QSTR_recovery__enter_any_share, Self::recovery__enter_any_share),
        (Qstr::MP_QSTR_recovery__enter_backup, Self::recovery__enter_backup),
        (Qstr::MP_QSTR_recovery__enter_different_share, Self::recovery__enter_different_share),
        (Qstr::MP_QSTR_recovery__enter_each_word, Self::recovery__enter_each_word),
        (Qstr::MP_QSTR_recovery__enter_share_from_diff_group, Self::recovery__enter_share_from_diff_group),
        (Qstr::MP_QSTR_recovery__group_num_template, Self::recovery__group_num_template),
        (Qstr::MP_QSTR_recovery__group_threshold_reached, Self::recovery__group_threshold_reached),
        (Qstr::MP_QSTR_recovery__info_about_disconnect, Self::recovery__info_about_disconnect),
        (Qstr::MP_QSTR_recovery__invalid_share_entered, Self::recovery__invalid_share_entered),
        (Qstr::MP_QSTR_recovery__invalid_wallet_backup_entered, Self::recovery__invalid_wallet_backup_entered),
        (Qstr::MP_QSTR_recovery__more_shares_needed, Self::recovery__more_shares_needed),
        (Qstr::MP_QSTR_recovery__num_of_words, Self::recovery__num_of_words),
        (Qstr::MP_QSTR_recovery__only_first_n_letters, Self::recovery__only_first_n_letters),
        (Qstr::MP_QSTR_recovery__progress_will_be_lost, Self::recovery__progress_will_be_lost),
        (Qstr::MP_QSTR_recovery__share_already_entered, Self::recovery__share_already_entered),
        (Qstr::MP_QSTR_recovery__share_does_not_match, Self::recovery__share_does_not_match),
        (Qstr::MP_QSTR_recovery__share_from_another_multi_share_backup, Self::recovery__share_from_another_multi_share_backup),
        (Qstr::MP_QSTR_recovery__share_from_group_entered_template, Self::recovery__share_from_group_entered_template),
        (Qstr::MP_QSTR_recovery__share_num_template, Self::recovery__share_num_template),
        (Qstr::MP_QSTR_recovery__start_entering, Self::recovery__start_entering),
        (Qstr::MP_QSTR_recovery__title, Self::recovery__title),
        (Qstr::MP_QSTR_recovery__title_cancel_dry_run, Self::recovery__title_cancel_dry_run),
        (Qstr::MP_QSTR_recovery__title_cancel_recovery, Self::recovery__title_cancel_recovery),
        (Qstr::MP_QSTR_recovery__title_dry_run, Self::recovery__title_dry_run),
        (Qstr::MP_QSTR_recovery__title_recover, Self::recovery__title_recover),
        (Qstr::MP_QSTR_recovery__title_remaining_shares, Self::recovery__title_remaining_shares),
        (Qstr::MP_QSTR_recovery__title_unlock_repeated_backup, Self::recovery__title_unlock_repeated_backup),
        (Qstr::MP_QSTR_recovery__type_word_x_of_y_template, Self::recovery__type_word_x_of_y_template),
        (Qstr::MP_QSTR_recovery__unlock_repeated_backup, Self::recovery__unlock_repeated_backup),
        (Qstr::MP_QSTR_recovery__unlock_repeated_backup_verb, Self::recovery__unlock_repeated_backup_verb),
        (Qstr::MP_QSTR_recovery__wallet_recovered, Self::recovery__wallet_recovered),
        (Qstr::MP_QSTR_recovery__wanna_cancel_dry_run, Self::recovery__wanna_cancel_dry_run),
        (Qstr::MP_QSTR_recovery__wanna_cancel_recovery, Self::recovery__wanna_cancel_recovery),
        (Qstr::MP_QSTR_recovery__word_count_template, Self::recovery__word_count_template),
        (Qstr::MP_QSTR_recovery__word_x_of_y_template, Self::recovery__word_x_of_y_template),
        (Qstr::MP_QSTR_recovery__x_more_items_starting_template_plural, Self::recovery__x_more_items_starting_template_plural),
        (Qstr::MP_QSTR_recovery__x_more_shares_needed_template_plural, Self::recovery__x_more_shares_needed_template_plural),
        (Qstr::MP_QSTR_recovery__x_of_y_entered_template, Self::recovery__x_of_y_entered_template),
        (Qstr::MP_QSTR_recovery__you_have_entered, Self::recovery__you_have_entered),
        (Qstr::MP_QSTR_regulatory__title, Self::regulatory__title),
        (Qstr::MP_QSTR_reset__advanced_group_threshold_info, Self::reset__advanced_group_threshold_info),
        (Qstr::MP_QSTR_reset__all_x_of_y_template, Self::reset__all_x_of_y_template),
        (Qstr::MP_QSTR_reset__any_x_of_y_template, Self::reset__any_x_of_y_template),
        (Qstr::MP_QSTR_reset__button_create, Self::reset__button_create),
        (Qstr::MP_QSTR_reset__button_recover, Self::reset__button_recover),
        (Qstr::MP_QSTR_reset__by_continuing, Self::reset__by_continuing),
        (Qstr::MP_QSTR_reset__cancel_create_wallet, Self::reset__cancel_create_wallet),
        (Qstr::MP_QSTR_reset__check_backup_instructions, Self::reset__check_backup_instructions),
        (Qstr::MP_QSTR_reset__check_backup_title, Self::reset__check_backup_title),
        (Qstr::MP_QSTR_reset__check_group_share_title_template, Self::reset__check_group_share_title_template),
        (Qstr::MP_QSTR_reset__check_share_backup_template, Self::reset__check_share_backup_template),
        (Qstr::MP_QSTR_reset__check_share_title_template, Self::reset__check_share_title_template),
        (Qstr::MP_QSTR_reset__check_wallet_backup_title, Self::reset__check_wallet_backup_title),
        (Qstr::MP_QSTR_reset__continue_with_next_share, Self::reset__continue_with_next_share),
        (Qstr::MP_QSTR_reset__continue_with_share_template, Self::reset__continue_with_share_template),
        (Qstr::MP_QSTR_reset__create_x_of_y_multi_share_backup_template, Self::reset__create_x_of_y_multi_share_backup_template),
        (Qstr::MP_QSTR_reset__finished_verifying_group_template, Self::reset__finished_verifying_group_template),
        (Qstr::MP_QSTR_reset__finished_verifying_shares, Self::reset__finished_verifying_shares),
        (Qstr::MP_QSTR_reset__finished_verifying_wallet_backup, Self::reset__finished_verifying_wallet_backup),
        (Qstr::MP_QSTR_reset__group_description, Self::reset__group_description),
        (Qstr::MP_QSTR_reset__group_info, Self::reset__group_info),
        (Qstr::MP_QSTR_reset__group_share_checked_successfully_template, Self::reset__group_share_checked_successfully_template),
        (Qstr::MP_QSTR_reset__group_share_title_template, Self::reset__group_share_title_template),
        (Qstr::MP_QSTR_reset__incorrect_word_selected, Self::reset__incorrect_word_selected),
        (Qstr::MP_QSTR_reset__more_at, Self::reset__more_at),
        (Qstr::MP_QSTR_reset__more_info_at, Self::reset__more_info_at),
        (Qstr::MP_QSTR_reset__need_all_share_template, Self::reset__need_all_share_template),
        (Qstr::MP_QSTR_reset__need_any_share_template, Self::reset__need_any_share_template),
        (Qstr::MP_QSTR_reset__needed_to_form_a_group, Self::reset__needed_to_form_a_group),
        (Qstr::MP_QSTR_reset__needed_to_recover_your_wallet, Self::reset__needed_to_recover_your_wallet),
        (Qstr::MP_QSTR_reset__never_make_digital_copy, Self::reset__never_make_digital_copy),
        (Qstr::MP_QSTR_reset__num_of_share_holders_template, Self::reset__num_of_share_holders_template),
        (Qstr::MP_QSTR_reset__num_of_shares_advanced_info_template, Self::reset__num_of_shares_advanced_info_template),
        (Qstr::MP_QSTR_reset__num_of_shares_basic_info_template, Self::reset__num_of_shares_basic_info_template),
        (Qstr::MP_QSTR_reset__num_of_shares_how_many, Self::reset__num_of_shares_how_many),
        (Qstr::MP_QSTR_reset__num_of_shares_long_info_template, Self::reset__num_of_shares_long_info_template),
        (Qstr::MP_QSTR_reset__num_shares_for_group_template, Self::reset__num_shares_for_group_template),
        (Qstr::MP_QSTR_reset__number_of_shares_info, Self::reset__number_of_shares_info),
        (Qstr::MP_QSTR_reset__one_share, Self::reset__one_share),
        (Qstr::MP_QSTR_reset__only_one_share_will_be_created, Self::reset__only_one_share_will_be_created),
        (Qstr::MP_QSTR_reset__recovery_share_description, Self::reset__recovery_share_description),
        (Qstr::MP_QSTR_reset__recovery_share_number, Self::reset__recovery_share_number),
        (Qstr::MP_QSTR_reset__recovery_share_title_template, Self::reset__recovery_share_title_template),
        (Qstr::MP_QSTR_reset__recovery_wallet_backup_title, Self::reset__recovery_wallet_backup_title),
        (Qstr::MP_QSTR_reset__repeat_for_all_shares, Self::reset__repeat_for_all_shares),
        (Qstr::MP_QSTR_reset__required_number_of_groups, Self::reset__required_number_of_groups),
        (Qstr::MP_QSTR_reset__select_correct_word, Self::reset__select_correct_word),
        (Qstr::MP_QSTR_reset__select_threshold, Self::reset__select_threshold),
        (Qstr::MP_QSTR_reset__select_word_from_share_template, Self::reset__select_word_from_share_template),
        (Qstr::MP_QSTR_reset__select_word_template, Self::reset__select_word_template),
        (Qstr::MP_QSTR_reset__select_word_x_of_y_template, Self::reset__select_word_x_of_y_template),
        (Qstr::MP_QSTR_reset__set_it_to_count_template, Self::reset__set_it_to_count_template),
        (Qstr::MP_QSTR_reset__share_checked_successfully_template, Self::reset__share_checked_successfully_template),
        (Qstr::MP_QSTR_reset__share_completed_template, Self::reset__share_completed_template),
        (Qstr::MP_QSTR_reset__share_words_first, Self::reset__share_words_first),
        (Qstr::MP_QSTR_reset__share_words_title, Self::reset__share_words_title),
        (Qstr::MP_QSTR_reset__slip39_checklist_more_info_threshold, Self::reset__slip39_checklist_more_info_threshold),
        (Qstr::MP_QSTR_reset__slip39_checklist_more_info_threshold_example_template, Self::reset__slip39_checklist_more_info_threshold_example_template),
        (Qstr::MP_QSTR_reset__slip39_checklist_num_groups, Self::reset__slip39_checklist_num_groups),
        (Qstr::MP_QSTR_reset__slip39_checklist_num_groups_x_template, Self::reset__slip39_checklist_num_groups_x_template),
        (Qstr::MP_QSTR_reset__slip39_checklist_num_shares, Self::reset__slip39_checklist_num_shares),
        (Qstr::MP_QSTR_reset__slip39_checklist_num_shares_x_template, Self::reset__slip39_checklist_num_shares_x_template),
        (Qstr::MP_QSTR_reset__slip39_checklist_set_num_groups, Self::reset__slip39_checklist_set_num_groups),
        (Qstr::MP_QSTR_reset__slip39_checklist_set_num_shares, Self::reset__slip39_checklist_set_num_shares),
        (Qstr::MP_QSTR_reset__slip39_checklist_set_sizes, Self::reset__slip39_checklist_set_sizes),
        (Qstr::MP_QSTR_reset__slip39_checklist_set_sizes_longer, Self::reset__slip39_checklist_set_sizes_longer),
        (Qstr::MP_QSTR_reset__slip39_checklist_set_threshold, Self::reset__slip39_checklist_set_threshold),
        (Qstr::MP_QSTR_reset__slip39_checklist_threshold_x_template, Self::reset__slip39_checklist_threshold_x_template),
        (Qstr::MP_QSTR_reset__slip39_checklist_title, Self::reset__slip39_checklist_title),
        (Qstr::MP_QSTR_reset__slip39_checklist_write_down, Self::reset__slip39_checklist_write_down),
        (Qstr::MP_QSTR_reset__slip39_checklist_write_down_recovery, Self::reset__slip39_checklist_write_down_recovery),
        (Qstr::MP_QSTR_reset__the_threshold_sets_the_number_of_shares, Self::reset__the_threshold_sets_the_number_of_shares),
        (Qstr::MP_QSTR_reset__the_word_is_repeated, Self::reset__the_word_is_repeated),
        (Qstr::MP_QSTR_reset__threshold_info, Self::reset__threshold_info),
        (Qstr::MP_QSTR_reset__title_backup_is_done, Self::reset__title_backup_is_done),
        (Qstr::MP_QSTR_reset__title_create_wallet, Self::reset__title_create_wallet),
        (Qstr::MP_QSTR_reset__title_group_threshold, Self::reset__title_group_threshold),
        (Qstr::MP_QSTR_reset__title_number_of_groups, Self::reset__title_number_of_groups),
        (Qstr::MP_QSTR_reset__title_number_of_shares, Self::reset__title_number_of_shares),
        (Qstr::MP_QSTR_reset__title_set_group_threshold, Self::reset__title_set_group_threshold),
        (Qstr::MP_QSTR_reset__title_set_number_of_groups, Self::reset__title_set_number_of_groups),
        (Qstr::MP_QSTR_reset__title_set_number_of_shares, Self::reset__title_set_number_of_shares),
        (Qstr::MP_QSTR_reset__title_set_threshold, Self::reset__title_set_threshold),
        (Qstr::MP_QSTR_reset__title_shamir_backup, Self::reset__title_shamir_backup),
        (Qstr::MP_QSTR_reset__to_form_group_template, Self::reset__to_form_group_template),
        (Qstr::MP_QSTR_reset__tos_link, Self::reset__tos_link),
        (Qstr::MP_QSTR_reset__total_number_of_shares_in_group_template, Self::reset__total_number_of_shares_in_group_template),
        (Qstr::MP_QSTR_reset__use_your_backup, Self::reset__use_your_backup),
        (Qstr::MP_QSTR_reset__words_may_repeat, Self::reset__words_may_repeat),
        (Qstr::MP_QSTR_reset__words_written_down_template, Self::reset__words_written_down_template),
        (Qstr::MP_QSTR_reset__write_down_words_template, Self::reset__write_down_words_template),
        (Qstr::MP_QSTR_reset__wrong_word_selected, Self::reset__wrong_word_selected),
        (Qstr::MP_QSTR_reset__you_need_one_share, Self::reset__you_need_one_share),
        (Qstr::MP_QSTR_reset__your_backup_is_done, Self::reset__your_backup_is_done),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ripple__confirm_tag, Self::ripple__confirm_tag),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ripple__destination_tag_missing, Self::ripple__destination_tag_missing),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ripple__destination_tag_template, Self::ripple__destination_tag_template),
        (Qstr::MP_QSTR_rotation__change_template, Self::rotation__change_template),
        (Qstr::MP_QSTR_rotation__east, Self::rotation__east),
        (Qstr::MP_QSTR_rotation__north, Self::rotation__north),
        (Qstr::MP_QSTR_rotation__south, Self::rotation__south),
        (Qstr::MP_QSTR_rotation__title_change, Self::rotation__title_change),
        (Qstr::MP_QSTR_rotation__west, Self::rotation__west),
        (Qstr::MP_QSTR_safety_checks__approve_unsafe_always, Self::safety_checks__approve_unsafe_always),
        (Qstr::MP_QSTR_safety_checks__approve_unsafe_temporary, Self::safety_checks__approve_unsafe_temporary),
        (Qstr::MP_QSTR_safety_checks__enforce_strict, Self::safety_checks__enforce_strict),
        (Qstr::MP_QSTR_safety_checks__title, Self::safety_checks__title),
        (Qstr::MP_QSTR_safety_checks__title_safety_override, Self::safety_checks__title_safety_override),
        (Qstr::MP_QSTR_sd_card__all_data_will_be_lost, Self::sd_card__all_data_will_be_lost),
        (Qstr::MP_QSTR_sd_card__card_required, Self::sd_card__card_required),
        (Qstr::MP_QSTR_sd_card__disable, Self::sd_card__disable),
        (Qstr::MP_QSTR_sd_card__disabled, Self::sd_card__disabled),
        (Qstr::MP_QSTR_sd_card__enable, Self::sd_card__enable),
        (Qstr::MP_QSTR_sd_card__enabled, Self::sd_card__enabled),
        (Qstr::MP_QSTR_sd_card__error, Self::sd_card__error),
        (Qstr::MP_QSTR_sd_card__format_card, Self::sd_card__format_card),
        (Qstr::MP_QSTR_sd_card__insert_correct_card, Self::sd_card__insert_correct_card),
        (Qstr::MP_QSTR_sd_card__please_insert, Self::sd_card__please_insert),
        (Qstr::MP_QSTR_sd_card__please_unplug_and_insert, Self::sd_card__please_unplug_and_insert),
        (Qstr::MP_QSTR_sd_card__problem_accessing, Self::sd_card__problem_accessing),
        (Qstr::MP_QSTR_sd_card__refresh, Self::sd_card__refresh),
        (Qstr::MP_QSTR_sd_card__refreshed, Self::sd_card__refreshed),
        (Qstr::MP_QSTR_sd_card__restart, Self::sd_card__restart),
        (Qstr::MP_QSTR_sd_card__title, Self::sd_card__title),
        (Qstr::MP_QSTR_sd_card__title_problem, Self::sd_card__title_problem),
        (Qstr::MP_QSTR_sd_card__unknown_filesystem, Self::sd_card__unknown_filesystem),
        (Qstr::MP_QSTR_sd_card__unplug_and_insert_correct, Self::sd_card__unplug_and_insert_correct),
        (Qstr::MP_QSTR_sd_card__use_different_card, Self::sd_card__use_different_card),
        (Qstr::MP_QSTR_sd_card__wanna_format, Self::sd_card__wanna_format),
        (Qstr::MP_QSTR_sd_card__wrong_sd_card, Self::sd_card__wrong_sd_card),
        (Qstr::MP_QSTR_secure_sync__delegated_identity_key_no_thp, Self::secure_sync__delegated_identity_key_no_thp),
        (Qstr::MP_QSTR_secure_sync__delegated_identity_key_thp, Self::secure_sync__delegated_identity_key_thp),
        (Qstr::MP_QSTR_secure_sync__header, Self::secure_sync__header),
        (Qstr::MP_QSTR_send__cancel_sign, Self::send__cancel_sign),
        (Qstr::MP_QSTR_send__cancel_transaction, Self::send__cancel_transaction),
        (Qstr::MP_QSTR_send__confirm_sending, Self::send__confirm_sending),
        (Qstr::MP_QSTR_send__from_multiple_accounts, Self::send__from_multiple_accounts),
        (Qstr::MP_QSTR_send__incl_transaction_fee, Self::send__incl_transaction_fee),
        (Qstr::MP_QSTR_send__including_fee, Self::send__including_fee),
        (Qstr::MP_QSTR_send__maximum_fee, Self::send__maximum_fee),
        (Qstr::MP_QSTR_send__multisig_different_paths, Self::send__multisig_different_paths),
        (Qstr::MP_QSTR_send__receiving_to_multisig, Self::send__receiving_to_multisig),
        (Qstr::MP_QSTR_send__send_from, Self::send__send_from),
        (Qstr::MP_QSTR_send__send_in_the_app, Self::send__send_in_the_app),
        (Qstr::MP_QSTR_send__sign_cancelled, Self::send__sign_cancelled),
        (Qstr::MP_QSTR_send__sign_transaction, Self::send__sign_transaction),
        (Qstr::MP_QSTR_send__title_confirm_sending, Self::send__title_confirm_sending),
        (Qstr::MP_QSTR_send__title_joint_transaction, Self::send__title_joint_transaction),
        (Qstr::MP_QSTR_send__title_receiving_to, Self::send__title_receiving_to),
        (Qstr::MP_QSTR_send__title_sending, Self::send__title_sending),
        (Qstr::MP_QSTR_send__title_sending_amount, Self::send__title_sending_amount),
        (Qstr::MP_QSTR_send__title_sending_to, Self::send__title_sending_to),
        (Qstr::MP_QSTR_send__to_the_total_amount, Self::send__to_the_total_amount),
        (Qstr::MP_QSTR_send__total_amount, Self::send__total_amount),
        (Qstr::MP_QSTR_send__transaction_id, Self::send__transaction_id),
        (Qstr::MP_QSTR_send__transaction_signed, Self::send__transaction_signed),
        (Qstr::MP_QSTR_send__you_are_contributing, Self::send__you_are_contributing),
        (Qstr::MP_QSTR_setting__adjust, Self::setting__adjust),
        (Qstr::MP_QSTR_setting__apply, Self::setting__apply),
        (Qstr::MP_QSTR_share_words__words_in_order, Self::share_words__words_in_order),
        (Qstr::MP_QSTR_share_words__wrote_down_all, Self::share_words__wrote_down_all),
        (Qstr::MP_QSTR_sign_message__bytes_template, Self::sign_message__bytes_template),
        (Qstr::MP_QSTR_sign_message__confirm_address, Self::sign_message__confirm_address),
        (Qstr::MP_QSTR_sign_message__confirm_message, Self::sign_message__confirm_message),
        (Qstr::MP_QSTR_sign_message__confirm_without_review, Self::sign_message__confirm_without_review),
        (Qstr::MP_QSTR_sign_message__message_size, Self::sign_message__message_size),
        (Qstr::MP_QSTR_sign_message__verify_address, Self::sign_message__verify_address),
        (Qstr::MP_QSTR_sn__action, Self::sn__action),
        (Qstr::MP_QSTR_sn__title, Self::sn__title),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__account_index, Self::solana__account_index),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__associated_token_account, Self::solana__associated_token_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__base_fee, Self::solana__base_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__claim, Self::solana__claim),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__claim_question, Self::solana__claim_question),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__claim_recipient_warning, Self::solana__claim_recipient_warning),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__confirm_multisig, Self::solana__confirm_multisig),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__expected_fee, Self::solana__expected_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__instruction_accounts_template, Self::solana__instruction_accounts_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__instruction_data, Self::solana__instruction_data),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__instruction_is_multisig, Self::solana__instruction_is_multisig),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__is_provided_via_lookup_table_template, Self::solana__is_provided_via_lookup_table_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__lookup_table_address, Self::solana__lookup_table_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__max_fees_rent, Self::solana__max_fees_rent),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__max_rent_fee, Self::solana__max_rent_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__multiple_signers, Self::solana__multiple_signers),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__priority_fee, Self::solana__priority_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake, Self::solana__stake),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_account, Self::solana__stake_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_on_question, Self::solana__stake_on_question),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_question, Self::solana__stake_question),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_withdrawal_warning, Self::solana__stake_withdrawal_warning),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_withdrawal_warning_title, Self::solana__stake_withdrawal_warning_title),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__transaction_contains_unknown_instructions, Self::solana__transaction_contains_unknown_instructions),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__transaction_requires_x_signers_template, Self::solana__transaction_requires_x_signers_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__unknown_token, Self::solana__unknown_token),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__unknown_token_address, Self::solana__unknown_token_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__unstake, Self::solana__unstake),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__unstake_question, Self::solana__unstake_question),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__vote_account, Self::solana__vote_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__account_merge, Self::stellar__account_merge),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__account_thresholds, Self::stellar__account_thresholds),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__add_signer, Self::stellar__add_signer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__add_trust, Self::stellar__add_trust),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__all_will_be_sent_to, Self::stellar__all_will_be_sent_to),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__allow_trust, Self::stellar__allow_trust),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__balance_id, Self::stellar__balance_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__bump_sequence, Self::stellar__bump_sequence),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__buying, Self::stellar__buying),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__claim_claimable_balance, Self::stellar__claim_claimable_balance),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__clear_data, Self::stellar__clear_data),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__clear_flags, Self::stellar__clear_flags),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__confirm_issuer, Self::stellar__confirm_issuer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__confirm_memo, Self::stellar__confirm_memo),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__confirm_operation, Self::stellar__confirm_operation),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__confirm_timebounds, Self::stellar__confirm_timebounds),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__create_account, Self::stellar__create_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__debited_amount, Self::stellar__debited_amount),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__delete, Self::stellar__delete),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__delete_passive_offer, Self::stellar__delete_passive_offer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__delete_trust, Self::stellar__delete_trust),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__destination, Self::stellar__destination),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__exchanges_require_memo, Self::stellar__exchanges_require_memo),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__final_confirm, Self::stellar__final_confirm),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__hash, Self::stellar__hash),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__high, Self::stellar__high),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__home_domain, Self::stellar__home_domain),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__inflation, Self::stellar__inflation),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__issuer_template, Self::stellar__issuer_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__key, Self::stellar__key),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__limit, Self::stellar__limit),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__low, Self::stellar__low),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__master_weight, Self::stellar__master_weight),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__medium, Self::stellar__medium),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__new_offer, Self::stellar__new_offer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__new_passive_offer, Self::stellar__new_passive_offer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__no_memo_set, Self::stellar__no_memo_set),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__no_restriction, Self::stellar__no_restriction),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__path_pay, Self::stellar__path_pay),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__path_pay_at_least, Self::stellar__path_pay_at_least),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__pay, Self::stellar__pay),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__pay_at_most, Self::stellar__pay_at_most),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__preauth_transaction, Self::stellar__preauth_transaction),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__price_per_template, Self::stellar__price_per_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__remove_signer, Self::stellar__remove_signer),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__revoke_trust, Self::stellar__revoke_trust),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__selling, Self::stellar__selling),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__set_data, Self::stellar__set_data),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__set_flags, Self::stellar__set_flags),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__set_sequence_to_template, Self::stellar__set_sequence_to_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__sign_tx_count_template, Self::stellar__sign_tx_count_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__sign_tx_fee_template, Self::stellar__sign_tx_fee_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__sign_with, Self::stellar__sign_with),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__source_account, Self::stellar__source_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__timebounds, Self::stellar__timebounds),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__token_info, Self::stellar__token_info),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__transaction_source, Self::stellar__transaction_source),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__transaction_source_diff_warning, Self::stellar__transaction_source_diff_warning),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__trusted_account, Self::stellar__trusted_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__update, Self::stellar__update),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__valid_from, Self::stellar__valid_from),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__valid_to, Self::stellar__valid_to),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__value_sha256, Self::stellar__value_sha256),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__wanna_clean_value_key_template, Self::stellar__wanna_clean_value_key_template),
        (Qstr::MP_QSTR_storage_msg__processing, Self::storage_msg__processing),
        (Qstr::MP_QSTR_storage_msg__starting, Self::storage_msg__starting),
        (Qstr::MP_QSTR_storage_msg__verifying_pin, Self::storage_msg__verifying_pin),
        (Qstr::MP_QSTR_storage_msg__wrong_pin, Self::storage_msg__wrong_pin),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__baker_address, Self::tezos__baker_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__balance, Self::tezos__balance),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__ballot, Self::tezos__ballot),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__confirm_delegation, Self::tezos__confirm_delegation),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__confirm_origination, Self::tezos__confirm_origination),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__delegator, Self::tezos__delegator),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__proposal, Self::tezos__proposal),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__register_delegate, Self::tezos__register_delegate),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__remove_delegation, Self::tezos__remove_delegation),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__submit_ballot, Self::tezos__submit_ballot),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__submit_proposal, Self::tezos__submit_proposal),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_tezos__submit_proposals, Self::tezos__submit_proposals),
        (Qstr::MP_QSTR_thp__autoconnect, Self::thp__autoconnect),
        (Qstr::MP_QSTR_thp__autoconnect_app, Self::thp__autoconnect_app),
        (Qstr::MP_QSTR_thp__autoconnect_title, Self::thp__autoconnect_title),
        (Qstr::MP_QSTR_thp__code_entry, Self::thp__code_entry),
        (Qstr::MP_QSTR_thp__code_title, Self::thp__code_title),
        (Qstr::MP_QSTR_thp__connect, Self::thp__connect),
        (Qstr::MP_QSTR_thp__connect_app, Self::thp__connect_app),
        (Qstr::MP_QSTR_thp__connect_title, Self::thp__connect_title),
        (Qstr::MP_QSTR_thp__nfc_text, Self::thp__nfc_text),
        (Qstr::MP_QSTR_thp__pair, Self::thp__pair),
        (Qstr::MP_QSTR_thp__pair_app, Self::thp__pair_app),
        (Qstr::MP_QSTR_thp__pair_name, Self::thp__pair_name),
        (Qstr::MP_QSTR_thp__pair_new_device, Self::thp__pair_new_device),
        (Qstr::MP_QSTR_thp__pair_title, Self::thp__pair_title),
        (Qstr::MP_QSTR_thp__qr_title, Self::thp__qr_title),
        (Qstr::MP_QSTR_tutorial__continue, Self::tutorial__continue),
        (Qstr::MP_QSTR_tutorial__did_you_know, Self::tutorial__did_you_know),
        (Qstr::MP_QSTR_tutorial__exit, Self::tutorial__exit),
        (Qstr::MP_QSTR_tutorial__first_wallet, Self::tutorial__first_wallet),
        (Qstr::MP_QSTR_tutorial__get_started, Self::tutorial__get_started),
        (Qstr::MP_QSTR_tutorial__last_one, Self::tutorial__last_one),
        (Qstr::MP_QSTR_tutorial__lets_begin, Self::tutorial__lets_begin),
        (Qstr::MP_QSTR_tutorial__menu, Self::tutorial__menu),
        (Qstr::MP_QSTR_tutorial__menu_appendix, Self::tutorial__menu_appendix),
        (Qstr::MP_QSTR_tutorial__middle_click, Self::tutorial__middle_click),
        (Qstr::MP_QSTR_tutorial__navigation_ts7, Self::tutorial__navigation_ts7),
        (Qstr::MP_QSTR_tutorial__one_more_step, Self::tutorial__one_more_step),
        (Qstr::MP_QSTR_tutorial__power, Self::tutorial__power),
        (Qstr::MP_QSTR_tutorial__press_and_hold, Self::tutorial__press_and_hold),
        (Qstr::MP_QSTR_tutorial__ready_to_use, Self::tutorial__ready_to_use),
        (Qstr::MP_QSTR_tutorial__ready_to_use_safe5, Self::tutorial__ready_to_use_safe5),
        (Qstr::MP_QSTR_tutorial__restart_tutorial, Self::tutorial__restart_tutorial),
        (Qstr::MP_QSTR_tutorial__scroll_down, Self::tutorial__scroll_down),
        (Qstr::MP_QSTR_tutorial__suite_restart, Self::tutorial__suite_restart),
        (Qstr::MP_QSTR_tutorial__sure_you_want_skip, Self::tutorial__sure_you_want_skip),
        (Qstr::MP_QSTR_tutorial__swipe_up_and_down, Self::tutorial__swipe_up_and_down),
        (Qstr::MP_QSTR_tutorial__tap_to_start, Self::tutorial__tap_to_start),
        (Qstr::MP_QSTR_tutorial__title_easy_navigation, Self::tutorial__title_easy_navigation),
        (Qstr::MP_QSTR_tutorial__title_handy_menu, Self::tutorial__title_handy_menu),
        (Qstr::MP_QSTR_tutorial__title_hello, Self::tutorial__title_hello),
        (Qstr::MP_QSTR_tutorial__title_hold, Self::tutorial__title_hold),
        (Qstr::MP_QSTR_tutorial__title_lets_begin, Self::tutorial__title_lets_begin),
        (Qstr::MP_QSTR_tutorial__title_screen_scroll, Self::tutorial__title_screen_scroll),
        (Qstr::MP_QSTR_tutorial__title_skip, Self::tutorial__title_skip),
        (Qstr::MP_QSTR_tutorial__title_tutorial_complete, Self::tutorial__title_tutorial_complete),
        (Qstr::MP_QSTR_tutorial__title_well_done, Self::tutorial__title_well_done),
        (Qstr::MP_QSTR_tutorial__tropic_info, Self::tutorial__tropic_info),
        (Qstr::MP_QSTR_tutorial__use_trezor, Self::tutorial__use_trezor),
        (Qstr::MP_QSTR_tutorial__welcome_press_right, Self::tutorial__welcome_press_right),
        (Qstr::MP_QSTR_tutorial__welcome_safe5, Self::tutorial__welcome_safe5),
        (Qstr::MP_QSTR_tutorial__welcome_safe7, Self::tutorial__welcome_safe7),
        (Qstr::MP_QSTR_tutorial__what_is_tropic, Self::tutorial__what_is_tropic),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__get, Self::u2f__get),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__set_template, Self::u2f__set_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__title_get, Self::u2f__title_get),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__title_set, Self::u2f__title_set),
        (Qstr::MP_QSTR_wipe__info, Self::wipe__info),
        (Qstr::MP_QSTR_wipe__start_again, Self::wipe__start_again),
        (Qstr::MP_QSTR_wipe__title, Self::wipe__title),
        (Qstr::MP_QSTR_wipe__want_to_wipe, Self::wipe__want_to_wipe),
        (Qstr::MP_QSTR_wipe_code__cancel_setup, Self::wipe_code__cancel_setup),
        (Qstr::MP_QSTR_wipe_code__change, Self::wipe_code__change),
        (Qstr::MP_QSTR_wipe_code__change_question, Self::wipe_code__change_question),
        (Qstr::MP_QSTR_wipe_code__changed, Self::wipe_code__changed),
        (Qstr::MP_QSTR_wipe_code__diff_from_pin, Self::wipe_code__diff_from_pin),
        (Qstr::MP_QSTR_wipe_code__disabled, Self::wipe_code__disabled),
        (Qstr::MP_QSTR_wipe_code__enabled, Self::wipe_code__enabled),
        (Qstr::MP_QSTR_wipe_code__enter_new, Self::wipe_code__enter_new),
        (Qstr::MP_QSTR_wipe_code__info, Self::wipe_code__info),
        (Qstr::MP_QSTR_wipe_code__invalid, Self::wipe_code__invalid),
        (Qstr::MP_QSTR_wipe_code__mismatch, Self::wipe_code__mismatch),
        (Qstr::MP_QSTR_wipe_code__pin_not_set_description, Self::wipe_code__pin_not_set_description),
        (Qstr::MP_QSTR_wipe_code__reenter, Self::wipe_code__reenter),
        (Qstr::MP_QSTR_wipe_code__reenter_to_confirm, Self::wipe_code__reenter_to_confirm),
        (Qstr::MP_QSTR_wipe_code__remove, Self::wipe_code__remove),
        (Qstr::MP_QSTR_wipe_code__title, Self::wipe_code__title),
        (Qstr::MP_QSTR_wipe_code__title_check, Self::wipe_code__title_check),
        (Qstr::MP_QSTR_wipe_code__title_invalid, Self::wipe_code__title_invalid),
        (Qstr::MP_QSTR_wipe_code__title_settings, Self::wipe_code__title_settings),
        (Qstr::MP_QSTR_wipe_code__turn_off, Self::wipe_code__turn_off),
        (Qstr::MP_QSTR_wipe_code__turn_on, Self::wipe_code__turn_on),
        (Qstr::MP_QSTR_wipe_code__wipe_code_mismatch, Self::wipe_code__wipe_code_mismatch),
        (Qstr::MP_QSTR_word_count__title, Self::word_count__title),
        (Qstr::MP_QSTR_words__about, Self::words__about),
        (Qstr::MP_QSTR_words__account, Self::words__account),
        (Qstr::MP_QSTR_words__account_colon, Self::words__account_colon),
        (Qstr::MP_QSTR_words__address, Self::words__address),
        (Qstr::MP_QSTR_words__amount, Self::words__amount),
        (Qstr::MP_QSTR_words__are_you_sure, Self::words__are_you_sure),
        (Qstr::MP_QSTR_words__array_of, Self::words__array_of),
        (Qstr::MP_QSTR_words__asset, Self::words__asset),
        (Qstr::MP_QSTR_words__assets, Self::words__assets),
        (Qstr::MP_QSTR_words__authenticate, Self::words__authenticate),
        (Qstr::MP_QSTR_words__blockhash, Self::words__blockhash),
        (Qstr::MP_QSTR_words__bluetooth, Self::words__bluetooth),
        (Qstr::MP_QSTR_words__buying, Self::words__buying),
        (Qstr::MP_QSTR_words__cancel_and_exit, Self::words__cancel_and_exit),
        (Qstr::MP_QSTR_words__cancel_question, Self::words__cancel_question),
        (Qstr::MP_QSTR_words__chain, Self::words__chain),
        (Qstr::MP_QSTR_words__comm_trouble, Self::words__comm_trouble),
        (Qstr::MP_QSTR_words__confirm, Self::words__confirm),
        (Qstr::MP_QSTR_words__confirm_fee, Self::words__confirm_fee),
        (Qstr::MP_QSTR_words__connect, Self::words__connect),
        (Qstr::MP_QSTR_words__connected, Self::words__connected),
        (Qstr::MP_QSTR_words__contains, Self::words__contains),
        (Qstr::MP_QSTR_words__continue_anyway, Self::words__continue_anyway),
        (Qstr::MP_QSTR_words__continue_anyway_question, Self::words__continue_anyway_question),
        (Qstr::MP_QSTR_words__continue_with, Self::words__continue_with),
        (Qstr::MP_QSTR_words__device, Self::words__device),
        (Qstr::MP_QSTR_words__disabled, Self::words__disabled),
        (Qstr::MP_QSTR_words__disconnect, Self::words__disconnect),
        (Qstr::MP_QSTR_words__disconnected, Self::words__disconnected),
        (Qstr::MP_QSTR_words__enabled, Self::words__enabled),
        (Qstr::MP_QSTR_words__error, Self::words__error),
        (Qstr::MP_QSTR_words__fee, Self::words__fee),
        (Qstr::MP_QSTR_words__forget, Self::words__forget),
        (Qstr::MP_QSTR_words__from, Self::words__from),
        (Qstr::MP_QSTR_words__good_to_know, Self::words__good_to_know),
        (Qstr::MP_QSTR_words__important, Self::words__important),
        (Qstr::MP_QSTR_words__instructions, Self::words__instructions),
        (Qstr::MP_QSTR_words__keep_it_safe, Self::words__keep_it_safe),
        (Qstr::MP_QSTR_words__know_what_your_doing, Self::words__know_what_your_doing),
        (Qstr::MP_QSTR_words__led, Self::words__led),
        (Qstr::MP_QSTR_words__manage, Self::words__manage),
        (Qstr::MP_QSTR_words__my_trezor, Self::words__my_trezor),
        (Qstr::MP_QSTR_words__name, Self::words__name),
        (Qstr::MP_QSTR_words__no, Self::words__no),
        (Qstr::MP_QSTR_words__not_recommended, Self::words__not_recommended),
        (Qstr::MP_QSTR_words__note, Self::words__note),
        (Qstr::MP_QSTR_words__off, Self::words__off),
        (Qstr::MP_QSTR_words__on, Self::words__on),
        (Qstr::MP_QSTR_words__operation_cancelled, Self::words__operation_cancelled),
        (Qstr::MP_QSTR_words__outputs, Self::words__outputs),
        (Qstr::MP_QSTR_words__pay_attention, Self::words__pay_attention),
        (Qstr::MP_QSTR_words__please_check_again, Self::words__please_check_again),
        (Qstr::MP_QSTR_words__please_try_again, Self::words__please_try_again),
        (Qstr::MP_QSTR_words__power, Self::words__power),
        (Qstr::MP_QSTR_words__provider, Self::words__provider),
        (Qstr::MP_QSTR_words__really_wanna, Self::words__really_wanna),
        (Qstr::MP_QSTR_words__receive, Self::words__receive),
        (Qstr::MP_QSTR_words__recipient, Self::words__recipient),
        (Qstr::MP_QSTR_words__recovery_share, Self::words__recovery_share),
        (Qstr::MP_QSTR_words__review, Self::words__review),
        (Qstr::MP_QSTR_words__security, Self::words__security),
        (Qstr::MP_QSTR_words__send, Self::words__send),
        (Qstr::MP_QSTR_words__set, Self::words__set),
        (Qstr::MP_QSTR_words__settings, Self::words__settings),
        (Qstr::MP_QSTR_words__sign, Self::words__sign),
        (Qstr::MP_QSTR_words__signer, Self::words__signer),
        (Qstr::MP_QSTR_words__swap, Self::words__swap),
        (Qstr::MP_QSTR_words__title_check, Self::words__title_check),
        (Qstr::MP_QSTR_words__title_done, Self::words__title_done),
        (Qstr::MP_QSTR_words__title_group, Self::words__title_group),
        (Qstr::MP_QSTR_words__title_information, Self::words__title_information),
        (Qstr::MP_QSTR_words__title_remember, Self::words__title_remember),
        (Qstr::MP_QSTR_words__title_share, Self::words__title_share),
        (Qstr::MP_QSTR_words__title_shares, Self::words__title_shares),
        (Qstr::MP_QSTR_words__title_success, Self::words__title_success),
        (Qstr::MP_QSTR_words__title_summary, Self::words__title_summary),
        (Qstr::MP_QSTR_words__title_threshold, Self::words__title_threshold),
        (Qstr::MP_QSTR_words__token, Self::words__token),
        (Qstr::MP_QSTR_words__transaction_fee, Self::words__transaction_fee),
        (Qstr::MP_QSTR_words__try_again, Self::words__try_again),
        (Qstr::MP_QSTR_words__unknown, Self::words__unknown),
        (Qstr::MP_QSTR_words__unlimited, Self::words__unlimited),
        (Qstr::MP_QSTR_words__unlocked, Self::words__unlocked),
        (Qstr::MP_QSTR_words__wallet, Self::words__wallet),
        (Qstr::MP_QSTR_words__warning, Self::words__warning),
        (Qstr::MP_QSTR_words__wipe, Self::words__wipe),
        (Qstr::MP_QSTR_words__writable, Self::words__writable),
        (Qstr::MP_QSTR_words__yes, Self::words__yes),
    ];
}
