use miniscript::bitcoin::hashes::{hash160, ripemd160, sha256};
use miniscript::bitcoin::ScriptBuf;
use miniscript::descriptor::{Wsh, WshInner};
use miniscript::expression::{FromTree, Tree};
use miniscript::{
    hash256, ForEachKey, FromStrKey, MiniscriptKey, SerializedPublicKey, TranslateErr, Translator,
};

extern crate alloc;

pub enum Error {
    Unsupported,
    Invalid,
}

impl From<miniscript::Error> for Error {
    fn from(_: miniscript::Error) -> Self {
        Error::Invalid
    }
}

/// Script descriptor
pub enum Descriptor<Pk: MiniscriptKey> {
    /// Pay-to-Witness-ScriptHash with Segwitv0 context
    Wsh(Wsh<Pk>),
}

impl<Pk: FromStrKey + MiniscriptKey> Descriptor<Pk> {
    pub fn parse(s: &str) -> Result<Descriptor<Pk>, Error> {
        let tree = Tree::from_str(s)?;
        let root = tree.root();
        let ret = match (root.name(), root.n_children()) {
            ("wsh", 1) => Descriptor::Wsh(Wsh::from_tree(root)?),
            _ => return Err(Error::Unsupported),
        };
        ret.sanity_check()?;
        Ok(ret)
    }

    /// Checks whether the descriptor is safe.
    fn sanity_check(&self) -> Result<(), Error> {
        Ok(match *self {
            Descriptor::Wsh(ref wsh) => wsh.sanity_check()?,
        })
    }

    /// Converts a descriptor using one kind of keys to another kind of key.
    pub fn translate_pk<T>(
        &self,
        t: &mut T,
    ) -> Result<Descriptor<T::TargetPk>, TranslateErr<T::Error>>
    where
        T: Translator<Pk>,
    {
        Ok(match *self {
            Descriptor::Wsh(ref wsh) => Descriptor::Wsh(wsh.translate_pk(t)?),
        })
    }

    pub fn try_for_each<'a, E, F>(&'a self, mut callback: F) -> Result<(), E>
    where
        F: FnMut(&'a Pk) -> Result<(), E>,
    {
        let mut result = Ok(());
        match *self {
            Descriptor::Wsh(ref wsh) => wsh.for_each_key(|pk| {
                if let Err(e) = callback(pk) {
                    result = Err(e);
                }
                result.is_ok()
            }),
        };
        result
    }
}

impl Descriptor<SerializedPublicKey> {
    pub fn inner_script(&self) -> ScriptBuf {
        match *self {
            Descriptor::Wsh(ref wsh) => match wsh.as_inner() {
                WshInner::SortedMulti(ref smv) => smv.encode(),
                WshInner::Ms(ms) => ms.encode(),
            },
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Debug)]
pub struct KeyExpr {
    pub key: u8,
    pub child: (u8, u8),
}

impl core::fmt::Display for KeyExpr {
    fn fmt(&self, f: &mut core::fmt::Formatter) -> core::fmt::Result {
        write!(f, "@{}/<{};{}>/*", self.key, self.child.0, self.child.1)
    }
}

impl miniscript::MiniscriptKey for KeyExpr {
    type Sha256 = sha256::Hash;
    type Hash256 = hash256::Hash;
    type Ripemd160 = ripemd160::Hash;
    type Hash160 = hash160::Hash;
}

#[derive(Debug)]
pub struct InvalidKeyExpr;

impl core::fmt::Display for InvalidKeyExpr {
    fn fmt(&self, f: &mut core::fmt::Formatter) -> core::fmt::Result {
        write!(f, "invalid key expression")
    }
}

impl core::str::FromStr for KeyExpr {
    type Err = InvalidKeyExpr;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        fn _trim<'a>(s: &'a str, prefix: &str, suffix: &str) -> Result<&'a str, InvalidKeyExpr> {
            if s.starts_with(prefix) && s.ends_with(suffix) {
                Ok(&s[prefix.len()..s.len() - suffix.len()])
            } else {
                Err(InvalidKeyExpr)
            }
        }

        fn _split<'a>(s: &'a str, sep: &str) -> Result<(&'a str, &'a str), InvalidKeyExpr> {
            let mut parts = s.split(sep);
            let first = parts.next().ok_or(InvalidKeyExpr)?;
            let second = parts.next().ok_or(InvalidKeyExpr)?;
            if parts.next().is_some() {
                return Err(InvalidKeyExpr);
            }
            Ok((first, second))
        }

        fn _parse(s: &str) -> Result<u8, InvalidKeyExpr> {
            // TODO: support larger digit-only indices, exclude leading zeroes
            if s.len() != 1 {
                return Err(InvalidKeyExpr);
            }
            s.parse().map_err(|_| InvalidKeyExpr)
        }

        let (key, change) = _split(_trim(s, "@", "/*")?, "/")?;
        let (left, right) = _split(_trim(change, "<", ">")?, ";")?;
        Ok(KeyExpr {
            key: _parse(key)?,
            child: (_parse(left)?, _parse(right)?),
        })
    }
}
