use core::cmp::Ordering;
#[cfg(feature = "debug")]
use core::fmt;
use core::marker::PhantomData;

use super::array::ByteArray;

/// A key: a byte array up to naming. Every `[u8; N]` is one, and so is a newtype over one,
/// which keeps an application's keys apart from its digests at the type level. The width is
/// the array's, and [`ByteArray`] is sealed, so there is nothing to declare and nothing to
/// get wrong.
///
/// A key that needs an encoding, say a `u32` as its big-endian bytes, is not covered: wrap
/// the array and encode at construction. Should that become common, `as_bytes` can turn into
/// `fn to_bytes(&self) -> Self::Bytes`, returning by value. Every array and newtype keeps
/// working, but the trait then has to require that the encoding is injective and agrees with
/// `Eq`, and that `from_bytes` is total, since the trie identifies a key by its bytes and the
/// terminal key of a proof comes from the host. Deferred until a caller needs it.
///
/// Bits are numbered MSB-first: bit 0 is the top bit of byte 0. The tree routes by these
/// bits. A branch names its crit bit as a [`BitPos`], which bounds the key width; a wider key
/// type fails to compile wherever one of its positions would be made.
pub trait Key: Copy + Eq {
    /// The array the key is.
    type Bytes: ByteArray;

    /// The key's bytes.
    fn as_bytes(&self) -> &Self::Bytes;

    /// The key with these bytes.
    fn from_bytes(bytes: Self::Bytes) -> Self;
}

impl<const N: usize> Key for [u8; N] {
    type Bytes = Self;

    fn as_bytes(&self) -> &Self {
        self
    }

    fn from_bytes(bytes: Self) -> Self {
        bytes
    }
}

/// Width of `K` in bytes.
pub const fn key_len<K: Key>() -> usize {
    K::Bytes::LEN
}

/// Width of `K` in bits.
pub const fn key_bits<K: Key>() -> usize {
    8 * key_len::<K>()
}

/// The position of a bit in a key of type `K`, MSB-first: 0 is the top bit of byte 0. It lies
/// inside the key by construction.
///
/// A branch names the bit it splits on, so positions enter the branch preimage and the proof
/// format. This is the one place that fixes their encoding, a big-endian `u16`, and with it
/// the widest key: one of 65536 bits.
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct BitPos<K: Key>(
    u16,
    /// No `K` is stored, but it fixes the key width the position lies within.
    PhantomData<K>,
);

impl<K: Key> BitPos<K> {
    /// The key's width in bits. Every position is made through it, which is what refuses a
    /// key too wide for the encoding.
    const BITS: usize = {
        assert!(
            key_bits::<K>() <= 1 << 16,
            "a key has more bits than a BitPos can address"
        );
        key_bits::<K>()
    };

    /// Width in the encodings and on the wire.
    pub const LEN: usize = 2;

    /// Position `i`, or `None` if the key has no such bit.
    #[expect(
        clippy::cast_possible_truncation,
        reason = "`i` is below `BITS`, which fits"
    )]
    pub const fn new(i: usize) -> Option<Self> {
        if i < Self::BITS {
            Some(Self(i as u16, PhantomData))
        } else {
            None
        }
    }

    /// The position as a number.
    pub const fn index(self) -> usize {
        self.0 as usize
    }

    /// The position's encoding.
    pub fn to_bytes(self) -> [u8; 2] {
        self.0.to_be_bytes()
    }

    /// A position from its encoding, or `None` if the key has no such bit.
    pub fn from_bytes(bytes: [u8; 2]) -> Option<Self> {
        Self::new(usize::from(u16::from_be_bytes(bytes)))
    }
}

// By hand: a derive would order and print positions only for `K: Ord` and `K: Debug`.

impl<K: Key> PartialOrd for BitPos<K> {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl<K: Key> Ord for BitPos<K> {
    fn cmp(&self, other: &Self) -> Ordering {
        self.0.cmp(&other.0)
    }
}

#[cfg(feature = "debug")]
impl<K: Key> fmt::Debug for BitPos<K> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_tuple("BitPos").field(&self.0).finish()
    }
}

/// Bit `i` of `key`.
pub fn bit<K: Key>(key: &K, i: BitPos<K>) -> bool {
    let i = i.index();
    (key.as_bytes().as_ref()[i / 8] >> (7 - i % 8)) & 1 == 1
}

