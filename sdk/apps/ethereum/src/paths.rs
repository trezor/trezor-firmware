extern crate alloc;
use crate::definitions::unknown_network;
use crate::strutil::hex_encode;
use alloc::string::{String, ToString};
use alloc::vec;
use alloc::vec::Vec;
use core::convert::AsRef;
use trezor_app_sdk::{Error, Result, ui};

const HARDENED: u32 = 0x8000_0000;

pub(crate) struct Bip32Path {
    path: alloc::vec::Vec<u32>,
}

impl Bip32Path {
    pub fn from_slice(path: &[u32]) -> Self {
        Self {
            path: path.to_vec(),
        }
    }

    pub fn length(&self) -> usize {
        self.path.len()
    }

    pub fn to_string(&self) -> alloc::string::String {
        if self.path.is_empty() {
            return String::from("m");
        }

        let mut s = String::from("m");
        for segment in &self.path {
            s.push('/');
            if segment & HARDENED != 0 {
                s.push_str(&(segment ^ HARDENED).to_string());
                s.push('\'');
            } else {
                s.push_str(&segment.to_string());
            }
        }
        s
    }

    pub fn is_hardened(&self) -> bool {
        self.path.iter().all(|segment| segment & HARDENED != 0)
    }

    pub fn get_account_name(&self, coin: &str, pattern: &[&str], slip44_id: u32) -> Option<String> {
        let account_num = self.get_account_num(pattern, slip44_id)?;
        let mut s = String::from(coin);
        s.push_str(" #");
        s.push_str(&account_num.to_string());
        Some(s)
    }

    pub fn validate(&self, keychain: &dyn KeychainValidator) -> Result<()> {
        keychain.verify_path(self)?;
        if !keychain.is_in_keychain(self) {
            ui::show_danger(
                "Wrong derivation path for selected account.",
                &self.to_string(),
            )?;
        }
        Ok(())
    }

    fn get_account_num(&self, patterns: &[&str], slip44_id: u32) -> Option<u32> {
        for pattern in patterns {
            if let Some(num) = self.get_account_num_single(pattern, slip44_id) {
                return Some(num);
            }
        }
        None
    }

    fn get_account_num_single(&self, pattern: &str, _slip44_id: u32) -> Option<u32> {
        if let Some(account_pos) = pattern.find("/account") {
            let slash_count = pattern[..account_pos].matches('/').count();

            if slash_count >= self.path.len() {
                return None;
            }

            let num = self.path[slash_count];

            if num & HARDENED != 0 {
                Some((num ^ HARDENED) + 1)
            } else {
                Some(num + 1)
            }
        } else {
            None
        }
    }

    pub fn slip44(&self) -> Option<u32> {
        if self.path.len() < 2 {
            return None;
        }

        if self.path[0] == 45 | HARDENED && self.path[1] & HARDENED == 0 {
            return Some(self.path[1]);
        }
        return Some(self.path[1] & !HARDENED);
    }
}

impl AsRef<[u32]> for Bip32Path {
    fn as_ref(&self) -> &[u32] {
        &self.path
    }
}

pub trait KeychainValidator {
    fn is_in_keychain(&self, path: &Bip32Path) -> bool;
    fn verify_path(&self, path: &Bip32Path) -> Result<()>;
}

pub trait PathSchemaTrait {
    fn matches(&self, path: &Bip32Path) -> bool;
}

