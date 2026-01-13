extern crate alloc;

use alloc::string::{String, ToString};

/// Hash function type for coin operations
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HashFunction {
    /// SHA256(SHA256(x))
    Sha256d32,
    /// Blake256(Blake256(x))
    Blake256d32,
    /// Groestl512(Groestl512(x))
    Groestl512d32,
    /// Keccak256
    Keccak32,
}

/// Script hash function type
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScriptHashFunction {
    /// SHA256(RIPEMD160(x))
    Sha256Ripemd160,
    /// Blake256(RIPEMD160(x))
    Blake256Ripemd160,
}

/// Coin information structure
#[derive(Debug, Clone)]
pub struct CoinInfo {
    pub coin_name: &'static str,
    pub coin_shortcut: &'static str,
    pub decimals: u32,
    pub address_type: u32,
    pub address_type_p2sh: u32,
    pub maxfee_kb: u64,
    pub signed_message_header: &'static str,
    pub xpub_magic: u32,
    pub xpub_magic_segwit_p2sh: Option<u32>,
    pub xpub_magic_segwit_native: Option<u32>,
    pub xpub_magic_multisig_segwit_p2sh: Option<u32>,
    pub xpub_magic_multisig_segwit_native: Option<u32>,
    pub bech32_prefix: Option<&'static str>,
    pub cashaddr_prefix: Option<&'static str>,
    pub slip44: u32,
    pub segwit: bool,
    pub taproot: bool,
    pub fork_id: Option<u32>,
    pub force_bip143: bool,
    pub decred: bool,
    pub negative_fee: bool,
    pub curve_name: &'static str,
    pub extra_data: bool,
    pub timestamp: bool,
    pub overwintered: bool,
    // Hash functions derived from curve_name
    pub b58_hash: HashFunction,
    pub sign_hash_double: bool,
    pub script_hash: ScriptHashFunction,
}

impl CoinInfo {
    /// Create a new CoinInfo with curve-specific hash functions
    fn new(
        coin_name: &'static str,
        coin_shortcut: &'static str,
        decimals: u32,
        address_type: u32,
        address_type_p2sh: u32,
        maxfee_kb: u64,
        signed_message_header: &'static str,
        xpub_magic: u32,
        xpub_magic_segwit_p2sh: Option<u32>,
        xpub_magic_segwit_native: Option<u32>,
        xpub_magic_multisig_segwit_p2sh: Option<u32>,
        xpub_magic_multisig_segwit_native: Option<u32>,
        bech32_prefix: Option<&'static str>,
        cashaddr_prefix: Option<&'static str>,
        slip44: u32,
        segwit: bool,
        taproot: bool,
        fork_id: Option<u32>,
        force_bip143: bool,
        decred: bool,
        negative_fee: bool,
        curve_name: &'static str,
        extra_data: bool,
        timestamp: bool,
        overwintered: bool,
    ) -> Self {
        let (b58_hash, sign_hash_double, script_hash) = match curve_name {
            "secp256k1-groestl" => (
                HashFunction::Groestl512d32,
                false,
                ScriptHashFunction::Sha256Ripemd160,
            ),
            "secp256k1-decred" => (
                HashFunction::Blake256d32,
                false,
                ScriptHashFunction::Blake256Ripemd160,
            ),
            "secp256k1-smart" => (
                HashFunction::Keccak32,
                false,
                ScriptHashFunction::Sha256Ripemd160,
            ),
            _ => (
                HashFunction::Sha256d32,
                true,
                ScriptHashFunction::Sha256Ripemd160,
            ),
        };

        CoinInfo {
            coin_name,
            coin_shortcut,
            decimals,
            address_type,
            address_type_p2sh,
            maxfee_kb,
            signed_message_header,
            xpub_magic,
            xpub_magic_segwit_p2sh,
            xpub_magic_segwit_native,
            xpub_magic_multisig_segwit_p2sh,
            xpub_magic_multisig_segwit_native,
            bech32_prefix,
            cashaddr_prefix,
            slip44,
            segwit,
            taproot,
            fork_id,
            force_bip143,
            decred,
            negative_fee,
            curve_name,
            extra_data,
            timestamp,
            overwintered,
            b58_hash,
            sign_hash_double,
            script_hash,
        }
    }
}

impl PartialEq for CoinInfo {
    fn eq(&self, other: &Self) -> bool {
        self.coin_name == other.coin_name
    }
}

