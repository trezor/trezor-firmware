use super::{handle_interaction, ResultHandler, Trezor};
use crate::{
    error::Result,
    protos::{
        self, tron_raw_transaction::tron_raw_contract::TronRawContractType, TronRawTransaction,
    },
    Error,
};
use protobuf::Message;

/// A TRON contract attached to a [`Trezor::tron_sign_tx`] call.
///
/// Each variant wraps the corresponding protobuf message. The firmware only
/// supports transactions with a single contract.
#[derive(Debug, Clone, PartialEq)]
pub enum TronContract {
    Transfer(protos::TronTransferContract),
    TriggerSmart(protos::TronTriggerSmartContract),
    FreezeBalanceV2(protos::TronFreezeBalanceV2Contract),
    UnfreezeBalanceV2(protos::TronUnfreezeBalanceV2Contract),
    WithdrawUnfreeze(protos::TronWithdrawUnfreeze),
    WithdrawBalance(protos::TronWithdrawBalance),
    VoteWitness(protos::TronVoteWitnessContract),
    DelegateResource(protos::TronDelegateResourceContract),
    UnDelegateResource(protos::TronUnDelegateResourceContract),
}

/// Parse a serialized TRON raw transaction (as returned by e.g. TronGrid's
/// `raw_data_hex`) into a [`protos::TronSignTx`] header and the single
/// [`TronContract`] it carries.
pub fn tron_parse_raw_transaction(raw: &[u8]) -> Result<(protos::TronSignTx, TronContract)> {
    let raw_tx = TronRawTransaction::parse_from_bytes(raw)?;

    let mut tx = protos::TronSignTx::new();
    tx.set_ref_block_bytes(raw_tx.ref_block_bytes().to_vec());
    tx.set_ref_block_hash(raw_tx.ref_block_hash().to_vec());
    tx.set_expiration(raw_tx.expiration());
    tx.set_timestamp(raw_tx.timestamp());
    if raw_tx.has_data() {
        tx.set_data(raw_tx.data().to_vec());
    }
    if raw_tx.has_fee_limit() {
        tx.set_fee_limit(raw_tx.fee_limit());
    }

    if raw_tx.contract.len() != 1 {
        return Err(Error::InvalidTronTransaction(
            "only single contract transactions are supported".to_owned(),
        ));
    }

    let raw_contract = &raw_tx.contract[0];
    if raw_contract.parameter.is_none() {
        return Err(Error::InvalidTronTransaction("contract parameter is missing".to_owned()));
    }
    let value = raw_contract.parameter.value();

    let contract = match raw_contract.type_() {
        TronRawContractType::TransferContract => {
            TronContract::Transfer(protos::TronTransferContract::parse_from_bytes(value)?)
        }
        TronRawContractType::TriggerSmartContract => {
            TronContract::TriggerSmart(protos::TronTriggerSmartContract::parse_from_bytes(value)?)
        }
        TronRawContractType::FreezeBalanceV2Contract => TronContract::FreezeBalanceV2(
            protos::TronFreezeBalanceV2Contract::parse_from_bytes(value)?,
        ),
        TronRawContractType::UnfreezeBalanceV2Contract => TronContract::UnfreezeBalanceV2(
            protos::TronUnfreezeBalanceV2Contract::parse_from_bytes(value)?,
        ),
        TronRawContractType::WithdrawExpireUnfreezeContract => {
            TronContract::WithdrawUnfreeze(protos::TronWithdrawUnfreeze::parse_from_bytes(value)?)
        }
        TronRawContractType::WithdrawBalanceContract => {
            TronContract::WithdrawBalance(protos::TronWithdrawBalance::parse_from_bytes(value)?)
        }
        TronRawContractType::VoteWitnessContract => {
            TronContract::VoteWitness(protos::TronVoteWitnessContract::parse_from_bytes(value)?)
        }
        TronRawContractType::DelegateResourceContract => TronContract::DelegateResource(
            protos::TronDelegateResourceContract::parse_from_bytes(value)?,
        ),
        TronRawContractType::UnDelegateResourceContract => TronContract::UnDelegateResource(
            protos::TronUnDelegateResourceContract::parse_from_bytes(value)?,
        ),
    };

    Ok((tx, contract))
}

/// Result handler extracting the raw signature from a `TronSignature` response.
fn tron_signature_handler<'a>() -> Box<ResultHandler<'a, Vec<u8>, protos::TronSignature>> {
    Box::new(|_, m: protos::TronSignature| Ok(m.signature().to_vec()))
}

impl Trezor {
    /// Get the TRON address derived from the given BIP-32 path.
    pub fn tron_get_address(
        &mut self,
        path: Vec<u32>,
        show_display: bool,
        chunkify: bool,
    ) -> Result<String> {
        let mut req = protos::TronGetAddress::new();
        req.address_n = path;
        req.set_show_display(show_display);
        req.set_chunkify(chunkify);
        handle_interaction(
            self.call(req, Box::new(|_, m: protos::TronAddress| Ok(m.address().to_owned())))?,
        )
    }

    /// Sign a TRON transaction.
    ///
    /// The transaction header (`tx`) and the single `contract` can be obtained
    /// via [`tron_parse_raw_transaction`]. Returns the raw 65-byte signature.
    pub fn tron_sign_tx(
        &mut self,
        tx: protos::TronSignTx,
        contract: TronContract,
        path: Vec<u32>,
        chunkify: bool,
    ) -> Result<Vec<u8>> {
        let mut tx = tx;
        tx.address_n = path;
        tx.set_chunkify(chunkify);

        // The device acknowledges the header with a contract request, then waits
        // for the contract details before asking the user to confirm.
        handle_interaction(self.call(tx, Box::new(|_, _: protos::TronContractRequest| Ok(())))?)?;

        let resp = match contract {
            TronContract::Transfer(c) => self.call(c, tron_signature_handler())?,
            TronContract::TriggerSmart(c) => self.call(c, tron_signature_handler())?,
            TronContract::FreezeBalanceV2(c) => self.call(c, tron_signature_handler())?,
            TronContract::UnfreezeBalanceV2(c) => self.call(c, tron_signature_handler())?,
            TronContract::WithdrawUnfreeze(c) => self.call(c, tron_signature_handler())?,
            TronContract::WithdrawBalance(c) => self.call(c, tron_signature_handler())?,
            TronContract::VoteWitness(c) => self.call(c, tron_signature_handler())?,
            TronContract::DelegateResource(c) => self.call(c, tron_signature_handler())?,
            TronContract::UnDelegateResource(c) => self.call(c, tron_signature_handler())?,
        };

        handle_interaction(resp)
    }
}
