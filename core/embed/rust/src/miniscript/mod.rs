use miniscript::bitcoin::{secp256k1, PublicKey, ScriptBuf};
use miniscript::descriptor::{DescriptorPublicKey, Wsh};
use miniscript::expression::{FromTree, Tree};
use miniscript::{
    translate_hash_clone, FromStrKey, MiniscriptKey, TranslateErr, Translator,
};

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

impl Translator<DescriptorPublicKey> for Derivator<'_> {
    type TargetPk = PublicKey;

    type Error = Error;

    fn pk(&mut self, pk: &DescriptorPublicKey) -> Result<Self::TargetPk, Self::Error> {
        // TODO: check global xpubs structure
        // TODO: avoid cloning
        let res = match pk
            .clone()
            .into_single_keys()
            .get(usize::from(self.internal))
        {
            Some(key) => key
                .clone()
                .at_derivation_index(self.index)
                .map_err(|_| Error::Unsupported)?
                .derive_public_key(self.secp),
            None => return Err(Error::Unsupported),
        };
        Ok(res)
    }

    // TODO: not sure if needed, and how much it costs us in flash space
    translate_hash_clone!(DescriptorPublicKey);
}

impl Descriptor<PublicKey> {
    pub fn inner_script(&self) -> ScriptBuf {
        match *self {
            Descriptor::Wsh(ref wsh) => wsh.inner_script(),
        }
    }
}

pub fn compile(desc: &str, internal: bool, index: u32) -> Result<ScriptBuf, Error> {
    let multipath = Descriptor::<DescriptorPublicKey>::parse(&desc)?;
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
