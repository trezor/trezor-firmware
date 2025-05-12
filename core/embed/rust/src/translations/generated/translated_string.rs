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
    authenticate__confirm_template = 13,  // "Allow connected computer to confirm your {0} is genuine?"
    authenticate__header = 14,  // "Authenticate device"
    auto_lock__change_template = 15,  // "Auto-lock Trezor after {0} of inactivity?"
    auto_lock__title = 16,  // "Auto-lock delay"
    backup__can_back_up_anytime = 17,  // "You can back up your Trezor once, at any time."
    backup__it_should_be_backed_up = 18,  // "You should back up your new wallet right now."
    backup__it_should_be_backed_up_now = 19,  // "It should be backed up now!"
    backup__new_wallet_created = 20,  // "Wallet created.\n"
    backup__new_wallet_successfully_created = 21,  // "Wallet created successfully."
    backup__recover_anytime = 22,  // "You can use your backup to recover your wallet at any time."
    backup__title_backup_wallet = 23,  // "Back up wallet"
    backup__title_skip = 24,  // "Skip backup"
    backup__want_to_skip = 25,  // "Are you sure you want to skip the backup?"
    #[cfg(feature = "universal_fw")]
    binance__buy = 26,  // "Buy"
    #[cfg(feature = "universal_fw")]
    binance__confirm_cancel = 27,  // "Confirm cancel"
    #[cfg(feature = "universal_fw")]
    binance__confirm_input = 28,  // "Confirm input"
    #[cfg(feature = "universal_fw")]
    binance__confirm_order = 29,  // "Confirm order"
    #[cfg(feature = "universal_fw")]
    binance__confirm_output = 30,  // "Confirm output"
    #[cfg(feature = "universal_fw")]
    binance__order_id = 31,  // "Order ID:"
    #[cfg(feature = "universal_fw")]
    binance__pair = 32,  // "Pair:"
    #[cfg(feature = "universal_fw")]
    binance__price = 33,  // "Price:"
    #[cfg(feature = "universal_fw")]
    binance__quantity = 34,  // "Quantity:"
    #[cfg(feature = "universal_fw")]
    binance__sell = 35,  // "Sell"
    #[cfg(feature = "universal_fw")]
    binance__sender_address = 36,  // "Sender address:"
    #[cfg(feature = "universal_fw")]
    binance__side = 37,  // "Side:"
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
    bitcoin__title_meld_transaction = 53,  // "Meld transactions"
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
    cardano__confirming_transction = 131,  // "Confirming a transaction."
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
    cardano__transaction_fee = 195,  // "Transaction fee:"
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
    coinjoin__title_do_not_disconnect = 217,  // "Do not disconnect your trezor!"
    coinjoin__title_progress = 218,  // "Coinjoin in progress"
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
    eos__about_to_sign_template = 231,  // "You are about to sign {0}."
    #[cfg(feature = "universal_fw")]
    eos__action_name = 232,  // "Action Name:"
    #[cfg(feature = "universal_fw")]
    eos__arbitrary_data = 233,  // "Arbitrary data"
    #[cfg(feature = "universal_fw")]
    eos__buy_ram = 234,  // "Buy RAM"
    #[cfg(feature = "universal_fw")]
    eos__bytes = 235,  // "Bytes:"
    #[cfg(feature = "universal_fw")]
    eos__cancel_vote = 236,  // "Cancel vote"
    #[cfg(feature = "universal_fw")]
    eos__checksum = 237,  // "Checksum:"
    #[cfg(feature = "universal_fw")]
    eos__code = 238,  // "Code:"
    #[cfg(feature = "universal_fw")]
    eos__contract = 239,  // "Contract:"
    #[cfg(feature = "universal_fw")]
    eos__cpu = 240,  // "CPU:"
    #[cfg(feature = "universal_fw")]
    eos__creator = 241,  // "Creator:"
    #[cfg(feature = "universal_fw")]
    eos__delegate = 242,  // "Delegate"
    #[cfg(feature = "universal_fw")]
    eos__delete_auth = 243,  // "Delete Auth"
    #[cfg(feature = "universal_fw")]
    eos__from = 244,  // "From:"
    #[cfg(feature = "universal_fw")]
    eos__link_auth = 245,  // "Link Auth"
    #[cfg(feature = "universal_fw")]
    eos__memo = 246,  // "Memo"
    #[cfg(feature = "universal_fw")]
    eos__name = 247,  // "Name:"
    #[cfg(feature = "universal_fw")]
    eos__net = 248,  // "NET:"
    #[cfg(feature = "universal_fw")]
    eos__new_account = 249,  // "New account"
    #[cfg(feature = "universal_fw")]
    eos__owner = 250,  // "Owner:"
    #[cfg(feature = "universal_fw")]
    eos__parent = 251,  // "Parent:"
    #[cfg(feature = "universal_fw")]
    eos__payer = 252,  // "Payer:"
    #[cfg(feature = "universal_fw")]
    eos__permission = 253,  // "Permission:"
    #[cfg(feature = "universal_fw")]
    eos__proxy = 254,  // "Proxy:"
    #[cfg(feature = "universal_fw")]
    eos__receiver = 255,  // "Receiver:"
    #[cfg(feature = "universal_fw")]
    eos__refund = 256,  // "Refund"
    #[cfg(feature = "universal_fw")]
    eos__requirement = 257,  // "Requirement:"
    #[cfg(feature = "universal_fw")]
    eos__sell_ram = 258,  // "Sell RAM"
    #[cfg(feature = "universal_fw")]
    eos__sender = 259,  // "Sender:"
    send__sign_transaction = 260,  // "Sign transaction"
    #[cfg(feature = "universal_fw")]
    eos__threshold = 261,  // "Threshold:"
    #[cfg(feature = "universal_fw")]
    eos__to = 262,  // "To:"
    #[cfg(feature = "universal_fw")]
    eos__transfer = 263,  // "Transfer:"
    #[cfg(feature = "universal_fw")]
    eos__type = 264,  // "Type:"
    #[cfg(feature = "universal_fw")]
    eos__undelegate = 265,  // "Undelegate"
    #[cfg(feature = "universal_fw")]
    eos__unlink_auth = 266,  // "Unlink Auth"
    #[cfg(feature = "universal_fw")]
    eos__update_auth = 267,  // "Update Auth"
    #[cfg(feature = "universal_fw")]
    eos__vote_for_producers = 268,  // "Vote for producers"
    #[cfg(feature = "universal_fw")]
    eos__vote_for_proxy = 269,  // "Vote for proxy"
    #[cfg(feature = "universal_fw")]
    eos__voter = 270,  // "Voter:"
    #[cfg(feature = "universal_fw")]
    ethereum__amount_sent = 271,  // "Amount sent:"
    #[cfg(feature = "universal_fw")]
    ethereum__contract = 272,  // "Contract:"
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
    fido__does_not_belong = 302,  // "The credential you are trying to import does\nnot belong to this authenticator."
    #[cfg(feature = "universal_fw")]
    fido__erase_credentials = 303,  // "erase all credentials?"
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
    inputs__back = 331,  // "BACK"
    inputs__cancel = 332,  // "CANCEL"
    inputs__delete = 333,  // "DELETE"
    inputs__enter = 334,  // "ENTER"
    inputs__return = 335,  // "RETURN"
    inputs__show = 336,  // "SHOW"
    inputs__space = 337,  // "SPACE"
    joint__title = 338,  // "Joint transaction"
    joint__to_the_total_amount = 339,  // "To the total amount:"
    joint__you_are_contributing = 340,  // "You are contributing:"
    language__change_to_template = 341,  // "Change language to {0}?"
    language__changed = 342,  // "Language changed successfully"
    language__progress = 343,  // "Changing language"
    language__title = 344,  // "Language settings"
    lockscreen__tap_to_connect = 345,  // "Tap to connect"
    lockscreen__tap_to_unlock = 346,  // "Tap to unlock"
    lockscreen__title_locked = 347,  // "Locked"
    lockscreen__title_not_connected = 348,  // "Not connected"
    misc__decrypt_value = 349,  // "Decrypt value"
    misc__encrypt_value = 350,  // "Encrypt value"
    misc__title_suite_labeling = 351,  // "Suite labeling"
    modify_amount__decrease_amount = 352,  // "Decrease amount by:"
    modify_amount__increase_amount = 353,  // "Increase amount by:"
    modify_amount__new_amount = 354,  // "New amount:"
    modify_amount__title = 355,  // "Modify amount"
    modify_fee__decrease_fee = 356,  // "Decrease fee by:"
    modify_fee__fee_rate = 357,  // "Fee rate:"
    modify_fee__increase_fee = 358,  // "Increase fee by:"
    modify_fee__new_transaction_fee = 359,  // "New transaction fee:"
    modify_fee__no_change = 360,  // "Fee did not change.\n"
    modify_fee__title = 361,  // "Modify fee"
    modify_fee__transaction_fee = 362,  // "Transaction fee:"
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
    nem__absolute = 381,  // "absolute"
    #[cfg(feature = "universal_fw")]
    nem__activate = 382,  // "Activate"
    #[cfg(feature = "universal_fw")]
    nem__add = 383,  // "Add"
    #[cfg(feature = "universal_fw")]
    nem__confirm_action = 384,  // "Confirm action"
    #[cfg(feature = "universal_fw")]
    nem__confirm_address = 385,  // "Confirm address"
    #[cfg(feature = "universal_fw")]
    nem__confirm_creation_fee = 386,  // "Confirm creation fee"
    #[cfg(feature = "universal_fw")]
    nem__confirm_mosaic = 387,  // "Confirm mosaic"
    #[cfg(feature = "universal_fw")]
    nem__confirm_multisig_fee = 388,  // "Confirm multisig fee"
    #[cfg(feature = "universal_fw")]
    nem__confirm_namespace = 389,  // "Confirm namespace"
    #[cfg(feature = "universal_fw")]
    nem__confirm_payload = 390,  // "Confirm payload"
    #[cfg(feature = "universal_fw")]
    nem__confirm_properties = 391,  // "Confirm properties"
    #[cfg(feature = "universal_fw")]
    nem__confirm_rental_fee = 392,  // "Confirm rental fee"
    #[cfg(feature = "universal_fw")]
    nem__confirm_transfer_of = 393,  // "Confirm transfer of"
    #[cfg(feature = "universal_fw")]
    nem__convert_account_to_multisig = 394,  // "Convert account to multisig account?"
    #[cfg(feature = "universal_fw")]
    nem__cosign_transaction_for = 395,  // "Cosign transaction for"
    #[cfg(feature = "universal_fw")]
    nem__cosignatory = 396,  // " cosignatory"
    #[cfg(feature = "universal_fw")]
    nem__create_mosaic = 397,  // "Create mosaic"
    #[cfg(feature = "universal_fw")]
    nem__create_namespace = 398,  // "Create namespace"
    #[cfg(feature = "universal_fw")]
    nem__deactivate = 399,  // "Deactivate"
    #[cfg(feature = "universal_fw")]
    nem__decrease = 400,  // "Decrease"
    #[cfg(feature = "universal_fw")]
    nem__description = 401,  // "Description:"
    #[cfg(feature = "universal_fw")]
    nem__divisibility_and_levy_cannot_be_shown = 402,  // "Divisibility and levy cannot be shown for unknown mosaics"
    #[cfg(feature = "universal_fw")]
    nem__encrypted = 403,  // "Encrypted"
    #[cfg(feature = "universal_fw")]
    nem__final_confirm = 404,  // "Final confirm"
    #[cfg(feature = "universal_fw")]
    nem__immutable = 405,  // "immutable"
    #[cfg(feature = "universal_fw")]
    nem__increase = 406,  // "Increase"
    #[cfg(feature = "universal_fw")]
    nem__initial_supply = 407,  // "Initial supply:"
    #[cfg(feature = "universal_fw")]
    nem__initiate_transaction_for = 408,  // "Initiate transaction for"
    #[cfg(feature = "universal_fw")]
    nem__levy_divisibility = 409,  // "Levy divisibility:"
    #[cfg(feature = "universal_fw")]
    nem__levy_fee = 410,  // "Levy fee:"
    #[cfg(feature = "universal_fw")]
    nem__levy_fee_of = 411,  // "Confirm mosaic levy fee of"
    #[cfg(feature = "universal_fw")]
    nem__levy_mosaic = 412,  // "Levy mosaic:"
    #[cfg(feature = "universal_fw")]
    nem__levy_namespace = 413,  // "Levy namespace:"
    #[cfg(feature = "universal_fw")]
    nem__levy_recipient = 414,  // "Levy recipient:"
    #[cfg(feature = "universal_fw")]
    nem__levy_type = 415,  // "Levy type:"
    #[cfg(feature = "universal_fw")]
    nem__modify_supply_for = 416,  // "Modify supply for"
    #[cfg(feature = "universal_fw")]
    nem__modify_the_number_of_cosignatories_by = 417,  // "Modify the number of cosignatories by "
    #[cfg(feature = "universal_fw")]
    nem__mutable = 418,  // "mutable"
    #[cfg(feature = "universal_fw")]
    nem__of = 419,  // "of"
    #[cfg(feature = "universal_fw")]
    nem__percentile = 420,  // "percentile"
    #[cfg(feature = "universal_fw")]
    nem__raw_units_template = 421,  // "{0} raw units"
    #[cfg(feature = "universal_fw")]
    nem__remote_harvesting = 422,  // " remote harvesting?"
    #[cfg(feature = "universal_fw")]
    nem__remove = 423,  // "Remove"
    #[cfg(feature = "universal_fw")]
    nem__set_minimum_cosignatories_to = 424,  // "Set minimum cosignatories to "
    #[cfg(feature = "universal_fw")]
    nem__sign_tx_fee_template = 425,  // "Sign this transaction\nand pay {0}\nfor network fee?"
    #[cfg(feature = "universal_fw")]
    nem__supply_change = 426,  // "Supply change"
    #[cfg(feature = "universal_fw")]
    nem__supply_units_template = 427,  // "{0} supply by {1} whole units?"
    #[cfg(feature = "universal_fw")]
    nem__transferable = 428,  // "Transferable?"
    #[cfg(feature = "universal_fw")]
    nem__under_namespace = 429,  // "under namespace"
    #[cfg(feature = "universal_fw")]
    nem__unencrypted = 430,  // "Unencrypted"
    #[cfg(feature = "universal_fw")]
    nem__unknown_mosaic = 431,  // "Unknown mosaic!"
    passphrase__access_wallet = 432,  // "Access passphrase wallet?"
    passphrase__always_on_device = 433,  // "Always enter your passphrase on Trezor?"
    passphrase__from_host_not_shown = 434,  // "Passphrase provided by host will be used but will not be displayed due to the device settings."
    passphrase__wallet = 435,  // "Passphrase wallet"
    passphrase__hide = 436,  // "Hide passphrase coming from host?"
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
    pin__change = 447,  // "Change PIN?"
    pin__changed = 448,  // "PIN changed."
    pin__cursor_will_change = 449,  // "Position of the cursor will change between entries for enhanced security."
    pin__diff_from_wipe_code = 450,  // "The new PIN must be different from your wipe code."
    pin__disabled = 451,  // "PIN protection\nturned off."
    pin__enabled = 452,  // "PIN protection\nturned on."
    pin__enter = 453,  // "Enter PIN"
    pin__enter_new = 454,  // "Enter new PIN"
    pin__entered_not_valid = 455,  // "The PIN you have entered is not valid."
    pin__info = 456,  // "PIN will be required to access this device."
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
    progress__please_wait = 486,  // "Please wait"
    storage_msg__processing = 487,  // "Processing"
    progress__refreshing = 488,  // "Refreshing..."
    progress__signing_transaction = 489,  // "Signing transaction..."
    progress__syncing = 490,  // "Syncing..."
    progress__x_seconds_left_template = 491,  // "{0} seconds left"
    reboot_to_bootloader__restart = 492,  // "Trezor will restart in bootloader mode."
    reboot_to_bootloader__title = 493,  // "Go to bootloader"
    reboot_to_bootloader__version_by_template = 494,  // "Firmware version {0}\nby {1}"
    recovery__cancel_dry_run = 495,  // "Cancel backup check"
    recovery__check_dry_run = 496,  // "Check your backup?"
    recovery__cursor_will_change = 497,  // "Position of the cursor will change between entries for enhanced security."
    recovery__dry_run_bip39_valid_match = 498,  // "The entered wallet backup is valid and matches the one in this device."
    recovery__dry_run_bip39_valid_mismatch = 499,  // "The entered wallet backup is valid but does not match the one in the device."
    recovery__dry_run_slip39_valid_match = 500,  // "The entered recovery shares are valid and match what is currently in the device."
    recovery__dry_run_slip39_valid_mismatch = 501,  // "The entered recovery shares are valid but do not match what is currently in the device."
    recovery__enter_any_share = 502,  // "Enter any share"
    recovery__enter_backup = 503,  // "Enter your backup."
    recovery__enter_different_share = 504,  // "Enter a different share."
    recovery__enter_share_from_diff_group = 505,  // "Enter share from a different group."
    recovery__group_num_template = 506,  // "Group {0}"
    recovery__group_threshold_reached = 507,  // "Group threshold reached."
    recovery__invalid_wallet_backup_entered = 508,  // "Invalid wallet backup entered."
    recovery__invalid_share_entered = 509,  // "Invalid recovery share entered."
    recovery__more_shares_needed = 510,  // "More shares needed"
    recovery__num_of_words = 511,  // "Select the number of words in your backup."
    recovery__only_first_n_letters = 512,  // "You'll only have to select the first 2-4 letters of each word."
    recovery__progress_will_be_lost = 513,  // "All progress will be lost."
    recovery__share_already_entered = 515,  // "Share already entered"
    recovery__share_from_another_multi_share_backup = 516,  // "You have entered a share from a different backup."
    recovery__share_num_template = 517,  // "Share {0}"
    recovery__title = 518,  // "Recover wallet"
    recovery__title_cancel_dry_run = 519,  // "Cancel backup check"
    recovery__title_cancel_recovery = 520,  // "Cancel recovery"
    recovery__title_dry_run = 521,  // "Backup check"
    recovery__title_recover = 522,  // "Recover wallet"
    recovery__title_remaining_shares = 523,  // "Remaining shares"
    recovery__type_word_x_of_y_template = 524,  // "Type word {0} of {1}"
    recovery__wallet_recovered = 525,  // "Wallet recovery completed"
    recovery__wanna_cancel_dry_run = 526,  // "Are you sure you want to cancel the backup check?"
    recovery__wanna_cancel_recovery = 527,  // "Are you sure you want to cancel the recovery process?"
    recovery__word_count_template = 528,  // "({0} words)"
    recovery__word_x_of_y_template = 529,  // "Word {0} of {1}"
    recovery__x_more_items_starting_template_plural = 530,  // "{count} more {plural} starting"
    recovery__x_more_shares_needed_template_plural = 531,  // "{count} more {plural} needed"
    recovery__x_of_y_entered_template = 532,  // "{0} of {1} shares entered"
    recovery__you_have_entered = 533,  // "You have entered"
    reset__advanced_group_threshold_info = 534,  // "The group threshold specifies the number of groups required to recover your wallet."
    reset__all_x_of_y_template = 535,  // "all {0} of {1} shares"
    reset__any_x_of_y_template = 536,  // "any {0} of {1} shares"
    reset__button_create = 537,  // "Create wallet"
    reset__button_recover = 538,  // "Recover wallet"
    reset__by_continuing = 539,  // "By continuing you agree to Trezor Company's terms and conditions."
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
    reset__group_share_title_template = 552,  // "Group {0} - share {1}"
    reset__more_info_at = 553,  // "More info at"
    reset__need_all_share_template = 554,  // "For recovery you need all {0} of the shares."
    reset__need_any_share_template = 555,  // "For recovery you need any {0} of the shares."
    reset__needed_to_form_a_group = 556,  // "needed to form a group. "
    reset__needed_to_recover_your_wallet = 557,  // "needed to recover your wallet. "
    reset__never_make_digital_copy = 558,  // "Never put your backup anywhere digital."
    reset__num_of_share_holders_template = 559,  // "{0} people or locations will each hold one share."
    reset__num_of_shares_advanced_info_template = 560,  // "Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}."
    reset__num_of_shares_basic_info_template = 561,  // "Each recovery share is a sequence of {0} words. Next you will choose how many shares you need to recover your wallet."
    reset__num_shares_for_group_template = 562,  // "The required number of shares to form Group {0}."
    reset__number_of_shares_info = 563,  // "= total number of unique word lists used for wallet backup."
    reset__one_share = 564,  // "1 share"
    reset__only_one_share_will_be_created = 565,  // "Only one share will be created."
    reset__recovery_wallet_backup_title = 566,  // "Wallet backup"
    reset__recovery_share_title_template = 567,  // "Recovery share #{0}"
    reset__required_number_of_groups = 568,  // "The required number of groups for recovery."
    reset__select_correct_word = 569,  // "Select the correct word for each position."
    reset__select_word_template = 570,  // "Select {0} word"
    reset__select_word_x_of_y_template = 571,  // "Select word {0} of {1}:"
    reset__set_it_to_count_template = 572,  // "Set it to {0} and you will need "
    reset__share_checked_successfully_template = 573,  // "Share #{0} checked successfully."
    reset__share_words_title = 574,  // "Standard backup"
    reset__slip39_checklist_num_groups = 575,  // "Number of groups"
    reset__slip39_checklist_num_shares = 576,  // "Number of shares"
    reset__slip39_checklist_set_num_groups = 577,  // "Set number of groups"
    reset__slip39_checklist_set_num_shares = 578,  // "Set number of shares"
    reset__slip39_checklist_set_sizes = 579,  // "Set sizes and thresholds"
    reset__slip39_checklist_set_sizes_longer = 580,  // "Set size and threshold for each group"
    reset__slip39_checklist_set_threshold = 581,  // "Set threshold"
    reset__slip39_checklist_title = 582,  // "Backup checklist"
    reset__slip39_checklist_write_down = 583,  // "Write down and check all shares"
    reset__slip39_checklist_write_down_recovery = 584,  // "Write down & check all wallet backup shares"
    reset__the_threshold_sets_the_number_of_shares = 585,  // "The threshold sets the number of shares "
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
    reset__to_form_group_template = 597,  // "to form Group {0}."
    reset__tos_link = 598,  // "trezor.io/tos"
    reset__total_number_of_shares_in_group_template = 599,  // "Set the total number of shares in Group {0}."
    reset__use_your_backup = 600,  // "Use your backup when you need to recover your wallet."
    reset__write_down_words_template = 601,  // "Write the following {0} words in order on your wallet backup card."
    reset__wrong_word_selected = 602,  // "Wrong word selected!"
    reset__you_need_one_share = 603,  // "For recovery you need 1 share."
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
    sd_card__all_data_will_be_lost = 618,  // "All data on the SD card will be lost."
    sd_card__card_required = 619,  // "SD card required."
    sd_card__disable = 620,  // "Do you really want to remove SD card protection from your device?"
    sd_card__disabled = 621,  // "You have successfully disabled SD protection."
    sd_card__enable = 622,  // "Do you really want to secure your device with SD card protection?"
    sd_card__enabled = 623,  // "You have successfully enabled SD protection."
    sd_card__error = 624,  // "SD card error"
    sd_card__format_card = 625,  // "Format SD card"
    sd_card__insert_correct_card = 626,  // "Please insert the correct SD card for this device."
    sd_card__please_insert = 627,  // "Please insert your SD card."
    sd_card__please_unplug_and_insert = 628,  // "Please unplug the device and insert your SD card."
    sd_card__problem_accessing = 629,  // "There was a problem accessing the SD card."
    sd_card__refresh = 630,  // "Do you really want to replace the current SD card secret with a newly generated one?"
    sd_card__refreshed = 631,  // "You have successfully refreshed SD protection."
    sd_card__restart = 632,  // "Do you want to restart Trezor in bootloader mode?"
    sd_card__title = 633,  // "SD card protection"
    sd_card__title_problem = 634,  // "SD card problem"
    sd_card__unknown_filesystem = 635,  // "Unknown filesystem."
    sd_card__unplug_and_insert_correct = 636,  // "Please unplug the device and insert the correct SD card."
    sd_card__use_different_card = 637,  // "Use a different card or format the SD card to the FAT32 filesystem."
    sd_card__wanna_format = 638,  // "Do you really want to format the SD card?"
    sd_card__wrong_sd_card = 639,  // "Wrong SD card."
    send__address_path = 640,  // "address path"
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
    solana__title_token = 673,  // "Token"
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
    #[cfg(feature = "universal_fw")]
    stellar__asset = 682,  // "Asset"
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
    stellar__confirm_network = 691,  // "Confirm network"
    #[cfg(feature = "universal_fw")]
    stellar__confirm_operation = 692,  // "Confirm operation"
    #[cfg(feature = "universal_fw")]
    stellar__confirm_stellar = 693,  // "Confirm Stellar"
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
    stellar__exchanges_require_memo = 701,  // "Important: Many exchanges require a memo when depositing"
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
    stellar__initial_balance = 707,  // "Initial Balance"
    #[cfg(feature = "universal_fw")]
    stellar__initialize_signing_with = 708,  // "Initialize signing with"
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
    stellar__on_network_template = 719,  // "Transaction is on {0}"
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
    stellar__private_network = 726,  // "private network"
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
    stellar__testnet_network = 736,  // "testnet network"
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
    stellar__your_account = 743,  // " your account"
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
    wipe_code__change = 774,  // "Change wipe code?"
    wipe_code__changed = 775,  // "Wipe code changed."
    wipe_code__diff_from_pin = 776,  // "The wipe code must be different from your PIN."
    wipe_code__disabled = 777,  // "Wipe code disabled."
    wipe_code__enabled = 778,  // "Wipe code enabled."
    wipe_code__enter_new = 779,  // "Enter new wipe code"
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
    inputs__previous = 833,  // "PREVIOUS"
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
    storage_msg__verifying_pin = 843,  // "Verifying PIN"
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
    backup__create_backup_to_prevent_loss = 858,  // "Create a backup to avoid losing access to your funds"
    reset__check_backup_instructions = 859,  // "Let's do a quick check of your backup."
    words__instructions = 860,  // "Instructions"
    words__not_recommended = 861,  // "Not recommended!"
    address_details__account_info = 862,  // "Account info"
    address__cancel_contact_support = 863,  // "If receive address doesn't match, contact Trezor Support at trezor.io/support."
    address__cancel_receive = 864,  // "Cancel receive"
    address__qr_code = 865,  // "QR code"
    address_details__derivation_path = 866,  // "Derivation path"
    instructions__continue_in_app = 867,  // "Continue in the app"
    words__cancel_and_exit = 868,  // "Cancel and exit"
    address__confirmed = 869,  // "Receive address confirmed"
    pin__cancel_description = 870,  // "Continue without PIN"
    pin__cancel_info = 871,  // "Without a PIN, anyone can access this device."
    pin__cancel_setup = 872,  // "Cancel PIN setup"
    send__cancel_sign = 873,  // "Cancel sign"
    send__send_from = 874,  // "Send from"
    instructions__hold_to_sign = 875,  // "Hold to sign"
    confirm_total__fee_rate = 876,  // "Fee rate"
    send__incl_transaction_fee = 877,  // "incl. Transaction fee"
    send__total_amount = 878,  // "Total amount"
    auto_lock__turned_on = 879,  // "Auto-lock turned on"
    backup__info_multi_share_backup = 880,  // "Your wallet backup contains multiple lists of words in a specific order (shares)."
    backup__info_single_share_backup = 881,  // "Your wallet backup contains {0} words in a specific order."
    backup__title_backup_completed = 882,  // "Wallet backup completed"
    backup__title_create_wallet_backup = 883,  // "Create wallet backup"
    haptic_feedback__disable = 884,  // "Disable haptic feedback?"
    haptic_feedback__enable = 885,  // "Enable haptic feedback?"
    haptic_feedback__subtitle = 886,  // "Setting"
    haptic_feedback__title = 887,  // "Haptic feedback"
    instructions__continue_holding = 888,  // "Continue\nholding"
    instructions__enter_next_share = 889,  // "Enter next share"
    instructions__hold_to_continue = 890,  // "Hold to continue"
    instructions__hold_to_exit_tutorial = 891,  // "Hold to exit tutorial"
    instructions__learn_more = 893,  // "Learn more"
    instructions__shares_continue_with_x_template = 894,  // "Continue with Share #{0}"
    instructions__shares_start_with_1 = 895,  // "Start with share #1"
    instructions__tap_to_start = 896,  // "Tap to start"
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
    reset__incorrect_word_selected = 907,  // "Incorrect word selected"
    reset__more_at = 908,  // "More at"
    reset__num_of_shares_how_many = 909,  // "How many wallet backup shares do you want to create?"
    reset__num_of_shares_long_info_template = 910,  // "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet."
    reset__select_threshold = 911,  // "Select the minimum shares required to recover your wallet."
    reset__share_completed_template = 912,  // "Share #{0} completed"
    reset__slip39_checklist_num_shares_x_template = 913,  // "Number of shares: {0}"
    reset__slip39_checklist_threshold_x_template = 914,  // "Recovery threshold: {0}"
    send__transaction_signed = 915,  // "Transaction signed"
    tutorial__continue = 916,  // "Continue tutorial"
    tutorial__exit = 917,  // "Exit tutorial"
    tutorial__menu = 920,  // "Find context-specific actions and options in the menu."
    tutorial__ready_to_use_safe5 = 922,  // "You're all set to start using your device!"
    tutorial__swipe_up_and_down = 924,  // "Tap the lower half of the screen to continue, or swipe down to go back."
    tutorial__title_easy_navigation = 925,  // "Easy navigation"
    tutorial__welcome_safe5 = 926,  // "Welcome to\nTrezor Safe 5"
    words__good_to_know = 927,  // "Good to know"
    words__operation_cancelled = 928,  // "Operation cancelled"
    words__settings = 929,  // "Settings"
    words__try_again = 930,  // "Try again."
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
    reset__the_word_is_repeated = 941,  // "The word is repeated"
    tutorial__title_lets_begin = 942,  // "Let's begin"
    tutorial__did_you_know = 943,  // "Did you know?"
    tutorial__first_wallet = 944,  // "The Trezor Model One, created in 2013,\nwas the world's first hardware wallet."
    tutorial__restart_tutorial = 945,  // "Restart tutorial"
    tutorial__title_handy_menu = 946,  // "Handy menu"
    tutorial__title_hold = 947,  // "Hold to confirm important actions"
    tutorial__title_well_done = 948,  // "Well done!"
    tutorial__lets_begin = 949,  // "Learn how to use and navigate this device with ease."
    tutorial__get_started = 950,  // "Get started!"
    instructions__swipe_horizontally = 951,  // "Swipe horizontally"
    setting__adjust = 952,  // "Adjust"
    setting__apply = 953,  // "Apply"
    brightness__changed_title = 954,  // "Display brightness changed"
    brightness__change_title = 955,  // "Change display brightness"
    words__title_done = 956,  // "Done"
    reset__slip39_checklist_more_info_threshold = 957,  // "The threshold sets the minumum number of shares needed to recover your wallet."
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
    ethereum__unknown_contract_address = 968,  // "Unknown contract address. Continue only if you know what you are doing."
    #[cfg(feature = "universal_fw")]
    ethereum__token_contract = 969,  // "Token contract"
    buttons__view_all_data = 970,  // "View all data"
    instructions__view_all_data = 971,  // "View all data in the menu."
    #[cfg(feature = "universal_fw")]
    ethereum__interaction_contract = 972,  // "Interaction contract"
    misc__enable_labeling = 973,  // "Enable labeling?"
    #[cfg(feature = "universal_fw")]
    ethereum__unknown_contract_address_short = 974,  // "Unknown contract address."
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
    #[cfg(feature = "universal_fw")]
    solana__stake_provider = 982,  // "Provider"
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
    ble__unpair_all = 993,  // "Unpair all bluetooth devices"
    ble__unpair_current = 994,  // "Unpair connected device"
    ble__unpair_title = 995,  // "Unpair"
    words__unlocked = 996,  // "Unlocked"
    #[cfg(feature = "universal_fw")]
    solana__max_fees_rent = 997,  // "Max fees and rent"
    #[cfg(feature = "universal_fw")]
    solana__max_rent_fee = 998,  // "Max rent fee"
    #[cfg(feature = "universal_fw")]
    solana__transaction_fee = 999,  // "Transaction fee"
}

