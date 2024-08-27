//! Logic to handle the sign_tx command flow.

use crate::{
    client::*,
    error::{Error, Result},
    protos::{
        self,
        tx_ack::{
            transaction_type::{TxOutputBinType, TxOutputType},
            TransactionType,
        },
    },
    utils,
};
use bitcoin::{hashes::sha256d, psbt, Network, Transaction};
use protos::{
    tx_ack::transaction_type::TxInputType, tx_request::RequestType as TxRequestType,
    InputScriptType, OutputScriptType,
};
use tracing::trace;

/// Fulfill a TxRequest for TXINPUT.
fn ack_input_request(req: &protos::TxRequest, psbt: &psbt::Psbt) -> Result<protos::TxAck> {
    if req.details.is_none() || !req.details.has_request_index() {
        return Err(Error::MalformedTxRequest(req.clone()));
    }

    // Choose either the tx we are signing or a dependent tx.
    let input_index = req.details.request_index() as usize;
    let input = if req.details.has_tx_hash() {
        let req_hash: sha256d::Hash = utils::from_rev_bytes(req.details.tx_hash())
            .ok_or_else(|| Error::MalformedTxRequest(req.clone()))?;
        trace!("Preparing ack for input {}:{}", req_hash, input_index);
        let inp = utils::psbt_find_input(psbt, req_hash)?;
        let tx = inp.non_witness_utxo.as_ref().ok_or(Error::PsbtMissingInputTx(req_hash))?;
        let opt = &tx.input.get(input_index);
        opt.ok_or_else(|| Error::TxRequestInvalidIndex(input_index))?
    } else {
        trace!("Preparing ack for tx input #{}", input_index);
        let opt = &psbt.unsigned_tx.input.get(input_index);
        opt.ok_or(Error::TxRequestInvalidIndex(input_index))?
    };

    let mut data_input = TxInputType::new();
    data_input
        .set_prev_hash(utils::to_rev_bytes(input.previous_output.txid.as_raw_hash()).to_vec());
    data_input.set_prev_index(input.previous_output.vout);
    data_input.set_script_sig(input.script_sig.to_bytes());
    data_input.set_sequence(input.sequence.to_consensus_u32());

    // Extra data only for currently signing tx.
    if !req.details.has_tx_hash() {
        let psbt_input = psbt
            .inputs
            .get(input_index)
            .ok_or_else(|| Error::InvalidPsbt("not enough psbt inputs".to_owned()))?;

        // Get the output we are spending from the PSBT input.
        let txout = if let Some(ref txout) = psbt_input.witness_utxo {
            txout
        } else if let Some(ref tx) = psbt_input.non_witness_utxo {
            tx.output.get(input.previous_output.vout as usize).ok_or_else(|| {
                Error::InvalidPsbt(format!("invalid utxo for PSBT input {}", input_index))
            })?
        } else {
            return Err(Error::InvalidPsbt(format!("no utxo for PSBT input {}", input_index)));
        };

        // If there is exactly 1 HD keypath known, we can provide it.  If more it's multisig.
        if psbt_input.bip32_derivation.len() == 1 {
            let (_, (_, path)) = psbt_input.bip32_derivation.iter().next().unwrap();
            data_input.address_n = path.as_ref().iter().map(|i| (*i).into()).collect();
        }

        // Since we know the keypath, we probably have to sign it.  So update script_type.
        let script_type = {
            let script_pubkey = &txout.script_pubkey;

            if script_pubkey.is_p2pkh() {
                InputScriptType::SPENDADDRESS
            } else if script_pubkey.is_p2wpkh() || script_pubkey.is_p2wsh() {
                InputScriptType::SPENDWITNESS
            } else if script_pubkey.is_p2sh() && psbt_input.witness_script.is_some() {
                InputScriptType::SPENDP2SHWITNESS
            } else {
                //TODO(stevenroose) normal p2sh is probably multisig
                InputScriptType::EXTERNAL
            }
        };
        data_input.set_script_type(script_type);
        //TODO(stevenroose) multisig

        data_input.set_amount(txout.value.to_sat());
    }

    trace!("Prepared input to ack: {:?}", data_input);
    let mut txdata = TransactionType::new();
    txdata.inputs.push(data_input);
    let mut msg = protos::TxAck::new();
    msg.tx = protobuf::MessageField::some(txdata);
    Ok(msg)
}

