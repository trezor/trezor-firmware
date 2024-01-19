use crate::strutil::{format_i64, TString};

pub trait Tracer {
    fn child(&mut self, key: &str, value: &dyn Trace);
    fn int(&mut self, key: &str, i: i64);
    fn string(&mut self, key: &str, s: TString<'_>);
    fn bool(&mut self, key: &str, b: bool);
    fn null(&mut self, key: &str);

    fn in_child(&mut self, key: &str, block: &dyn Fn(&mut dyn Tracer));
    fn in_list(&mut self, key: &str, block: &dyn Fn(&mut dyn ListTracer));

    fn component(&mut self, name: &str) {
        self.string("component", name.into());
    }
}

pub trait ListTracer {
    fn child(&mut self, value: &dyn Trace);
    fn int(&mut self, i: i64);
    fn string(&mut self, s: &TString<'_>);
    fn bool(&mut self, b: bool);

    fn in_child(&mut self, block: &dyn Fn(&mut dyn Tracer));
    fn in_list(&mut self, block: &dyn Fn(&mut dyn ListTracer));
}

/// Generic tracer based on a TraceWriter.
pub struct JsonTracer<F: FnMut(&str)> {
    write_fn: F,
    write_buf: [u8; 32],
    buf_pos: usize,
    first: bool,
}

impl<F: FnMut(&str)> JsonTracer<F> {
    pub fn new(write_fn: F) -> Self {
        Self {
            write_fn,
            write_buf: [0; 32],
            buf_pos: 0,
            first: true,
        }
    }

    fn maybe_comma(&mut self) {
        if !self.first {
            (self.write_fn)(", ");
        }
        self.first = false;
    }

    fn write_int(&mut self, i: i64) {
        let s = format_i64(i, &mut self.write_buf).unwrap_or("\"###NUMERR###\"");
        (self.write_fn)(s);
    }

    // SAFETY: there must be a valid utf8 string in write_buf[..buf_pos]
    unsafe fn flush_buf(&mut self) {
        if self.buf_pos == 0 {
            return;
        }
        let substr = &self.write_buf[..self.buf_pos];
        let s = unsafe { core::str::from_utf8_unchecked(substr) };
        (self.write_fn)(s);
        self.buf_pos = 0;
    }

    // SAFETY: there must be a valid utf8 string in write_buf[..buf_pos].
    // Given that there is valid utf8 at start, there will be valid utf8 when done.
    unsafe fn push_or_flush(&mut self, ch: char) {
        let size = ch.len_utf8();
        if self.buf_pos + size > self.write_buf.len() {
            unsafe { self.flush_buf() };
        }
        ch.encode_utf8(&mut self.write_buf[self.buf_pos..]);
        self.buf_pos += size;
    }

    fn write_str_quoted(&mut self, s: &str) {
        self.buf_pos = 0;
        // SAFETY: we clear the writebuf by resetting buf_pos to 0, so its contents
        // are only affected by push_or_flush, which keeps contents of write_buf
        // correct.
        unsafe {
            self.push_or_flush('"');
            for mut ch in s.chars() {
                if ch == '\\' || ch == '"' {
                    self.push_or_flush('\\');
                } else if ch == '\n' {
                    self.push_or_flush('\\');
                    ch = 'n';
                }
                self.push_or_flush(ch);
            }
            self.push_or_flush('"');
            self.flush_buf();
        }
    }

    fn key(&mut self, key: &str) {
        self.maybe_comma();
        self.write_str_quoted(key);
        (self.write_fn)(": ");
    }

    pub fn root(&mut self, block: &dyn Fn(&mut dyn Tracer)) {
        (self.write_fn)("{");
        block(self);
        (self.write_fn)("}");
    }
}

impl<F: FnMut(&str)> ListTracer for JsonTracer<F> {
    fn child(&mut self, value: &dyn Trace) {
        ListTracer::in_child(self, &|t| value.trace(t));
    }

    fn int(&mut self, i: i64) {
        self.maybe_comma();
        self.write_int(i);
    }

    fn string(&mut self, s: &TString<'_>) {
        self.maybe_comma();
        s.map(|s| self.write_str_quoted(s));
    }

    fn bool(&mut self, b: bool) {
        self.maybe_comma();
        (self.write_fn)(if b { "true" } else { "false" });
    }

    fn in_child(&mut self, block: &dyn Fn(&mut dyn Tracer)) {
        self.maybe_comma();
        self.first = true;
        (self.write_fn)("{");
        block(self);
        (self.write_fn)("}");
        self.first = false;
    }

    fn in_list(&mut self, block: &dyn Fn(&mut dyn ListTracer)) {
        self.maybe_comma();
        self.first = true;
        (self.write_fn)("[");
        block(self);
        (self.write_fn)("]");
        self.first = false;
    }
}

impl<F: FnMut(&str)> Tracer for JsonTracer<F> {
    fn child(&mut self, key: &str, value: &dyn Trace) {
        Tracer::in_child(self, key, &|t| value.trace(t));
    }

    fn int(&mut self, key: &str, i: i64) {
        self.key(key);
        self.write_int(i);
    }

    fn string(&mut self, key: &str, s: TString<'_>) {
        self.key(key);
        s.map(|s| self.write_str_quoted(s));
    }

    fn bool(&mut self, key: &str, b: bool) {
        self.key(key);
        (self.write_fn)(if b { "true" } else { "false" });
    }

    fn null(&mut self, key: &str) {
        self.key(key);
        (self.write_fn)("null");
    }

    fn in_child(&mut self, key: &str, block: &dyn Fn(&mut dyn Tracer)) {
        self.key(key);
        (self.write_fn)("{");
        self.first = true;
        block(self);
        (self.write_fn)("}");
        self.first = false;
    }

    fn in_list(&mut self, key: &str, block: &dyn Fn(&mut dyn ListTracer)) {
        self.key(key);
        (self.write_fn)("[");
        self.first = true;
        block(self);
        (self.write_fn)("]");
        self.first = false;
    }
}

/// Value that can describe own structure and data using the `Tracer`
/// interface.
pub trait Trace {
    fn trace(&self, t: &mut dyn Tracer);
}

#[cfg(test)]
pub mod tests {
    use serde_json::Value;

    use super::*;

    pub fn trace(val: &impl Trace) -> Value {
        let mut buf = Vec::new();
        let mut tracer = JsonTracer::new(|text| buf.extend_from_slice(text.as_bytes()));
        tracer.root(&|t| val.trace(t));
        let s = String::from_utf8(buf).unwrap();
        //crate::micropython::print::print(s.as_str());
        s.parse().unwrap()
    }
}
