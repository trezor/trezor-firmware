use crate::{
    alloc_types::{String, vec},
    clear_signing::{
        AbiValue, AtomicType, ContainerPath, DisplayFormat, FieldDefinition, FieldFormatter, Path,
        TokenAmountFormatterParams,
    },
};
use primitive_types::U256;

// https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/ercs/calldata-erc20-tokens.json#L27

pub(crate) fn get_approve_display_format() -> DisplayFormat {
    DisplayFormat {
        binding_context: None,
        func_sig: *b"\x09\x5e\xa7\xb3", // approve(address,uint256)
        intent: String::from("Approve"),
        parameter_definitions: vec![
            AbiValue::Atomic(AtomicType::Address), // _spender
            AbiValue::Atomic(AtomicType::Uint256), // _value
        ],
        field_definitions: vec![
            FieldDefinition {
                path: Path::Fields(vec![crate::clear_signing::PathStep::Index(0)]),
                label: String::from("Spender"),
                formatter: FieldFormatter::AddressName,
            },
            FieldDefinition {
                path: Path::Fields(vec![crate::clear_signing::PathStep::Index(1)]),
                label: String::from("Amount"),
                formatter: FieldFormatter::TokenAmount(TokenAmountFormatterParams {
                    token_path: Path::Container(ContainerPath::To),
                    threshold: Some(U256::from(1u8) << 255), //0x8000000000000000000000000000000000000000000000000000000000000000
                }),
            },
        ],
    }
}

pub(crate) fn get_all_display_formats() -> [DisplayFormat; 2] {
    [get_approve_display_format(), get_transfer_display_format()]
}

pub(crate) const SC_FUNC_APPROVE_REVOKE_AMOUNT: U256 = U256::zero();

pub(crate) fn get_transfer_display_format() -> DisplayFormat {
    DisplayFormat {
        binding_context: None,
        func_sig: *b"\xa9\x05\x9c\xbb", // transfer(address,uint256)
        intent: String::from("Transfer"),
        parameter_definitions: vec![
            AbiValue::Atomic(AtomicType::Address), // _to
            AbiValue::Atomic(AtomicType::Uint256), // _value
        ],
        field_definitions: vec![
            FieldDefinition {
                path: Path::Fields(vec![crate::clear_signing::PathStep::Index(0)]),
                label: String::from("To"),
                formatter: FieldFormatter::AddressName,
            },
            FieldDefinition {
                path: Path::Fields(vec![crate::clear_signing::PathStep::Index(1)]),
                label: String::from("Amount"),
                formatter: FieldFormatter::TokenAmount(TokenAmountFormatterParams {
                    token_path: Path::Container(ContainerPath::To),
                    threshold: None,
                }),
            },
        ],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use trezor_app_sdk::crypto;

    fn keccak_32(input: &[u8]) -> [u8; 4] {
        let mut hasher = crypto::Keccak256::new(Some(input));
        hasher.digest()[..4]
            .try_into()
            .expect("slice with incorrect length")
    }

    fn test_func_sig_approve_display_format() {
        assert_eq!(
            get_approve_display_format().func_sig,
            keccak_32(b"approve(address,uint256)")
        );
    }

    fn test_func_sig_transfer_display_format() {
        assert_eq!(
            get_transfer_display_format().func_sig,
            keccak_32(b"transfer(address,uint256)")
        );
    }
}
