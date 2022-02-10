/// Visitor passed into `Trace` types.
pub trait Tracer {
    fn int(&mut self, i: i64);
    fn bytes(&mut self, b: &[u8]);
    fn string(&mut self, s: &str);
    fn symbol(&mut self, name: &str);
    fn open(&mut self, name: &str);
    fn field(&mut self, name: &str, value: &dyn Trace);
    fn close(&mut self);
}

/// Value that can describe own structure and data using the `Tracer` interface.
pub trait Trace {
    fn trace(&self, d: &mut dyn Tracer);
}

impl Trace for &[u8] {
    fn trace(&self, t: &mut dyn Tracer) {
        t.bytes(self);
    }
}

impl<const N: usize> Trace for &[u8; N] {
    fn trace(&self, t: &mut dyn Tracer) {
        t.bytes(&self[..])
    }
}

impl Trace for &str {
    fn trace(&self, t: &mut dyn Tracer) {
        t.string(self);
    }
}

impl Trace for usize {
    fn trace(&self, t: &mut dyn Tracer) {
        t.int(*self as i64);
    }
}

impl<T> Trace for Option<T>
where
    T: Trace,
{
    fn trace(&self, d: &mut dyn Tracer) {
        match self {
            Some(v) => v.trace(d),
            None => d.symbol("None"),
        }
    }
}