/// Get coin info by name and model
pub fn by_name(name: &str, model: &str) -> Option<CoinInfo> {
    match model {
        "T2B1" => by_name_t2b1(name),
        "T2T1" => by_name_t2t1(name),
        "T3B1" => by_name_t3b1(name),
        "T3T1" => by_name_t3t1(name),
        "T3W1" => by_name_t3w1(name),
        "D001" => by_name_d001(name),
        "D002" => by_name_d002(name),
        _ => None,
    }
}

fn by_name_t2b1(name: &str) -> Option<CoinInfo> {
    match name {
        "Bitcoin" => Some(CoinInfo::new(
            "Bitcoin",
            "BTC",
            8,
            0,
            5,
            2000000,
            "Bitcoin Signed Message:\n",
            0x0488b21e,
            Some(0x049d7cb2),
            Some(0x04b24746),
            Some(0x0295b43f),
            Some(0x02aa7ed3),
            Some("bc"),
            None,
            0,
            true,
            true,
            None,
            false,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        "Regtest" => Some(CoinInfo::new(
            "Regtest",
            "REGTEST",
            8,
            111,
            196,
            10000000,
            "Bitcoin Signed Message:\n",
            0x043587cf,
            Some(0x044a5262),
            Some(0x045f1cf6),
            Some(0x024289ef),
            Some(0x02575483),
            Some("bcrt"),
            None,
            1,
            true,
            true,
            None,
            false,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        "Testnet" => Some(CoinInfo::new(
            "Testnet",
            "TEST",
            8,
            111,
            196,
            10000000,
            "Bitcoin Signed Message:\n",
            0x043587cf,
            Some(0x044a5262),
            Some(0x045f1cf6),
            Some(0x024289ef),
            Some(0x02575483),
            Some("tb"),
            None,
            1,
            true,
            true,
            None,
            false,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        "Litecoin" => Some(CoinInfo::new(
            "Litecoin",
            "LTC",
            8,
            48,
            50,
            67000000,
            "Litecoin Signed Message:\n",
            0x019da462,
            Some(0x01b26ef6),
            Some(0x04b24746),
            Some(0x019da462),
            Some(0x019da462),
            Some("ltc"),
            None,
            2,
            true,
            false,
            None,
            false,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        "Dogecoin" => Some(CoinInfo::new(
            "Dogecoin",
            "DOGE",
            8,
            30,
            22,
            1200000000000,
            "Dogecoin Signed Message:\n",
            0x02facafd,
            None,
            None,
            None,
            None,
            None,
            None,
            3,
            false,
            false,
            None,
            false,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        "Bcash" => Some(CoinInfo::new(
            "Bcash",
            "BCH",
            8,
            0,
            5,
            14000000,
            "Bitcoin Signed Message:\n",
            0x0488b21e,
            None,
            None,
            None,
            None,
            None,
            Some("bitcoincash"),
            145,
            false,
            false,
            Some(0),
            true,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        _ => None,
    }
}

fn by_name_t2t1(name: &str) -> Option<CoinInfo> {
    match name {
        "Bitcoin" => Some(CoinInfo::new(
            "Bitcoin",
            "BTC",
            8,
            0,
            5,
            2000000,
            "Bitcoin Signed Message:\n",
            0x0488b21e,
            Some(0x049d7cb2),
            Some(0x04b24746),
            Some(0x0295b43f),
            Some(0x02aa7ed3),
            Some("bc"),
            None,
            0,
            true,
            true,
            None,
            false,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        "Litecoin" => Some(CoinInfo::new(
            "Litecoin",
            "LTC",
            8,
            48,
            50,
            67000000,
            "Litecoin Signed Message:\n",
            0x019da462,
            Some(0x01b26ef6),
            Some(0x04b24746),
            Some(0x019da462),
            Some(0x019da462),
            Some("ltc"),
            None,
            2,
            true,
            false,
            None,
            false,
            false,
            false,
            "secp256k1",
            false,
            false,
            false,
        )),
        _ => None,
    }
}

fn by_name_t3b1(name: &str) -> Option<CoinInfo> {
    by_name_t2b1(name)
}

fn by_name_t3t1(name: &str) -> Option<CoinInfo> {
    by_name_t2t1(name)
}

fn by_name_t3w1(name: &str) -> Option<CoinInfo> {
    by_name_t2t1(name)
}

fn by_name_d001(name: &str) -> Option<CoinInfo> {
    by_name_t2b1(name)
}

fn by_name_d002(name: &str) -> Option<CoinInfo> {
    by_name_t2b1(name)
}