/// Fulfill a TxRequest for TXOUTPUT.
fn ack_output_request(
    req: &protos::TxRequest,
    psbt: &psbt::Psbt,
    network: Network,
) -> Result<protos::TxAck> {
    if req.details.is_none() || !req.details.has_request_index() {
        return Err(Error::MalformedTxRequest(req.clone()));
    }

    // For outputs, the Trezor only needs bin_outputs to be set for dependent txs and full outputs
    // for the signing tx.
    let mut txdata = TransactionType::new();
    if req.details.has_tx_hash() {
        // Dependent tx, take the output from the PSBT and just create bin_output.
        let output_index = req.details.request_index() as usize;
        let req_hash: sha256d::Hash = utils::from_rev_bytes(req.details.tx_hash())
            .ok_or_else(|| Error::MalformedTxRequest(req.clone()))?;
        trace!("Preparing ack for output {}:{}", req_hash, output_index);
        let inp = utils::psbt_find_input(psbt, req_hash)?;
        let output = if let Some(ref tx) = inp.non_witness_utxo {
            let opt = &tx.output.get(output_index);
            opt.ok_or_else(|| Error::TxRequestInvalidIndex(output_index))?
        } else if let Some(ref utxo) = inp.witness_utxo {
            utxo
        } else {
            return Err(Error::InvalidPsbt("not all inputs have utxo data".to_owned()));
        };

        let mut bin_output = TxOutputBinType::new();
        bin_output.set_amount(output.value.to_sat());
        bin_output.set_script_pubkey(output.script_pubkey.to_bytes());

        trace!("Prepared bin_output to ack: {:?}", bin_output);
        txdata.bin_outputs.push(bin_output);
    } else {
        // Signing tx, we need to fill the full output meta object.
        let output_index = req.details.request_index() as usize;
        trace!("Preparing ack for tx output #{}", output_index);
        let opt = &psbt.unsigned_tx.output.get(output_index);
        let output = opt.ok_or(Error::TxRequestInvalidIndex(output_index))?;

        let mut data_output = TxOutputType::new();
        data_output.set_amount(output.value.to_sat());
        // Set script type to PAYTOADDRESS unless we find out otherwise from the PSBT.
        data_output.set_script_type(OutputScriptType::PAYTOADDRESS);
        if let Some(addr) = utils::address_from_script(&output.script_pubkey, network) {
            data_output.set_address(addr.to_string());
        }

        let psbt_output = psbt
            .outputs
            .get(output_index)
            .ok_or_else(|| Error::InvalidPsbt("output indices don't match".to_owned()))?;
        if psbt_output.bip32_derivation.len() == 1 {
            let (_, (_, path)) = psbt_output.bip32_derivation.iter().next().unwrap();
            data_output.address_n = path.as_ref().iter().map(|i| (*i).into()).collect();

            // Since we know the keypath, it's probably a change output.  So update script_type.
            let script_pubkey = &psbt.unsigned_tx.output[output_index].script_pubkey;
            if script_pubkey.is_op_return() {
                data_output.set_script_type(OutputScriptType::PAYTOOPRETURN);
                data_output.set_op_return_data(script_pubkey.as_bytes()[1..].to_vec());
            } else if psbt_output.witness_script.is_some() {
                if psbt_output.redeem_script.is_some() {
                    data_output.set_script_type(OutputScriptType::PAYTOP2SHWITNESS);
                } else {
                    data_output.set_script_type(OutputScriptType::PAYTOWITNESS);
                }
            } else {
                data_output.set_script_type(OutputScriptType::PAYTOADDRESS);
            }
        }

        trace!("Prepared output to ack: {:?}", data_output);
        txdata.outputs.push(data_output);
    };

    let mut msg = protos::TxAck::new();
    msg.tx = protobuf::MessageField::some(txdata);
    Ok(msg)
}

/// Fulfill a TxRequest for TXMETA.
fn ack_meta_request(req: &protos::TxRequest, psbt: &psbt::Psbt) -> Result<protos::TxAck> {
    if req.details.is_none() {
        return Err(Error::MalformedTxRequest(req.clone()));
    }

    // Choose either the tx we are signing or a dependent tx.
    let tx: &Transaction = if req.details.has_tx_hash() {
        // dependeny tx, look for it in PSBT inputs
        let req_hash: sha256d::Hash = utils::from_rev_bytes(req.details.tx_hash())
            .ok_or_else(|| Error::MalformedTxRequest(req.clone()))?;
        trace!("Preparing ack for tx meta of {}", req_hash);
        let inp = utils::psbt_find_input(psbt, req_hash)?;
        inp.non_witness_utxo.as_ref().ok_or(Error::PsbtMissingInputTx(req_hash))?
    } else {
        // currently signing tx
        trace!("Preparing ack for tx meta of tx being signed");
        &psbt.unsigned_tx
    };

    let mut txdata = TransactionType::new();
    txdata.set_version(tx.version.0 as u32);
    txdata.set_lock_time(tx.lock_time.to_consensus_u32());
    txdata.set_inputs_cnt(tx.input.len() as u32);
    txdata.set_outputs_cnt(tx.output.len() as u32);
    //TODO(stevenroose) python does something with extra data?

    trace!("Prepared tx meta to ack: {:?}", txdata);
    let mut msg = protos::TxAck::new();
    msg.tx = protobuf::MessageField::some(txdata);
    Ok(msg)
}

