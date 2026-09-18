use miniscript::bitcoin::{PublicKey, ScriptBuf};
use miniscript::descriptor::Wsh;
use miniscript::expression::{FromTree, Tree};
use miniscript::{FromStrKey, MiniscriptKey, TranslateErr, Translator};

#[cfg_attr(test, derive(Debug))]
pub enum Error {
    Miniscript(miniscript::Error),
    Unsupported(&'static str),
}

impl From<miniscript::Error> for Error {
    fn from(value: miniscript::Error) -> Self {
        Error::Miniscript(value)
    }
}

/// Script descriptor
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
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
            _ => return Err(Error::Unsupported("context")),
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
}

impl Descriptor<PublicKey> {
    pub fn inner_script(&self) -> ScriptBuf {
        match *self {
            Descriptor::Wsh(ref wsh) => wsh.inner_script(),
        }
    }
}
