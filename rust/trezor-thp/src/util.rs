pub(crate) fn prepare_zeroed<const C: usize>(buf: &mut heapless::Vec<u8, C>) {
    buf.clear();
    buf.resize(buf.capacity(), 0u8).unwrap();
}

// Ord::max is not (yet) const.
pub(crate) const fn max(lhs: usize, rhs: usize) -> usize {
    if lhs > rhs { lhs } else { rhs }
}