/// Object to track the progress in the transaction signing flow.  The device will ask for various
/// parts of the transaction and dependent transactions and can at any point also ask for user
/// interaction.  The information asked for by the device is provided based on a PSBT object and the
/// resulting extra signatures are also added to the PSBT file.
///
/// It's important to always first check with the `finished()` method if more data is requested by
/// the device.  If you're not yet finished you must call the `ack_psbt()` method to send more
/// information to the device.
pub struct SignTxProgress<'a> {
    client: &'a mut Trezor,
    req: protos::TxRequest,
}

impl<'a> SignTxProgress<'a> {
    /// Only intended for internal usage.
    pub fn new(client: &mut Trezor, req: protos::TxRequest) -> SignTxProgress<'_> {
        SignTxProgress { client, req }
    }

    /// Inspector to the request message received from the device.
    pub fn tx_request(&self) -> &protos::TxRequest {
        &self.req
    }

    /// Check whether or not the signing process is finished.
    pub fn finished(&self) -> bool {
        self.req.request_type() == TxRequestType::TXFINISHED
    }

    /// Check if a signature is provided by the device.
    pub fn has_signature(&self) -> bool {
        let serialized = &self.req.serialized;
        serialized.is_some() && serialized.has_signature_index() && serialized.has_signature()
    }

    /// Get the signature provided from the device along with the input index of the signature.
    pub fn get_signature(&self) -> Option<(usize, &[u8])> {
        if self.has_signature() {
            let serialized = &self.req.serialized;
            Some((serialized.signature_index() as usize, serialized.signature()))
        } else {
            None
        }
    }

    //TODO(stevenroose) We used to have a method here `apply_signature(&mut psbt)` that would put
    // the received signature in the correct PSBT input.  However, since the signature is just a raw
    // signature instead of a scriptSig, this is harder.  It can be done, but then we'd have to have
    // the pubkey provided in the PSBT (possible thought HD path) and we'd have to do some Script
    // inspection to see if we should put it as a p2pkh sciptSig or witness data.

    /// Check if a part of the serialized signed tx is provided by the device.
    pub fn has_serialized_tx_part(&self) -> bool {
        let serialized = &self.req.serialized;
        serialized.is_some() && serialized.has_serialized_tx()
    }

    /// Get the part of the serialized signed tx from the device.
    pub fn get_serialized_tx_part(&self) -> Option<&[u8]> {
        if self.has_serialized_tx_part() {
            Some(self.req.serialized.serialized_tx())
        } else {
            None
        }
    }

    /// Manually provide a TxAck message to the device.
    ///
    /// This method will panic if `finished()` returned true,
    /// so it should always be checked in advance.
    pub fn ack_msg(
        self,
        ack: protos::TxAck,
    ) -> Result<TrezorResponse<'a, SignTxProgress<'a>, protos::TxRequest>> {
        assert!(!self.finished());

        self.client.call(ack, Box::new(|c, m| Ok(SignTxProgress::new(c, m))))
    }

    /// Provide additional PSBT information to the device.
    ///
    /// This method will panic if `apply()` returned true,
    /// so it should always be checked in advance.
    pub fn ack_psbt(
        self,
        psbt: &psbt::Psbt,
        network: Network,
    ) -> Result<TrezorResponse<'a, SignTxProgress<'a>, protos::TxRequest>> {
        assert!(self.req.request_type() != TxRequestType::TXFINISHED);

        let ack = match self.req.request_type() {
            TxRequestType::TXINPUT => ack_input_request(&self.req, psbt),
            TxRequestType::TXOUTPUT => ack_output_request(&self.req, psbt, network),
            TxRequestType::TXMETA => ack_meta_request(&self.req, psbt),
            TxRequestType::TXEXTRADATA => unimplemented!(), //TODO(stevenroose) implement
            TxRequestType::TXORIGINPUT |
            TxRequestType::TXORIGOUTPUT |
            TxRequestType::TXPAYMENTREQ => unimplemented!(),
            TxRequestType::TXFINISHED => unreachable!(),
        }?;
        self.ack_msg(ack)
    }
}