pub struct AlwaysMatchingSchema;
impl PathSchemaTrait for AlwaysMatchingSchema {
    fn matches(&self, _path: &Bip32Path) -> bool {
        true
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Interval {
    pub min: u32,
    pub max: u32,
}

impl Interval {
    pub fn contains(&self, value: u32) -> bool {
        value >= self.min && value <= self.max
    }
}

pub enum PathComponent {
    Set(Vec<u32>),
    Interval(Interval),
    Single(u32),
}

impl PathComponent {
    pub fn contains(&self, value: u32) -> bool {
        match self {
            PathComponent::Set(values) => values.contains(&value),
            PathComponent::Interval(interval) => interval.contains(value),
            PathComponent::Single(v) => *v == value,
        }
    }
}

pub struct PathSchema {
    schemas: Vec<PathComponent>,
    trailing_components: Option<Interval>,
}

impl PathSchema {
    /// Create a new PathSchema from a list of containers and trailing components.
    ///
    /// Mainly for internal use in `PathSchema.parse`, which is the method you should
    /// be using.
    ///
    /// Can be used to create a schema manually without parsing a path string:
    pub fn new(schema: Vec<PathComponent>, trailing_components: Option<Interval>) -> Self {
        Self {
            schemas: schema,
            trailing_components,
        }
    }

    pub fn parse(pattern: &str, slip44: &[u32]) -> Result<Self> {
        // TODO
        if !pattern.starts_with("m/") {
            return Err(Error::DataError);
        }

        let components: Vec<&str> = pattern[2..].split('/').collect();
        let mut schema: Vec<PathComponent> = Vec::new();
        let mut trailing_components: Option<Interval> = None;

        for (idx, mut component) in components.iter().copied().enumerate() {
            // wildcard ranges must be last
            if let Some(range) = Self::wildcard_range(component) {
                if idx != components.len() - 1 {
                    return Err(Error::DataError);
                }
                trailing_components = Some(range);
                break;
            }

            // figure out if the component is hardened
            let hardened = component.ends_with('\'');
            if hardened {
                component = &component[..component.len() - 1];
            }

            // strip brackets
            if component.starts_with('[') && component.ends_with(']') && component.len() >= 2 {
                component = &component[1..component.len() - 1];
            }

            // optionally replace a keyword
            let component = Self::replace_keyword(component);

            let parsed = if component.contains('-') {
                let mut it = component.splitn(2, '-');
                let a = Self::parse_component(it.next().ok_or(Error::DataError)?, hardened)?;
                let b = Self::parse_component(it.next().ok_or(Error::DataError)?, hardened)?;
                PathComponent::Interval(Interval { min: a, max: b })
            } else if component.contains(',') {
                let mut values = Vec::new();
                for part in component.split(',') {
                    values.push(Self::parse_component(part, hardened)?);
                }
                PathComponent::Set(values)
            } else if component == "coin_type" {
                let mut values = Vec::new();
                for id in slip44 {
                    values.push(if hardened { id | HARDENED } else { *id });
                }
                PathComponent::Set(values)
            } else {
                PathComponent::Single(Self::parse_component(component, hardened)?)
            };

            schema.push(parsed);
        }

        Ok(Self::new(schema, trailing_components))
    }

    fn parse_component(s: &str, hardened: bool) -> Result<u32> {
        let v: u32 = s.parse().map_err(|_| Error::DataError)?;
        Ok(if hardened { v | HARDENED } else { v })
    }

    fn replace_keyword(s: &str) -> &str {
        match s {
            "account" => "0-100",
            "change" => "0,1",
            "address_index" => "0-1000000",
            _ => s,
        }
    }

    fn wildcard_range(s: &str) -> Option<Interval> {
        match s {
            "*" => Some(Interval {
                min: 0,
                max: 0x7FFF_FFFF,
            }),
            "*'" => Some(Interval {
                min: HARDENED,
                max: HARDENED | 0x7FFF_FFFF,
            }),
            _ => None,
        }
    }
}

impl PathSchemaTrait for PathSchema {
    fn matches(&self, path: &Bip32Path) -> bool {
        // The path must not be shorter than schema. It may be longer.
        if path.path.len() < self.schemas.len() {
            return false;
        }

        let mut path_iter = path.path.iter();

        // iterate over length of schema, consuming path components
        for expected in &self.schemas {
            let value = match path_iter.next() {
                Some(v) => v,
                None => return false,
            };
            if !expected.contains(*value) {
                return false;
            }
        }

        // iterate over remaining path components
        for value in path_iter {
            if !self
                .trailing_components
                .as_ref()
                .map_or(false, |tc| tc.contains(*value))
            {
                return false;
            }
        }

        true
    }
}