impl TranslatedString {

    const BTC_ONLY_BLOB: StringsBlob = StringsBlob {
        text: concat!(
            "Please contact Trezor support at",
            "Key mismatch?",
            "Address mismatch?",
            "trezor.io/support",
            "Wrong derivation path for selected account.",
            "XPUB mismatch?",
            "Public key",
            "Cosigner",
            "Receive address",
            "Yours",
            "Derivation path:",
            "Receive address",
            "Receiving to",
            "Allow connected computer to confirm your {0} is genuine?",
            "Authenticate device",
            "Auto-lock Trezor after {0} of inactivity?",
            "Auto-lock delay",
            "You can back up your Trezor once, at any time.",
            "You should back up your new wallet right now.",
            "It should be backed up now!",
            "Wallet created.\n",
            "Wallet created successfully.",
            "You can use your backup to recover your wallet at any time.",
            "Back up wallet",
            "Skip backup",
            "Are you sure you want to skip the backup?",
            "Commitment data",
            "Confirm locktime",
            "Do you want to create a proof of ownership?",
            "The mining fee of\n{0}\nis unexpectedly high.",
            "Locktime is set but will have no effect.",
            "Locktime set to",
            "Locktime set to blockheight",
            "A lot of change-outputs.",
            "Multiple accounts",
            "New fee rate:",
            "Simple send of",
            "Ticket amount",
            "Confirm details",
            "Finalize transaction",
            "High mining fee",
            "Meld transactions",
            "Modify amount",
            "Payjoin",
            "Proof of ownership",
            "Purchase ticket",
            "Update transaction",
            "Unknown path",
            "Unknown transaction",
            "Unusually high fee.",
            "The transaction contains unverified external inputs.",
            "The signature is valid.",
            "Voting rights to",
            "Abort",
            "Access",
            "Again",
            "Allow",
            "Back",
            "Back up",
            "Cancel",
            "Change",
            "Check",
            "Check again",
            "Close",
            "Confirm",
            "Continue",
            "Details",
            "Enable",
            "Enter",
            "Enter share",
            "Export",
            "Format",
            "Go back",
            "Hold to confirm",
            "Info",
            "Install",
            "More info",
            "Ok, I understand",
            "Purchase",
            "Quit",
            "Restart",
            "Retry",
            "Select",
            "Set",
            "Show all",
            "Show details",
            "Show words",
            "Skip",
            "Try again",
            "Turn off",
            "Turn on",
            "Access your coinjoin account?",
            "Do not disconnect your Trezor!",
            "Max mining fee",
            "Max rounds",
            "Authorize coinjoin",
            "Do not disconnect your trezor!",
            "Coinjoin in progress",
            "Waiting for others",
            "Fee rate:",
            "Sending from account:",
            "Fee info",
            "Sending from",
            "Change device name to {0}?",
            "Device name",
            "Do you really want to send entropy?",
            "Confirm entropy",
            "Sign transaction",
            "Enable experimental features?",
            "Only for development and beta testing!",
            "Experimental mode",
            "Update firmware",
            "FW fingerprint",
            "Click to Connect",
            "Click to Unlock",
            "Backup failed",
            "Backup needed",
            "Coinjoin authorized",
            "Experimental mode",
            "No USB connection",
            "PIN not set",
            "Seedless",
            "Change wallpaper",
            "BACK",
            "CANCEL",
            "DELETE",
            "ENTER",
            "RETURN",
            "SHOW",
            "SPACE",
            "Joint transaction",
            "To the total amount:",
            "You are contributing:",
            "Change language to {0}?",
            "Language changed successfully",
            "Changing language",
            "Language settings",
            "Tap to connect",
            "Tap to unlock",
            "Locked",
            "Not connected",
            "Decrypt value",
            "Encrypt value",
            "Suite labeling",
            "Decrease amount by:",
            "Increase amount by:",
            "New amount:",
            "Modify amount",
            "Decrease fee by:",
            "Fee rate:",
            "Increase fee by:",
            "New transaction fee:",
            "Fee did not change.\n",
            "Modify fee",
            "Transaction fee:",
            "Access passphrase wallet?",
            "Always enter your passphrase on Trezor?",
            "Passphrase provided by host will be used but will not be displayed due to the device settings.",
            "Passphrase wallet",
            "Hide passphrase coming from host?",
            "The next screen shows your passphrase.",
            "Please enter your passphrase.",
            "Do you want to revoke the passphrase on device setting?",
            "Confirm passphrase",
            "Enter passphrase",
            "Hide passphrase",
            "Passphrase settings",
            "Passphrase source",
            "Turn off passphrase protection?",
            "Turn on passphrase protection?",
            "Change PIN?",
            "PIN changed.",
            "Position of the cursor will change between entries for enhanced security.",
            "The new PIN must be different from your wipe code.",
            "PIN protection\nturned off.",
            "PIN protection\nturned on.",
            "Enter PIN",
            "Enter new PIN",
            "The PIN you have entered is not valid.",
            "PIN will be required to access this device.",
            "Invalid PIN",
            "Last attempt",
            "Entered PINs do not match!",
            "PIN mismatch",
            "Please check again.",
            "Re-enter new PIN",
            "Please re-enter PIN to confirm.",
            "PIN should be 4-50 digits long.",
            "Check PIN",
            "PIN settings",
            "Wrong PIN",
            "tries left",
            "Are you sure you want to turn off PIN protection?",
            "Turn on PIN protection?",
            "Wrong PIN",
            "key|keys",
            "hour|hours",
            "millisecond|milliseconds",
            "minute|minutes",
            "second|seconds",
            "action|actions",
            "operation|operations",
            "group|groups",
            "share|shares",
            "Checking authenticity...",
            "Done",
            "Loading transaction...",
            "Locking the device...",
            "1 second left",
            "Please wait",
            "Processing",
            "Refreshing...",
            "Signing transaction...",
            "Syncing...",
            "{0} seconds left",
            "Trezor will restart in bootloader mode.",
            "Go to bootloader",
            "Firmware version {0}\nby {1}",
            "Cancel backup check",
            "Check your backup?",
            "Position of the cursor will change between entries for enhanced security.",
            "The entered wallet backup is valid and matches the one in this device.",
            "The entered wallet backup is valid but does not match the one in the device.",
            "The entered recovery shares are valid and match what is currently in the device.",
            "The entered recovery shares are valid but do not match what is currently in the device.",
            "Enter any share",
            "Enter your backup.",
            "Enter a different share.",
            "Enter share from a different group.",
            "Group {0}",
            "Group threshold reached.",
            "Invalid wallet backup entered.",
            "Invalid recovery share entered.",
            "More shares needed",
            "Select the number of words in your backup.",
            "You'll only have to select the first 2-4 letters of each word.",
            "All progress will be lost.",
            "Share already entered",
            "You have entered a share from a different backup.",
            "Share {0}",
            "Recover wallet",
            "Cancel backup check",
            "Cancel recovery",
            "Backup check",
            "Recover wallet",
            "Remaining shares",
            "Type word {0} of {1}",
            "Wallet recovery completed",
            "Are you sure you want to cancel the backup check?",
            "Are you sure you want to cancel the recovery process?",
            "({0} words)",
            "Word {0} of {1}",
            "{count} more {plural} starting",
            "{count} more {plural} needed",
            "{0} of {1} shares entered",
            "You have entered",
            "The group threshold specifies the number of groups required to recover your wallet.",
            "all {0} of {1} shares",
            "any {0} of {1} shares",
            "Create wallet",
            "Recover wallet",
            "By continuing you agree to Trezor Company's terms and conditions.",
            "Check backup",
            "Check g{0} - share {1}",
            "Check wallet backup",
            "Check share #{0}",
            "Continue with the next share.",
            "Continue with share #{0}.",
            "You have finished verifying your recovery shares for group {0}.",
            "You have finished verifying your wallet backup.",
            "You have finished verifying your recovery shares.",
            "A group is made up of recovery shares.",
            "Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds.",
            "Group {0} - Share {1} checked successfully.",
            "Group {0} - share {1}",
            "More info at",
            "For recovery you need all {0} of the shares.",
            "For recovery you need any {0} of the shares.",
            "needed to form a group. ",
            "needed to recover your wallet. ",
            "Never put your backup anywhere digital.",
            "{0} people or locations will each hold one share.",
            "Each recovery share is a sequence of {0} words. Next you will choose the threshold number of shares needed to form Group {1}.",
            "Each recovery share is a sequence of {0} words. Next you will choose how many shares you need to recover your wallet.",
            "The required number of shares to form Group {0}.",
            "= total number of unique word lists used for wallet backup.",
            "1 share",
            "Only one share will be created.",
            "Wallet backup",
            "Recovery share #{0}",
            "The required number of groups for recovery.",
            "Select the correct word for each position.",
            "Select {0} word",
            "Select word {0} of {1}:",
            "Set it to {0} and you will need ",
            "Share #{0} checked successfully.",
            "Standard backup",
            "Number of groups",
            "Number of shares",
            "Set number of groups",
            "Set number of shares",
            "Set sizes and thresholds",
            "Set size and threshold for each group",
            "Set threshold",
            "Backup checklist",
            "Write down and check all shares",
            "Write down & check all wallet backup shares",
            "The threshold sets the number of shares ",
            "= minimum number of unique word lists used for recovery.",
            "Backup is done",
            "Create wallet",
            "Group threshold",
            "Number of groups",
            "Number of shares",
            "Set group threshold",
            "Set number of groups",
            "Set number of shares",
            "Set threshold",
            "to form Group {0}.",
            "trezor.io/tos",
            "Set the total number of shares in Group {0}.",
            "Use your backup when you need to recover your wallet.",
            "Write the following {0} words in order on your wallet backup card.",
            "Wrong word selected!",
            "For recovery you need 1 share.",
            "Your backup is done.",
            "Change display orientation to {0}?",
            "east",
            "north",
            "south",
            "Display orientation",
            "west",
            "Trezor will allow you to approve some actions which might be unsafe.",
            "Trezor will temporarily allow you to approve some actions which might be unsafe.",
            "Do you really want to enforce strict safety checks (recommended)?",
            "Safety checks",
            "Safety override",
            "All data on the SD card will be lost.",
            "SD card required.",
            "Do you really want to remove SD card protection from your device?",
            "You have successfully disabled SD protection.",
            "Do you really want to secure your device with SD card protection?",
            "You have successfully enabled SD protection.",
            "SD card error",
            "Format SD card",
            "Please insert the correct SD card for this device.",
            "Please insert your SD card.",
            "Please unplug the device and insert your SD card.",
            "There was a problem accessing the SD card.",
            "Do you really want to replace the current SD card secret with a newly generated one?",
            "You have successfully refreshed SD protection.",
            "Do you want to restart Trezor in bootloader mode?",
            "SD card protection",
            "SD card problem",
            "Unknown filesystem.",
            "Please unplug the device and insert the correct SD card.",
            "Use a different card or format the SD card to the FAT32 filesystem.",
            "Do you really want to format the SD card?",
            "Wrong SD card.",
            "address path",
            "Sending amount",
            "Sending from multiple accounts.",
            "Including fee:",
            "Maximum fee",
            "Receiving to a multisig address.",
            "Confirm sending",
            "Joint transaction",
            "Receiving to",
            "Sending",
            "Sending amount",
            "Sending to",
            "To the total amount:",
            "Transaction ID",
            "You are contributing:",
            " words in order.",
            "I wrote down all ",
            "{0} Bytes",
            "Signing address",
            "Confirm message",
            "Message size",
            "Verify address",
            "Press both left and right at the same\ntime to confirm.",
            "Press and hold the right button to\napprove important operations.",
            "You're ready to\nuse Trezor.",
            "Press right to scroll down to read all content when text doesn't fit on one screen.\n\rPress left to scroll up.",
            "Are you sure you\nwant to skip the tutorial?",
            "Hello",
            "Screen scroll",
            "Skip tutorial",
            "Tutorial complete",
            "Use Trezor by\nclicking the left and right buttons.\n\rContinue right.",
            "Welcome to Trezor. Press right to continue.",
            "All data will be erased.",
            "Wipe device",
            "Do you really want to wipe the device?\n",
            "Change wipe code?",
            "Wipe code changed.",
            "The wipe code must be different from your PIN.",
            "Wipe code disabled.",
            "Wipe code enabled.",
            "Enter new wipe code",
            "Wipe code can be used to erase all data from this device.",
            "Invalid wipe code",
            "The wipe codes you entered do not match.",
            "Re-enter wipe code",
            "Please re-enter wipe code to confirm.",
            "Check wipe code",
            "Invalid wipe code",
            "Wipe code settings",
            "Turn off wipe code protection?",
            "Turn on wipe code protection?",
            "Wipe code mismatch",
            "Number of words",
            "Account",
            "Account:",
            "Address",
            "Amount",
            "Are you sure?",
            "Array of",
            "Blockhash",
            "Buying",
            "Confirm",
            "Confirm fee",
            "Contains",
            "Continue anyway?",
            "Continue with",
            "Error",
            "Fee",
            "from",
            "Keep it safe!",
            "Continue only if you know what you are doing!",
            "My Trezor",
            "No",
            "outputs",
            "Please check again",
            "Please try again",
            "Do you really want to",
            "Recipient",
            "Sign",
            "Signer",
            "Check",
            "Group",
            "Information",
            "Remember",
            "Share",
            "Shares",
            "Success",
            "Summary",
            "Threshold",
            "Unknown",
            "Warning",
            "Writable",
            "Yes",
            "Just a moment...",
            "PREVIOUS",
            "Starting up",
            "Verifying PIN",
            "Wrong PIN",
            "Do you want to create a {0} of {1} multi-share backup?",
            "Multi-share backup",
            "Tap to confirm",
            "Hold to confirm",
            "Important",
            "I wrote down all {0} words in order.",
            "Create a backup to avoid losing access to your funds",
            "Let's do a quick check of your backup.",
            "Instructions",
            "Not recommended!",
            "Account info",
            "If receive address doesn't match, contact Trezor Support at trezor.io/support.",
            "Cancel receive",
            "QR code",
            "Derivation path",
            "Continue in the app",
            "Cancel and exit",
            "Receive address confirmed",
            "Continue without PIN",
            "Without a PIN, anyone can access this device.",
            "Cancel PIN setup",
            "Cancel sign",
            "Send from",
            "Hold to sign",
            "Fee rate",
            "incl. Transaction fee",
            "Total amount",
            "Auto-lock turned on",
            "Your wallet backup contains multiple lists of words in a specific order (shares).",
            "Your wallet backup contains {0} words in a specific order.",
            "Wallet backup completed",
            "Create wallet backup",
            "Disable haptic feedback?",
            "Enable haptic feedback?",
            "Setting",
            "Haptic feedback",
            "Continue\nholding",
            "Enter next share",
            "Hold to continue",
            "Hold to exit tutorial",
            "Learn more",
            "Continue with Share #{0}",
            "Start with share #1",
            "Tap to start",
            "Passphrase",
            "Wallet backup not on this device",
            "Invalid wallet backup entered",
            "All shares are valid and belong to the backup in this device",
            "Entered share is valid and belongs to the backup in the device",
            "Verify remaining recovery shares?",
            "Enter each word of your wallet backup in order.",
            "It's safe to disconnect your Trezor while recovering your wallet and continue later.",
            "Share doesn't match",
            "Cancel create wallet",
            "Incorrect word selected",
            "More at",
            "How many wallet backup shares do you want to create?",
            "Each backup share is a sequence of {0} words. Store each wordlist in a separate, safe location or share with trusted individuals. Collect as needed to recover your wallet.",
            "Select the minimum shares required to recover your wallet.",
            "Share #{0} completed",
            "Number of shares: {0}",
            "Recovery threshold: {0}",
            "Transaction signed",
            "Continue tutorial",
            "Exit tutorial",
            "Find context-specific actions and options in the menu.",
            "You're all set to start using your device!",
            "Tap the lower half of the screen to continue, or swipe down to go back.",
            "Easy navigation",
            "Welcome to\nTrezor Safe 5",
            "Good to know",
            "Operation cancelled",
            "Settings",
            "Try again.",
            "Number of groups: {0}",
            "Display brightness",
            "Multi-share backup",
            "Create additional backup?",
            "Create backup",
            "Change wallpaper to default image?",
            "Words may repeat.",
            "Repeat for all shares.",
            "Settings",
            "Homescreen",
            "The word is repeated",
            "Let's begin",
            "Did you know?",
            "The Trezor Model One, created in 2013,\nwas the world's first hardware wallet.",
            "Restart tutorial",
            "Handy menu",
            "Hold to confirm important actions",
            "Well done!",
            "Learn how to use and navigate this device with ease.",
            "Get started!",
            "Swipe horizontally",
            "Adjust",
            "Apply",
            "Display brightness changed",
            "Change display brightness",
            "Done",
            "The threshold sets the minumum number of shares needed to recover your wallet.",
            "If you set {0} out of {1} shares, you'll need {2} backup shares to recover your wallet.",
            "Continue with empty passphrase?",
            "Swipe down",
            "Public key confirmed",
            "Continue anyway",
            "View all data",
            "View all data in the menu.",
            "Enable labeling?",
            "Confirm without review",
            "Tap to continue",
            "Unpair all bluetooth devices",
            "Unpair connected device",
            "Unpair",
            "Unlocked",
        ),
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
            (Self::authenticate__confirm_template, 273),
            (Self::authenticate__header, 292),
            (Self::auto_lock__change_template, 333),
            (Self::auto_lock__title, 348),
            (Self::backup__can_back_up_anytime, 394),
            (Self::backup__it_should_be_backed_up, 439),
            (Self::backup__it_should_be_backed_up_now, 466),
            (Self::backup__new_wallet_created, 482),
            (Self::backup__new_wallet_successfully_created, 510),
            (Self::backup__recover_anytime, 569),
            (Self::backup__title_backup_wallet, 583),
            (Self::backup__title_skip, 594),
            (Self::backup__want_to_skip, 635),
            (Self::bitcoin__commitment_data, 650),
            (Self::bitcoin__confirm_locktime, 666),
            (Self::bitcoin__create_proof_of_ownership, 709),
            (Self::bitcoin__high_mining_fee_template, 752),
            (Self::bitcoin__locktime_no_effect, 792),
            (Self::bitcoin__locktime_set_to, 807),
            (Self::bitcoin__locktime_set_to_blockheight, 834),
            (Self::bitcoin__lot_of_change_outputs, 858),
            (Self::bitcoin__multiple_accounts, 875),
            (Self::bitcoin__new_fee_rate, 888),
            (Self::bitcoin__simple_send_of, 902),
            (Self::bitcoin__ticket_amount, 915),
            (Self::bitcoin__title_confirm_details, 930),
            (Self::bitcoin__title_finalize_transaction, 950),
            (Self::bitcoin__title_high_mining_fee, 965),
            (Self::bitcoin__title_meld_transaction, 982),
            (Self::bitcoin__title_modify_amount, 995),
            (Self::bitcoin__title_payjoin, 1002),
            (Self::bitcoin__title_proof_of_ownership, 1020),
            (Self::bitcoin__title_purchase_ticket, 1035),
            (Self::bitcoin__title_update_transaction, 1053),
            (Self::bitcoin__unknown_path, 1065),
            (Self::bitcoin__unknown_transaction, 1084),
            (Self::bitcoin__unusually_high_fee, 1103),
            (Self::bitcoin__unverified_external_inputs, 1155),
            (Self::bitcoin__valid_signature, 1178),
            (Self::bitcoin__voting_rights, 1194),
            (Self::buttons__abort, 1199),
            (Self::buttons__access, 1205),
            (Self::buttons__again, 1210),
            (Self::buttons__allow, 1215),
            (Self::buttons__back, 1219),
            (Self::buttons__back_up, 1226),
            (Self::buttons__cancel, 1232),
            (Self::buttons__change, 1238),
            (Self::buttons__check, 1243),
            (Self::buttons__check_again, 1254),
            (Self::buttons__close, 1259),
            (Self::buttons__confirm, 1266),
            (Self::buttons__continue, 1274),
            (Self::buttons__details, 1281),
            (Self::buttons__enable, 1287),
            (Self::buttons__enter, 1292),
            (Self::buttons__enter_share, 1303),
            (Self::buttons__export, 1309),
            (Self::buttons__format, 1315),
            (Self::buttons__go_back, 1322),
            (Self::buttons__hold_to_confirm, 1337),
            (Self::buttons__info, 1341),
            (Self::buttons__install, 1348),
            (Self::buttons__more_info, 1357),
            (Self::buttons__ok_i_understand, 1373),
            (Self::buttons__purchase, 1381),
            (Self::buttons__quit, 1385),
            (Self::buttons__restart, 1392),
            (Self::buttons__retry, 1397),
            (Self::buttons__select, 1403),
            (Self::buttons__set, 1406),
            (Self::buttons__show_all, 1414),
            (Self::buttons__show_details, 1426),
            (Self::buttons__show_words, 1436),
            (Self::buttons__skip, 1440),
            (Self::buttons__try_again, 1449),
            (Self::buttons__turn_off, 1457),
            (Self::buttons__turn_on, 1464),
            (Self::coinjoin__access_account, 1493),
            (Self::coinjoin__do_not_disconnect, 1523),
            (Self::coinjoin__max_mining_fee, 1537),
            (Self::coinjoin__max_rounds, 1547),
            (Self::coinjoin__title, 1565),
            (Self::coinjoin__title_do_not_disconnect, 1595),
            (Self::coinjoin__title_progress, 1615),
            (Self::coinjoin__waiting_for_others, 1633),
            (Self::confirm_total__fee_rate_colon, 1642),
            (Self::confirm_total__sending_from_account, 1663),
            (Self::confirm_total__title_fee, 1671),
            (Self::confirm_total__title_sending_from, 1683),
            (Self::device_name__change_template, 1709),
            (Self::device_name__title, 1720),
            (Self::entropy__send, 1755),
            (Self::entropy__title_confirm, 1770),
            (Self::send__sign_transaction, 1786),
            (Self::experimental_mode__enable, 1815),
            (Self::experimental_mode__only_for_dev, 1853),
            (Self::experimental_mode__title, 1870),
            (Self::firmware_update__title, 1885),
            (Self::firmware_update__title_fingerprint, 1899),
            (Self::homescreen__click_to_connect, 1915),
            (Self::homescreen__click_to_unlock, 1930),
            (Self::homescreen__title_backup_failed, 1943),
            (Self::homescreen__title_backup_needed, 1956),
            (Self::homescreen__title_coinjoin_authorized, 1975),
            (Self::homescreen__title_experimental_mode, 1992),
            (Self::homescreen__title_no_usb_connection, 2009),
            (Self::homescreen__title_pin_not_set, 2020),
            (Self::homescreen__title_seedless, 2028),
            (Self::homescreen__title_set, 2044),
            (Self::inputs__back, 2048),
            (Self::inputs__cancel, 2054),
            (Self::inputs__delete, 2060),
            (Self::inputs__enter, 2065),
            (Self::inputs__return, 2071),
            (Self::inputs__show, 2075),
            (Self::inputs__space, 2080),
            (Self::joint__title, 2097),
            (Self::joint__to_the_total_amount, 2117),
            (Self::joint__you_are_contributing, 2138),
            (Self::language__change_to_template, 2161),
            (Self::language__changed, 2190),
            (Self::language__progress, 2207),
            (Self::language__title, 2224),
            (Self::lockscreen__tap_to_connect, 2238),
            (Self::lockscreen__tap_to_unlock, 2251),
            (Self::lockscreen__title_locked, 2257),
            (Self::lockscreen__title_not_connected, 2270),
            (Self::misc__decrypt_value, 2283),
            (Self::misc__encrypt_value, 2296),
            (Self::misc__title_suite_labeling, 2310),
            (Self::modify_amount__decrease_amount, 2329),
            (Self::modify_amount__increase_amount, 2348),
            (Self::modify_amount__new_amount, 2359),
            (Self::modify_amount__title, 2372),
            (Self::modify_fee__decrease_fee, 2388),
            (Self::modify_fee__fee_rate, 2397),
            (Self::modify_fee__increase_fee, 2413),
            (Self::modify_fee__new_transaction_fee, 2433),
            (Self::modify_fee__no_change, 2453),
            (Self::modify_fee__title, 2463),
            (Self::modify_fee__transaction_fee, 2479),
            (Self::passphrase__access_wallet, 2504),
            (Self::passphrase__always_on_device, 2543),
            (Self::passphrase__from_host_not_shown, 2637),
            (Self::passphrase__wallet, 2654),
            (Self::passphrase__hide, 2687),
            (Self::passphrase__next_screen_will_show_passphrase, 2725),
            (Self::passphrase__please_enter, 2754),
            (Self::passphrase__revoke_on_device, 2809),
            (Self::passphrase__title_confirm, 2827),
            (Self::passphrase__title_enter, 2843),
            (Self::passphrase__title_hide, 2858),
            (Self::passphrase__title_settings, 2877),
            (Self::passphrase__title_source, 2894),
            (Self::passphrase__turn_off, 2925),
            (Self::passphrase__turn_on, 2955),
            (Self::pin__change, 2966),
            (Self::pin__changed, 2978),
            (Self::pin__cursor_will_change, 3051),
            (Self::pin__diff_from_wipe_code, 3101),
            (Self::pin__disabled, 3127),
            (Self::pin__enabled, 3152),
            (Self::pin__enter, 3161),
            (Self::pin__enter_new, 3174),
            (Self::pin__entered_not_valid, 3212),
            (Self::pin__info, 3255),
            (Self::pin__invalid_pin, 3266),
            (Self::pin__last_attempt, 3278),
            (Self::pin__mismatch, 3304),
            (Self::pin__pin_mismatch, 3316),
            (Self::pin__please_check_again, 3335),
            (Self::pin__reenter_new, 3351),
            (Self::pin__reenter_to_confirm, 3382),
            (Self::pin__should_be_long, 3413),
            (Self::pin__title_check_pin, 3422),
            (Self::pin__title_settings, 3434),
            (Self::pin__title_wrong_pin, 3443),
            (Self::pin__tries_left, 3453),
            (Self::pin__turn_off, 3502),
            (Self::pin__turn_on, 3525),
            (Self::pin__wrong_pin, 3534),
            (Self::plurals__contains_x_keys, 3542),
            (Self::plurals__lock_after_x_hours, 3552),
            (Self::plurals__lock_after_x_milliseconds, 3576),
            (Self::plurals__lock_after_x_minutes, 3590),
            (Self::plurals__lock_after_x_seconds, 3604),
            (Self::plurals__sign_x_actions, 3618),
            (Self::plurals__transaction_of_x_operations, 3638),
            (Self::plurals__x_groups_needed, 3650),
            (Self::plurals__x_shares_needed, 3662),
            (Self::progress__authenticity_check, 3686),
            (Self::progress__done, 3690),
            (Self::progress__loading_transaction, 3712),
            (Self::progress__locking_device, 3733),
            (Self::progress__one_second_left, 3746),
            (Self::progress__please_wait, 3757),
            (Self::storage_msg__processing, 3767),
            (Self::progress__refreshing, 3780),
            (Self::progress__signing_transaction, 3802),
            (Self::progress__syncing, 3812),
            (Self::progress__x_seconds_left_template, 3828),
            (Self::reboot_to_bootloader__restart, 3867),
            (Self::reboot_to_bootloader__title, 3883),
            (Self::reboot_to_bootloader__version_by_template, 3910),
            (Self::recovery__cancel_dry_run, 3929),
            (Self::recovery__check_dry_run, 3947),
            (Self::recovery__cursor_will_change, 4020),
            (Self::recovery__dry_run_bip39_valid_match, 4090),
            (Self::recovery__dry_run_bip39_valid_mismatch, 4166),
            (Self::recovery__dry_run_slip39_valid_match, 4246),
            (Self::recovery__dry_run_slip39_valid_mismatch, 4333),
            (Self::recovery__enter_any_share, 4348),
            (Self::recovery__enter_backup, 4366),
            (Self::recovery__enter_different_share, 4390),
            (Self::recovery__enter_share_from_diff_group, 4425),
            (Self::recovery__group_num_template, 4434),
            (Self::recovery__group_threshold_reached, 4458),
            (Self::recovery__invalid_wallet_backup_entered, 4488),
            (Self::recovery__invalid_share_entered, 4519),
            (Self::recovery__more_shares_needed, 4537),
            (Self::recovery__num_of_words, 4579),
            (Self::recovery__only_first_n_letters, 4641),
            (Self::recovery__progress_will_be_lost, 4667),
            (Self::recovery__share_already_entered, 4688),
            (Self::recovery__share_from_another_multi_share_backup, 4737),
            (Self::recovery__share_num_template, 4746),
            (Self::recovery__title, 4760),
            (Self::recovery__title_cancel_dry_run, 4779),
            (Self::recovery__title_cancel_recovery, 4794),
            (Self::recovery__title_dry_run, 4806),
            (Self::recovery__title_recover, 4820),
            (Self::recovery__title_remaining_shares, 4836),
            (Self::recovery__type_word_x_of_y_template, 4856),
            (Self::recovery__wallet_recovered, 4881),
            (Self::recovery__wanna_cancel_dry_run, 4930),
            (Self::recovery__wanna_cancel_recovery, 4983),
            (Self::recovery__word_count_template, 4994),
            (Self::recovery__word_x_of_y_template, 5009),
            (Self::recovery__x_more_items_starting_template_plural, 5039),
            (Self::recovery__x_more_shares_needed_template_plural, 5067),
            (Self::recovery__x_of_y_entered_template, 5092),
            (Self::recovery__you_have_entered, 5108),
            (Self::reset__advanced_group_threshold_info, 5191),
            (Self::reset__all_x_of_y_template, 5212),
            (Self::reset__any_x_of_y_template, 5233),
            (Self::reset__button_create, 5246),
            (Self::reset__button_recover, 5260),
            (Self::reset__by_continuing, 5325),
            (Self::reset__check_backup_title, 5337),
            (Self::reset__check_group_share_title_template, 5359),
            (Self::reset__check_wallet_backup_title, 5378),
            (Self::reset__check_share_title_template, 5394),
            (Self::reset__continue_with_next_share, 5423),
            (Self::reset__continue_with_share_template, 5448),
            (Self::reset__finished_verifying_group_template, 5511),
            (Self::reset__finished_verifying_wallet_backup, 5558),
            (Self::reset__finished_verifying_shares, 5607),
            (Self::reset__group_description, 5645),
            (Self::reset__group_info, 5778),
            (Self::reset__group_share_checked_successfully_template, 5821),
            (Self::reset__group_share_title_template, 5842),
            (Self::reset__more_info_at, 5854),
            (Self::reset__need_all_share_template, 5898),
            (Self::reset__need_any_share_template, 5942),
            (Self::reset__needed_to_form_a_group, 5966),
            (Self::reset__needed_to_recover_your_wallet, 5997),
            (Self::reset__never_make_digital_copy, 6036),
            (Self::reset__num_of_share_holders_template, 6085),
            (Self::reset__num_of_shares_advanced_info_template, 6210),
            (Self::reset__num_of_shares_basic_info_template, 6327),
            (Self::reset__num_shares_for_group_template, 6375),
            (Self::reset__number_of_shares_info, 6434),
            (Self::reset__one_share, 6441),
            (Self::reset__only_one_share_will_be_created, 6472),
            (Self::reset__recovery_wallet_backup_title, 6485),
            (Self::reset__recovery_share_title_template, 6504),
            (Self::reset__required_number_of_groups, 6547),
            (Self::reset__select_correct_word, 6589),
            (Self::reset__select_word_template, 6604),
            (Self::reset__select_word_x_of_y_template, 6627),
            (Self::reset__set_it_to_count_template, 6659),
            (Self::reset__share_checked_successfully_template, 6691),
            (Self::reset__share_words_title, 6706),
            (Self::reset__slip39_checklist_num_groups, 6722),
            (Self::reset__slip39_checklist_num_shares, 6738),
            (Self::reset__slip39_checklist_set_num_groups, 6758),
            (Self::reset__slip39_checklist_set_num_shares, 6778),
            (Self::reset__slip39_checklist_set_sizes, 6802),
            (Self::reset__slip39_checklist_set_sizes_longer, 6839),
            (Self::reset__slip39_checklist_set_threshold, 6852),
            (Self::reset__slip39_checklist_title, 6868),
            (Self::reset__slip39_checklist_write_down, 6899),
            (Self::reset__slip39_checklist_write_down_recovery, 6942),
            (Self::reset__the_threshold_sets_the_number_of_shares, 6982),
            (Self::reset__threshold_info, 7038),
            (Self::reset__title_backup_is_done, 7052),
            (Self::reset__title_create_wallet, 7065),
            (Self::reset__title_group_threshold, 7080),
            (Self::reset__title_number_of_groups, 7096),
            (Self::reset__title_number_of_shares, 7112),
            (Self::reset__title_set_group_threshold, 7131),
            (Self::reset__title_set_number_of_groups, 7151),
            (Self::reset__title_set_number_of_shares, 7171),
            (Self::reset__title_set_threshold, 7184),
            (Self::reset__to_form_group_template, 7202),
            (Self::reset__tos_link, 7215),
            (Self::reset__total_number_of_shares_in_group_template, 7259),
            (Self::reset__use_your_backup, 7312),
            (Self::reset__write_down_words_template, 7378),
            (Self::reset__wrong_word_selected, 7398),
            (Self::reset__you_need_one_share, 7428),
            (Self::reset__your_backup_is_done, 7448),
            (Self::rotation__change_template, 7482),
            (Self::rotation__east, 7486),
            (Self::rotation__north, 7491),
            (Self::rotation__south, 7496),
            (Self::rotation__title_change, 7515),
            (Self::rotation__west, 7519),
            (Self::safety_checks__approve_unsafe_always, 7587),
            (Self::safety_checks__approve_unsafe_temporary, 7667),
            (Self::safety_checks__enforce_strict, 7732),
            (Self::safety_checks__title, 7745),
            (Self::safety_checks__title_safety_override, 7760),
            (Self::sd_card__all_data_will_be_lost, 7797),
            (Self::sd_card__card_required, 7814),
            (Self::sd_card__disable, 7879),
            (Self::sd_card__disabled, 7924),
            (Self::sd_card__enable, 7989),
            (Self::sd_card__enabled, 8033),
            (Self::sd_card__error, 8046),
            (Self::sd_card__format_card, 8060),
            (Self::sd_card__insert_correct_card, 8110),
            (Self::sd_card__please_insert, 8137),
            (Self::sd_card__please_unplug_and_insert, 8186),
            (Self::sd_card__problem_accessing, 8228),
            (Self::sd_card__refresh, 8312),
            (Self::sd_card__refreshed, 8358),
            (Self::sd_card__restart, 8407),
            (Self::sd_card__title, 8425),
            (Self::sd_card__title_problem, 8440),
            (Self::sd_card__unknown_filesystem, 8459),
            (Self::sd_card__unplug_and_insert_correct, 8515),
            (Self::sd_card__use_different_card, 8582),
            (Self::sd_card__wanna_format, 8623),
            (Self::sd_card__wrong_sd_card, 8637),
            (Self::send__address_path, 8649),
            (Self::send__confirm_sending, 8663),
            (Self::send__from_multiple_accounts, 8694),
            (Self::send__including_fee, 8708),
            (Self::send__maximum_fee, 8719),
            (Self::send__receiving_to_multisig, 8751),
            (Self::send__title_confirm_sending, 8766),
            (Self::send__title_joint_transaction, 8783),
            (Self::send__title_receiving_to, 8795),
            (Self::send__title_sending, 8802),
            (Self::send__title_sending_amount, 8816),
            (Self::send__title_sending_to, 8826),
            (Self::send__to_the_total_amount, 8846),
            (Self::send__transaction_id, 8860),
            (Self::send__you_are_contributing, 8881),
            (Self::share_words__words_in_order, 8897),
            (Self::share_words__wrote_down_all, 8914),
            (Self::sign_message__bytes_template, 8923),
            (Self::sign_message__confirm_address, 8938),
            (Self::sign_message__confirm_message, 8953),
            (Self::sign_message__message_size, 8965),
            (Self::sign_message__verify_address, 8979),
            (Self::tutorial__middle_click, 9033),
            (Self::tutorial__press_and_hold, 9097),
            (Self::tutorial__ready_to_use, 9124),
            (Self::tutorial__scroll_down, 9233),
            (Self::tutorial__sure_you_want_skip, 9276),
            (Self::tutorial__title_hello, 9281),
            (Self::tutorial__title_screen_scroll, 9294),
            (Self::tutorial__title_skip, 9307),
            (Self::tutorial__title_tutorial_complete, 9324),
            (Self::tutorial__use_trezor, 9391),
            (Self::tutorial__welcome_press_right, 9434),
            (Self::wipe__info, 9458),
            (Self::wipe__title, 9469),
            (Self::wipe__want_to_wipe, 9508),
            (Self::wipe_code__change, 9525),
            (Self::wipe_code__changed, 9543),
            (Self::wipe_code__diff_from_pin, 9589),
            (Self::wipe_code__disabled, 9608),
            (Self::wipe_code__enabled, 9626),
            (Self::wipe_code__enter_new, 9645),
            (Self::wipe_code__info, 9702),
            (Self::wipe_code__invalid, 9719),
            (Self::wipe_code__mismatch, 9759),
            (Self::wipe_code__reenter, 9777),
            (Self::wipe_code__reenter_to_confirm, 9814),
            (Self::wipe_code__title_check, 9829),
            (Self::wipe_code__title_invalid, 9846),
            (Self::wipe_code__title_settings, 9864),
            (Self::wipe_code__turn_off, 9894),
            (Self::wipe_code__turn_on, 9923),
            (Self::wipe_code__wipe_code_mismatch, 9941),
            (Self::word_count__title, 9956),
            (Self::words__account, 9963),
            (Self::words__account_colon, 9971),
            (Self::words__address, 9978),
            (Self::words__amount, 9984),
            (Self::words__are_you_sure, 9997),
            (Self::words__array_of, 10005),
            (Self::words__blockhash, 10014),
            (Self::words__buying, 10020),
            (Self::words__confirm, 10027),
            (Self::words__confirm_fee, 10038),
            (Self::words__contains, 10046),
            (Self::words__continue_anyway_question, 10062),
            (Self::words__continue_with, 10075),
            (Self::words__error, 10080),
            (Self::words__fee, 10083),
            (Self::words__from, 10087),
            (Self::words__keep_it_safe, 10100),
            (Self::words__know_what_your_doing, 10145),
            (Self::words__my_trezor, 10154),
            (Self::words__no, 10156),
            (Self::words__outputs, 10163),
            (Self::words__please_check_again, 10181),
            (Self::words__please_try_again, 10197),
            (Self::words__really_wanna, 10218),
            (Self::words__recipient, 10227),
            (Self::words__sign, 10231),
            (Self::words__signer, 10237),
            (Self::words__title_check, 10242),
            (Self::words__title_group, 10247),
            (Self::words__title_information, 10258),
            (Self::words__title_remember, 10266),
            (Self::words__title_share, 10271),
            (Self::words__title_shares, 10277),
            (Self::words__title_success, 10284),
            (Self::words__title_summary, 10291),
            (Self::words__title_threshold, 10300),
            (Self::words__unknown, 10307),
            (Self::words__warning, 10314),
            (Self::words__writable, 10322),
            (Self::words__yes, 10325),
            (Self::reboot_to_bootloader__just_a_moment, 10341),
            (Self::inputs__previous, 10349),
            (Self::storage_msg__starting, 10360),
            (Self::storage_msg__verifying_pin, 10373),
            (Self::storage_msg__wrong_pin, 10382),
            (Self::reset__create_x_of_y_multi_share_backup_template, 10436),
            (Self::reset__title_shamir_backup, 10454),
            (Self::instructions__tap_to_confirm, 10468),
            (Self::instructions__hold_to_confirm, 10483),
            (Self::words__important, 10492),
            (Self::reset__words_written_down_template, 10528),
            (Self::backup__create_backup_to_prevent_loss, 10580),
            (Self::reset__check_backup_instructions, 10618),
            (Self::words__instructions, 10630),
            (Self::words__not_recommended, 10646),
            (Self::address_details__account_info, 10658),
            (Self::address__cancel_contact_support, 10736),
            (Self::address__cancel_receive, 10750),
            (Self::address__qr_code, 10757),
            (Self::address_details__derivation_path, 10772),
            (Self::instructions__continue_in_app, 10791),
            (Self::words__cancel_and_exit, 10806),
            (Self::address__confirmed, 10831),
            (Self::pin__cancel_description, 10851),
            (Self::pin__cancel_info, 10896),
            (Self::pin__cancel_setup, 10912),
            (Self::send__cancel_sign, 10923),
            (Self::send__send_from, 10932),
            (Self::instructions__hold_to_sign, 10944),
            (Self::confirm_total__fee_rate, 10952),
            (Self::send__incl_transaction_fee, 10973),
            (Self::send__total_amount, 10985),
            (Self::auto_lock__turned_on, 11004),
            (Self::backup__info_multi_share_backup, 11085),
            (Self::backup__info_single_share_backup, 11143),
            (Self::backup__title_backup_completed, 11166),
            (Self::backup__title_create_wallet_backup, 11186),
            (Self::haptic_feedback__disable, 11210),
            (Self::haptic_feedback__enable, 11233),
            (Self::haptic_feedback__subtitle, 11240),
            (Self::haptic_feedback__title, 11255),
            (Self::instructions__continue_holding, 11271),
            (Self::instructions__enter_next_share, 11287),
            (Self::instructions__hold_to_continue, 11303),
            (Self::instructions__hold_to_exit_tutorial, 11324),
            (Self::instructions__learn_more, 11334),
            (Self::instructions__shares_continue_with_x_template, 11358),
            (Self::instructions__shares_start_with_1, 11377),
            (Self::instructions__tap_to_start, 11389),
            (Self::passphrase__title_passphrase, 11399),
            (Self::recovery__dry_run_backup_not_on_this_device, 11431),
            (Self::recovery__dry_run_invalid_backup_entered, 11460),
            (Self::recovery__dry_run_slip39_valid_all_shares, 11520),
            (Self::recovery__dry_run_slip39_valid_share, 11582),
            (Self::recovery__dry_run_verify_remaining_shares, 11615),
            (Self::recovery__enter_each_word, 11662),
            (Self::recovery__info_about_disconnect, 11746),
            (Self::recovery__share_does_not_match, 11765),
            (Self::reset__cancel_create_wallet, 11785),
            (Self::reset__incorrect_word_selected, 11808),
            (Self::reset__more_at, 11815),
            (Self::reset__num_of_shares_how_many, 11867),
            (Self::reset__num_of_shares_long_info_template, 12038),
            (Self::reset__select_threshold, 12096),
            (Self::reset__share_completed_template, 12116),
            (Self::reset__slip39_checklist_num_shares_x_template, 12137),
            (Self::reset__slip39_checklist_threshold_x_template, 12160),
            (Self::send__transaction_signed, 12178),
            (Self::tutorial__continue, 12195),
            (Self::tutorial__exit, 12208),
            (Self::tutorial__menu, 12262),
            (Self::tutorial__ready_to_use_safe5, 12304),
            (Self::tutorial__swipe_up_and_down, 12375),
            (Self::tutorial__title_easy_navigation, 12390),
            (Self::tutorial__welcome_safe5, 12414),
            (Self::words__good_to_know, 12426),
            (Self::words__operation_cancelled, 12445),
            (Self::words__settings, 12453),
            (Self::words__try_again, 12463),
            (Self::reset__slip39_checklist_num_groups_x_template, 12484),
            (Self::brightness__title, 12502),
            (Self::recovery__title_unlock_repeated_backup, 12520),
            (Self::recovery__unlock_repeated_backup, 12545),
            (Self::recovery__unlock_repeated_backup_verb, 12558),
            (Self::homescreen__set_default, 12592),
            (Self::reset__words_may_repeat, 12609),
            (Self::reset__repeat_for_all_shares, 12631),
            (Self::homescreen__settings_subtitle, 12639),
            (Self::homescreen__settings_title, 12649),
            (Self::reset__the_word_is_repeated, 12669),
            (Self::tutorial__title_lets_begin, 12680),
            (Self::tutorial__did_you_know, 12693),
            (Self::tutorial__first_wallet, 12770),
            (Self::tutorial__restart_tutorial, 12786),
            (Self::tutorial__title_handy_menu, 12796),
            (Self::tutorial__title_hold, 12829),
            (Self::tutorial__title_well_done, 12839),
            (Self::tutorial__lets_begin, 12891),
            (Self::tutorial__get_started, 12903),
            (Self::instructions__swipe_horizontally, 12921),
            (Self::setting__adjust, 12927),
            (Self::setting__apply, 12932),
            (Self::brightness__changed_title, 12958),
            (Self::brightness__change_title, 12983),
            (Self::words__title_done, 12987),
            (Self::reset__slip39_checklist_more_info_threshold, 13065),
            (Self::reset__slip39_checklist_more_info_threshold_example_template, 13152),
            (Self::passphrase__continue_with_empty_passphrase, 13183),
            (Self::instructions__swipe_down, 13193),
            (Self::address__public_key_confirmed, 13213),
            (Self::words__continue_anyway, 13228),
            (Self::buttons__view_all_data, 13241),
            (Self::instructions__view_all_data, 13267),
            (Self::misc__enable_labeling, 13283),
            (Self::sign_message__confirm_without_review, 13305),
            (Self::instructions__tap_to_continue, 13320),
            (Self::ble__unpair_all, 13348),
            (Self::ble__unpair_current, 13371),
            (Self::ble__unpair_title, 13377),
            (Self::words__unlocked, 13385),
        ],
    };
    const ALTCOIN_BLOB: StringsBlob = StringsBlob {
        text: concat!(
            "Buy",
            "Confirm cancel",
            "Confirm input",
            "Confirm order",
            "Confirm output",
            "Order ID:",
            "Pair:",
            "Price:",
            "Quantity:",
            "Sell",
            "Sender address:",
            "Side:",
            "Base",
            "Enterprise",
            "Legacy",
            "Pointer",
            "Reward",
            "address - no staking rewards.",
            "Amount burned (decimals unknown):",
            "Amount minted (decimals unknown):",
            "Amount sent (decimals unknown):",
            "Pool has no metadata (anonymous pool)",
            "Asset fingerprint:",
            "Auxiliary data hash:",
            "Block",
            "Catalyst",
            "Certificate",
            "Change output",
            "Check all items carefully.",
            "Choose level of details:",
            "Collateral input ID:",
            "Collateral input index:",
            "The collateral return output contains tokens.",
            "Collateral return",
            "Confirm signing the stake pool registration as an owner.",
            "Confirm transaction",
            "Confirming a multisig transaction.",
            "Confirming a Plutus transaction.",
            "Confirming pool registration as owner.",
            "Confirming a transaction.",
            "Cost",
            "Credential doesn't match payment credential.",
            "Datum hash:",
            "Delegating to:",
            "for account {0} and index {1}:",
            "for account {0}:",
            "for key hash:",
            "for script:",
            "Inline datum",
            "Input ID:",
            "Input index:",
            "The following address is a change address. Its",
            "The following address is owned by this device. Its",
            "The vote key registration payment address is owned by this device. Its",
            "key hash",
            "Margin",
            "multi-sig path",
            "Contains {0} nested scripts.",
            "Network:",
            "Transaction has no outputs, network cannot be verified.",
            "Nonce:",
            "other",
            "path",
            "Pledge",
            "pointer",
            "Policy ID",
            "Pool metadata hash:",
            "Pool metadata url:",
            "Pool owner:",
            "Pool reward account:",
            "Reference input ID:",
            "Reference input index:",
            "Reference script",
            "Required signer",
            "reward",
            "Address is a reward address.",
            "Warning: The address is not a payment address, it is not eligible for rewards.",
            "Rewards go to:",
            "script",
            "All",
            "Any",
            "Script data hash:",
            "Script hash:",
            "Invalid before",
            "Invalid hereafter",
            "Key",
            "N of K",
            "script reward",
            "Sending",
            "Show Simple",
            "Sign transaction with {0}",
            "Stake delegation",
            "Stake key deregistration",
            "Stakepool registration",
            "Stake pool registration\nPool ID:",
            "Stake key registration",
            "Staking key for account",
            "to pool:",
            "token minting path",
            "Total collateral:",
            "Transaction",
            "The transaction contains minting or burning of tokens.",
            "The following transaction output contains a script address, but does not contain a datum.",
            "Transaction fee:",
            "Transaction ID:",
            "The transaction contains no collateral inputs. Plutus script will not be able to run.",
            "The transaction contains no script data hash. Plutus script will not be able to run.",
            "The following transaction output contains tokens.",
            "TTL:",
            "Unknown collateral amount.",
            "Path is unusual.",
            "Valid since:",
            "Verify script",
            "Vote key registration (CIP-36)",
            "Vote public key:",
            "Voting purpose:",
            "Warning",
            "Weight:",
            "Confirm withdrawal for {0} address:",
            "Requires {0} out of {1} signatures.",
            "You are about to sign {0}.",
            "Action Name:",
            "Arbitrary data",
            "Buy RAM",
            "Bytes:",
            "Cancel vote",
            "Checksum:",
            "Code:",
            "Contract:",
            "CPU:",
            "Creator:",
            "Delegate",
            "Delete Auth",
            "From:",
            "Link Auth",
            "Memo",
            "Name:",
            "NET:",
            "New account",
            "Owner:",
            "Parent:",
            "Payer:",
            "Permission:",
            "Proxy:",
            "Receiver:",
            "Refund",
            "Requirement:",
            "Sell RAM",
            "Sender:",
            "Threshold:",
            "To:",
            "Transfer:",
            "Type:",
            "Undelegate",
            "Unlink Auth",
            "Update Auth",
            "Vote for producers",
            "Vote for proxy",
            "Voter:",
            "Amount sent:",
            "Contract:",
            "Size: {0} bytes",
            "Gas limit",
            "Gas price",
            "Max fee per gas",
            "Name and version",
            "New contract will be deployed",
            "No message field",
            "Max priority fee",
            "Show full array",
            "Show full domain",
            "Show full message",
            "Show full struct",
            "Really sign EIP-712 typed data?",
            "Input data",
            "Confirm domain",
            "Confirm message",
            "Confirm struct",
            "Confirm typed data",
            "Signing address",
            "{0} units",
            "Unknown token",
            "The signature is valid.",
            "Already registered",
            "This device is already registered with this application.",
            "This device is already registered with {0}.",
            "This device is not registered with this application.",
            "The credential you are trying to import does\nnot belong to this authenticator.",
            "erase all credentials?",
            "Export information about the credentials stored on this device?",
            "Not registered",
            "This device is not registered with\n{0}.",
            "Please enable PIN protection.",
            "FIDO2 authenticate",
            "Import credential",
            "List credentials",
            "FIDO2 register",
            "Remove credential",
            "FIDO2 reset",
            "U2F authenticate",
            "U2F register",
            "FIDO2 verify user",
            "Unable to verify user.",
            "Do you really want to erase all credentials?",
            "Confirm export",
            "Confirm ki sync",
            "Confirm refresh",
            "Confirm unlock time",
            "Hashing inputs",
            "Payment ID",
            "Postprocessing...",
            "Processing...",
            "Processing inputs",
            "Processing outputs",
            "Signing...",
            "Signing inputs",
            "Unlock time for this transaction is set to {0}",
            "Do you really want to export tx_der\nfor tx_proof?",
            "Do you really want to export tx_key?",
            "Do you really want to export watch-only credentials?",
            "Do you really want to\nstart refresh?",
            "Do you really want to\nsync key images?",
            "absolute",
            "Activate",
            "Add",
            "Confirm action",
            "Confirm address",
            "Confirm creation fee",
            "Confirm mosaic",
            "Confirm multisig fee",
            "Confirm namespace",
            "Confirm payload",
            "Confirm properties",
            "Confirm rental fee",
            "Confirm transfer of",
            "Convert account to multisig account?",
            "Cosign transaction for",
            " cosignatory",
            "Create mosaic",
            "Create namespace",
            "Deactivate",
            "Decrease",
            "Description:",
            "Divisibility and levy cannot be shown for unknown mosaics",
            "Encrypted",
            "Final confirm",
            "immutable",
            "Increase",
            "Initial supply:",
            "Initiate transaction for",
            "Levy divisibility:",
            "Levy fee:",
            "Confirm mosaic levy fee of",
            "Levy mosaic:",
            "Levy namespace:",
            "Levy recipient:",
            "Levy type:",
            "Modify supply for",
            "Modify the number of cosignatories by ",
            "mutable",
            "of",
            "percentile",
            "{0} raw units",
            " remote harvesting?",
            "Remove",
            "Set minimum cosignatories to ",
            "Sign this transaction\nand pay {0}\nfor network fee?",
            "Supply change",
            "{0} supply by {1} whole units?",
            "Transferable?",
            "under namespace",
            "Unencrypted",
            "Unknown mosaic!",
            "Confirm tag",
            "Destination tag:\n{0}",
            "Account index",
            "Associated token account",
            "Confirm multisig",
            "Expected fee",
            "Instruction contains {0} accounts and its data is {1} bytes long.",
            "Instruction data",
            "The following instruction is a multisig instruction.",
            "{0} is provided via a lookup table.",
            "Lookup table address",
            "Multiple signers",
            "Token",
            "Transaction contains unknown instructions.",
            "Transaction requires {0} signers which increases the fee.",
            "Account Merge",
            "Account Thresholds",
            "Add Signer",
            "Add trust",
            "All XLM will be sent to",
            "Allow trust",
            "Asset",
            "Balance ID",
            "Bump Sequence",
            "Buying:",
            "Claim Claimable Balance",
            "Clear data",
            "Clear flags",
            "Confirm Issuer",
            "Confirm memo",
            "Confirm network",
            "Confirm operation",
            "Confirm Stellar",
            "Confirm timebounds",
            "Create Account",
            "Debited amount",
            "Delete",
            "Delete Passive Offer",
            "Delete trust",
            "Destination",
            "Important: Many exchanges require a memo when depositing",
            "Final confirm",
            "Hash",
            "High:",
            "Home Domain",
            "Inflation",
            "Initial Balance",
            "Initialize signing with",
            "{0} issuer",
            "Key:",
            "Limit",
            "Low:",
            "Master Weight:",
            "Medium:",
            "New Offer",
            "New Passive Offer",
            "No memo set!",
            "[no restriction]",
            "Transaction is on {0}",
            "Path Pay",
            "Path Pay at least",
            "Pay",
            "Pay at most",
            "Pre-auth transaction",
            "Price per {0}:",
            "private network",
            "Remove Signer",
            "Revoke trust",
            "Selling:",
            "Set data",
            "Set flags",
            "Set sequence to {0}?",
            "Sign this transaction made up of {0}",
            "and pay {0}\nfor fee?",
            "Source account",
            "testnet network",
            "Trusted Account",
            "Update",
            "Valid from (UTC)",
            "Valid to (UTC)",
            "Value (SHA-256):",
            "Do you want to clear value key {0}?",
            " your account",
            "Baker address",
            "Balance:",
            "Ballot:",
            "Confirm delegation",
            "Confirm origination",
            "Delegator",
            "Proposal",
            "Register delegate",
            "Remove delegation",
            "Submit ballot",
            "Submit proposal",
            "Submit proposals",
            "Increase and retrieve the U2F counter?",
            "Set the U2F counter to {0}?",
            "Get U2F counter",
            "Set U2F counter",
            "Claim",
            "Claim address",
            "Claim ETH from Everstake?",
            "Stake",
            "Stake address",
            "Stake ETH on Everstake?",
            "Unstake",
            "Unstake ETH from Everstake?",
            "Always Abstain",
            "Always No Confidence",
            "Delegating to key hash:",
            "Delegating to script:",
            "Deposit:",
            "Vote delegation",
            "More credentials",
            "Select the credential that you would like to use for authentication.",
            "for authentication",
            "Select credential",
            "Credential details",
            "Unknown contract address. Continue only if you know what you are doing.",
            "Token contract",
            "Interaction contract",
            "Unknown contract address.",
            "Base fee",
            "Claim",
            "Claim SOL from stake account?",
            "Claiming SOL to address outside your current wallet.",
            "Priority fee",
            "Stake",
            "Stake account",
            "Provider",
            "Stake SOL?",
            "The current wallet isn't the SOL staking withdraw authority.",
            "Withdraw authority address",
            "Unstake",
            "Unstake SOL from stake account?",
            "Vote account",
            "Stake SOL on {0}?",
            "Event kind: {0}",
            "Max fees and rent",
            "Max rent fee",
            "Transaction fee",
        ),
        offsets: &[
            (Self::binance__buy, 3),
            (Self::binance__confirm_cancel, 17),
            (Self::binance__confirm_input, 30),
            (Self::binance__confirm_order, 43),
            (Self::binance__confirm_output, 57),
            (Self::binance__order_id, 66),
            (Self::binance__pair, 71),
            (Self::binance__price, 77),
            (Self::binance__quantity, 86),
            (Self::binance__sell, 90),
            (Self::binance__sender_address, 105),
            (Self::binance__side, 110),
            (Self::cardano__addr_base, 114),
            (Self::cardano__addr_enterprise, 124),
            (Self::cardano__addr_legacy, 130),
            (Self::cardano__addr_pointer, 137),
            (Self::cardano__addr_reward, 143),
            (Self::cardano__address_no_staking, 172),
            (Self::cardano__amount_burned_decimals_unknown, 205),
            (Self::cardano__amount_minted_decimals_unknown, 238),
            (Self::cardano__amount_sent_decimals_unknown, 269),
            (Self::cardano__anonymous_pool, 306),
            (Self::cardano__asset_fingerprint, 324),
            (Self::cardano__auxiliary_data_hash, 344),
            (Self::cardano__block, 349),
            (Self::cardano__catalyst, 357),
            (Self::cardano__certificate, 368),
            (Self::cardano__change_output, 381),
            (Self::cardano__check_all_items, 407),
            (Self::cardano__choose_level_of_details, 431),
            (Self::cardano__collateral_input_id, 451),
            (Self::cardano__collateral_input_index, 474),
            (Self::cardano__collateral_output_contains_tokens, 519),
            (Self::cardano__collateral_return, 536),
            (Self::cardano__confirm_signing_stake_pool, 592),
            (Self::cardano__confirm_transaction, 611),
            (Self::cardano__confirming_a_multisig_transaction, 645),
            (Self::cardano__confirming_a_plutus_transaction, 677),
            (Self::cardano__confirming_pool_registration, 715),
            (Self::cardano__confirming_transction, 740),
            (Self::cardano__cost, 744),
            (Self::cardano__credential_mismatch, 788),
            (Self::cardano__datum_hash, 799),
            (Self::cardano__delegating_to, 813),
            (Self::cardano__for_account_and_index_template, 843),
            (Self::cardano__for_account_template, 859),
            (Self::cardano__for_key_hash, 872),
            (Self::cardano__for_script, 883),
            (Self::cardano__inline_datum, 895),
            (Self::cardano__input_id, 904),
            (Self::cardano__input_index, 916),
            (Self::cardano__intro_text_change, 962),
            (Self::cardano__intro_text_owned_by_device, 1012),
            (Self::cardano__intro_text_registration_payment, 1082),
            (Self::cardano__key_hash, 1090),
            (Self::cardano__margin, 1096),
            (Self::cardano__multisig_path, 1110),
            (Self::cardano__nested_scripts_template, 1138),
            (Self::cardano__network, 1146),
            (Self::cardano__no_output_tx, 1201),
            (Self::cardano__nonce, 1207),
            (Self::cardano__other, 1212),
            (Self::cardano__path, 1216),
            (Self::cardano__pledge, 1222),
            (Self::cardano__pointer, 1229),
            (Self::cardano__policy_id, 1238),
            (Self::cardano__pool_metadata_hash, 1257),
            (Self::cardano__pool_metadata_url, 1275),
            (Self::cardano__pool_owner, 1286),
            (Self::cardano__pool_reward_account, 1306),
            (Self::cardano__reference_input_id, 1325),
            (Self::cardano__reference_input_index, 1347),
            (Self::cardano__reference_script, 1363),
            (Self::cardano__required_signer, 1378),
            (Self::cardano__reward, 1384),
            (Self::cardano__reward_address, 1412),
            (Self::cardano__reward_eligibility_warning, 1490),
            (Self::cardano__rewards_go_to, 1504),
            (Self::cardano__script, 1510),
            (Self::cardano__script_all, 1513),
            (Self::cardano__script_any, 1516),
            (Self::cardano__script_data_hash, 1533),
            (Self::cardano__script_hash, 1545),
            (Self::cardano__script_invalid_before, 1559),
            (Self::cardano__script_invalid_hereafter, 1576),
            (Self::cardano__script_key, 1579),
            (Self::cardano__script_n_of_k, 1585),
            (Self::cardano__script_reward, 1598),
            (Self::cardano__sending, 1605),
            (Self::cardano__show_simple, 1616),
            (Self::cardano__sign_tx_path_template, 1641),
            (Self::cardano__stake_delegation, 1657),
            (Self::cardano__stake_deregistration, 1681),
            (Self::cardano__stake_pool_registration, 1703),
            (Self::cardano__stake_pool_registration_pool_id, 1735),
            (Self::cardano__stake_registration, 1757),
            (Self::cardano__staking_key_for_account, 1780),
            (Self::cardano__to_pool, 1788),
            (Self::cardano__token_minting_path, 1806),
            (Self::cardano__total_collateral, 1823),
            (Self::cardano__transaction, 1834),
            (Self::cardano__transaction_contains_minting_or_burning, 1888),
            (Self::cardano__transaction_contains_script_address_no_datum, 1977),
            (Self::cardano__transaction_fee, 1993),
            (Self::cardano__transaction_id, 2008),
            (Self::cardano__transaction_no_collateral_input, 2093),
            (Self::cardano__transaction_no_script_data_hash, 2177),
            (Self::cardano__transaction_output_contains_tokens, 2226),
            (Self::cardano__ttl, 2230),
            (Self::cardano__unknown_collateral_amount, 2256),
            (Self::cardano__unusual_path, 2272),
            (Self::cardano__valid_since, 2284),
            (Self::cardano__verify_script, 2297),
            (Self::cardano__vote_key_registration, 2327),
            (Self::cardano__vote_public_key, 2343),
            (Self::cardano__voting_purpose, 2358),
            (Self::cardano__warning, 2365),
            (Self::cardano__weight, 2372),
            (Self::cardano__withdrawal_for_address_template, 2407),
            (Self::cardano__x_of_y_signatures_template, 2442),
            (Self::eos__about_to_sign_template, 2468),
            (Self::eos__action_name, 2480),
            (Self::eos__arbitrary_data, 2494),
            (Self::eos__buy_ram, 2501),
            (Self::eos__bytes, 2507),
            (Self::eos__cancel_vote, 2518),
            (Self::eos__checksum, 2527),
            (Self::eos__code, 2532),
            (Self::eos__contract, 2541),
            (Self::eos__cpu, 2545),
            (Self::eos__creator, 2553),
            (Self::eos__delegate, 2561),
            (Self::eos__delete_auth, 2572),
            (Self::eos__from, 2577),
            (Self::eos__link_auth, 2586),
            (Self::eos__memo, 2590),
            (Self::eos__name, 2595),
            (Self::eos__net, 2599),
            (Self::eos__new_account, 2610),
            (Self::eos__owner, 2616),
            (Self::eos__parent, 2623),
            (Self::eos__payer, 2629),
            (Self::eos__permission, 2640),
            (Self::eos__proxy, 2646),
            (Self::eos__receiver, 2655),
            (Self::eos__refund, 2661),
            (Self::eos__requirement, 2673),
            (Self::eos__sell_ram, 2681),
            (Self::eos__sender, 2688),
            (Self::eos__threshold, 2698),
            (Self::eos__to, 2701),
            (Self::eos__transfer, 2710),
            (Self::eos__type, 2715),
            (Self::eos__undelegate, 2725),
            (Self::eos__unlink_auth, 2736),
            (Self::eos__update_auth, 2747),
            (Self::eos__vote_for_producers, 2765),
            (Self::eos__vote_for_proxy, 2779),
            (Self::eos__voter, 2785),
            (Self::ethereum__amount_sent, 2797),
            (Self::ethereum__contract, 2806),
            (Self::ethereum__data_size_template, 2821),
            (Self::ethereum__gas_limit, 2830),
            (Self::ethereum__gas_price, 2839),
            (Self::ethereum__max_gas_price, 2854),
            (Self::ethereum__name_and_version, 2870),
            (Self::ethereum__new_contract, 2899),
            (Self::ethereum__no_message_field, 2915),
            (Self::ethereum__priority_fee, 2931),
            (Self::ethereum__show_full_array, 2946),
            (Self::ethereum__show_full_domain, 2962),
            (Self::ethereum__show_full_message, 2979),
            (Self::ethereum__show_full_struct, 2995),
            (Self::ethereum__sign_eip712, 3026),
            (Self::ethereum__title_input_data, 3036),
            (Self::ethereum__title_confirm_domain, 3050),
            (Self::ethereum__title_confirm_message, 3065),
            (Self::ethereum__title_confirm_struct, 3079),
            (Self::ethereum__title_confirm_typed_data, 3097),
            (Self::ethereum__title_signing_address, 3112),
            (Self::ethereum__units_template, 3121),
            (Self::ethereum__unknown_token, 3134),
            (Self::ethereum__valid_signature, 3157),
            (Self::fido__already_registered, 3175),
            (Self::fido__device_already_registered, 3231),
            (Self::fido__device_already_registered_with_template, 3274),
            (Self::fido__device_not_registered, 3326),
            (Self::fido__does_not_belong, 3404),
            (Self::fido__erase_credentials, 3426),
            (Self::fido__export_credentials, 3489),
            (Self::fido__not_registered, 3503),
            (Self::fido__not_registered_with_template, 3542),
            (Self::fido__please_enable_pin_protection, 3571),
            (Self::fido__title_authenticate, 3589),
            (Self::fido__title_import_credential, 3606),
            (Self::fido__title_list_credentials, 3622),
            (Self::fido__title_register, 3636),
            (Self::fido__title_remove_credential, 3653),
            (Self::fido__title_reset, 3664),
            (Self::fido__title_u2f_auth, 3680),
            (Self::fido__title_u2f_register, 3692),
            (Self::fido__title_verify_user, 3709),
            (Self::fido__unable_to_verify_user, 3731),
            (Self::fido__wanna_erase_credentials, 3775),
            (Self::monero__confirm_export, 3789),
            (Self::monero__confirm_ki_sync, 3804),
            (Self::monero__confirm_refresh, 3819),
            (Self::monero__confirm_unlock_time, 3838),
            (Self::monero__hashing_inputs, 3852),
            (Self::monero__payment_id, 3862),
            (Self::monero__postprocessing, 3879),
            (Self::monero__processing, 3892),
            (Self::monero__processing_inputs, 3909),
            (Self::monero__processing_outputs, 3927),
            (Self::monero__signing, 3937),
            (Self::monero__signing_inputs, 3951),
            (Self::monero__unlock_time_set_template, 3997),
            (Self::monero__wanna_export_tx_der, 4046),
            (Self::monero__wanna_export_tx_key, 4082),
            (Self::monero__wanna_export_watchkey, 4134),
            (Self::monero__wanna_start_refresh, 4170),
            (Self::monero__wanna_sync_key_images, 4208),
            (Self::nem__absolute, 4216),
            (Self::nem__activate, 4224),
            (Self::nem__add, 4227),
            (Self::nem__confirm_action, 4241),
            (Self::nem__confirm_address, 4256),
            (Self::nem__confirm_creation_fee, 4276),
            (Self::nem__confirm_mosaic, 4290),
            (Self::nem__confirm_multisig_fee, 4310),
            (Self::nem__confirm_namespace, 4327),
            (Self::nem__confirm_payload, 4342),
            (Self::nem__confirm_properties, 4360),
            (Self::nem__confirm_rental_fee, 4378),
            (Self::nem__confirm_transfer_of, 4397),
            (Self::nem__convert_account_to_multisig, 4433),
            (Self::nem__cosign_transaction_for, 4455),
            (Self::nem__cosignatory, 4467),
            (Self::nem__create_mosaic, 4480),
            (Self::nem__create_namespace, 4496),
            (Self::nem__deactivate, 4506),
            (Self::nem__decrease, 4514),
            (Self::nem__description, 4526),
            (Self::nem__divisibility_and_levy_cannot_be_shown, 4583),
            (Self::nem__encrypted, 4592),
            (Self::nem__final_confirm, 4605),
            (Self::nem__immutable, 4614),
            (Self::nem__increase, 4622),
            (Self::nem__initial_supply, 4637),
            (Self::nem__initiate_transaction_for, 4661),
            (Self::nem__levy_divisibility, 4679),
            (Self::nem__levy_fee, 4688),
            (Self::nem__levy_fee_of, 4714),
            (Self::nem__levy_mosaic, 4726),
            (Self::nem__levy_namespace, 4741),
            (Self::nem__levy_recipient, 4756),
            (Self::nem__levy_type, 4766),
            (Self::nem__modify_supply_for, 4783),
            (Self::nem__modify_the_number_of_cosignatories_by, 4821),
            (Self::nem__mutable, 4828),
            (Self::nem__of, 4830),
            (Self::nem__percentile, 4840),
            (Self::nem__raw_units_template, 4853),
            (Self::nem__remote_harvesting, 4872),
            (Self::nem__remove, 4878),
            (Self::nem__set_minimum_cosignatories_to, 4907),
            (Self::nem__sign_tx_fee_template, 4957),
            (Self::nem__supply_change, 4970),
            (Self::nem__supply_units_template, 5000),
            (Self::nem__transferable, 5013),
            (Self::nem__under_namespace, 5028),
            (Self::nem__unencrypted, 5039),
            (Self::nem__unknown_mosaic, 5054),
            (Self::ripple__confirm_tag, 5065),
            (Self::ripple__destination_tag_template, 5085),
            (Self::solana__account_index, 5098),
            (Self::solana__associated_token_account, 5122),
            (Self::solana__confirm_multisig, 5138),
            (Self::solana__expected_fee, 5150),
            (Self::solana__instruction_accounts_template, 5215),
            (Self::solana__instruction_data, 5231),
            (Self::solana__instruction_is_multisig, 5283),
            (Self::solana__is_provided_via_lookup_table_template, 5318),
            (Self::solana__lookup_table_address, 5338),
            (Self::solana__multiple_signers, 5354),
            (Self::solana__title_token, 5359),
            (Self::solana__transaction_contains_unknown_instructions, 5401),
            (Self::solana__transaction_requires_x_signers_template, 5458),
            (Self::stellar__account_merge, 5471),
            (Self::stellar__account_thresholds, 5489),
            (Self::stellar__add_signer, 5499),
            (Self::stellar__add_trust, 5508),
            (Self::stellar__all_will_be_sent_to, 5531),
            (Self::stellar__allow_trust, 5542),
            (Self::stellar__asset, 5547),
            (Self::stellar__balance_id, 5557),
            (Self::stellar__bump_sequence, 5570),
            (Self::stellar__buying, 5577),
            (Self::stellar__claim_claimable_balance, 5600),
            (Self::stellar__clear_data, 5610),
            (Self::stellar__clear_flags, 5621),
            (Self::stellar__confirm_issuer, 5635),
            (Self::stellar__confirm_memo, 5647),
            (Self::stellar__confirm_network, 5662),
            (Self::stellar__confirm_operation, 5679),
            (Self::stellar__confirm_stellar, 5694),
            (Self::stellar__confirm_timebounds, 5712),
            (Self::stellar__create_account, 5726),
            (Self::stellar__debited_amount, 5740),
            (Self::stellar__delete, 5746),
            (Self::stellar__delete_passive_offer, 5766),
            (Self::stellar__delete_trust, 5778),
            (Self::stellar__destination, 5789),
            (Self::stellar__exchanges_require_memo, 5845),
            (Self::stellar__final_confirm, 5858),
            (Self::stellar__hash, 5862),
            (Self::stellar__high, 5867),
            (Self::stellar__home_domain, 5878),
            (Self::stellar__inflation, 5887),
            (Self::stellar__initial_balance, 5902),
            (Self::stellar__initialize_signing_with, 5925),
            (Self::stellar__issuer_template, 5935),
            (Self::stellar__key, 5939),
            (Self::stellar__limit, 5944),
            (Self::stellar__low, 5948),
            (Self::stellar__master_weight, 5962),
            (Self::stellar__medium, 5969),
            (Self::stellar__new_offer, 5978),
            (Self::stellar__new_passive_offer, 5995),
            (Self::stellar__no_memo_set, 6007),
            (Self::stellar__no_restriction, 6023),
            (Self::stellar__on_network_template, 6044),
            (Self::stellar__path_pay, 6052),
            (Self::stellar__path_pay_at_least, 6069),
            (Self::stellar__pay, 6072),
            (Self::stellar__pay_at_most, 6083),
            (Self::stellar__preauth_transaction, 6103),
            (Self::stellar__price_per_template, 6117),
            (Self::stellar__private_network, 6132),
            (Self::stellar__remove_signer, 6145),
            (Self::stellar__revoke_trust, 6157),
            (Self::stellar__selling, 6165),
            (Self::stellar__set_data, 6173),
            (Self::stellar__set_flags, 6182),
            (Self::stellar__set_sequence_to_template, 6202),
            (Self::stellar__sign_tx_count_template, 6238),
            (Self::stellar__sign_tx_fee_template, 6258),
            (Self::stellar__source_account, 6272),
            (Self::stellar__testnet_network, 6287),
            (Self::stellar__trusted_account, 6302),
            (Self::stellar__update, 6308),
            (Self::stellar__valid_from, 6324),
            (Self::stellar__valid_to, 6338),
            (Self::stellar__value_sha256, 6354),
            (Self::stellar__wanna_clean_value_key_template, 6389),
            (Self::stellar__your_account, 6402),
            (Self::tezos__baker_address, 6415),
            (Self::tezos__balance, 6423),
            (Self::tezos__ballot, 6430),
            (Self::tezos__confirm_delegation, 6448),
            (Self::tezos__confirm_origination, 6467),
            (Self::tezos__delegator, 6476),
            (Self::tezos__proposal, 6484),
            (Self::tezos__register_delegate, 6501),
            (Self::tezos__remove_delegation, 6518),
            (Self::tezos__submit_ballot, 6531),
            (Self::tezos__submit_proposal, 6546),
            (Self::tezos__submit_proposals, 6562),
            (Self::u2f__get, 6600),
            (Self::u2f__set_template, 6627),
            (Self::u2f__title_get, 6642),
            (Self::u2f__title_set, 6657),
            (Self::ethereum__staking_claim, 6662),
            (Self::ethereum__staking_claim_address, 6675),
            (Self::ethereum__staking_claim_intro, 6700),
            (Self::ethereum__staking_stake, 6705),
            (Self::ethereum__staking_stake_address, 6718),
            (Self::ethereum__staking_stake_intro, 6741),
            (Self::ethereum__staking_unstake, 6748),
            (Self::ethereum__staking_unstake_intro, 6775),
            (Self::cardano__always_abstain, 6789),
            (Self::cardano__always_no_confidence, 6809),
            (Self::cardano__delegating_to_key_hash, 6832),
            (Self::cardano__delegating_to_script, 6853),
            (Self::cardano__deposit, 6861),
            (Self::cardano__vote_delegation, 6876),
            (Self::fido__more_credentials, 6892),
            (Self::fido__select_intro, 6960),
            (Self::fido__title_for_authentication, 6978),
            (Self::fido__title_select_credential, 6995),
            (Self::fido__title_credential_details, 7013),
            (Self::ethereum__unknown_contract_address, 7084),
            (Self::ethereum__token_contract, 7098),
            (Self::ethereum__interaction_contract, 7118),
            (Self::ethereum__unknown_contract_address_short, 7143),
            (Self::solana__base_fee, 7151),
            (Self::solana__claim, 7156),
            (Self::solana__claim_question, 7185),
            (Self::solana__claim_recipient_warning, 7237),
            (Self::solana__priority_fee, 7249),
            (Self::solana__stake, 7254),
            (Self::solana__stake_account, 7267),
            (Self::solana__stake_provider, 7275),
            (Self::solana__stake_question, 7285),
            (Self::solana__stake_withdrawal_warning, 7345),
            (Self::solana__stake_withdrawal_warning_title, 7371),
            (Self::solana__unstake, 7378),
            (Self::solana__unstake_question, 7409),
            (Self::solana__vote_account, 7421),
            (Self::solana__stake_on_question, 7438),
            (Self::nostr__event_kind_template, 7453),
            (Self::solana__max_fees_rent, 7470),
            (Self::solana__max_rent_fee, 7482),
            (Self::solana__transaction_fee, 7497),
        ],
    };
    const DEBUG_BLOB: StringsBlob = StringsBlob {
        text: concat!(
            "Loading seed",
            "Loading private seed is not recommended.",
        ),
        offsets: &[
            (Self::debug__loading_seed, 12),
            (Self::debug__loading_seed_not_recommended, 52),
        ],
    };

    pub const BLOBS: &'static [StringsBlob] = &[
        Self::BTC_ONLY_BLOB,
        Self::ALTCOIN_BLOB,
        Self::DEBUG_BLOB,
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
        (Qstr::MP_QSTR_address__confirmed, Self::address__confirmed),
        (Qstr::MP_QSTR_address__public_key, Self::address__public_key),
        (Qstr::MP_QSTR_address__public_key_confirmed, Self::address__public_key_confirmed),
        (Qstr::MP_QSTR_address__qr_code, Self::address__qr_code),
        (Qstr::MP_QSTR_address__title_cosigner, Self::address__title_cosigner),
        (Qstr::MP_QSTR_address__title_receive_address, Self::address__title_receive_address),
        (Qstr::MP_QSTR_address__title_yours, Self::address__title_yours),
        (Qstr::MP_QSTR_address_details__account_info, Self::address_details__account_info),
        (Qstr::MP_QSTR_address_details__derivation_path, Self::address_details__derivation_path),
        (Qstr::MP_QSTR_address_details__derivation_path_colon, Self::address_details__derivation_path_colon),
        (Qstr::MP_QSTR_address_details__title_receive_address, Self::address_details__title_receive_address),
        (Qstr::MP_QSTR_address_details__title_receiving_to, Self::address_details__title_receiving_to),
        (Qstr::MP_QSTR_authenticate__confirm_template, Self::authenticate__confirm_template),
        (Qstr::MP_QSTR_authenticate__header, Self::authenticate__header),
        (Qstr::MP_QSTR_auto_lock__change_template, Self::auto_lock__change_template),
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
        (Qstr::MP_QSTR_backup__recover_anytime, Self::backup__recover_anytime),
        (Qstr::MP_QSTR_backup__title_backup_completed, Self::backup__title_backup_completed),
        (Qstr::MP_QSTR_backup__title_backup_wallet, Self::backup__title_backup_wallet),
        (Qstr::MP_QSTR_backup__title_create_wallet_backup, Self::backup__title_create_wallet_backup),
        (Qstr::MP_QSTR_backup__title_skip, Self::backup__title_skip),
        (Qstr::MP_QSTR_backup__want_to_skip, Self::backup__want_to_skip),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__buy, Self::binance__buy),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__confirm_cancel, Self::binance__confirm_cancel),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__confirm_input, Self::binance__confirm_input),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__confirm_order, Self::binance__confirm_order),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__confirm_output, Self::binance__confirm_output),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__order_id, Self::binance__order_id),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__pair, Self::binance__pair),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__price, Self::binance__price),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__quantity, Self::binance__quantity),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__sell, Self::binance__sell),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__sender_address, Self::binance__sender_address),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_binance__side, Self::binance__side),
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
        (Qstr::MP_QSTR_ble__unpair_all, Self::ble__unpair_all),
        (Qstr::MP_QSTR_ble__unpair_current, Self::ble__unpair_current),
        (Qstr::MP_QSTR_ble__unpair_title, Self::ble__unpair_title),
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
        (Qstr::MP_QSTR_cardano__confirming_transction, Self::cardano__confirming_transction),
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
        (Qstr::MP_QSTR_cardano__transaction_fee, Self::cardano__transaction_fee),
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
        (Qstr::MP_QSTR_coinjoin__title_do_not_disconnect, Self::coinjoin__title_do_not_disconnect),
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
        (Qstr::MP_QSTR_ethereum__contract, Self::ethereum__contract),
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
        (Qstr::MP_QSTR_ethereum__title_confirm_domain, Self::ethereum__title_confirm_domain),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_ethereum__title_confirm_message, Self::ethereum__title_confirm_message),
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
        (Qstr::MP_QSTR_ethereum__unknown_contract_address_short, Self::ethereum__unknown_contract_address_short),
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
        (Qstr::MP_QSTR_firmware_update__title, Self::firmware_update__title),
        (Qstr::MP_QSTR_firmware_update__title_fingerprint, Self::firmware_update__title_fingerprint),
        (Qstr::MP_QSTR_haptic_feedback__disable, Self::haptic_feedback__disable),
        (Qstr::MP_QSTR_haptic_feedback__enable, Self::haptic_feedback__enable),
        (Qstr::MP_QSTR_haptic_feedback__subtitle, Self::haptic_feedback__subtitle),
        (Qstr::MP_QSTR_haptic_feedback__title, Self::haptic_feedback__title),
        (Qstr::MP_QSTR_homescreen__click_to_connect, Self::homescreen__click_to_connect),
        (Qstr::MP_QSTR_homescreen__click_to_unlock, Self::homescreen__click_to_unlock),
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
        (Qstr::MP_QSTR_instructions__shares_continue_with_x_template, Self::instructions__shares_continue_with_x_template),
        (Qstr::MP_QSTR_instructions__shares_start_with_1, Self::instructions__shares_start_with_1),
        (Qstr::MP_QSTR_instructions__swipe_down, Self::instructions__swipe_down),
        (Qstr::MP_QSTR_instructions__swipe_horizontally, Self::instructions__swipe_horizontally),
        (Qstr::MP_QSTR_instructions__tap_to_confirm, Self::instructions__tap_to_confirm),
        (Qstr::MP_QSTR_instructions__tap_to_continue, Self::instructions__tap_to_continue),
        (Qstr::MP_QSTR_instructions__tap_to_start, Self::instructions__tap_to_start),
        (Qstr::MP_QSTR_instructions__view_all_data, Self::instructions__view_all_data),
        (Qstr::MP_QSTR_joint__title, Self::joint__title),
        (Qstr::MP_QSTR_joint__to_the_total_amount, Self::joint__to_the_total_amount),
        (Qstr::MP_QSTR_joint__you_are_contributing, Self::joint__you_are_contributing),
        (Qstr::MP_QSTR_language__change_to_template, Self::language__change_to_template),
        (Qstr::MP_QSTR_language__changed, Self::language__changed),
        (Qstr::MP_QSTR_language__progress, Self::language__progress),
        (Qstr::MP_QSTR_language__title, Self::language__title),
        (Qstr::MP_QSTR_lockscreen__tap_to_connect, Self::lockscreen__tap_to_connect),
        (Qstr::MP_QSTR_lockscreen__tap_to_unlock, Self::lockscreen__tap_to_unlock),
        (Qstr::MP_QSTR_lockscreen__title_locked, Self::lockscreen__title_locked),
        (Qstr::MP_QSTR_lockscreen__title_not_connected, Self::lockscreen__title_not_connected),
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
        (Qstr::MP_QSTR_passphrase__access_wallet, Self::passphrase__access_wallet),
        (Qstr::MP_QSTR_passphrase__always_on_device, Self::passphrase__always_on_device),
        (Qstr::MP_QSTR_passphrase__continue_with_empty_passphrase, Self::passphrase__continue_with_empty_passphrase),
        (Qstr::MP_QSTR_passphrase__from_host_not_shown, Self::passphrase__from_host_not_shown),
        (Qstr::MP_QSTR_passphrase__hide, Self::passphrase__hide),
        (Qstr::MP_QSTR_passphrase__next_screen_will_show_passphrase, Self::passphrase__next_screen_will_show_passphrase),
        (Qstr::MP_QSTR_passphrase__please_enter, Self::passphrase__please_enter),
        (Qstr::MP_QSTR_passphrase__revoke_on_device, Self::passphrase__revoke_on_device),
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
        (Qstr::MP_QSTR_pin__reenter_new, Self::pin__reenter_new),
        (Qstr::MP_QSTR_pin__reenter_to_confirm, Self::pin__reenter_to_confirm),
        (Qstr::MP_QSTR_pin__should_be_long, Self::pin__should_be_long),
        (Qstr::MP_QSTR_pin__title_check_pin, Self::pin__title_check_pin),
        (Qstr::MP_QSTR_pin__title_settings, Self::pin__title_settings),
        (Qstr::MP_QSTR_pin__title_wrong_pin, Self::pin__title_wrong_pin),
        (Qstr::MP_QSTR_pin__tries_left, Self::pin__tries_left),
        (Qstr::MP_QSTR_pin__turn_off, Self::pin__turn_off),
        (Qstr::MP_QSTR_pin__turn_on, Self::pin__turn_on),
        (Qstr::MP_QSTR_pin__wrong_pin, Self::pin__wrong_pin),
        (Qstr::MP_QSTR_plurals__contains_x_keys, Self::plurals__contains_x_keys),
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
        (Qstr::MP_QSTR_recovery__share_num_template, Self::recovery__share_num_template),
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
        (Qstr::MP_QSTR_reset__recovery_share_title_template, Self::reset__recovery_share_title_template),
        (Qstr::MP_QSTR_reset__recovery_wallet_backup_title, Self::reset__recovery_wallet_backup_title),
        (Qstr::MP_QSTR_reset__repeat_for_all_shares, Self::reset__repeat_for_all_shares),
        (Qstr::MP_QSTR_reset__required_number_of_groups, Self::reset__required_number_of_groups),
        (Qstr::MP_QSTR_reset__select_correct_word, Self::reset__select_correct_word),
        (Qstr::MP_QSTR_reset__select_threshold, Self::reset__select_threshold),
        (Qstr::MP_QSTR_reset__select_word_template, Self::reset__select_word_template),
        (Qstr::MP_QSTR_reset__select_word_x_of_y_template, Self::reset__select_word_x_of_y_template),
        (Qstr::MP_QSTR_reset__set_it_to_count_template, Self::reset__set_it_to_count_template),
        (Qstr::MP_QSTR_reset__share_checked_successfully_template, Self::reset__share_checked_successfully_template),
        (Qstr::MP_QSTR_reset__share_completed_template, Self::reset__share_completed_template),
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
        (Qstr::MP_QSTR_send__address_path, Self::send__address_path),
        (Qstr::MP_QSTR_send__cancel_sign, Self::send__cancel_sign),
        (Qstr::MP_QSTR_send__confirm_sending, Self::send__confirm_sending),
        (Qstr::MP_QSTR_send__from_multiple_accounts, Self::send__from_multiple_accounts),
        (Qstr::MP_QSTR_send__incl_transaction_fee, Self::send__incl_transaction_fee),
        (Qstr::MP_QSTR_send__including_fee, Self::send__including_fee),
        (Qstr::MP_QSTR_send__maximum_fee, Self::send__maximum_fee),
        (Qstr::MP_QSTR_send__receiving_to_multisig, Self::send__receiving_to_multisig),
        (Qstr::MP_QSTR_send__send_from, Self::send__send_from),
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
        (Qstr::MP_QSTR_solana__stake_provider, Self::solana__stake_provider),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_question, Self::solana__stake_question),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_withdrawal_warning, Self::solana__stake_withdrawal_warning),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__stake_withdrawal_warning_title, Self::solana__stake_withdrawal_warning_title),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__title_token, Self::solana__title_token),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__transaction_contains_unknown_instructions, Self::solana__transaction_contains_unknown_instructions),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__transaction_fee, Self::solana__transaction_fee),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_solana__transaction_requires_x_signers_template, Self::solana__transaction_requires_x_signers_template),
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
        (Qstr::MP_QSTR_stellar__asset, Self::stellar__asset),
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
        (Qstr::MP_QSTR_stellar__confirm_network, Self::stellar__confirm_network),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__confirm_operation, Self::stellar__confirm_operation),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__confirm_stellar, Self::stellar__confirm_stellar),
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
        (Qstr::MP_QSTR_stellar__initial_balance, Self::stellar__initial_balance),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__initialize_signing_with, Self::stellar__initialize_signing_with),
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
        (Qstr::MP_QSTR_stellar__on_network_template, Self::stellar__on_network_template),
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
        (Qstr::MP_QSTR_stellar__private_network, Self::stellar__private_network),
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
        (Qstr::MP_QSTR_stellar__source_account, Self::stellar__source_account),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__testnet_network, Self::stellar__testnet_network),
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
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_stellar__your_account, Self::stellar__your_account),
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
        (Qstr::MP_QSTR_tutorial__continue, Self::tutorial__continue),
        (Qstr::MP_QSTR_tutorial__did_you_know, Self::tutorial__did_you_know),
        (Qstr::MP_QSTR_tutorial__exit, Self::tutorial__exit),
        (Qstr::MP_QSTR_tutorial__first_wallet, Self::tutorial__first_wallet),
        (Qstr::MP_QSTR_tutorial__get_started, Self::tutorial__get_started),
        (Qstr::MP_QSTR_tutorial__lets_begin, Self::tutorial__lets_begin),
        (Qstr::MP_QSTR_tutorial__menu, Self::tutorial__menu),
        (Qstr::MP_QSTR_tutorial__middle_click, Self::tutorial__middle_click),
        (Qstr::MP_QSTR_tutorial__press_and_hold, Self::tutorial__press_and_hold),
        (Qstr::MP_QSTR_tutorial__ready_to_use, Self::tutorial__ready_to_use),
        (Qstr::MP_QSTR_tutorial__ready_to_use_safe5, Self::tutorial__ready_to_use_safe5),
        (Qstr::MP_QSTR_tutorial__restart_tutorial, Self::tutorial__restart_tutorial),
        (Qstr::MP_QSTR_tutorial__scroll_down, Self::tutorial__scroll_down),
        (Qstr::MP_QSTR_tutorial__sure_you_want_skip, Self::tutorial__sure_you_want_skip),
        (Qstr::MP_QSTR_tutorial__swipe_up_and_down, Self::tutorial__swipe_up_and_down),
        (Qstr::MP_QSTR_tutorial__title_easy_navigation, Self::tutorial__title_easy_navigation),
        (Qstr::MP_QSTR_tutorial__title_handy_menu, Self::tutorial__title_handy_menu),
        (Qstr::MP_QSTR_tutorial__title_hello, Self::tutorial__title_hello),
        (Qstr::MP_QSTR_tutorial__title_hold, Self::tutorial__title_hold),
        (Qstr::MP_QSTR_tutorial__title_lets_begin, Self::tutorial__title_lets_begin),
        (Qstr::MP_QSTR_tutorial__title_screen_scroll, Self::tutorial__title_screen_scroll),
        (Qstr::MP_QSTR_tutorial__title_skip, Self::tutorial__title_skip),
        (Qstr::MP_QSTR_tutorial__title_tutorial_complete, Self::tutorial__title_tutorial_complete),
        (Qstr::MP_QSTR_tutorial__title_well_done, Self::tutorial__title_well_done),
        (Qstr::MP_QSTR_tutorial__use_trezor, Self::tutorial__use_trezor),
        (Qstr::MP_QSTR_tutorial__welcome_press_right, Self::tutorial__welcome_press_right),
        (Qstr::MP_QSTR_tutorial__welcome_safe5, Self::tutorial__welcome_safe5),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__get, Self::u2f__get),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__set_template, Self::u2f__set_template),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__title_get, Self::u2f__title_get),
        #[cfg(feature = "universal_fw")]
        (Qstr::MP_QSTR_u2f__title_set, Self::u2f__title_set),
        (Qstr::MP_QSTR_wipe__info, Self::wipe__info),
        (Qstr::MP_QSTR_wipe__title, Self::wipe__title),
        (Qstr::MP_QSTR_wipe__want_to_wipe, Self::wipe__want_to_wipe),
        (Qstr::MP_QSTR_wipe_code__change, Self::wipe_code__change),
        (Qstr::MP_QSTR_wipe_code__changed, Self::wipe_code__changed),
        (Qstr::MP_QSTR_wipe_code__diff_from_pin, Self::wipe_code__diff_from_pin),
        (Qstr::MP_QSTR_wipe_code__disabled, Self::wipe_code__disabled),
        (Qstr::MP_QSTR_wipe_code__enabled, Self::wipe_code__enabled),
        (Qstr::MP_QSTR_wipe_code__enter_new, Self::wipe_code__enter_new),
        (Qstr::MP_QSTR_wipe_code__info, Self::wipe_code__info),
        (Qstr::MP_QSTR_wipe_code__invalid, Self::wipe_code__invalid),
        (Qstr::MP_QSTR_wipe_code__mismatch, Self::wipe_code__mismatch),
        (Qstr::MP_QSTR_wipe_code__reenter, Self::wipe_code__reenter),
        (Qstr::MP_QSTR_wipe_code__reenter_to_confirm, Self::wipe_code__reenter_to_confirm),
        (Qstr::MP_QSTR_wipe_code__title_check, Self::wipe_code__title_check),
        (Qstr::MP_QSTR_wipe_code__title_invalid, Self::wipe_code__title_invalid),
        (Qstr::MP_QSTR_wipe_code__title_settings, Self::wipe_code__title_settings),
        (Qstr::MP_QSTR_wipe_code__turn_off, Self::wipe_code__turn_off),
        (Qstr::MP_QSTR_wipe_code__turn_on, Self::wipe_code__turn_on),
        (Qstr::MP_QSTR_wipe_code__wipe_code_mismatch, Self::wipe_code__wipe_code_mismatch),
        (Qstr::MP_QSTR_word_count__title, Self::word_count__title),
        (Qstr::MP_QSTR_words__account, Self::words__account),
        (Qstr::MP_QSTR_words__account_colon, Self::words__account_colon),
        (Qstr::MP_QSTR_words__address, Self::words__address),
        (Qstr::MP_QSTR_words__amount, Self::words__amount),
        (Qstr::MP_QSTR_words__are_you_sure, Self::words__are_you_sure),
        (Qstr::MP_QSTR_words__array_of, Self::words__array_of),
        (Qstr::MP_QSTR_words__blockhash, Self::words__blockhash),
        (Qstr::MP_QSTR_words__buying, Self::words__buying),
        (Qstr::MP_QSTR_words__cancel_and_exit, Self::words__cancel_and_exit),
        (Qstr::MP_QSTR_words__confirm, Self::words__confirm),
        (Qstr::MP_QSTR_words__confirm_fee, Self::words__confirm_fee),
        (Qstr::MP_QSTR_words__contains, Self::words__contains),
        (Qstr::MP_QSTR_words__continue_anyway, Self::words__continue_anyway),
        (Qstr::MP_QSTR_words__continue_anyway_question, Self::words__continue_anyway_question),
        (Qstr::MP_QSTR_words__continue_with, Self::words__continue_with),
        (Qstr::MP_QSTR_words__error, Self::words__error),
        (Qstr::MP_QSTR_words__fee, Self::words__fee),
        (Qstr::MP_QSTR_words__from, Self::words__from),
        (Qstr::MP_QSTR_words__good_to_know, Self::words__good_to_know),
        (Qstr::MP_QSTR_words__important, Self::words__important),
        (Qstr::MP_QSTR_words__instructions, Self::words__instructions),
        (Qstr::MP_QSTR_words__keep_it_safe, Self::words__keep_it_safe),
        (Qstr::MP_QSTR_words__know_what_your_doing, Self::words__know_what_your_doing),
        (Qstr::MP_QSTR_words__my_trezor, Self::words__my_trezor),
        (Qstr::MP_QSTR_words__no, Self::words__no),
        (Qstr::MP_QSTR_words__not_recommended, Self::words__not_recommended),
        (Qstr::MP_QSTR_words__operation_cancelled, Self::words__operation_cancelled),
        (Qstr::MP_QSTR_words__outputs, Self::words__outputs),
        (Qstr::MP_QSTR_words__please_check_again, Self::words__please_check_again),
        (Qstr::MP_QSTR_words__please_try_again, Self::words__please_try_again),
        (Qstr::MP_QSTR_words__really_wanna, Self::words__really_wanna),
        (Qstr::MP_QSTR_words__recipient, Self::words__recipient),
        (Qstr::MP_QSTR_words__settings, Self::words__settings),
        (Qstr::MP_QSTR_words__sign, Self::words__sign),
        (Qstr::MP_QSTR_words__signer, Self::words__signer),
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
        (Qstr::MP_QSTR_words__try_again, Self::words__try_again),
        (Qstr::MP_QSTR_words__unknown, Self::words__unknown),
        (Qstr::MP_QSTR_words__unlocked, Self::words__unlocked),
        (Qstr::MP_QSTR_words__warning, Self::words__warning),
        (Qstr::MP_QSTR_words__writable, Self::words__writable),
        (Qstr::MP_QSTR_words__yes, Self::words__yes),
    ];
}