/// A child of a branch. A key goes right where its bit at the branch's crit bit is 1.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Side {
    Left,
    Right,
}

impl Side {
    /// The side `key` takes at the branch on `crit_bit`.
    pub(crate) fn of<K: Key>(key: &K, crit_bit: BitPos<K>) -> Self {
        if bit(key, crit_bit) {
            Self::Right
        } else {
            Self::Left
        }
    }

    /// `[left, right]` from the child on this side and the other one.
    pub(crate) fn place<T>(self, hit: T, other: T) -> [T; 2] {
        match self {
            Self::Left => [hit, other],
            Self::Right => [other, hit],
        }
    }

    /// The child on this side and the other one, from `[left, right]`: the inverse of `place`,
    /// needed only by the prover.
    #[cfg(feature = "use_std")]
    pub(crate) fn pick<T>(self, [left, right]: [T; 2]) -> (T, T) {
        match self {
            Self::Left => (left, right),
            Self::Right => (right, left),
        }
    }
}

/// The first bit on which two keys differ, or `None` if they are equal.
pub fn crit_bit<K: Key>(a: &K, b: &K) -> Option<BitPos<K>> {
    a.as_bytes()
        .as_ref()
        .iter()
        .zip(b.as_bytes().as_ref())
        .enumerate()
        .find_map(|(i, (x, y))| {
            let diff = x ^ y;
            // A bit of byte `i` is a bit of the key.
            (diff != 0).then(|| BitPos::new(8 * i + diff.leading_zeros() as usize).unwrap())
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bits_are_msb_first() {
        let key = [0b1000_0000u8, 0b0000_0001];
        assert_eq!(key_bits::<[u8; 2]>(), 16);
        let bits: Vec<bool> = (0..16)
            .map(|i| bit(&key, BitPos::new(i).unwrap()))
            .collect();
        let expected = [true, false, false, false, false, false, false, false]
            .into_iter()
            .chain([false, false, false, false, false, false, false, true]);
        assert!(bits.into_iter().eq(expected));
    }

    #[test]
    fn crit_bit_is_the_first_difference() {
        assert_eq!(crit_bit(&[0b0000_0000u8], &[0b0010_0000]), BitPos::new(2));
        assert_eq!(crit_bit(&[0b0000_0000u8], &[0b0000_1111]), BitPos::new(4));
        assert_eq!(
            crit_bit(&[0xffu8, 0b0111_1111], &[0xff, 0b1111_1111]),
            BitPos::new(8)
        );
        assert_eq!(crit_bit(&[0u8; 32], &[0u8; 32]), None);
        let (mut a, mut b) = ([0u8; 32], [0u8; 32]);
        (a[31], b[31]) = (0b0000_0010, 0b0000_0011);
        assert_eq!(crit_bit(&a, &b), BitPos::new(255));
    }

    #[test]
    fn a_position_lies_inside_its_key() {
        type Pos = BitPos<[u8; 2]>;
        let last = Pos::new(15).unwrap();
        assert_eq!(Pos::new(16), None);
        assert_eq!(Pos::from_bytes([0, 15]), Some(last));
        assert_eq!(Pos::from_bytes([0, 16]), None);
        assert_eq!(Pos::from_bytes([1, 0]), None);
        assert_eq!((last.index(), last.to_bytes()), (15, [0, 15]));
        assert!(Pos::new(3) < Pos::new(4));
    }

    #[test]
    fn a_newtype_is_a_key() {
        #[derive(Clone, Copy, PartialEq, Eq, Debug)]
        struct Wrapped([u8; 2]);
        impl Key for Wrapped {
            type Bytes = [u8; 2];
            fn as_bytes(&self) -> &[u8; 2] {
                &self.0
            }
            fn from_bytes(bytes: [u8; 2]) -> Self {
                Self(bytes)
            }
        }
        let key = Wrapped::from_bytes([0b0000_0001, 0]);
        assert_eq!((key_len::<Wrapped>(), key_bits::<Wrapped>()), (2, 16));
        let (seven, eight) = (BitPos::new(7).unwrap(), BitPos::new(8).unwrap());
        assert!(bit(&key, seven) && !bit(&key, eight));
        assert_eq!(crit_bit(&key, &Wrapped([0, 0])), Some(seven));
    }
}
