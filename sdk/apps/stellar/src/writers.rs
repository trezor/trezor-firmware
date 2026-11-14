//! XDR serialization of the Stellar structures the device signs.
//!
//! Everything is written through [`Writer`], so a transaction can be hashed as
//! it is serialized instead of being buffered in the (small) app heap.

use crate::{
    alloc_types::Vec,
    consts::SCSYMBOL_MAX_SIZE,
    helpers::{
        STRKEY_CLAIMABLE_BALANCE, STRKEY_CONTRACT, STRKEY_ED25519_PUBLIC_KEY,
        STRKEY_LIQUIDITY_POOL, STRKEY_MUXED_ACCOUNT, decode_strkey, public_key_from_address,
    },
    proto::stellar::{
        Asset, AssetType, ContractExecutable, ContractIdPreimage, CreateContractArgsV2,
        InvokeContractArgs, ScVal, SorobanAuthorizedFunction, SorobanAuthorizedInvocation,
        contract_executable::ContractExecutableType,
        contract_id_preimage::ContractIdPreimageType,
        sc_val::{Int128Parts, Int256Parts, ScValMapEntry, ScValType, UInt128Parts, UInt256Parts},
        soroban_authorized_function::SorobanAuthorizedFunctionType,
    },
};
use trezor_app_sdk::{Error, Result, ResultExt, crypto::BoxedHasher, crypto::HasherExt as _};

/// Sink the XDR is serialized into.
pub trait Writer {
    fn write(&mut self, data: &[u8]);
}

impl Writer for Vec<u8> {
    fn write(&mut self, data: &[u8]) {
        self.extend_from_slice(data);
    }
}

impl Writer for BoxedHasher {
    fn write(&mut self, data: &[u8]) {
        self.update(data);
    }
}

pub fn write_bytes_fixed(w: &mut dyn Writer, data: &[u8], len: usize) -> Result<()> {
    if data.len() != len {
        return Err(Error::DataError("Stellar: invalid fixed-size bytes length"));
    }
    w.write(data);
    Ok(())
}

pub fn write_uint32(w: &mut dyn Writer, value: u32) {
    w.write(&value.to_be_bytes());
}

pub fn write_uint64(w: &mut dyn Writer, value: u64) {
    w.write(&value.to_be_bytes());
}

pub fn write_int32(w: &mut dyn Writer, value: i32) {
    w.write(&value.to_be_bytes());
}

pub fn write_int64(w: &mut dyn Writer, value: i64) {
    w.write(&value.to_be_bytes());
}

/// Writes a non-negative signed amount as an unsigned 64-bit value.
pub fn write_amount(w: &mut dyn Writer, value: i64) -> Result<()> {
    let value = u64::try_from(value).map_err(|_| Error::DataError("Stellar: negative amount"))?;
    write_uint64(w, value);
    Ok(())
}

/// Writes an XDR string/opaque padded to a multiple of 4 bytes.
/// Returns the length written (without padding).
pub fn write_string(w: &mut dyn Writer, s: &[u8]) -> usize {
    write_uint32(w, s.len() as u32);
    w.write(s);
    // if len isn't a multiple of 4, add padding bytes
    let remainder = s.len() % 4;
    if remainder != 0 {
        w.write(&[0u8; 4][..4 - remainder]);
    }
    s.len()
}

pub fn write_bool(w: &mut dyn Writer, val: bool) {
    write_uint32(w, val as u32);
}

pub fn write_pubkey(w: &mut dyn Writer, address: &str) -> Result<()> {
    // first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0);
    w.write(&public_key_from_address(address).c()?);
    Ok(())
}

pub fn write_asset_code(
    w: &mut dyn Writer,
    asset_type: AssetType,
    asset_code: Option<&str>,
) -> Result<()> {
    let width = match asset_type {
        AssetType::Native => return Ok(()), // nothing is needed
        AssetType::Alphanum4 => 4,
        AssetType::Alphanum12 => 12,
    };
    let code = asset_code
        .ok_or(Error::DataError("Stellar: invalid asset"))?
        .as_bytes();
    if code.len() > width {
        return Err(Error::DataError(if width == 4 {
            "Stellar: asset code too long for ALPHANUM4"
        } else {
            "Stellar: asset code too long for ALPHANUM12"
        }));
    }
    // pad with zeros to the full width
    w.write(code);
    w.write(&[0u8; 12][..width - code.len()]);
    Ok(())
}

pub fn asset_type(value: i32) -> Result<AssetType> {
    AssetType::try_from(value).map_err(|_| Error::DataError("Stellar: invalid asset type"))
}

