extern crate alloc;

use alloc::string::String;
use core::iter;
use core::str::FromStr;

use miniscript::bitcoin::hashes::{hash160, ripemd160, sha256};
use miniscript::bitcoin::{bip32, secp256k1, PublicKey, ScriptBuf};
use miniscript::descriptor::{DescriptorMultiXKey, DescriptorPublicKey, Wildcard, Wsh};
use miniscript::expression::{FromTree, Tree};
use miniscript::{hash256, FromStrKey, MiniscriptKey, TranslateErr, Translator};

use crate::miniscript::Error::Unsupported;

pub enum Error {
    Miniscript(miniscript::Error),
    Unsupported,
}

impl From<miniscript::Error> for Error {
    fn from(value: miniscript::Error) -> Self {
        Error::Miniscript(value)
    }
}

/// Script descriptor
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
enum Descriptor<Pk: MiniscriptKey> {
    /// Pay-to-Witness-ScriptHash with Segwitv0 context
    Wsh(Wsh<Pk>),
}

impl<Pk: FromStrKey + MiniscriptKey> Descriptor<Pk> {
    fn parse(s: &str) -> Result<Descriptor<Pk>, Error> {
        let tree = Tree::from_str(s)?;
        let root = tree.root();
        let ret = match (root.name(), root.n_children()) {
            ("wsh", 1) => Descriptor::Wsh(Wsh::from_tree(root)?),
            _ => return Err(Unsupported),
        };
        ret.sanity_check()?;
        Ok(ret)
    }

    /// Checks whether the descriptor is safe.
    fn sanity_check(&self) -> Result<(), Error> {
        match *self {
            Descriptor::Wsh(ref wsh) => wsh.sanity_check(),
        }
        .map_err(Error::Miniscript)
    }

    /// Converts a descriptor using one kind of keys to another kind of key.
    fn translate_pk<T>(&self, t: &mut T) -> Result<Descriptor<T::TargetPk>, TranslateErr<T::Error>>
    where
        T: Translator<Pk>,
    {
        Ok(match *self {
            Descriptor::Wsh(ref wsh) => Descriptor::Wsh(wsh.translate_pk(t)?),
        })
    }
}

struct Derivator<'a> {
    internal: bool,
    index: u32,
    secp: &'a secp256k1::Secp256k1<secp256k1::VerifyOnly>,
}

impl Translator<String> for Derivator<'_> {
    type TargetPk = PublicKey;

    type Error = Error;

    fn pk(&mut self, pk: &String) -> Result<Self::TargetPk, Self::Error> {
        // TODO: check global xpubs structure
        // TODO: avoid cloning
        let DescriptorMultiXKey {
            origin: _,
            xkey,
            derivation_paths,
            wildcard,
        } = match DescriptorPublicKey::from_str(pk).expect("TODO") {
            DescriptorPublicKey::MultiXPub(multi) => multi,
            _ => return Err(Error::Unsupported),
        };
        if wildcard != Wildcard::Unhardened {
            return Err(Error::Unsupported);
        }
        let derivation_paths = derivation_paths.into_paths();
        if derivation_paths.len() != 2 {
            return Err(Error::Unsupported);
        }
        let path = &derivation_paths[usize::from(self.internal)];
        if path.len() != 1 {
            return Err(Error::Unsupported);
        }
        let index =
            bip32::ChildNumber::from_normal_idx(self.index).map_err(|_| Error::Unsupported)?;

        let mut result = xkey;
        for number in iter::chain(path.into_iter(), iter::once(&index)) {
            result = result
                .ckd_pub(self.secp, *number)
                .map_err(|_| Error::Unsupported)?;
        }
        Ok(PublicKey::new(result.public_key))
    }

    fn sha256(&mut self, _sha256: &String) -> Result<sha256::Hash, Error> {
        Err(Error::Unsupported)
    }

    fn hash256(&mut self, _hash256: &String) -> Result<hash256::Hash, Error> {
        Err(Error::Unsupported)
    }

    fn ripemd160(&mut self, _ripemd160: &String) -> Result<ripemd160::Hash, Error> {
        Err(Error::Unsupported)
    }

    fn hash160(&mut self, _hash160: &String) -> Result<hash160::Hash, Error> {
        Err(Error::Unsupported)
    }
}

impl Descriptor<PublicKey> {
    pub fn inner_script(&self) -> ScriptBuf {
        match *self {
            Descriptor::Wsh(ref wsh) => wsh.inner_script(),
        }
    }
}

pub fn compile(desc: &str, internal: bool, index: u32) -> Result<ScriptBuf, Error> {
    let multipath = Descriptor::parse(&desc)?;
    let mut derivator = Derivator {
        internal,
        index,
        secp: &secp256k1::Secp256k1::verification_only(),
    };
    match multipath.translate_pk(&mut derivator) {
        Ok(desc) => Ok(desc.inner_script()),
        Err(TranslateErr::OuterError(e)) => Err(e.into()),
        Err(TranslateErr::TranslatorErr(e)) => Err(e),
    }
}
