//! generated from translated_string.rs.mako
//! (by running `make templates` in `core`)
//! do not edit manually!

#![cfg_attr(rustfmt, rustfmt_skip)]
#[cfg(feature = "micropython")]
use crate::micropython::qstr::Qstr;

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
    words__fee_limit = 1175,  // "Fee limit"
}

impl TranslatedString {
    pub const DATA_MAP: &'static [(Self, &'static str)] = &[
            (Self::addr_mismatch__contact_support_at, "Please contact Trezor support at"),
            (Self::addr_mismatch__key_mismatch, "Key mismatch?"),
            (Self::addr_mismatch__mismatch, "Address mismatch?"),
            (Self::addr_mismatch__support_url, "trezor.io/support"),
            (Self::addr_mismatch__wrong_derivation_path, "Wrong derivation path for selected account."),
            (Self::addr_mismatch__xpub_mismatch, "XPUB mismatch?"),
            (Self::address__public_key, "Public key"),
            (Self::address__title_cosigner, "Cosigner"),
            (Self::address__title_receive_address, "Receive address"),
            (Self::address__title_yours, "Yours"),
            (Self::address_details__derivation_path_colon, "Derivation path:"),
            (Self::address_details__title_receive_address, "Receive address"),
            (Self::address_details__title_receiving_to, "Receiving to"),
            (Self::authenticate__confirm_template, "Allow connected app to check the authenticity of your {0}?"),
            (Self::authenticate__header, "Authenticate device"),
            (Self::auto_lock__change_template, "Auto-lock Trezor after {0} of inactivity?"),
            #[cfg(feature = "layout_bolt")]
            (Self::auto_lock__title, "Auto-lock delay"),
            #[cfg(feature = "layout_caesar")]
            (Self::auto_lock__title, "Auto-lock delay"),
            #[cfg(feature = "layout_delizia")]
            (Self::auto_lock__title, "Auto-lock delay"),
            #[cfg(feature = "layout_eckhart")]
            (Self::auto_lock__title, "Auto-lock"),
            (Self::backup__can_back_up_anytime, "You can back up your Trezor once, at any time."),
            #[cfg(feature = "layout_bolt")]
            (Self::backup__it_should_be_backed_up, "You should back up your new wallet right now."),
            #[cfg(feature = "layout_caesar")]
            (Self::backup__it_should_be_backed_up, "You should back up your new wallet right now."),
            #[cfg(feature = "layout_delizia")]
            (Self::backup__it_should_be_backed_up, "You should back up your new wallet right now."),
            #[cfg(feature = "layout_eckhart")]
            (Self::backup__it_should_be_backed_up, "Back up your new wallet now."),
            (Self::backup__it_should_be_backed_up_now, "It should be backed up now!"),
            (Self::backup__new_wallet_created, "Wallet created.\n"),
            (Self::backup__new_wallet_successfully_created, "Wallet created successfully."),
            (Self::backup__recover_anytime, "You can use your backup to recover your wallet at any time."),
            (Self::backup__title_backup_wallet, "Back up wallet"),
            (Self::backup__title_skip, "Skip backup"),
            (Self::backup__want_to_skip, "Are you sure you want to skip the backup?"),
            (Self::bitcoin__commitment_data, "Commitment data"),
            (Self::bitcoin__confirm_locktime, "Confirm locktime"),
            (Self::bitcoin__create_proof_of_ownership, "Do you want to create a proof of ownership?"),
            (Self::bitcoin__high_mining_fee_template, "The mining fee of\n{0}\nis unexpectedly high."),
            (Self::bitcoin__locktime_no_effect, "Locktime is set but will have no effect."),
            (Self::bitcoin__locktime_set_to, "Locktime set to"),
            (Self::bitcoin__locktime_set_to_blockheight, "Locktime set to blockheight"),
            (Self::bitcoin__lot_of_change_outputs, "A lot of change-outputs."),
            (Self::bitcoin__multiple_accounts, "Multiple accounts"),
            (Self::bitcoin__new_fee_rate, "New fee rate:"),
            (Self::bitcoin__simple_send_of, "Simple send of"),
            (Self::bitcoin__ticket_amount, "Ticket amount"),
            (Self::bitcoin__title_confirm_details, "Confirm details"),
            (Self::bitcoin__title_finalize_transaction, "Finalize transaction"),
            (Self::bitcoin__title_high_mining_fee, "High mining fee"),
            (Self::bitcoin__title_meld_transaction, "Meld transaction"),
            (Self::bitcoin__title_modify_amount, "Modify amount"),
            (Self::bitcoin__title_payjoin, "Payjoin"),
            (Self::bitcoin__title_proof_of_ownership, "Proof of ownership"),
            (Self::bitcoin__title_purchase_ticket, "Purchase ticket"),
            (Self::bitcoin__title_update_transaction, "Update transaction"),
            (Self::bitcoin__unknown_path, "Unknown path"),
            (Self::bitcoin__unknown_transaction, "Unknown transaction"),
            (Self::bitcoin__unusually_high_fee, "Unusually high fee."),
            (Self::bitcoin__unverified_external_inputs, "The transaction contains unverified external inputs."),
            (Self::bitcoin__valid_signature, "The signature is valid."),
            (Self::bitcoin__voting_rights, "Voting rights to"),
            (Self::buttons__abort, "Abort"),
            (Self::buttons__access, "Access"),
            (Self::buttons__again, "Again"),
            (Self::buttons__allow, "Allow"),
            (Self::buttons__back, "Back"),
            (Self::buttons__back_up, "Back up"),
            (Self::buttons__cancel, "Cancel"),
            (Self::buttons__change, "Change"),
            (Self::buttons__check, "Check"),
            (Self::buttons__check_again, "Check again"),
            (Self::buttons__close, "Close"),
            (Self::buttons__confirm, "Confirm"),
            (Self::buttons__continue, "Continue"),
            (Self::buttons__details, "Details"),
            (Self::buttons__enable, "Enable"),
            (Self::buttons__enter, "Enter"),
            (Self::buttons__enter_share, "Enter share"),
            (Self::buttons__export, "Export"),
            (Self::buttons__format, "Format"),
            (Self::buttons__go_back, "Go back"),
            (Self::buttons__hold_to_confirm, "Hold to confirm"),
            (Self::buttons__info, "Info"),
            (Self::buttons__install, "Install"),
            (Self::buttons__more_info, "More info"),
            (Self::buttons__ok_i_understand, "Ok, I understand"),
            (Self::buttons__purchase, "Purchase"),
            (Self::buttons__quit, "Quit"),
            (Self::buttons__restart, "Restart"),
            (Self::buttons__retry, "Retry"),
            (Self::buttons__select, "Select"),
            (Self::buttons__set, "Set"),
            (Self::buttons__show_all, "Show all"),
            (Self::buttons__show_details, "Show details"),
            (Self::buttons__show_words, "Show words"),
            (Self::buttons__skip, "Skip"),
            (Self::buttons__try_again, "Try again"),
            (Self::buttons__turn_off, "Turn off"),
            (Self::buttons__turn_on, "Turn on"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__addr_base, "Base"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__addr_enterprise, "Enterprise"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__addr_legacy, "Legacy"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__addr_pointer, "Pointer"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__addr_reward, "Reward"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__address_no_staking, "address - no staking rewards."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__amount_burned_decimals_unknown, "Amount burned (decimals unknown):"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__amount_minted_decimals_unknown, "Amount minted (decimals unknown):"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__amount_sent_decimals_unknown, "Amount sent (decimals unknown):"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__anonymous_pool, "Pool has no metadata (anonymous pool)"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__asset_fingerprint, "Asset fingerprint:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__auxiliary_data_hash, "Auxiliary data hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__block, "Block"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__catalyst, "Catalyst"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__certificate, "Certificate"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__change_output, "Change output"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__check_all_items, "Check all items carefully."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__choose_level_of_details, "Choose level of details:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__collateral_input_id, "Collateral input ID:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__collateral_input_index, "Collateral input index:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__collateral_output_contains_tokens, "The collateral return output contains tokens."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__collateral_return, "Collateral return"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__confirm_signing_stake_pool, "Confirm signing the stake pool registration as an owner."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__confirm_transaction, "Confirm transaction"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__confirming_a_multisig_transaction, "Confirming a multisig transaction."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__confirming_a_plutus_transaction, "Confirming a Plutus transaction."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__confirming_pool_registration, "Confirming pool registration as owner."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__confirming_transaction, "Confirming a transaction."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__cost, "Cost"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__credential_mismatch, "Credential doesn't match payment credential."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__datum_hash, "Datum hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__delegating_to, "Delegating to:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__for_account_and_index_template, "for account {0} and index {1}:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__for_account_template, "for account {0}:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__for_key_hash, "for key hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__for_script, "for script:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__inline_datum, "Inline datum"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__input_id, "Input ID:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__input_index, "Input index:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__intro_text_change, "The following address is a change address. Its"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__intro_text_owned_by_device, "The following address is owned by this device. Its"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__intro_text_registration_payment, "The vote key registration payment address is owned by this device. Its"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__key_hash, "key hash"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__margin, "Margin"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__multisig_path, "multi-sig path"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__nested_scripts_template, "Contains {0} nested scripts."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__network, "Network:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__no_output_tx, "Transaction has no outputs, network cannot be verified."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__nonce, "Nonce:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__other, "other"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__path, "path"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__pledge, "Pledge"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__pointer, "pointer"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__policy_id, "Policy ID"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__pool_metadata_hash, "Pool metadata hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__pool_metadata_url, "Pool metadata url:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__pool_owner, "Pool owner:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__pool_reward_account, "Pool reward account:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__reference_input_id, "Reference input ID:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__reference_input_index, "Reference input index:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__reference_script, "Reference script"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__required_signer, "Required signer"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__reward, "reward"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__reward_address, "Address is a reward address."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__reward_eligibility_warning, "Warning: The address is not a payment address, it is not eligible for rewards."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__rewards_go_to, "Rewards go to:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script, "script"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_all, "All"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_any, "Any"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_data_hash, "Script data hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_hash, "Script hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_invalid_before, "Invalid before"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_invalid_hereafter, "Invalid hereafter"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_key, "Key"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_n_of_k, "N of K"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__script_reward, "script reward"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__sending, "Sending"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__show_simple, "Show Simple"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__sign_tx_path_template, "Sign transaction with {0}"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__stake_delegation, "Stake delegation"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__stake_deregistration, "Stake key deregistration"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__stake_pool_registration, "Stakepool registration"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__stake_pool_registration_pool_id, "Stake pool registration\nPool ID:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__stake_registration, "Stake key registration"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__staking_key_for_account, "Staking key for account"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__to_pool, "to pool:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__token_minting_path, "token minting path"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__total_collateral, "Total collateral:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__transaction, "Transaction"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__transaction_contains_minting_or_burning, "The transaction contains minting or burning of tokens."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__transaction_contains_script_address_no_datum, "The following transaction output contains a script address, but does not contain a datum."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__transaction_id, "Transaction ID:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__transaction_no_collateral_input, "The transaction contains no collateral inputs. Plutus script will not be able to run."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__transaction_no_script_data_hash, "The transaction contains no script data hash. Plutus script will not be able to run."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__transaction_output_contains_tokens, "The following transaction output contains tokens."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__ttl, "TTL:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__unknown_collateral_amount, "Unknown collateral amount."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__unusual_path, "Path is unusual."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__valid_since, "Valid since:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__verify_script, "Verify script"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__vote_key_registration, "Vote key registration (CIP-36)"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__vote_public_key, "Vote public key:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__voting_purpose, "Voting purpose:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__warning, "Warning"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__weight, "Weight:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__withdrawal_for_address_template, "Confirm withdrawal for {0} address:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__x_of_y_signatures_template, "Requires {0} out of {1} signatures."),
            (Self::coinjoin__access_account, "Access your coinjoin account?"),
            (Self::coinjoin__do_not_disconnect, "Do not disconnect your Trezor!"),
            (Self::coinjoin__max_mining_fee, "Max mining fee"),
            (Self::coinjoin__max_rounds, "Max rounds"),
            (Self::coinjoin__title, "Authorize coinjoin"),
            #[cfg(feature = "layout_bolt")]
            (Self::coinjoin__title_progress, "Coinjoin in progress"),
            #[cfg(feature = "layout_caesar")]
            (Self::coinjoin__title_progress, "Coinjoin in progress"),
            #[cfg(feature = "layout_delizia")]
            (Self::coinjoin__title_progress, "Coinjoin in progress"),
            #[cfg(feature = "layout_eckhart")]
            (Self::coinjoin__title_progress, "Coinjoin in progress..."),
            (Self::coinjoin__waiting_for_others, "Waiting for others"),
            (Self::confirm_total__fee_rate_colon, "Fee rate:"),
            (Self::confirm_total__sending_from_account, "Sending from account:"),
            (Self::confirm_total__title_fee, "Fee info"),
            (Self::confirm_total__title_sending_from, "Sending from"),
            #[cfg(feature = "debug")]
            (Self::debug__loading_seed, "Loading seed"),
            #[cfg(feature = "debug")]
            (Self::debug__loading_seed_not_recommended, "Loading private seed is not recommended."),
            (Self::device_name__change_template, "Change device name to {0}?"),
            (Self::device_name__title, "Device name"),
            (Self::entropy__send, "Do you really want to send entropy?"),
            (Self::entropy__title_confirm, "Confirm entropy"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__about_to_sign_template, "You are about to sign {0}."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__about_to_sign_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__about_to_sign_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__about_to_sign_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__action_name, "Action Name:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__action_name, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__action_name, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__action_name, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__arbitrary_data, "Arbitrary data"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__arbitrary_data, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__arbitrary_data, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__arbitrary_data, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__buy_ram, "Buy RAM"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__buy_ram, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__buy_ram, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__buy_ram, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__bytes, "Bytes:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__bytes, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__bytes, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__bytes, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__cancel_vote, "Cancel vote"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__cancel_vote, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__cancel_vote, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__cancel_vote, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__checksum, "Checksum:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__checksum, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__checksum, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__checksum, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__code, "Code:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__code, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__code, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__code, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__contract, "Contract:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__contract, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__contract, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__contract, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__cpu, "CPU:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__cpu, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__cpu, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__cpu, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__creator, "Creator:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__creator, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__creator, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__creator, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__delegate, "Delegate"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__delegate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__delegate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__delegate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__delete_auth, "Delete Auth"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__delete_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__delete_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__delete_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__from, "From:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__from, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__from, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__from, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__link_auth, "Link Auth"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__link_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__link_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__link_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__memo, "Memo"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__memo, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__memo, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__memo, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__name, "Name:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__name, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__name, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__name, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__net, "NET:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__net, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__net, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__net, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__new_account, "New account"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__new_account, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__new_account, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__new_account, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__owner, "Owner:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__owner, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__owner, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__owner, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__parent, "Parent:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__parent, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__parent, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__parent, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__payer, "Payer:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__payer, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__payer, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__payer, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__permission, "Permission:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__permission, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__permission, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__permission, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__proxy, "Proxy:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__proxy, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__proxy, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__proxy, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__receiver, "Receiver:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__receiver, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__receiver, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__receiver, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__refund, "Refund"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__refund, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__refund, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__refund, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__requirement, "Requirement:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__requirement, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__requirement, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__requirement, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__sell_ram, "Sell RAM"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__sell_ram, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__sell_ram, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__sell_ram, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__sender, "Sender:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__sender, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__sender, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__sender, ""),
            (Self::send__sign_transaction, "Sign transaction"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__threshold, "Threshold:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__threshold, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__threshold, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__threshold, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__to, "To:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__to, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__to, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__to, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__transfer, "Transfer:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__transfer, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__transfer, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__transfer, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__type, "Type:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__type, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__type, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__type, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__undelegate, "Undelegate"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__undelegate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__undelegate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__undelegate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__unlink_auth, "Unlink Auth"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__unlink_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__unlink_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__unlink_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__update_auth, "Update Auth"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__update_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__update_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__update_auth, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__vote_for_producers, "Vote for producers"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__vote_for_producers, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__vote_for_producers, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__vote_for_producers, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__vote_for_proxy, "Vote for proxy"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__vote_for_proxy, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__vote_for_proxy, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__vote_for_proxy, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::eos__voter, "Voter:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::eos__voter, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::eos__voter, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::eos__voter, ""),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__amount_sent, "Amount sent:"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__data_size_template, "Size: {0} bytes"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__gas_limit, "Gas limit"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__gas_price, "Gas price"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__max_gas_price, "Max fee per gas"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__name_and_version, "Name and version"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__new_contract, "New contract will be deployed"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__no_message_field, "No message field"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__priority_fee, "Max priority fee"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__show_full_array, "Show full array"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__show_full_domain, "Show full domain"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__show_full_message, "Show full message"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__show_full_struct, "Show full struct"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__sign_eip712, "Really sign EIP-712 typed data?"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_input_data, "Input data"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_confirm_domain, "Confirm domain"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_confirm_message, "Confirm message"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_confirm_struct, "Confirm struct"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_confirm_typed_data, "Confirm typed data"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_signing_address, "Signing address"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__units_template, "{0} units"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__unknown_token, "Unknown token"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__valid_signature, "The signature is valid."),
            (Self::experimental_mode__enable, "Enable experimental features?"),
            (Self::experimental_mode__only_for_dev, "Only for development and beta testing!"),
            (Self::experimental_mode__title, "Experimental mode"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__already_registered, "Already registered"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__device_already_registered, "This device is already registered with this application."),
            #[cfg(feature = "universal_fw")]
            (Self::fido__device_already_registered_with_template, "This device is already registered with {0}."),
            #[cfg(feature = "universal_fw")]
            (Self::fido__device_not_registered, "This device is not registered with this application."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::fido__does_not_belong, "The credential you are trying to import does\nnot belong to this authenticator."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::fido__does_not_belong, "The credential you are trying to import does\nnot belong to this authenticator."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::fido__does_not_belong, "The credential you are trying to import does\nnot belong to this authenticator."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::fido__does_not_belong, "The credential you are trying to import does not belong to this authenticator."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::fido__erase_credentials, "erase all credentials?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::fido__erase_credentials, "erase all credentials?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::fido__erase_credentials, "erase all credentials?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::fido__erase_credentials, "Delete all of the saved credentials?"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__export_credentials, "Export information about the credentials stored on this device?"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__not_registered, "Not registered"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__not_registered_with_template, "This device is not registered with\n{0}."),
            #[cfg(feature = "universal_fw")]
            (Self::fido__please_enable_pin_protection, "Please enable PIN protection."),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_authenticate, "FIDO2 authenticate"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_import_credential, "Import credential"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_list_credentials, "List credentials"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_register, "FIDO2 register"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_remove_credential, "Remove credential"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_reset, "FIDO2 reset"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_u2f_auth, "U2F authenticate"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_u2f_register, "U2F register"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_verify_user, "FIDO2 verify user"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__unable_to_verify_user, "Unable to verify user."),
            #[cfg(feature = "universal_fw")]
            (Self::fido__wanna_erase_credentials, "Do you really want to erase all credentials?"),
            (Self::firmware_update__title, "Update firmware"),
            (Self::firmware_update__title_fingerprint, "FW fingerprint"),
            (Self::homescreen__click_to_connect, "Click to Connect"),
            (Self::homescreen__click_to_unlock, "Click to Unlock"),
            (Self::homescreen__title_backup_failed, "Backup failed"),
            (Self::homescreen__title_backup_needed, "Backup needed"),
            (Self::homescreen__title_coinjoin_authorized, "Coinjoin authorized"),
            (Self::homescreen__title_experimental_mode, "Experimental mode"),
            (Self::homescreen__title_no_usb_connection, "No USB connection"),
            (Self::homescreen__title_pin_not_set, "PIN not set"),
            (Self::homescreen__title_seedless, "Seedless"),
            (Self::homescreen__title_set, "Change wallpaper"),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__back, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__back, "BACK"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__back, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__back, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__cancel, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__cancel, "CANCEL"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__cancel, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__cancel, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__delete, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__delete, "DELETE"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__delete, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__delete, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__enter, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__enter, "ENTER"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__enter, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__enter, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__return, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__return, "RETURN"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__return, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__return, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__show, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__show, "SHOW"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__show, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__show, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__space, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__space, "SPACE"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__space, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__space, ""),
            (Self::joint__title, "Joint transaction"),
            (Self::joint__to_the_total_amount, "To the total amount:"),
            (Self::joint__you_are_contributing, "You are contributing:"),
            (Self::language__change_to_template, "Change language to {0}?"),
            (Self::language__changed, "Language changed successfully"),
            #[cfg(feature = "layout_bolt")]
            (Self::language__progress, "Changing language"),
            #[cfg(feature = "layout_caesar")]
            (Self::language__progress, "Changing language"),
            #[cfg(feature = "layout_delizia")]
            (Self::language__progress, "Changing language"),
            #[cfg(feature = "layout_eckhart")]
            (Self::language__progress, "Changing language..."),
            (Self::language__title, "Language settings"),
            (Self::lockscreen__tap_to_connect, "Tap to connect"),
            (Self::lockscreen__tap_to_unlock, "Tap to unlock"),
            (Self::lockscreen__title_locked, "Locked"),
            (Self::lockscreen__title_not_connected, "Not connected"),
            (Self::misc__decrypt_value, "Decrypt value"),
            (Self::misc__encrypt_value, "Encrypt value"),
            (Self::misc__title_suite_labeling, "Suite labeling"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_amount__decrease_amount, "Decrease amount by:"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_amount__decrease_amount, "Decrease amount by:"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_amount__decrease_amount, "Decrease amount by:"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_amount__decrease_amount, "Decrease amount by"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_amount__increase_amount, "Increase amount by:"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_amount__increase_amount, "Increase amount by:"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_amount__increase_amount, "Increase amount by:"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_amount__increase_amount, "Increase amount by"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_amount__new_amount, "New amount:"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_amount__new_amount, "New amount:"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_amount__new_amount, "New amount:"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_amount__new_amount, "New amount"),
            (Self::modify_amount__title, "Modify amount"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_fee__decrease_fee, "Decrease fee by:"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_fee__decrease_fee, "Decrease fee by:"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_fee__decrease_fee, "Decrease fee by:"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_fee__decrease_fee, "Decrease fee by"),
            (Self::modify_fee__fee_rate, "Fee rate:"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_fee__increase_fee, "Increase fee by:"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_fee__increase_fee, "Increase fee by:"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_fee__increase_fee, "Increase fee by:"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_fee__increase_fee, "Increase fee by"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_fee__new_transaction_fee, "New transaction fee:"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_fee__new_transaction_fee, "New transaction fee:"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_fee__new_transaction_fee, "New transaction fee:"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_fee__new_transaction_fee, "New transaction fee"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_fee__no_change, "Fee did not change.\n"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_fee__no_change, "Fee did not change.\n"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_fee__no_change, "Fee did not change.\n"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_fee__no_change, "Fee did not change"),
            (Self::modify_fee__title, "Modify fee"),
            #[cfg(feature = "layout_bolt")]
            (Self::modify_fee__transaction_fee, "Transaction fee:"),
            #[cfg(feature = "layout_caesar")]
            (Self::modify_fee__transaction_fee, "Transaction fee:"),
            #[cfg(feature = "layout_delizia")]
            (Self::modify_fee__transaction_fee, "Transaction fee:"),
            #[cfg(feature = "layout_eckhart")]
            (Self::modify_fee__transaction_fee, "Transaction fee"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__confirm_export, "Confirm export"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__confirm_ki_sync, "Confirm ki sync"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__confirm_refresh, "Confirm refresh"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__confirm_unlock_time, "Confirm unlock time"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__hashing_inputs, "Hashing inputs"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__payment_id, "Payment ID"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__postprocessing, "Postprocessing..."),
            #[cfg(feature = "universal_fw")]
            (Self::monero__processing, "Processing..."),
            #[cfg(feature = "universal_fw")]
            (Self::monero__processing_inputs, "Processing inputs"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__processing_outputs, "Processing outputs"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__signing, "Signing..."),
            #[cfg(feature = "universal_fw")]
            (Self::monero__signing_inputs, "Signing inputs"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__unlock_time_set_template, "Unlock time for this transaction is set to {0}"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__wanna_export_tx_der, "Do you really want to export tx_der\nfor tx_proof?"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__wanna_export_tx_key, "Do you really want to export tx_key?"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__wanna_export_watchkey, "Do you really want to export watch-only credentials?"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__wanna_start_refresh, "Do you really want to\nstart refresh?"),
            #[cfg(feature = "universal_fw")]
            (Self::monero__wanna_sync_key_images, "Do you really want to\nsync key images?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__absolute, "absolute"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__absolute, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__absolute, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__absolute, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__activate, "Activate"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__activate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__activate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__activate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__add, "Add"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__add, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__add, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__add, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_action, "Confirm action"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_action, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_action, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_action, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_address, "Confirm address"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_address, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_address, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_address, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_creation_fee, "Confirm creation fee"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_creation_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_creation_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_creation_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_mosaic, "Confirm mosaic"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_multisig_fee, "Confirm multisig fee"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_multisig_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_multisig_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_multisig_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_namespace, "Confirm namespace"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_payload, "Confirm payload"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_payload, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_payload, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_payload, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_properties, "Confirm properties"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_properties, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_properties, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_properties, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_rental_fee, "Confirm rental fee"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_rental_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_rental_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_rental_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__confirm_transfer_of, "Confirm transfer of"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__confirm_transfer_of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__confirm_transfer_of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__confirm_transfer_of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__convert_account_to_multisig, "Convert account to multisig account?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__convert_account_to_multisig, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__convert_account_to_multisig, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__convert_account_to_multisig, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__cosign_transaction_for, "Cosign transaction for"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__cosign_transaction_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__cosign_transaction_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__cosign_transaction_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__cosignatory, " cosignatory"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__cosignatory, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__cosignatory, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__cosignatory, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__create_mosaic, "Create mosaic"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__create_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__create_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__create_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__create_namespace, "Create namespace"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__create_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__create_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__create_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__deactivate, "Deactivate"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__deactivate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__deactivate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__deactivate, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__decrease, "Decrease"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__decrease, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__decrease, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__decrease, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__description, "Description:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__description, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__description, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__description, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__divisibility_and_levy_cannot_be_shown, "Divisibility and levy cannot be shown for unknown mosaics"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__divisibility_and_levy_cannot_be_shown, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__divisibility_and_levy_cannot_be_shown, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__divisibility_and_levy_cannot_be_shown, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__encrypted, "Encrypted"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__encrypted, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__encrypted, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__encrypted, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__final_confirm, "Final confirm"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__final_confirm, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__final_confirm, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__final_confirm, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__immutable, "immutable"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__immutable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__immutable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__immutable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__increase, "Increase"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__increase, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__increase, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__increase, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__initial_supply, "Initial supply:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__initial_supply, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__initial_supply, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__initial_supply, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__initiate_transaction_for, "Initiate transaction for"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__initiate_transaction_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__initiate_transaction_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__initiate_transaction_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__levy_divisibility, "Levy divisibility:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__levy_divisibility, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__levy_divisibility, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__levy_divisibility, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__levy_fee, "Levy fee:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__levy_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__levy_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__levy_fee, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__levy_fee_of, "Confirm mosaic levy fee of"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__levy_fee_of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__levy_fee_of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__levy_fee_of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__levy_mosaic, "Levy mosaic:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__levy_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__levy_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__levy_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__levy_namespace, "Levy namespace:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__levy_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__levy_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__levy_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__levy_recipient, "Levy recipient:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__levy_recipient, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__levy_recipient, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__levy_recipient, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__levy_type, "Levy type:"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__levy_type, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__levy_type, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__levy_type, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__modify_supply_for, "Modify supply for"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__modify_supply_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__modify_supply_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__modify_supply_for, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__modify_the_number_of_cosignatories_by, "Modify the number of cosignatories by "),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__modify_the_number_of_cosignatories_by, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__modify_the_number_of_cosignatories_by, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__modify_the_number_of_cosignatories_by, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__mutable, "mutable"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__mutable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__mutable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__mutable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__of, "of"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__of, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__percentile, "percentile"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__percentile, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__percentile, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__percentile, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__raw_units_template, "{0} raw units"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__raw_units_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__raw_units_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__raw_units_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__remote_harvesting, " remote harvesting?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__remote_harvesting, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__remote_harvesting, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__remote_harvesting, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__remove, "Remove"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__remove, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__remove, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__remove, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__set_minimum_cosignatories_to, "Set minimum cosignatories to "),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__set_minimum_cosignatories_to, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__set_minimum_cosignatories_to, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__set_minimum_cosignatories_to, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__sign_tx_fee_template, "Sign this transaction\nand pay {0}\nfor network fee?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__sign_tx_fee_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__sign_tx_fee_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__sign_tx_fee_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__supply_change, "Supply change"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__supply_change, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__supply_change, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__supply_change, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__supply_units_template, "{0} supply by {1} whole units?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__supply_units_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__supply_units_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__supply_units_template, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__transferable, "Transferable?"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__transferable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__transferable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__transferable, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__under_namespace, "under namespace"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__under_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__under_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__under_namespace, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__unencrypted, "Unencrypted"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__unencrypted, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__unencrypted, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__unencrypted, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::nem__unknown_mosaic, "Unknown mosaic!"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::nem__unknown_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::nem__unknown_mosaic, ""),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::nem__unknown_mosaic, ""),
            (Self::passphrase__access_wallet, "Access passphrase wallet?"),
            (Self::passphrase__always_on_device, "Always enter your passphrase on Trezor?"),
            (Self::passphrase__from_host_not_shown, "Passphrase provided by connected app will be used but will not be displayed due to the device settings."),
            (Self::passphrase__wallet, "Passphrase wallet"),
            #[cfg(feature = "layout_bolt")]
            (Self::passphrase__hide, "Hide passphrase coming from app?"),
            #[cfg(feature = "layout_caesar")]
            (Self::passphrase__hide, "Hide passphrase coming from app?"),
            #[cfg(feature = "layout_delizia")]
            (Self::passphrase__hide, "Hide passphrase coming from app?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::passphrase__hide, "Hide your passphrase on Trezor entered on connected app?"),
            (Self::passphrase__next_screen_will_show_passphrase, "The next screen shows your passphrase."),
            (Self::passphrase__please_enter, "Please enter your passphrase."),
            (Self::passphrase__revoke_on_device, "Do you want to revoke the passphrase on device setting?"),
            (Self::passphrase__title_confirm, "Confirm passphrase"),
            (Self::passphrase__title_enter, "Enter passphrase"),
            (Self::passphrase__title_hide, "Hide passphrase"),
            (Self::passphrase__title_settings, "Passphrase settings"),
            (Self::passphrase__title_source, "Passphrase source"),
            (Self::passphrase__turn_off, "Turn off passphrase protection?"),
            (Self::passphrase__turn_on, "Turn on passphrase protection?"),
            (Self::pin__change, "Change PIN"),
            (Self::pin__changed, "PIN changed."),
            (Self::pin__cursor_will_change, "Position of the cursor will change between entries for enhanced security."),
            (Self::pin__diff_from_wipe_code, "The new PIN must be different from your wipe code."),
            (Self::pin__disabled, "PIN protection\nturned off."),
            (Self::pin__enabled, "PIN protection\nturned on."),
            (Self::pin__enter, "Enter PIN"),
            (Self::pin__enter_new, "Enter new PIN"),
            (Self::pin__entered_not_valid, "The PIN you have entered is not valid."),
            #[cfg(feature = "layout_bolt")]
            (Self::pin__info, "PIN will be required to access this device."),
            #[cfg(feature = "layout_caesar")]
            (Self::pin__info, "PIN will be required to access this device."),
            #[cfg(feature = "layout_delizia")]
            (Self::pin__info, "PIN will be required to access this device."),
            #[cfg(feature = "layout_eckhart")]
            (Self::pin__info, "The PIN will be required to access this device."),
            (Self::pin__invalid_pin, "Invalid PIN"),
            (Self::pin__last_attempt, "Last attempt"),
            (Self::pin__mismatch, "Entered PINs do not match!"),
            (Self::pin__pin_mismatch, "PIN mismatch"),
            (Self::pin__please_check_again, "Please check again."),
            (Self::pin__reenter_new, "Re-enter new PIN"),
            (Self::pin__reenter_to_confirm, "Please re-enter PIN to confirm."),
            (Self::pin__should_be_long, "PIN should be 4-50 digits long."),
            (Self::pin__title_check_pin, "Check PIN"),
            (Self::pin__title_settings, "PIN settings"),
            (Self::pin__title_wrong_pin, "Wrong PIN"),
            (Self::pin__tries_left, "tries left"),
            (Self::pin__turn_off, "Are you sure you want to turn off PIN protection?"),
            (Self::pin__turn_on, "Turn on PIN protection?"),
            (Self::pin__wrong_pin, "Wrong PIN"),
            (Self::plurals__contains_x_keys, "key|keys"),
            (Self::plurals__lock_after_x_hours, "hour|hours"),
            (Self::plurals__lock_after_x_milliseconds, "millisecond|milliseconds"),
            (Self::plurals__lock_after_x_minutes, "minute|minutes"),
            (Self::plurals__lock_after_x_seconds, "second|seconds"),
            (Self::plurals__sign_x_actions, "action|actions"),
            (Self::plurals__transaction_of_x_operations, "operation|operations"),
            (Self::plurals__x_groups_needed, "group|groups"),
            (Self::plurals__x_shares_needed, "share|shares"),
            (Self::progress__authenticity_check, "Checking authenticity..."),
            (Self::progress__done, "Done"),
            (Self::progress__loading_transaction, "Loading transaction..."),
            (Self::progress__locking_device, "Locking the device..."),
            (Self::progress__one_second_left, "1 second left"),
            #[cfg(feature = "layout_bolt")]
            (Self::progress__please_wait, "Please wait"),
            #[cfg(feature = "layout_caesar")]
            (Self::progress__please_wait, "Please wait"),
            #[cfg(feature = "layout_delizia")]
            (Self::progress__please_wait, "Please wait"),
            #[cfg(feature = "layout_eckhart")]
            (Self::progress__please_wait, "Please wait..."),
            #[cfg(feature = "layout_bolt")]
            (Self::storage_msg__processing, "Processing"),
            #[cfg(feature = "layout_caesar")]
            (Self::storage_msg__processing, "Processing"),
            #[cfg(feature = "layout_delizia")]
            (Self::storage_msg__processing, "Processing"),
            #[cfg(feature = "layout_eckhart")]
            (Self::storage_msg__processing, "Processing..."),
            (Self::progress__refreshing, "Refreshing..."),
            (Self::progress__signing_transaction, "Signing transaction..."),
            (Self::progress__syncing, "Syncing..."),
            (Self::progress__x_seconds_left_template, "{0} seconds left"),
            (Self::reboot_to_bootloader__restart, "Trezor will restart in bootloader mode."),
            (Self::reboot_to_bootloader__title, "Go to bootloader"),
            (Self::reboot_to_bootloader__version_by_template, "Firmware version {0}\nby {1}"),
            (Self::recovery__cancel_dry_run, "Cancel backup check"),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__check_dry_run, "Check your backup?"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__check_dry_run, "Check your backup?"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__check_dry_run, "Check your backup?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__check_dry_run, "Let's do a wallet backup check."),
            (Self::recovery__cursor_will_change, "Position of the cursor will change between entries for enhanced security."),
            (Self::recovery__dry_run_bip39_valid_match, "The entered wallet backup is valid and matches the one in this device."),
            (Self::recovery__dry_run_bip39_valid_mismatch, "The entered wallet backup is valid but does not match the one in the device."),
            (Self::recovery__dry_run_slip39_valid_match, "The entered recovery shares are valid and match what is currently in the device."),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__dry_run_slip39_valid_mismatch, "The entered recovery shares are valid but do not match what is currently in the device."),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__dry_run_slip39_valid_mismatch, "The entered recovery shares are valid but do not match what is currently in the device."),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__dry_run_slip39_valid_mismatch, "The entered wallet backup is valid but doesn't match the one on this device."),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__dry_run_slip39_valid_mismatch, "The entered wallet backup is valid but doesn't match the one on this device."),
            (Self::recovery__enter_any_share, "Enter any share"),
            (Self::recovery__enter_backup, "Enter your backup."),
            (Self::recovery__enter_different_share, "Enter a different share."),
            (Self::recovery__enter_share_from_diff_group, "Enter share from a different group."),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__group_num_template, "Group {0}"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__group_num_template, "Group {0}"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__group_num_template, "Group {0}"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__group_num_template, "Group #{0}"),
            (Self::recovery__group_threshold_reached, "Group threshold reached."),
            (Self::recovery__invalid_wallet_backup_entered, "Invalid wallet backup entered."),
            (Self::recovery__invalid_share_entered, "Invalid recovery share entered."),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__more_shares_needed, "More shares needed"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__more_shares_needed, "More shares needed"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__more_shares_needed, "More shares needed"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__more_shares_needed, "More shares needed."),
            (Self::recovery__num_of_words, "Select the number of words in your backup."),
            (Self::recovery__only_first_n_letters, "You'll only have to select the first 2-4 letters of each word."),
            (Self::recovery__progress_will_be_lost, "All progress will be lost."),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__share_already_entered, "Share already entered"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__share_already_entered, "Share already entered"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__share_already_entered, "Share already entered"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__share_already_entered, "Share already entered."),
            (Self::recovery__share_from_another_multi_share_backup, "You have entered a share from a different backup."),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__share_num_template, "Share {0}"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__share_num_template, "Share {0}"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__share_num_template, "Share {0}"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__share_num_template, "Share #{0}"),
            (Self::recovery__title, "Recover wallet"),
            (Self::recovery__title_cancel_dry_run, "Cancel backup check"),
            (Self::recovery__title_cancel_recovery, "Cancel recovery"),
            (Self::recovery__title_dry_run, "Backup check"),
            (Self::recovery__title_recover, "Recover wallet"),
            (Self::recovery__title_remaining_shares, "Remaining shares"),
            (Self::recovery__type_word_x_of_y_template, "Type word {0} of {1}"),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__wallet_recovered, "Wallet recovery completed"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__wallet_recovered, "Wallet recovery completed"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__wallet_recovered, "Wallet recovery completed"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__wallet_recovered, "Wallet recovery completed."),
            (Self::recovery__wanna_cancel_dry_run, "Are you sure you want to cancel the backup check?"),
            (Self::recovery__wanna_cancel_recovery, "Are you sure you want to cancel the recovery process?"),
            (Self::recovery__word_count_template, "({0} words)"),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__word_x_of_y_template, "Word {0} of {1}"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__word_x_of_y_template, "Word {0} of {1}"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__word_x_of_y_template, "Word {0} of {1}"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__word_x_of_y_template, "Word {0}\nof {1}"),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__x_more_items_starting_template_plural, "{count} more {plural} starting"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__x_more_items_starting_template_plural, "{count} more {plural} starting"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__x_more_items_starting_template_plural, "{count} more {plural} starting"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__x_more_items_starting_template_plural, "You need {count} more {plural} starting"),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__x_more_shares_needed_template_plural, "{count} more {plural} needed"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__x_more_shares_needed_template_plural, "{count} more {plural} needed"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__x_more_shares_needed_template_plural, "{count} more {plural} needed"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__x_more_shares_needed_template_plural, "{count} more {plural} needed."),
            #[cfg(feature = "layout_bolt")]
            (Self::recovery__x_of_y_entered_template, "{0} of {1} shares entered"),
            #[cfg(feature = "layout_caesar")]
            (Self::recovery__x_of_y_entered_template, "{0} of {1} shares entered"),
            #[cfg(feature = "layout_delizia")]
            (Self::recovery__x_of_y_entered_template, "{0} of {1} shares entered"),
            #[cfg(feature = "layout_eckhart")]
            (Self::recovery__x_of_y_entered_template, "{0} of {1} shares entered."),
            (Self::recovery__you_have_entered, "You have entered"),
            (Self::reset__advanced_group_threshold_info, "The group threshold specifies the number of groups required to recover your wallet."),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__all_x_of_y_template, "all {0} of {1} shares"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__all_x_of_y_template, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__all_x_of_y_template, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__all_x_of_y_template, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__any_x_of_y_template, "any {0} of {1} shares"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__any_x_of_y_template, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__any_x_of_y_template, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__any_x_of_y_template, ""),
            (Self::reset__button_create, "Create wallet"),
            (Self::reset__button_recover, "Recover wallet"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__by_continuing, "By continuing you agree to Trezor Company's terms and conditions."),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__by_continuing, "By continuing you agree to Trezor Company's terms and conditions."),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__by_continuing, "By continuing you agree to Trezor Company's terms and conditions."),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__by_continuing, "By continuing, you agree to Trezor Company's Terms of Use."),
            (Self::reset__check_backup_title, "Check backup"),
            (Self::reset__check_group_share_title_template, "Check g{0} - share {1}"),
            (Self::reset__check_wallet_backup_title, "Check wallet backup"),
            (Self::reset__check_share_title_template, "Check share #{0}"),
            (Self::reset__continue_with_next_share, "Continue with the next share."),
            (Self::reset__continue_with_share_template, "Continue with share #{0}."),
            (Self::reset__finished_verifying_group_template, "You have finished verifying your recovery shares for group {0}."),
            (Self::reset__finished_verifying_wallet_backup, "You have finished verifying your wallet backup."),
            (Self::reset__finished_verifying_shares, "You have finished verifying your recovery shares."),
            (Self::reset__group_description, "A group is made up of recovery shares."),
            (Self::reset__group_info, "Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds."),
            (Self::reset__group_share_checked_successfully_template, "Group {0} - Share {1} checked successfully."),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__group_share_title_template, "Group {0} - share {1}"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__group_share_title_template, "Group {0} - share {1}"),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__group_share_title_template, "Group {0} - share {1}"),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__group_share_title_template, "Group #{0} - Share #{1}"),
            (Self::reset__more_info_at, "More info at"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__need_all_share_template, "For recovery you need all {0} of the shares."),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__need_all_share_template, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__need_all_share_template, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__need_all_share_template, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__need_any_share_template, "For recovery you need any {0} of the shares."),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__need_any_share_template, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__need_any_share_template, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__need_any_share_template, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__needed_to_form_a_group, "needed to form a group. "),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__needed_to_form_a_group, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__needed_to_form_a_group, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__needed_to_form_a_group, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__needed_to_recover_your_wallet, "needed to recover your wallet. "),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__needed_to_recover_your_wallet, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__needed_to_recover_your_wallet, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__needed_to_recover_your_wallet, ""),
            (Self::reset__never_make_digital_copy, "Never put your backup anywhere digital."),
            (Self::reset__num_of_share_holders_template, "{0} people or locations will each hold one share."),
            (Self::reset__num_of_shares_advanced_info_template, "Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}."),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__num_of_shares_basic_info_template, "Each recovery share is a sequence of {0} words. Next you will choose how many shares you need to recover your wallet."),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__num_of_shares_basic_info_template, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__num_of_shares_basic_info_template, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__num_of_shares_basic_info_template, ""),
            (Self::reset__num_shares_for_group_template, "The required number of shares to form Group {0}."),
            (Self::reset__number_of_shares_info, "= total number of unique word lists used for wallet backup."),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__one_share, "1 share"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__one_share, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__one_share, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__one_share, ""),
            (Self::reset__only_one_share_will_be_created, "Only one share will be created."),
            (Self::reset__recovery_wallet_backup_title, "Wallet backup"),
            (Self::reset__recovery_share_title_template, "Recovery share #{0}"),
            (Self::reset__required_number_of_groups, "The required number of groups for recovery."),
            (Self::reset__select_correct_word, "Select the correct word for each position."),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__select_word_template, "Select {0} word"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__select_word_template, "Select {0} word"),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__select_word_template, "Select {0} word"),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__select_word_template, "Select word #{0} from your wallet backup"),
            (Self::reset__select_word_x_of_y_template, "Select word {0} of {1}:"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__set_it_to_count_template, "Set it to {0} and you will need "),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__set_it_to_count_template, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__set_it_to_count_template, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__set_it_to_count_template, ""),
            (Self::reset__share_checked_successfully_template, "Share #{0} checked successfully."),
            (Self::reset__share_words_title, "Standard backup"),
            (Self::reset__slip39_checklist_num_groups, "Number of groups"),
            (Self::reset__slip39_checklist_num_shares, "Number of shares"),
            (Self::reset__slip39_checklist_set_num_groups, "Set number of groups"),
            (Self::reset__slip39_checklist_set_num_shares, "Set number of shares"),
            (Self::reset__slip39_checklist_set_sizes, "Set sizes and thresholds"),
            (Self::reset__slip39_checklist_set_sizes_longer, "Set size and threshold for each group"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__slip39_checklist_set_threshold, "Set threshold"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__slip39_checklist_set_threshold, "Set threshold"),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__slip39_checklist_set_threshold, "Set threshold"),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__slip39_checklist_set_threshold, "Set recovery threshold"),
            (Self::reset__slip39_checklist_title, "Backup checklist"),
            (Self::reset__slip39_checklist_write_down, "Write down and check all shares"),
            (Self::reset__slip39_checklist_write_down_recovery, "Write down & check all wallet backup shares"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__the_threshold_sets_the_number_of_shares, "The threshold sets the number of shares "),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__the_threshold_sets_the_number_of_shares, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__the_threshold_sets_the_number_of_shares, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__the_threshold_sets_the_number_of_shares, ""),
            (Self::reset__threshold_info, "= minimum number of unique word lists used for recovery."),
            (Self::reset__title_backup_is_done, "Backup is done"),
            (Self::reset__title_create_wallet, "Create wallet"),
            (Self::reset__title_group_threshold, "Group threshold"),
            (Self::reset__title_number_of_groups, "Number of groups"),
            (Self::reset__title_number_of_shares, "Number of shares"),
            (Self::reset__title_set_group_threshold, "Set group threshold"),
            (Self::reset__title_set_number_of_groups, "Set number of groups"),
            (Self::reset__title_set_number_of_shares, "Set number of shares"),
            (Self::reset__title_set_threshold, "Set threshold"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__to_form_group_template, "to form Group {0}."),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__to_form_group_template, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__to_form_group_template, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__to_form_group_template, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__tos_link, "trezor.io/tos"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__tos_link, "trezor.io/tos"),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__tos_link, "trezor.io/tos"),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__tos_link, "More at trezor.io/tos"),
            (Self::reset__total_number_of_shares_in_group_template, "Set the total number of shares in Group {0}."),
            (Self::reset__use_your_backup, "Use your backup when you need to recover your wallet."),
            (Self::reset__write_down_words_template, "Write the following {0} words in order on your wallet backup card."),
            (Self::reset__wrong_word_selected, "Wrong word selected!"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__you_need_one_share, "For recovery you need 1 share."),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__you_need_one_share, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__you_need_one_share, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__you_need_one_share, ""),
            (Self::reset__your_backup_is_done, "Your backup is done."),
            #[cfg(feature = "universal_fw")]
            (Self::ripple__confirm_tag, "Confirm tag"),
            #[cfg(feature = "universal_fw")]
            (Self::ripple__destination_tag_template, "Destination tag:\n{0}"),
            (Self::rotation__change_template, "Change display orientation to {0}?"),
            (Self::rotation__east, "east"),
            (Self::rotation__north, "north"),
            (Self::rotation__south, "south"),
            (Self::rotation__title_change, "Display orientation"),
            (Self::rotation__west, "west"),
            (Self::safety_checks__approve_unsafe_always, "Trezor will allow you to approve some actions which might be unsafe."),
            (Self::safety_checks__approve_unsafe_temporary, "Trezor will temporarily allow you to approve some actions which might be unsafe."),
            (Self::safety_checks__enforce_strict, "Do you really want to enforce strict safety checks (recommended)?"),
            (Self::safety_checks__title, "Safety checks"),
            (Self::safety_checks__title_safety_override, "Safety override"),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__all_data_will_be_lost, "All data on the SD card will be lost."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__all_data_will_be_lost, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__all_data_will_be_lost, "All data on the SD card will be lost."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__all_data_will_be_lost, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__card_required, "SD card required."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__card_required, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__card_required, "SD card required."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__card_required, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__disable, "Do you really want to remove SD card protection from your device?"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__disable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__disable, "Do you really want to remove SD card protection from your device?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__disable, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__disabled, "You have successfully disabled SD protection."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__disabled, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__disabled, "You have successfully disabled SD protection."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__disabled, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__enable, "Do you really want to secure your device with SD card protection?"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__enable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__enable, "Do you really want to secure your device with SD card protection?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__enable, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__enabled, "You have successfully enabled SD protection."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__enabled, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__enabled, "You have successfully enabled SD protection."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__enabled, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__error, "SD card error"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__error, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__error, "SD card error"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__error, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__format_card, "Format SD card"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__format_card, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__format_card, "Format SD card"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__format_card, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__insert_correct_card, "Please insert the correct SD card for this device."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__insert_correct_card, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__insert_correct_card, "Please insert the correct SD card for this device."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__insert_correct_card, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__please_insert, "Please insert your SD card."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__please_insert, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__please_insert, "Please insert your SD card."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__please_insert, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__please_unplug_and_insert, "Please unplug the device and insert your SD card."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__please_unplug_and_insert, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__please_unplug_and_insert, "Please unplug the device and insert your SD card."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__please_unplug_and_insert, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__problem_accessing, "There was a problem accessing the SD card."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__problem_accessing, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__problem_accessing, "There was a problem accessing the SD card."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__problem_accessing, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__refresh, "Do you really want to replace the current SD card secret with a newly generated one?"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__refresh, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__refresh, "Do you really want to replace the current SD card secret with a newly generated one?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__refresh, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__refreshed, "You have successfully refreshed SD protection."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__refreshed, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__refreshed, "You have successfully refreshed SD protection."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__refreshed, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__restart, "Do you want to restart Trezor in bootloader mode?"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__restart, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__restart, "Do you want to restart Trezor in bootloader mode?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__restart, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__title, "SD card protection"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__title, "SD card protection"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__title, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__title_problem, "SD card problem"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__title_problem, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__title_problem, "SD card problem"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__title_problem, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__unknown_filesystem, "Unknown filesystem."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__unknown_filesystem, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__unknown_filesystem, "Unknown filesystem."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__unknown_filesystem, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__unplug_and_insert_correct, "Please unplug the device and insert the correct SD card."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__unplug_and_insert_correct, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__unplug_and_insert_correct, "Please unplug the device and insert the correct SD card."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__unplug_and_insert_correct, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__use_different_card, "Use a different card or format the SD card to the FAT32 filesystem."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__use_different_card, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__use_different_card, "Use a different card or format the SD card to the FAT32 filesystem."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__use_different_card, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__wanna_format, "Do you really want to format the SD card?"),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__wanna_format, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__wanna_format, "Do you really want to format the SD card?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__wanna_format, ""),
            #[cfg(feature = "layout_bolt")]
            (Self::sd_card__wrong_sd_card, "Wrong SD card."),
            #[cfg(feature = "layout_caesar")]
            (Self::sd_card__wrong_sd_card, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sd_card__wrong_sd_card, "Wrong SD card."),
            #[cfg(feature = "layout_eckhart")]
            (Self::sd_card__wrong_sd_card, ""),
            (Self::send__confirm_sending, "Sending amount"),
            (Self::send__from_multiple_accounts, "Sending from multiple accounts."),
            (Self::send__including_fee, "Including fee:"),
            (Self::send__maximum_fee, "Maximum fee"),
            (Self::send__receiving_to_multisig, "Receiving to a multisig address."),
            (Self::send__title_confirm_sending, "Confirm sending"),
            (Self::send__title_joint_transaction, "Joint transaction"),
            (Self::send__title_receiving_to, "Receiving to"),
            (Self::send__title_sending, "Sending"),
            (Self::send__title_sending_amount, "Sending amount"),
            (Self::send__title_sending_to, "Sending to"),
            (Self::send__to_the_total_amount, "To the total amount:"),
            (Self::send__transaction_id, "Transaction ID"),
            (Self::send__you_are_contributing, "You are contributing:"),
            (Self::share_words__words_in_order, " words in order."),
            (Self::share_words__wrote_down_all, "I wrote down all "),
            (Self::sign_message__bytes_template, "{0} Bytes"),
            (Self::sign_message__confirm_address, "Signing address"),
            (Self::sign_message__confirm_message, "Confirm message"),
            (Self::sign_message__message_size, "Message size"),
            (Self::sign_message__verify_address, "Verify address"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__account_index, "Account index"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__associated_token_account, "Associated token account"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__confirm_multisig, "Confirm multisig"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__expected_fee, "Expected fee"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__instruction_accounts_template, "Instruction contains {0} accounts and its data is {1} bytes long."),
            #[cfg(feature = "universal_fw")]
            (Self::solana__instruction_data, "Instruction data"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__instruction_is_multisig, "The following instruction is a multisig instruction."),
            #[cfg(feature = "universal_fw")]
            (Self::solana__is_provided_via_lookup_table_template, "{0} is provided via a lookup table."),
            #[cfg(feature = "universal_fw")]
            (Self::solana__lookup_table_address, "Lookup table address"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__multiple_signers, "Multiple signers"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__transaction_contains_unknown_instructions, "Transaction contains unknown instructions."),
            #[cfg(feature = "universal_fw")]
            (Self::solana__transaction_requires_x_signers_template, "Transaction requires {0} signers which increases the fee."),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__account_merge, "Account Merge"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__account_thresholds, "Account Thresholds"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__add_signer, "Add Signer"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__add_trust, "Add trust"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__all_will_be_sent_to, "All XLM will be sent to"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__allow_trust, "Allow trust"),
            (Self::words__asset, "Asset"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__balance_id, "Balance ID"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__bump_sequence, "Bump Sequence"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__buying, "Buying:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__claim_claimable_balance, "Claim Claimable Balance"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__clear_data, "Clear data"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__clear_flags, "Clear flags"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__confirm_issuer, "Confirm Issuer"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__confirm_memo, "Confirm memo"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__confirm_operation, "Confirm operation"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__confirm_timebounds, "Confirm timebounds"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__create_account, "Create Account"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__debited_amount, "Debited amount"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__delete, "Delete"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__delete_passive_offer, "Delete Passive Offer"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__delete_trust, "Delete trust"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__destination, "Destination"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__exchanges_require_memo, "Memo is not set.\nTypically needed when sending to exchanges."),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__final_confirm, "Final confirm"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__hash, "Hash"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__high, "High:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__home_domain, "Home Domain"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__inflation, "Inflation"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__issuer_template, "{0} issuer"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__key, "Key:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__limit, "Limit"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__low, "Low:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__master_weight, "Master Weight:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__medium, "Medium:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__new_offer, "New Offer"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__new_passive_offer, "New Passive Offer"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__no_memo_set, "No memo set!"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__no_restriction, "[no restriction]"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__path_pay, "Path Pay"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__path_pay_at_least, "Path Pay at least"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__pay, "Pay"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__pay_at_most, "Pay at most"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__preauth_transaction, "Pre-auth transaction"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__price_per_template, "Price per {0}:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__remove_signer, "Remove Signer"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__revoke_trust, "Revoke trust"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__selling, "Selling:"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__set_data, "Set data"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__set_flags, "Set flags"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__set_sequence_to_template, "Set sequence to {0}?"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__sign_tx_count_template, "Sign this transaction made up of {0}"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__sign_tx_fee_template, "and pay {0}\nfor fee?"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__source_account, "Source account"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__trusted_account, "Trusted Account"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__update, "Update"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__valid_from, "Valid from (UTC)"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__valid_to, "Valid to (UTC)"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__value_sha256, "Value (SHA-256):"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__wanna_clean_value_key_template, "Do you want to clear value key {0}?"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__baker_address, "Baker address"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__balance, "Balance:"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__ballot, "Ballot:"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__confirm_delegation, "Confirm delegation"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__confirm_origination, "Confirm origination"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__delegator, "Delegator"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__proposal, "Proposal"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__register_delegate, "Register delegate"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__remove_delegation, "Remove delegation"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__submit_ballot, "Submit ballot"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__submit_proposal, "Submit proposal"),
            #[cfg(feature = "universal_fw")]
            (Self::tezos__submit_proposals, "Submit proposals"),
            (Self::tutorial__middle_click, "Press both left and right at the same\ntime to confirm."),
            (Self::tutorial__press_and_hold, "Press and hold the right button to\napprove important operations."),
            (Self::tutorial__ready_to_use, "You're ready to\nuse Trezor."),
            (Self::tutorial__scroll_down, "Press right to scroll down to read all content when text doesn't fit on one screen.\n\rPress left to scroll up."),
            (Self::tutorial__sure_you_want_skip, "Are you sure you\nwant to skip the tutorial?"),
            (Self::tutorial__title_hello, "Hello"),
            (Self::tutorial__title_screen_scroll, "Screen scroll"),
            (Self::tutorial__title_skip, "Skip tutorial"),
            (Self::tutorial__title_tutorial_complete, "Tutorial complete"),
            (Self::tutorial__use_trezor, "Use Trezor by\nclicking the left and right buttons.\n\rContinue right."),
            (Self::tutorial__welcome_press_right, "Welcome to Trezor. Press right to continue."),
            #[cfg(feature = "universal_fw")]
            (Self::u2f__get, "Increase and retrieve the U2F counter?"),
            #[cfg(feature = "universal_fw")]
            (Self::u2f__set_template, "Set the U2F counter to {0}?"),
            #[cfg(feature = "universal_fw")]
            (Self::u2f__title_get, "Get U2F counter"),
            #[cfg(feature = "universal_fw")]
            (Self::u2f__title_set, "Set U2F counter"),
            (Self::wipe__info, "All data will be erased."),
            (Self::wipe__title, "Wipe device"),
            (Self::wipe__want_to_wipe, "Do you really want to wipe the device?\n"),
            (Self::wipe_code__change, "Change wipe code"),
            (Self::wipe_code__changed, "Wipe code changed."),
            (Self::wipe_code__diff_from_pin, "The wipe code must be different from your PIN."),
            (Self::wipe_code__disabled, "Wipe code disabled."),
            (Self::wipe_code__enabled, "Wipe code enabled."),
            (Self::wipe_code__enter_new, "New wipe code"),
            (Self::wipe_code__info, "Wipe code can be used to erase all data from this device."),
            (Self::wipe_code__invalid, "Invalid wipe code"),
            (Self::wipe_code__mismatch, "The wipe codes you entered do not match."),
            (Self::wipe_code__reenter, "Re-enter wipe code"),
            (Self::wipe_code__reenter_to_confirm, "Please re-enter wipe code to confirm."),
            (Self::wipe_code__title_check, "Check wipe code"),
            (Self::wipe_code__title_invalid, "Invalid wipe code"),
            (Self::wipe_code__title_settings, "Wipe code settings"),
            (Self::wipe_code__turn_off, "Turn off wipe code protection?"),
            (Self::wipe_code__turn_on, "Turn on wipe code protection?"),
            (Self::wipe_code__wipe_code_mismatch, "Wipe code mismatch"),
            (Self::word_count__title, "Number of words"),
            (Self::words__account, "Account"),
            (Self::words__account_colon, "Account:"),
            (Self::words__address, "Address"),
            (Self::words__amount, "Amount"),
            (Self::words__are_you_sure, "Are you sure?"),
            (Self::words__array_of, "Array of"),
            (Self::words__blockhash, "Blockhash"),
            (Self::words__buying, "Buying"),
            (Self::words__confirm, "Confirm"),
            (Self::words__confirm_fee, "Confirm fee"),
            (Self::words__contains, "Contains"),
            (Self::words__continue_anyway_question, "Continue anyway?"),
            (Self::words__continue_with, "Continue with"),
            (Self::words__error, "Error"),
            (Self::words__fee, "Fee"),
            (Self::words__from, "from"),
            (Self::words__keep_it_safe, "Keep it safe!"),
            (Self::words__know_what_your_doing, "Continue only if you know what you are doing!"),
            (Self::words__my_trezor, "My Trezor"),
            (Self::words__no, "No"),
            (Self::words__outputs, "outputs"),
            (Self::words__please_check_again, "Please check again"),
            (Self::words__please_try_again, "Please try again"),
            (Self::words__really_wanna, "Do you really want to"),
            (Self::words__recipient, "Recipient"),
            (Self::words__sign, "Sign"),
            (Self::words__signer, "Signer"),
            (Self::words__title_check, "Check"),
            (Self::words__title_group, "Group"),
            (Self::words__title_information, "Information"),
            (Self::words__title_remember, "Remember"),
            (Self::words__title_share, "Share"),
            (Self::words__title_shares, "Shares"),
            (Self::words__title_success, "Success"),
            (Self::words__title_summary, "Summary"),
            (Self::words__title_threshold, "Threshold"),
            (Self::words__unknown, "Unknown"),
            (Self::words__warning, "Warning"),
            (Self::words__writable, "Writable"),
            (Self::words__yes, "Yes"),
            (Self::reboot_to_bootloader__just_a_moment, "Just a moment..."),
            #[cfg(feature = "layout_bolt")]
            (Self::inputs__previous, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::inputs__previous, "PREVIOUS"),
            #[cfg(feature = "layout_delizia")]
            (Self::inputs__previous, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::inputs__previous, ""),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_claim, "Claim"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_claim_address, "Claim address"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_claim_intro, "Claim ETH from Everstake?"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_stake, "Stake"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_stake_address, "Stake address"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_stake_intro, "Stake ETH on Everstake?"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_unstake, "Unstake"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__staking_unstake_intro, "Unstake ETH from Everstake?"),
            (Self::storage_msg__starting, "Starting up"),
            #[cfg(feature = "layout_bolt")]
            (Self::storage_msg__verifying_pin, "Verifying PIN"),
            #[cfg(feature = "layout_caesar")]
            (Self::storage_msg__verifying_pin, "Verifying PIN"),
            #[cfg(feature = "layout_delizia")]
            (Self::storage_msg__verifying_pin, "Verifying PIN"),
            #[cfg(feature = "layout_eckhart")]
            (Self::storage_msg__verifying_pin, "Verifying PIN..."),
            (Self::storage_msg__wrong_pin, "Wrong PIN"),
            (Self::reset__create_x_of_y_multi_share_backup_template, "Do you want to create a {0} of {1} multi-share backup?"),
            (Self::reset__title_shamir_backup, "Multi-share backup"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__always_abstain, "Always Abstain"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__always_no_confidence, "Always No Confidence"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__delegating_to_key_hash, "Delegating to key hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__delegating_to_script, "Delegating to script:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__deposit, "Deposit:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__vote_delegation, "Vote delegation"),
            (Self::instructions__tap_to_confirm, "Tap to confirm"),
            (Self::instructions__hold_to_confirm, "Hold to confirm"),
            (Self::words__important, "Important"),
            (Self::reset__words_written_down_template, "I wrote down all {0} words in order."),
            #[cfg(feature = "layout_bolt")]
            (Self::backup__create_backup_to_prevent_loss, "Create a backup to avoid losing access to your funds"),
            #[cfg(feature = "layout_caesar")]
            (Self::backup__create_backup_to_prevent_loss, "Create a backup to avoid losing access to your funds"),
            #[cfg(feature = "layout_delizia")]
            (Self::backup__create_backup_to_prevent_loss, "Create a backup to avoid losing access to your funds"),
            #[cfg(feature = "layout_eckhart")]
            (Self::backup__create_backup_to_prevent_loss, "Create a wallet backup to avoid losing access to your funds."),
            (Self::reset__check_backup_instructions, "Let's do a quick check of your backup."),
            (Self::words__instructions, "Instructions"),
            (Self::words__not_recommended, "Not recommended!"),
            (Self::address_details__account_info, "Account info"),
            (Self::address__cancel_contact_support, "If receive address doesn't match, contact Trezor Support at trezor.io/support."),
            #[cfg(feature = "layout_bolt")]
            (Self::address__cancel_receive, "Cancel receive"),
            #[cfg(feature = "layout_caesar")]
            (Self::address__cancel_receive, "Cancel receive"),
            #[cfg(feature = "layout_delizia")]
            (Self::address__cancel_receive, "Cancel receive"),
            #[cfg(feature = "layout_eckhart")]
            (Self::address__cancel_receive, "Cancel receive?"),
            (Self::address__qr_code, "QR code"),
            (Self::address_details__derivation_path, "Derivation path"),
            (Self::instructions__continue_in_app, "Continue in the app"),
            (Self::words__cancel_and_exit, "Cancel and exit"),
            (Self::address__confirmed, "Receive address confirmed"),
            (Self::pin__cancel_description, "Continue without PIN"),
            (Self::pin__cancel_info, "Without a PIN, anyone can access this device."),
            #[cfg(feature = "layout_bolt")]
            (Self::pin__cancel_setup, "Cancel PIN setup"),
            #[cfg(feature = "layout_caesar")]
            (Self::pin__cancel_setup, "Cancel PIN setup"),
            #[cfg(feature = "layout_delizia")]
            (Self::pin__cancel_setup, "Cancel PIN setup"),
            #[cfg(feature = "layout_eckhart")]
            (Self::pin__cancel_setup, "Cancel PIN setup?"),
            (Self::send__cancel_sign, "Cancel sign"),
            (Self::send__send_from, "Send from"),
            (Self::instructions__hold_to_sign, "Hold to sign"),
            (Self::confirm_total__fee_rate, "Fee rate"),
            (Self::send__incl_transaction_fee, "incl. Transaction fee"),
            (Self::send__total_amount, "Total amount"),
            (Self::auto_lock__turned_on, "Auto-lock turned on"),
            (Self::backup__info_multi_share_backup, "Your wallet backup contains multiple lists of words in a specific order (shares)."),
            (Self::backup__info_single_share_backup, "Your wallet backup contains {0} words in a specific order."),
            #[cfg(feature = "layout_bolt")]
            (Self::backup__title_backup_completed, "Wallet backup completed"),
            #[cfg(feature = "layout_caesar")]
            (Self::backup__title_backup_completed, "Wallet backup completed"),
            #[cfg(feature = "layout_delizia")]
            (Self::backup__title_backup_completed, "Wallet backup completed"),
            #[cfg(feature = "layout_eckhart")]
            (Self::backup__title_backup_completed, "Wallet backup completed."),
            (Self::backup__title_create_wallet_backup, "Create wallet backup"),
            #[cfg(feature = "layout_bolt")]
            (Self::haptic_feedback__disable, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::haptic_feedback__disable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::haptic_feedback__disable, "Disable haptic feedback?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::haptic_feedback__disable, "Disable haptic feedback?"),
            #[cfg(feature = "layout_bolt")]
            (Self::haptic_feedback__enable, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::haptic_feedback__enable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::haptic_feedback__enable, "Enable haptic feedback?"),
            #[cfg(feature = "layout_eckhart")]
            (Self::haptic_feedback__enable, "Enable haptic feedback?"),
            #[cfg(feature = "layout_bolt")]
            (Self::haptic_feedback__subtitle, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::haptic_feedback__subtitle, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::haptic_feedback__subtitle, "Setting"),
            #[cfg(feature = "layout_eckhart")]
            (Self::haptic_feedback__subtitle, "Setting"),
            #[cfg(feature = "layout_bolt")]
            (Self::haptic_feedback__title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::haptic_feedback__title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::haptic_feedback__title, "Haptic feedback"),
            #[cfg(feature = "layout_eckhart")]
            (Self::haptic_feedback__title, "Haptic feedback"),
            #[cfg(feature = "layout_bolt")]
            (Self::instructions__continue_holding, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::instructions__continue_holding, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::instructions__continue_holding, "Continue\nholding"),
            #[cfg(feature = "layout_eckhart")]
            (Self::instructions__continue_holding, "Keep holding"),
            (Self::instructions__enter_next_share, "Enter next share"),
            (Self::instructions__hold_to_continue, "Hold to continue"),
            (Self::instructions__hold_to_exit_tutorial, "Hold to exit tutorial"),
            (Self::instructions__learn_more, "Learn more"),
            (Self::instructions__shares_continue_with_x_template, "Continue with Share #{0}"),
            (Self::instructions__shares_start_with_1, "Start with share #1"),
            (Self::passphrase__title_passphrase, "Passphrase"),
            (Self::recovery__dry_run_backup_not_on_this_device, "Wallet backup not on this device"),
            (Self::recovery__dry_run_invalid_backup_entered, "Invalid wallet backup entered"),
            (Self::recovery__dry_run_slip39_valid_all_shares, "All shares are valid and belong to the backup in this device"),
            (Self::recovery__dry_run_slip39_valid_share, "Entered share is valid and belongs to the backup in the device"),
            (Self::recovery__dry_run_verify_remaining_shares, "Verify remaining recovery shares?"),
            (Self::recovery__enter_each_word, "Enter each word of your wallet backup in order."),
            (Self::recovery__info_about_disconnect, "It's safe to disconnect your Trezor while recovering your wallet and continue later."),
            (Self::recovery__share_does_not_match, "Share doesn't match"),
            (Self::reset__cancel_create_wallet, "Cancel create wallet"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__incorrect_word_selected, "Incorrect word selected"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__incorrect_word_selected, "Incorrect word selected"),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__incorrect_word_selected, "Incorrect word selected"),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__incorrect_word_selected, "Incorrect word selected."),
            (Self::reset__more_at, "More at"),
            (Self::reset__num_of_shares_how_many, "How many wallet backup shares do you want to create?"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__num_of_shares_long_info_template, "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet."),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__num_of_shares_long_info_template, "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet."),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__num_of_shares_long_info_template, "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet."),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__num_of_shares_long_info_template, "Each backup share is a sequence of {0} words.\nStore each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet."),
            (Self::reset__select_threshold, "Select the minimum shares required to recover your wallet."),
            (Self::reset__share_completed_template, "Share #{0} completed"),
            (Self::reset__slip39_checklist_num_shares_x_template, "Number of shares: {0}"),
            (Self::reset__slip39_checklist_threshold_x_template, "Recovery threshold: {0}"),
            (Self::send__transaction_signed, "Transaction signed"),
            (Self::tutorial__continue, "Continue tutorial"),
            (Self::tutorial__exit, "Exit tutorial"),
            (Self::tutorial__menu, "Find context-specific actions and options in the menu."),
            (Self::tutorial__one_more_step, "One more step"),
            (Self::tutorial__ready_to_use_safe5, "You're all set to start using your device!"),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__swipe_up_and_down, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__swipe_up_and_down, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__swipe_up_and_down, "Tap the lower half of the screen to continue, or swipe down to go back."),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__swipe_up_and_down, ""),
            (Self::tutorial__title_easy_navigation, "Easy navigation"),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__welcome_safe5, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__welcome_safe5, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__welcome_safe5, "Welcome to\nTrezor Safe 5"),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__welcome_safe5, ""),
            (Self::words__good_to_know, "Good to know"),
            (Self::words__operation_cancelled, "Operation cancelled"),
            (Self::words__settings, "Settings"),
            #[cfg(feature = "layout_bolt")]
            (Self::words__try_again, "Try again."),
            #[cfg(feature = "layout_caesar")]
            (Self::words__try_again, "Try again."),
            #[cfg(feature = "layout_delizia")]
            (Self::words__try_again, "Try again."),
            #[cfg(feature = "layout_eckhart")]
            (Self::words__try_again, "Try again"),
            (Self::reset__slip39_checklist_num_groups_x_template, "Number of groups: {0}"),
            (Self::brightness__title, "Display brightness"),
            (Self::recovery__title_unlock_repeated_backup, "Multi-share backup"),
            (Self::recovery__unlock_repeated_backup, "Create additional backup?"),
            (Self::recovery__unlock_repeated_backup_verb, "Create backup"),
            (Self::homescreen__set_default, "Change wallpaper to default image?"),
            (Self::reset__words_may_repeat, "Words may repeat."),
            (Self::reset__repeat_for_all_shares, "Repeat for all shares."),
            (Self::homescreen__settings_subtitle, "Settings"),
            (Self::homescreen__settings_title, "Homescreen"),
            #[cfg(feature = "layout_bolt")]
            (Self::reset__the_word_is_repeated, "The word is repeated"),
            #[cfg(feature = "layout_caesar")]
            (Self::reset__the_word_is_repeated, "The word is repeated"),
            #[cfg(feature = "layout_delizia")]
            (Self::reset__the_word_is_repeated, "The word is repeated"),
            #[cfg(feature = "layout_eckhart")]
            (Self::reset__the_word_is_repeated, "The word appears multiple times in the backup."),
            (Self::tutorial__title_lets_begin, "Let's begin"),
            (Self::tutorial__did_you_know, "Did you know?"),
            (Self::tutorial__first_wallet, "The Trezor Model One, created in 2013,\nwas the world's first hardware wallet."),
            (Self::tutorial__restart_tutorial, "Restart tutorial"),
            (Self::tutorial__title_handy_menu, "Handy menu"),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__title_hold, "Hold to confirm important actions"),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__title_hold, "Hold to confirm important actions"),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__title_hold, "Hold to confirm important actions"),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__title_hold, "Hold the on-screen button at the bottom to confirm important actions."),
            (Self::tutorial__title_well_done, "Well done!"),
            (Self::tutorial__lets_begin, "Learn how to use and navigate this device with ease."),
            (Self::tutorial__get_started, "Get started!"),
            (Self::instructions__swipe_horizontally, "Swipe horizontally"),
            (Self::setting__adjust, "Adjust"),
            (Self::setting__apply, "Apply"),
            (Self::brightness__changed_title, "Display brightness changed"),
            (Self::brightness__change_title, "Change display brightness"),
            (Self::words__title_done, "Done"),
            (Self::reset__slip39_checklist_more_info_threshold, "The threshold sets the minimum number of shares needed to recover your wallet."),
            (Self::reset__slip39_checklist_more_info_threshold_example_template, "If you set {0} out of {1} shares, you'll need {2} backup shares to recover your wallet."),
            (Self::passphrase__continue_with_empty_passphrase, "Continue with empty passphrase?"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__more_credentials, "More credentials"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__select_intro, "Select the credential that you would like to use for authentication."),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_for_authentication, "for authentication"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_select_credential, "Select credential"),
            (Self::instructions__swipe_down, "Swipe down"),
            #[cfg(feature = "universal_fw")]
            (Self::fido__title_credential_details, "Credential details"),
            (Self::address__public_key_confirmed, "Public key confirmed"),
            (Self::words__continue_anyway, "Continue anyway"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::ethereum__unknown_contract_address, "Unknown contract address"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::ethereum__unknown_contract_address, "Unknown contract address"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::ethereum__unknown_contract_address, "Unknown contract address"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::ethereum__unknown_contract_address, "Unknown token contract address."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::ethereum__token_contract, "Token contract"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::ethereum__token_contract, "Token contract"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::ethereum__token_contract, "Token contract"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::ethereum__token_contract, "Token contract address"),
            (Self::buttons__view_all_data, "View all data"),
            (Self::instructions__view_all_data, "View all data in the menu."),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_bolt")]
            (Self::ethereum__interaction_contract, "Interaction contract"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_caesar")]
            (Self::ethereum__interaction_contract, "Interaction contract"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_delizia")]
            (Self::ethereum__interaction_contract, "Interaction contract"),
            #[cfg(feature = "universal_fw")]
            #[cfg(feature = "layout_eckhart")]
            (Self::ethereum__interaction_contract, "Interaction contract address"),
            (Self::misc__enable_labeling, "Enable labeling?"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__base_fee, "Base fee"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__claim, "Claim"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__claim_question, "Claim SOL from stake account?"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__claim_recipient_warning, "Claiming SOL to address outside your current wallet."),
            #[cfg(feature = "universal_fw")]
            (Self::solana__priority_fee, "Priority fee"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__stake, "Stake"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__stake_account, "Stake account"),
            (Self::words__provider, "Provider"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__stake_question, "Stake SOL?"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__stake_withdrawal_warning, "The current wallet isn't the SOL staking withdraw authority."),
            #[cfg(feature = "universal_fw")]
            (Self::solana__stake_withdrawal_warning_title, "Withdraw authority address"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__unstake, "Unstake"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__unstake_question, "Unstake SOL from stake account?"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__vote_account, "Vote account"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__stake_on_question, "Stake SOL on {0}?"),
            (Self::sign_message__confirm_without_review, "Confirm without review"),
            (Self::instructions__tap_to_continue, "Tap to continue"),
            #[cfg(feature = "universal_fw")]
            (Self::nostr__event_kind_template, "Event kind: {0}"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__unpair_all, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__unpair_all, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__unpair_all, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__unpair_all, "Unpair all bluetooth devices"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__unpair_current, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__unpair_current, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__unpair_current, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__unpair_current, "Unpair connected device"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__unpair_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__unpair_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__unpair_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__unpair_title, "Unpair"),
            (Self::words__unlocked, "Unlocked"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__max_fees_rent, "Max fees and rent"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__max_rent_fee, "Max rent fee"),
            (Self::words__transaction_fee, "Transaction fee"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve, "Approve"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_amount_allowance, "Amount allowance"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_chain_id, "Chain ID"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_intro, "Review details to approve token spending."),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_intro_title, "Token approval"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_to, "Approve to"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_unlimited_template, "Approving unlimited amount of {0}"),
            (Self::words__unlimited, "Unlimited"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_intro_revoke, "Review details to revoke token approval."),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_intro_title_revoke, "Token revocation"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_revoke, "Revoke"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__approve_revoke_from, "Revoke from"),
            (Self::words__chain, "Chain"),
            (Self::words__token, "Token"),
            (Self::instructions__tap, "Tap"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__unknown_token, "Unknown token"),
            #[cfg(feature = "universal_fw")]
            (Self::solana__unknown_token_address, "Unknown token address"),
            (Self::reset__share_words_first, "Write down the first word from the backup."),
            (Self::backup__not_recommend, "We don't recommend to skip wallet backup creation."),
            (Self::words__pay_attention, "Pay attention"),
            (Self::address__check_with_source, "Check the address with source."),
            (Self::words__receive, "Receive"),
            (Self::reset__recovery_share_description, "A recovery share is a list of words you wrote down when setting up your Trezor."),
            (Self::reset__recovery_share_number, "Your wallet backup consists of 1 to 16 shares."),
            (Self::words__recovery_share, "Recovery share"),
            (Self::send__send_in_the_app, "After signing, send the transaction in the app."),
            (Self::send__sign_cancelled, "Sign cancelled."),
            (Self::words__send, "Send"),
            (Self::words__wallet, "Wallet"),
            (Self::words__authenticate, "Authenticate"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_all_input_data_template, "All input data ({0} bytes)"),
            (Self::auto_lock__description, "Set the time before your Trezor locks automatically."),
            (Self::plurals__lock_after_x_days, "day|days"),
            (Self::firmware_update__restart, "Trezor will restart after update."),
            (Self::passphrase__access_hidden_wallet, "Access hidden wallet"),
            (Self::passphrase__hidden_wallet, "Hidden wallet"),
            (Self::passphrase__show, "Show passphrase"),
            (Self::pin__reenter, "Re-enter PIN"),
            (Self::pin__setup_completed, "PIN setup completed."),
            (Self::instructions__shares_start_with_x_template, "Start with Share #{0}"),
            (Self::reset__check_share_backup_template, "Let's do a quick check of Share #{0}."),
            (Self::reset__select_word_from_share_template, "Select word #{0} from\nShare #{1}"),
            (Self::recovery__share_from_group_entered_template, "Share #{0} from Group #{1} entered."),
            (Self::send__cancel_transaction, "Cancel transaction"),
            (Self::send__multisig_different_paths, "Using different paths for different XPUBs."),
            #[cfg(feature = "layout_bolt")]
            (Self::address__xpub, "XPUB"),
            #[cfg(feature = "layout_caesar")]
            (Self::address__xpub, "XPUB"),
            #[cfg(feature = "layout_delizia")]
            (Self::address__xpub, "XPUB"),
            #[cfg(feature = "layout_eckhart")]
            (Self::address__xpub, "Public key (XPUB)"),
            (Self::words__cancel_question, "Cancel?"),
            (Self::address__coin_address_template, "{0} address"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__contract_address, "Provider contract address"),
            (Self::buttons__view, "View"),
            (Self::words__swap, "Swap"),
            (Self::address__title_provider_address, "Provider address"),
            (Self::address__title_refund_address, "Refund address"),
            (Self::words__assets, "Assets"),
            #[cfg(feature = "universal_fw")]
            (Self::ethereum__title_confirm_message_hash, "Confirm message hash"),
            (Self::buttons__finish, "Finish"),
            (Self::instructions__menu_to_continue, "Use menu to continue"),
            (Self::tutorial__last_one, "Last one"),
            (Self::tutorial__menu_appendix, "View more info, quit flow, ..."),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__navigation_ts7, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__navigation_ts7, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__navigation_ts7, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__navigation_ts7, "Use the on-screen buttons to navigate and confirm your actions."),
            (Self::tutorial__suite_restart, "Replay this tutorial anytime from the Trezor Suite app."),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__welcome_safe7, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__welcome_safe7, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__welcome_safe7, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__welcome_safe7, "Welcome\nto Trezor\nSafe 7"),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__what_is_tropic, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__what_is_tropic, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__what_is_tropic, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__what_is_tropic, "What is TROPIC01?"),
            (Self::tutorial__tap_to_start, "Tap to start tutorial"),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__tropic_info, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__tropic_info, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__tropic_info, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__tropic_info, "TROPIC01 is a next-gen open-source secure element chip designed for transparent and auditable hardware security."),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__sign_with, "Sign with"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__timebounds, "Timebounds"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__token_info, "Token info"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__transaction_source, "Transaction source"),
            #[cfg(feature = "universal_fw")]
            (Self::stellar__transaction_source_diff_warning, "Transaction source does not belong to this Trezor."),
            (Self::device_name__continue_with_empty_label, "Continue with empty device name?"),
            (Self::device_name__enter, "Enter device name"),
            #[cfg(feature = "layout_bolt")]
            (Self::regulatory__title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::regulatory__title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::regulatory__title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::regulatory__title, "Regulatory"),
            (Self::words__name, "Name"),
            (Self::device_name__changed, "Device name changed."),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__confirm_message, "Confirm message"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__empty_message, "Empty message"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__message_hash, "Message hash:"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__message_hex, "Message hex"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__message_text, "Message text"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__sign_message_hash_path_template, "Sign message hash with {0}"),
            #[cfg(feature = "universal_fw")]
            (Self::cardano__sign_message_path_template, "Sign message with {0}"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__manage_paired, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__manage_paired, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__manage_paired, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__manage_paired, "Manage paired devices"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__pair_new, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__pair_new, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__pair_new, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__pair_new, "Pair new device"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__pair_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__pair_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__pair_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__pair_title, "Pair & Connect"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__version, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__version, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__version, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__version, "Bluetooth version"),
            (Self::homescreen__firmware_type, "Firmware type"),
            (Self::homescreen__firmware_version, "Firmware version"),
            #[cfg(feature = "layout_bolt")]
            (Self::led__disable, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::led__disable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::led__disable, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::led__disable, "Disable LED?"),
            #[cfg(feature = "layout_bolt")]
            (Self::led__enable, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::led__enable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::led__enable, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::led__enable, "Enable LED?"),
            #[cfg(feature = "layout_bolt")]
            (Self::led__title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::led__title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::led__title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::led__title, "LED"),
            (Self::words__about, "About"),
            (Self::words__connected, "Connected"),
            (Self::words__device, "Device"),
            (Self::words__disconnect, "Disconnect"),
            (Self::words__led, "LED"),
            (Self::words__manage, "Manage"),
            (Self::words__off, "OFF"),
            (Self::words__on, "ON"),
            (Self::words__review, "Review"),
            (Self::words__security, "Security"),
            (Self::pin__change_question, "Change PIN?"),
            (Self::pin__remove, "Remove PIN"),
            (Self::pin__title, "PIN code"),
            (Self::wipe_code__change_question, "Change wipe code?"),
            (Self::wipe_code__remove, "Remove wipe code"),
            (Self::wipe_code__title, "Wipe code"),
            (Self::words__disabled, "Disabled"),
            (Self::words__enabled, "Enabled"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__disable, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__disable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__disable, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__disable, "Turn Bluetooth off?"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__enable, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__enable, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__enable, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__enable, "Turn Bluetooth on?"),
            (Self::words__bluetooth, "Bluetooth"),
            (Self::wipe__start_again, "Wipe your Trezor and start the setup process again."),
            (Self::words__set, "Set"),
            (Self::words__wipe, "Wipe"),
            (Self::lockscreen__unlock, "Unlock"),
            (Self::recovery__start_entering, "Start entering"),
            (Self::words__disconnected, "Disconnected"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__forget_all, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__forget_all, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__forget_all, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__forget_all, "Forget all"),
            (Self::words__connect, "Connect"),
            (Self::words__forget, "Forget"),
            (Self::words__power, "Power"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__limit_reached, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__limit_reached, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__limit_reached, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__limit_reached, "Limit of paired devices reached"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__forget_all_description, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__forget_all_description, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__forget_all_description, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__forget_all_description, "They'll be removed, and you'll need to pair them again before use."),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__forget_all_devices, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__forget_all_devices, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__forget_all_devices, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__forget_all_devices, "Forget all devices?"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__forget_all_success, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__forget_all_success, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__forget_all_success, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__forget_all_success, "All connections removed."),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__forget_this_description, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__forget_this_description, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__forget_this_description, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__forget_this_description, "It will be removed, and you'll need to pair it again before use."),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__forget_this_device, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__forget_this_device, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__forget_this_device, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__forget_this_device, "Forget this device?"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__forget_this_success, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__forget_this_success, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__forget_this_success, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__forget_this_success, "Connection removed."),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__autoconnect, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__autoconnect, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__autoconnect, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__autoconnect, "Allow {0} to connect automatically to this Trezor?"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__autoconnect_app, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__autoconnect_app, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__autoconnect_app, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__autoconnect_app, "Allow {0} on {1} to connect automatically to this Trezor?"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__connect, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__connect, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__connect, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__connect, "Allow {0} to connect with this Trezor?"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__connect_app, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__connect_app, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__connect_app, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__connect_app, "Allow {0} on {1} to connect with this Trezor?"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__pair, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__pair, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__pair, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__pair, "Allow {0} to pair with this Trezor?"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__pair_app, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__pair_app, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__pair_app, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__pair_app, "Allow {0} on {1} to pair with this Trezor?"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__autoconnect_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__autoconnect_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__autoconnect_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__autoconnect_title, "Autoconnect credential"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__code_entry, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__code_entry, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__code_entry, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__code_entry, "Enter this one-time security code on {0}"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__code_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__code_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__code_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__code_title, "One more step"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__connect_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__connect_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__connect_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__connect_title, "Connection dialog"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__nfc_text, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__nfc_text, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__nfc_text, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__nfc_text, "Keep your Trezor near your phone to complete the setup."),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__pair_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__pair_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__pair_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__pair_title, "Before you continue"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__qr_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__qr_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__qr_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__qr_title, "Scan QR code to pair"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__pairing_match, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__pairing_match, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__pairing_match, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__pairing_match, "Pairing code match?"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__pairing_title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__pairing_title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__pairing_title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__pairing_title, "Bluetooth pairing"),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__pair_name, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__pair_name, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__pair_name, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__pair_name, "{0} is your Trezor's name."),
            #[cfg(feature = "layout_bolt")]
            (Self::thp__pair_new_device, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::thp__pair_new_device, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::thp__pair_new_device, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::thp__pair_new_device, "Pair with new device"),
            #[cfg(feature = "layout_bolt")]
            (Self::tutorial__power, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::tutorial__power, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::tutorial__power, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::tutorial__power, "Use the power button on the side to turn your device on or off."),
            #[cfg(feature = "layout_bolt")]
            (Self::auto_lock__on_battery, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::auto_lock__on_battery, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::auto_lock__on_battery, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::auto_lock__on_battery, "on battery / wireless charger"),
            #[cfg(feature = "layout_bolt")]
            (Self::auto_lock__on_usb, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::auto_lock__on_usb, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::auto_lock__on_usb, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::auto_lock__on_usb, "connected to USB"),
            (Self::pin__wipe_code_exists_description, "Wipe code must be turned off before turning off PIN protection."),
            (Self::pin__wipe_code_exists_title, "Wipe code set"),
            (Self::wipe_code__pin_not_set_description, "PIN must be set before enabling wipe code."),
            #[cfg(feature = "layout_bolt")]
            (Self::wipe_code__cancel_setup, "Cancel wipe code setup"),
            #[cfg(feature = "layout_caesar")]
            (Self::wipe_code__cancel_setup, "Cancel wipe code setup"),
            #[cfg(feature = "layout_delizia")]
            (Self::wipe_code__cancel_setup, "Cancel wipe code setup"),
            #[cfg(feature = "layout_eckhart")]
            (Self::wipe_code__cancel_setup, "Cancel wipe code setup?"),
            (Self::homescreen__backup_needed_info, "Open Trezor Suite and create a wallet backup. This is the only way to recover access to your assets."),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__host_info, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__host_info, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__host_info, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__host_info, "Connection info"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__mac_address, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__mac_address, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__mac_address, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__mac_address, "MAC address"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__waiting_for_host, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__waiting_for_host, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__waiting_for_host, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__waiting_for_host, "Waiting for connection..."),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__apps_connected, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__apps_connected, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__apps_connected, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__apps_connected, "Apps connected"),
            #[cfg(feature = "layout_bolt")]
            (Self::sn__action, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::sn__action, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sn__action, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::sn__action, "Allow connected device to get serial number of your Trezor Safe 7?"),
            #[cfg(feature = "layout_bolt")]
            (Self::sn__title, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::sn__title, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::sn__title, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::sn__title, "Serial number"),
            #[cfg(feature = "layout_bolt")]
            (Self::ble__must_be_enabled, ""),
            #[cfg(feature = "layout_caesar")]
            (Self::ble__must_be_enabled, ""),
            #[cfg(feature = "layout_delizia")]
            (Self::ble__must_be_enabled, ""),
            #[cfg(feature = "layout_eckhart")]
            (Self::ble__must_be_enabled, "The Bluetooth must be turned on to pair with a new device."),
            #[cfg(feature = "universal_fw")]
            (Self::ripple__destination_tag_missing, "Destination tag is not set. Typically needed when sending to exchanges."),
            (Self::words__comm_trouble, "Your Trezor is having trouble communicating with your connected device."),
            (Self::secure_sync__delegated_identity_key_no_thp, "Allow Trezor Suite to use Suite Sync with this Trezor?"),
            (Self::secure_sync__delegated_identity_key_thp, "Allow {0} on {1} to use Suite Sync with this Trezor?"),
            (Self::secure_sync__header, "Suite Sync"),
            (Self::words__note, "Note"),
            (Self::words__fee_limit, "Fee limit"),
    ];

    #[cfg(feature = "micropython")]
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
        (Qstr::MP_QSTR_words__fee_limit, Self::words__fee_limit),
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