pub fn write_asset(w: &mut dyn Writer, asset: &Asset) -> Result<()> {
    let asset_type = asset_type(asset.r#type)?;
    if asset_type == AssetType::Native {
        write_uint32(w, 0);
        return Ok(());
    }
    let (Some(code), Some(issuer)) = (&asset.code, &asset.issuer) else {
        return Err(Error::DataError("Stellar: invalid asset"));
    };
    write_uint32(w, asset_type as u32);
    write_asset_code(w, asset_type, Some(code)).c()?;
    write_pubkey(w, issuer).c()
}

pub fn write_vec<T>(
    w: &mut dyn Writer,
    items: &[T],
    mut write_item: impl FnMut(&mut dyn Writer, &T) -> Result<()>,
) -> Result<()> {
    write_uint32(w, items.len() as u32);
    for item in items {
        write_item(w, item)?;
    }
    Ok(())
}

pub fn write_invoke_contract_args(w: &mut dyn Writer, msg: &InvokeContractArgs) -> Result<()> {
    write_sc_address(w, &msg.contract_address).c()?;
    write_sc_symbol(w, &msg.function_name).c()?;
    write_vec(w, &msg.args, |w, arg| write_sc_val(w, arg))
}

pub fn write_create_contract_args_v2(w: &mut dyn Writer, msg: &CreateContractArgsV2) -> Result<()> {
    write_contract_id_preimage(w, &msg.contract_id_preimage).c()?;
    write_contract_executable(w, &msg.executable).c()?;
    write_vec(w, &msg.constructor_args, |w, arg| write_sc_val(w, arg))
}

/// Writes what every HashIDPreimage variant starts with: its envelope type and
/// the ID of the network it is bound to.
pub fn write_hash_id_preimage_header(
    w: &mut dyn Writer,
    envelope_type: u32,
    network_id: &[u8; 32],
) {
    write_uint32(w, envelope_type);
    w.write(network_id);
}

/// Writes a ContractIDPreimage, of which only the address variant is supported.
pub fn write_contract_id_preimage(w: &mut dyn Writer, msg: &ContractIdPreimage) -> Result<()> {
    if ContractIdPreimageType::try_from(msg.r#type).ok()
        != Some(ContractIdPreimageType::ContractIdPreimageFromAddress)
    {
        return Err(Error::DataError(
            "Stellar: unsupported contract ID preimage type",
        ));
    }
    let from_address = msg
        .from_address
        .as_ref()
        .ok_or(Error::DataError("Stellar: missing from_address"))?;
    write_contract_id_preimage_from_address(w, &from_address.address, &from_address.salt)
}

/// Writes the CONTRACT_ID_PREIMAGE_FROM_ADDRESS variant of ContractIDPreimage.
pub fn write_contract_id_preimage_from_address(
    w: &mut dyn Writer,
    address: &str,
    salt: &[u8],
) -> Result<()> {
    if salt.len() != 32 {
        return Err(Error::DataError("Stellar: invalid salt length"));
    }
    write_uint32(w, 0); // CONTRACT_ID_PREIMAGE_FROM_ADDRESS
    write_sc_address(w, address).c()?;
    w.write(salt);
    Ok(())
}

/// Writes the CONTRACT_ID_PREIMAGE_FROM_ASSET variant of ContractIDPreimage.
///
/// Contracts are not created from it on the device; it only serves to derive
/// the address of an asset's Stellar Asset Contract.
pub fn write_contract_id_preimage_from_asset(w: &mut dyn Writer, asset: &Asset) -> Result<()> {
    write_uint32(w, 1); // CONTRACT_ID_PREIMAGE_FROM_ASSET
    write_asset(w, asset)
}

pub fn write_contract_executable(w: &mut dyn Writer, msg: &ContractExecutable) -> Result<()> {
    if ContractExecutableType::try_from(msg.r#type).ok()
        != Some(ContractExecutableType::ContractExecutableWasm)
    {
        return Err(Error::DataError(
            "Stellar: unsupported contract executable type",
        ));
    }
    let wasm_hash = msg
        .wasm_hash
        .as_ref()
        .ok_or(Error::DataError("Stellar: missing wasm_hash"))?;
    if wasm_hash.len() != 32 {
        return Err(Error::DataError("Stellar: invalid wasm_hash length"));
    }
    write_uint32(w, msg.r#type as u32);
    w.write(wasm_hash);
    Ok(())
}

pub fn write_sc_address(w: &mut dyn Writer, addr: &str) -> Result<()> {
    let (version, data) = decode_strkey(addr).c()?;

    match version {
        STRKEY_ED25519_PUBLIC_KEY => {
            // AccountID is a PublicKey: KEY_TYPE_ED25519 (0) + 32 bytes ed25519
            write_uint32(w, 0); // SC_ADDRESS_TYPE_ACCOUNT
            write_uint32(w, 0); // KEY_TYPE_ED25519
            w.write(&data);
        }
        STRKEY_CONTRACT => {
            // ContractID is a Hash (32 bytes)
            write_uint32(w, 1); // SC_ADDRESS_TYPE_CONTRACT
            w.write(&data);
        }
        STRKEY_MUXED_ACCOUNT => {
            // MuxedEd25519Account: { id: uint64, ed25519: uint256 }
            // address format: 32 bytes ed25519 + 8 bytes id
            write_uint32(w, 2); // SC_ADDRESS_TYPE_MUXED_ACCOUNT
            w.write(&data[32..40]); // id (uint64)
            w.write(&data[..32]); // ed25519
        }
        STRKEY_CLAIMABLE_BALANCE => {
            // ClaimableBalanceID: { type: uint32, v0: Hash }
            // address format: 1 byte type + 32 bytes hash (from strkey decoding);
            // decode_strkey has already checked that the type byte is v0
            write_uint32(w, 3); // SC_ADDRESS_TYPE_CLAIMABLE_BALANCE
            write_uint32(w, 0); // CLAIMABLE_BALANCE_ID_TYPE_V0
            w.write(&data[1..33]); // v0 hash
        }
        STRKEY_LIQUIDITY_POOL => {
            // PoolID is a Hash (32 bytes)
            write_uint32(w, 4); // SC_ADDRESS_TYPE_LIQUIDITY_POOL
            w.write(&data);
        }
        _ => return Err(Error::DataError("Stellar: unsupported SC address type")),
    }
    Ok(())
}

fn write_sc_symbol(w: &mut dyn Writer, symbol: &str) -> Result<()> {
    let written = write_string(w, symbol.as_bytes());
    if written > SCSYMBOL_MAX_SIZE {
        return Err(Error::DataError("Stellar: symbol too long"));
    }
    Ok(())
}

fn require<'a, T>(value: &'a Option<T>, msg: &'static str) -> Result<&'a T> {
    value.as_ref().ok_or(Error::DataError(msg))
}

pub fn write_sc_val(w: &mut dyn Writer, msg: &ScVal) -> Result<()> {
    let ty = ScValType::try_from(msg.r#type)
        .map_err(|_| Error::DataError("Stellar: unsupported SCVal type"))?;
    write_uint32(w, msg.r#type as u32);

    match ty {
        ScValType::ScvBool => write_bool(w, *require(&msg.b, "Stellar: missing bool value")?),
        ScValType::ScvVoid => {} // no data
        ScValType::ScvU32 => write_uint32(w, *require(&msg.u32, "Stellar: missing u32 value")?),
        ScValType::ScvI32 => write_int32(w, *require(&msg.i32, "Stellar: missing i32 value")?),
        ScValType::ScvU64 => write_uint64(w, *require(&msg.u64, "Stellar: missing u64 value")?),
        ScValType::ScvI64 => write_int64(w, *require(&msg.i64, "Stellar: missing i64 value")?),
        ScValType::ScvTimepoint => write_uint64(
            w,
            *require(&msg.timepoint, "Stellar: missing timepoint value")?,
        ),
        ScValType::ScvDuration => write_uint64(
            w,
            *require(&msg.duration, "Stellar: missing duration value")?,
        ),
        ScValType::ScvU128 => {
            write_uint128_parts(w, require(&msg.u128, "Stellar: missing u128 value")?)
        }
        ScValType::ScvI128 => {
            write_int128_parts(w, require(&msg.i128, "Stellar: missing i128 value")?)
        }
        ScValType::ScvU256 => {
            write_uint256_parts(w, require(&msg.u256, "Stellar: missing u256 value")?)
        }
        ScValType::ScvI256 => {
            write_int256_parts(w, require(&msg.i256, "Stellar: missing i256 value")?)
        }
        ScValType::ScvBytes => {
            write_string(w, require(&msg.bytes, "Stellar: missing bytes value")?);
        }
        ScValType::ScvString => {
            write_string(w, require(&msg.string, "Stellar: missing string value")?);
        }
        ScValType::ScvSymbol => {
            write_sc_symbol(w, require(&msg.symbol, "Stellar: missing symbol value")?).c()?
        }
        ScValType::ScvVec => {
            // In XDR the vector is a pointer (SCVec*), i.e. nullable, but a null vector
            // is not a valid Soroban value (only Some([...]), possibly empty). Here it
            // is a `repeated` field that is always a list, never None, so encoding it
            // as present is correct.
            write_bool(w, true); // present
            write_vec(w, &msg.vec, |w, item| write_sc_val(w, item)).c()?
        }
        ScValType::ScvMap => {
            // map is a pointer (SCMap*) in XDR; same reasoning as SCV_VEC above.
            write_bool(w, true); // present
            write_vec(w, &msg.map, |w, entry| write_sc_map_entry(w, entry)).c()?
        }
        ScValType::ScvAddress => {
            write_sc_address(w, require(&msg.address, "Stellar: missing address value")?).c()?
        }
    }
    Ok(())
}

fn write_sc_map_entry(w: &mut dyn Writer, entry: &ScValMapEntry) -> Result<()> {
    write_sc_val(w, &entry.key)?;
    write_sc_val(w, &entry.value)
}

fn write_uint128_parts(w: &mut dyn Writer, msg: &UInt128Parts) {
    write_uint64(w, msg.hi);
    write_uint64(w, msg.lo);
}

fn write_int128_parts(w: &mut dyn Writer, msg: &Int128Parts) {
    write_int64(w, msg.hi);
    write_uint64(w, msg.lo);
}

fn write_uint256_parts(w: &mut dyn Writer, msg: &UInt256Parts) {
    write_uint64(w, msg.hi_hi);
    write_uint64(w, msg.hi_lo);
    write_uint64(w, msg.lo_hi);
    write_uint64(w, msg.lo_lo);
}

fn write_int256_parts(w: &mut dyn Writer, msg: &Int256Parts) {
    write_int64(w, msg.hi_hi);
    write_uint64(w, msg.hi_lo);
    write_uint64(w, msg.lo_hi);
    write_uint64(w, msg.lo_lo);
}

pub fn write_soroban_authorized_invocation(
    w: &mut dyn Writer,
    msg: &SorobanAuthorizedInvocation,
) -> Result<()> {
    write_soroban_authorized_function(w, &msg.function)?;
    write_vec(w, &msg.sub_invocations, |w, inv| {
        write_soroban_authorized_invocation(w, inv)
    })
}

fn write_soroban_authorized_function(
    w: &mut dyn Writer,
    msg: &SorobanAuthorizedFunction,
) -> Result<()> {
    let ty = SorobanAuthorizedFunctionType::try_from(msg.r#type)
        .map_err(|_| Error::DataError("Stellar: unsupported authorized function type"))?;
    write_uint32(w, msg.r#type as u32);
    match ty {
        SorobanAuthorizedFunctionType::ContractFn => {
            let args = require(&msg.contract_fn, "Stellar: missing contract_fn")?;
            write_invoke_contract_args(w, args)
        }
        SorobanAuthorizedFunctionType::CreateContractV2HostFn => {
            let args = require(
                &msg.create_contract_v2_host_fn,
                "Stellar: missing create_contract_v2_host_fn",
            )?;
            write_create_contract_args_v2(w, args)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn string_is_padded_to_four_bytes() {
        let mut w = Vec::new();
        assert_eq!(write_string(&mut w, b"abcde"), 5);
        assert_eq!(w, [0, 0, 0, 5, b'a', b'b', b'c', b'd', b'e', 0, 0, 0]);
    }

    #[test]
    fn empty_string_has_no_padding() {
        let mut w = Vec::new();
        write_string(&mut w, b"");
        assert_eq!(w, [0, 0, 0, 0]);
    }

    #[test]
    fn integers_are_big_endian() {
        let mut w = Vec::new();
        write_uint32(&mut w, 0x0102_0304);
        write_int64(&mut w, -2);
        assert_eq!(
            w,
            [1, 2, 3, 4, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfe]
        );
    }

    #[test]
    fn negative_amount_is_rejected() {
        let mut w = Vec::new();
        assert!(write_amount(&mut w, -1).is_err());
        assert!(write_amount(&mut w, 5).is_ok());
    }

    #[test]
    fn asset_code_is_zero_padded() {
        let mut w = Vec::new();
        write_asset_code(&mut w, AssetType::Alphanum4, Some("USD")).unwrap();
        assert_eq!(w, [b'U', b'S', b'D', 0]);
        assert!(write_asset_code(&mut Vec::new(), AssetType::Alphanum4, Some("TOOLONG")).is_err());
    }
}
