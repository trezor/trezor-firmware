use crate::micropython::buffer::StrBuffer;

/// Parse interpolation format string.
pub fn parse(format: impl Into<StrBuffer>) -> impl Iterator<Item = Item> {
    let iter = Interpolate {
        format: format.into(),
    };
    iter.filter(|part| !matches!(part, Item::Text(s) if s.is_empty()))
}

struct Interpolate {
    format: StrBuffer,
}

#[cfg_attr(test, derive(Debug))]
pub enum Item {
    Text(StrBuffer),
    Arg(usize),
}

#[cfg(test)]
impl PartialEq for Item {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Text(l), Self::Text(r)) => l.as_ref() == r.as_ref(),
            (Self::Arg(l), Self::Arg(r)) => l == r,
            _ => false,
        }
    }
}

impl Iterator for Interpolate {
    type Item = Item;

    fn next(&mut self) -> Option<Self::Item> {
        if self.format.is_empty() {
            return None; // iteration is over
        }
        // check 3-byte prefix (if exists) for a valid interpolation pattern
        let prefix: Option<[u8; 3]> = self
            .format
            .as_bytes()
            .get(..3)
            .and_then(|s| s.try_into().ok());
        match prefix {
            Some([b'{', c, b'}']) if c.is_ascii_digit() => {
                let arg = c - b'0';
                self.format = self.format.skip_prefix(3);
                return Some(Item::Arg(arg.into()));
            }
            _ => (),
        };
        let next_offset = self
            .format
            .as_bytes()
            .iter()
            .skip(1)
            .position(|&c| c == b'{')
            .map_or_else(|| self.format.len(), |pos| pos + 1);

        let part = Item::Text(self.format.prefix(next_offset));
        self.format = self.format.skip_prefix(next_offset);
        Some(part)
    }
}

#[cfg(test)]
mod tests {
    use crate::strutil::ShortString;

    #[test]
    fn test_interpolate() {
        use super::*;

        fn check(s: &'static str, expected: &'static str) {
            let mut res = ShortString::new();
            for item in parse(s) {
                unwrap!(match item {
                    Item::Text(buf) => res.push_str(buf.as_ref()),
                    Item::Arg(i) => res.push_str(&format!("{}{}", i, i)),
                });
            }
            assert_eq!(res, expected);
        }

        check("", "");
        check("{", "{");
        check("}", "}");
        check("{}", "{}");
        check("123", "123");
        check("{0}", "00");

        check("A {1}", "A 11");
        check("{1} A", "11 A");
        check("{1}{2}{3}", "112233");

        check("A {1} B {2} C{}{}$", "A 11 B 22 C{}{}$");
        check("}{ {x}_{0}{{}}abc{", "}{ {x}_00{{}}abc{");
        check("{}{{}}{{{}}}}123", "{}{{}}{{{}}}}123");
    }
}
