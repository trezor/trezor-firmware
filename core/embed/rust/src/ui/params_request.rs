use heapless::Vec;

use crate::micropython::qstr::Qstr;

/// How many distinct keys one request can name before it degrades to "all".
pub const MAX_PARAM_KEYS: usize = 8;

/// The construction parameters a layout wants supplied again, named by key.
///
/// A component that notices some of its inputs went stale raises a request
/// through `EventCtx::request_params()` instead of returning a "please restart
/// me" message. It names the keys it dirtied -- the same keys the layout was
/// constructed with -- so the application layer recomputes only those. The
/// layout keeps running and receives the answer as `Event::UpdateParams`.
///
/// An empty request means "everything went stale". Requests raised during one
/// event pass are merged, so two components asking for different keys are both
/// served.
///
/// The application layer answers with the *complete* parameter set; the keys
/// only say what it has to recompute. Applying a partial set inside the layout
/// is a possible later improvement, and would start here.
#[derive(Clone, PartialEq, Eq)]
pub struct ParamsRequest {
    keys: Vec<Qstr, MAX_PARAM_KEYS>,
    /// Set instead of listing keys. Not the same as an empty `keys`, which
    /// would be a request for nothing at all.
    everything: bool,
}

impl ParamsRequest {
    /// A request for the named keys. An empty slice, or more than
    /// `MAX_PARAM_KEYS` distinct keys, asks for everything -- a superset of
    /// what was asked for, so nothing is lost but the narrowing.
    pub fn new(keys: &[Qstr]) -> Self {
        if keys.is_empty() {
            return Self::everything();
        }
        let mut request = Self {
            keys: Vec::new(),
            everything: false,
        };
        for key in keys {
            request.push(*key);
        }
        request
    }

    /// A request for the whole parameter set.
    pub fn everything() -> Self {
        Self {
            keys: Vec::new(),
            everything: true,
        }
    }

    /// Whether this request asks for the whole parameter set.
    pub fn is_everything(&self) -> bool {
        self.everything
    }

    /// The keys asked for; empty when the request is for everything.
    pub fn keys(&self) -> &[Qstr] {
        &self.keys
    }

    /// Fold another request into this one, so that several components asking
    /// during the same event pass are all served.
    pub fn merge(&mut self, other: &Self) {
        if other.is_everything() {
            self.widen();
            return;
        }
        for key in other.keys() {
            self.push(*key);
        }
    }

    fn push(&mut self, key: Qstr) {
        if self.everything || self.keys.contains(&key) {
            return;
        }
        if self.keys.push(key).is_err() {
            self.widen();
        }
    }

    fn widen(&mut self) {
        self.keys.clear();
        self.everything = true;
    }
}

#[cfg(feature = "debug")]
impl ufmt::uDebug for ParamsRequest {
    fn fmt<W>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite + ?Sized,
    {
        f.write_str("ParamsRequest")
    }
}
