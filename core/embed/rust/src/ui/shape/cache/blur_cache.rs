use super::super::algo::{BlurAlgorithm, BlurBuff};
use crate::ui::geometry::Offset;
use core::cell::UnsafeCell;
use without_alloc::alloc::LocalAllocLeakExt;

pub struct BlurCache<'a> {
    algo: Option<BlurAlgorithm<'a>>,
    buff: &'a UnsafeCell<BlurBuff>,
    tag: u32,
}

impl<'a> BlurCache<'a> {
    pub fn new<'alloc: 'a, T>(bump: &'alloc T) -> Option<Self>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let buff = bump
            .alloc_t::<UnsafeCell<BlurBuff>>()?
            .uninit
            .init(UnsafeCell::new([0; 7928])); // TODO !!! 7928

        Some(Self {
            algo: None,
            buff,
            tag: 0,
        })
    }

    pub fn get(
        &mut self,
        size: Offset,
        radius: usize,
        tag: Option<u32>,
    ) -> Result<(&mut BlurAlgorithm<'a>, u32), ()> {
        if let Some(tag) = tag {
            if self.tag == tag {
                return Ok((unwrap!(self.algo.as_mut()), self.tag));
            }
        }

        // Drop the existing blurring inbstance holding
        // a mutable reference to its scratchpad buffer
        self.algo = None;
        self.tag += 1;

        // Now there's nobody else holding any reference to our buffer
        // so we can get mutable reference and pass it to a new
        // instance of the blurring algorithm
        let buff = unsafe { &mut *self.buff.get() };

        self.algo = Some(BlurAlgorithm::new(size, radius, buff)?);

        Ok((unwrap!(self.algo.as_mut()), self.tag))
    }
}
