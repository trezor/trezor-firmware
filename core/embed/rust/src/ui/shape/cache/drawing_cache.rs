use super::zlib_cache::ZlibCache;

#[cfg(feature = "ui_blurring")]
use super::blur_cache::BlurCache;

#[cfg(feature = "ui_jpeg_decoder")]
use super::jpeg_cache::JpegCache;

use core::cell::{RefCell, RefMut};
use without_alloc::alloc::LocalAllocLeakExt;

const ALIGN_PAD: usize = 8;

#[cfg(feature = "xframebuff")]
const ZLIB_CACHE_SLOTS: usize = 1;
#[cfg(not(feature = "xframebuff"))]
const ZLIB_CACHE_SLOTS: usize = 3;

const RENDER_BUFF_SIZE: usize = (240 * 2 * 16) + ALIGN_PAD;

#[cfg(feature = "model_mercury")]
const IMAGE_BUFF_SIZE: usize = 240 * 240 + ALIGN_PAD;
#[cfg(not(feature = "model_mercury"))]
const IMAGE_BUFF_SIZE: usize = 2048 + ALIGN_PAD;

pub type ImageBuff = [u8; IMAGE_BUFF_SIZE];
pub type RenderBuff = [u8; RENDER_BUFF_SIZE];

pub type ImageBuffRef<'a> = RefMut<'a, ImageBuff>;
pub type RenderBuffRef<'a> = RefMut<'a, RenderBuff>;

pub struct DrawingCache<'a> {
    image_buff: &'a RefCell<ImageBuff>,
    zlib_cache: RefCell<ZlibCache<'a>>,

    #[cfg(feature = "ui_jpeg_decoder")]
    jpeg_cache: RefCell<JpegCache<'a>>,

    #[cfg(feature = "ui_blurring")]
    blur_cache: RefCell<BlurCache<'a>>,

    #[cfg(not(feature = "xframebuff"))]
    render_buff: &'a RefCell<RenderBuff>,
}

fn alloc_buf<'a, const S: usize, B>(bump: &'a B) -> Option<&'a RefCell<[u8; S]>>
where
    B: LocalAllocLeakExt<'a>,
{
    Some(bump.alloc_t()?.uninit.init(RefCell::new([0; S])))
}

impl<'a> DrawingCache<'a> {
    pub fn new<TA, TB>(bump_a: &'a TA, bump_b: &'a TB) -> Self
    where
        TA: LocalAllocLeakExt<'a>,
        TB: LocalAllocLeakExt<'a>,
    {
        Self {
            image_buff: unwrap!(alloc_buf(bump_b), "Toif buff alloc"),
            zlib_cache: RefCell::new(unwrap!(
                ZlibCache::new(bump_a, ZLIB_CACHE_SLOTS),
                "ZLIB cache alloc"
            )),
            #[cfg(feature = "ui_jpeg_decoder")]
            jpeg_cache: RefCell::new(unwrap!(JpegCache::new(bump_a), "JPEG cache alloc")),
            #[cfg(feature = "ui_blurring")]
            blur_cache: RefCell::new(unwrap!(BlurCache::new(bump_a), "Blur cache alloc")),

            #[cfg(not(feature = "xframebuff"))]
            render_buff: unwrap!(alloc_buf(bump_b), "Render buff alloc"),
        }
    }

    /// Returns an object for decompression of TOIF images
    pub fn zlib(&self) -> RefMut<ZlibCache<'a>> {
        self.zlib_cache.borrow_mut()
    }

    /// Returns an object for decompression of JPEG images
    #[cfg(feature = "ui_jpeg_decoder")]
    pub fn jpeg(&self) -> RefMut<JpegCache<'a>> {
        self.jpeg_cache.borrow_mut()
    }

    /// Returns an object providing blurring algorithm
    #[cfg(feature = "ui_blurring")]
    pub fn blur(&self) -> RefMut<BlurCache<'a>> {
        self.blur_cache.borrow_mut()
    }

    /// Returns a buffer used for ProgressiveRenderer slice
    #[cfg(not(feature = "xframebuff"))]
    pub fn render_buff(&self) -> Option<RenderBuffRef<'a>> {
        self.render_buff.try_borrow_mut().ok()
    }

    /// Returns a buffer for intended for drawing of
    /// QrCode or ToifImage
    pub fn image_buff(&self) -> Option<ImageBuffRef<'a>> {
        self.image_buff.try_borrow_mut().ok()
    }

    pub const fn get_bump_a_size() -> usize {
        let mut size = 0;

        size += ZlibCache::get_bump_size(ZLIB_CACHE_SLOTS);

        #[cfg(feature = "ui_jpeg_decoder")]
        {
            size += JpegCache::get_bump_size();
        }

        #[cfg(feature = "ui_blurring")]
        {
            size += BlurCache::get_bump_size();
        }

        size
    }

    pub const fn get_bump_b_size() -> usize {
        let mut size = 0;

        #[cfg(not(feature = "xframebuff"))]
        {
            size += core::mem::size_of::<RefCell<RenderBuff>>();
        }

        size += core::mem::size_of::<RefCell<ImageBuff>>();

        size
    }
}
