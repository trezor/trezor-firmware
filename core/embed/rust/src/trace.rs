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

#[cfg(test)]
mod tests {
    use super::*;

    impl Tracer for Vec<u8> {
        fn int(&mut self, i: i64) {
            self.string(&i.to_string());
        }

        fn bytes(&mut self, b: &[u8]) {
            self.extend(b)
        }

        fn string(&mut self, s: &str) {
            self.extend(s.as_bytes())
        }

        fn symbol(&mut self, name: &str) {
            self.extend(name.as_bytes())
        }

        fn open(&mut self, name: &str) {
            self.extend(b"<");
            self.extend(name.as_bytes());
            self.extend(b" ");
        }

        fn field(&mut self, name: &str, value: &dyn Trace) {
            self.extend(name.as_bytes());
            self.extend(b":");
            value.trace(self);
            self.extend(b" ");
        }

        fn close(&mut self) {
            self.extend(b">")
        }
    }
}
