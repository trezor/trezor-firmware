use miniscript::bitcoin::{PublicKey, ScriptBuf};
use miniscript::descriptor::Wsh;
use miniscript::expression::{FromTree, Tree};
pub use miniscript::Error;
use miniscript::{ForEachKey, FromStrKey, MiniscriptKey, TranslateErr, Translator};

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
            _ => return Err(Error::Unexpected),
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

    pub fn try_for_each<'a, E, F: FnMut(&'a Pk) -> Result<(), E>>(
        &'a self,
        mut pred: F,
    ) -> Result<(), E> {
        let mut result = Ok(());
        match *self {
            Descriptor::Wsh(ref wsh) => wsh.for_each_key(|pk| {
                result = pred(pk);
                result.is_ok()
            }),
        };
        result
    }
}

impl Descriptor<PublicKey> {
    pub fn inner_script(&self) -> ScriptBuf {
        match *self {
            Descriptor::Wsh(ref wsh) => wsh.inner_script(),
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct KeyExpr {
    pub key: u8,
    pub children: (u8, u8),
}

impl miniscript::MiniscriptKey for KeyExpr {}

impl core::str::FromStr for KeyExpr {
    type Err = ();

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        fn _trim<'a>(s: &'a str, prefix: &str, suffix: &str) -> Result<&'a str, ()> {
            if s.starts_with(prefix) && s.ends_with(suffix) {
                Ok(&s[prefix.len()..s.len() - suffix.len()])
            } else {
                Err(())
            }
        }

        fn _split<'a>(s: &'a str, sep: &str) -> Result<(&'a str, &'a str), ()> {
            let mut parts = s.split(sep);
            let first = parts.next().ok_or(())?;
            let second = parts.next().ok_or(())?;
            if parts.next().is_some() {
                return Err(());
            }
            Ok((first, second))
        }

        fn _parse(s: &str) -> Result<u8, ()> {
            // TODO: support larger indices
            if s.len() != 1 {
                return Err(());
            }
            s.parse().map_err(|_| ())
        }

        let (key, change) = _split(_trim(s, "@", "/*")?, "/")?;
        let (left, right) = _split(_trim(change, "<", ">")?, ";")?;
        Ok(KeyExpr {
            key: _parse(key)?,
            children: (_parse(left)?, _parse(right)?),
        })
    }
}
