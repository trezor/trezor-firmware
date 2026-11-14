//! rkyv serialization of app IPC messages on Core's side.

use rkyv::api::high::{to_bytes_in_with_alloc, HighSerializer};
use rkyv::rancor::Failure;
use rkyv::ser::allocator::{Arena, ArenaHandle};
use rkyv::util::AlignedVec;
use rkyv::Serialize;

use crate::micropython::error::Error;
use crate::micropython::obj::Obj;
use crate::micropython::tracked_allocator::with_alloc;

/// Alignment of serialized messages. MicroPython's tracked allocator, which
/// backs Core's heap, only guarantees 8 bytes on 32-bit targets (16-byte GC
/// blocks minus the 8-byte tracking header), so rkyv's default of 16 would
/// fail there. All archived message types need at most 4.
const ALIGNMENT: usize = 8;

/// Serializes `value` into a MicroPython `bytes` object.
///
/// Core may only use the heap within a `with_alloc` scope, which must leave
/// nothing allocated: the scratch arena and the serialized buffer are dropped
/// within it, and only the GC-managed copy is returned.
pub fn to_bytes_obj<T>(value: &T) -> Result<Obj, Error>
where
    T: for<'a> Serialize<HighSerializer<AlignedVec<ALIGNMENT>, ArenaHandle<'a>, Failure>>,
{
    with_alloc(|| -> Result<Obj, Error> {
        let mut arena = Arena::new();
        let bytes: AlignedVec<ALIGNMENT> =
            to_bytes_in_with_alloc(value, AlignedVec::new(), arena.acquire())
                .map_err(|_| Error::RuntimeError(c"Failed to serialize message"))?;
        let bytes: &[u8] = bytes.as_slice();
        bytes.try_into()
    })
}
