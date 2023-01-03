/*----------------------------------------------------------------------------/
/ TJpgDec - Tiny JPEG Decompressor R0.03+trezor               (C)ChaN, 2021
/-----------------------------------------------------------------------------/
/ The TJpgDec is a generic JPEG decompressor module for tiny embedded systems.
/ This is a free software that opened for education, research and commercial
/  developments under license policy of following terms.
/
/  Copyright (C) 2021, ChaN, all right reserved.
/
/ * The TJpgDec module is a free software and there is NO WARRANTY.
/ * No restriction on use. You can use, modify and redistribute it for
/   personal, non-profit or commercial products UNDER YOUR RESPONSIBILITY.
/ * Redistributions of source code must retain the above copyright notice.
/
/-----------------------------------------------------------------------------/
/ Oct 04, 2011 R0.01  First release.
/ Feb 19, 2012 R0.01a Fixed decompression fails when scan starts with an escape seq.
/ Sep 03, 2012 R0.01b Added JD_TBLCLIP option.
/ Mar 16, 2019 R0.01c Supprted stdint.h.
/ Jul 01, 2020 R0.01d Fixed wrong integer type usage.
/ May 08, 2021 R0.02  Supprted grayscale image. Separated configuration options.
/ Jun 11, 2021 R0.02a Some performance improvement.
/ Jul 01, 2021 R0.03  Added JD_FASTDECODE option.
/                     Some performance improvement.
/ Jan 02, 2023        Rust version by Trezor Company, modified to meet our needs.

Trezor modifications:
 - included overflow detection from https://github.com/cmumford/TJpgDec
 - removed JD_FASTDECODE=0 option
 - removed JD_TBLCLIP option
 - allowed interrupted functionality
 - tighter integration into Trezor codebase by using our data structures
 - removed generic input and output functions, replaced by our specific functionality
/----------------------------------------------------------------------------*/

use crate::{
    trezorhal::{
        buffers::{get_jpeg_work_buffer, BufferJpeg},
        display::pixeldata,
    },
    ui::{
        constant,
        display::set_window,
        geometry::{Offset, Point, Rect},
    },
};
use core::{
    f64::consts::{FRAC_1_SQRT_2, SQRT_2},
    mem, slice,
};

/// Specifies output pixel format.
///  0: RGB888 (24-bit/pix)
///  1: RGB565 (16-bit/pix)
///  2: Grayscale (8-bit/pix)
const JD_FORMAT: u32 = 1;

/// Switches output descaling feature.
/// 0: Disable
/// 1: Enable
const JD_USE_SCALE: u32 = 1;

/// Optimization level
/// 0: NOT IMPLEMENTED Basic optimization. Suitable for 8/16-bit MCUs.
/// 1: + 32-bit barrel shifter. Suitable for 32-bit MCUs.
/// 2: + Table conversion for huffman decoding (wants 6 << HUFF_BIT bytes of
/// RAM)
const JD_FASTDECODE: u32 = 2;

/// Specifies size of stream input buffer
const JD_SZBUF: usize = 512;

const HUFF_BIT: u32 = 10;
const HUFF_LEN: u32 = 1 << HUFF_BIT;
const HUFF_MASK: u32 = HUFF_LEN - 1;

const NUM_DEQUANTIZER_TABLES: usize = 4;

#[derive(PartialEq, Eq)]
pub enum Error {
    /// Interrupted by output function, call `JDEC::decomp` to continue.
    Interrupted,
    /// Device error or wrong termination of input stream.
    Input,
    /// Insufficient memory pool for the image.
    MemoryPool,
    /// Insufficient stream input buffer.
    MemoryInput,
    /// Parameter error.
    Parameter,
    /// Data format error (may be broken data).
    InvalidData,
    /// Not supported JPEG standard.
    UnsupportedJpeg,
}

pub struct JDEC<'i, 'p> {
    dctr: usize,
    dptr: usize,
    inbuf: &'p mut [u8],
    dbit: u8,
    scale: u8,
    msx: u8,
    msy: u8,
    qtid: [u8; 3],
    ncomp: u8,
    dcv: [i16; 3],
    nrst: u16,
    rst: u16,
    rsc: u16,
    width: u16,
    height: u16,
    huffbits: [[&'p mut [u8]; 2]; 2],
    huffcode: [[&'p mut [u16]; 2]; 2],
    huffcode_len: [[usize; 2]; 2],
    huffdata: [[&'p mut [u8]; 2]; 2],
    qttbl: [&'p mut [i32]; 4],
    wreg: u32,
    marker: u8,
    longofs: [[u8; 2]; 2],
    hufflut_ac: [&'p mut [u16]; 2],
    hufflut_dc: [&'p mut [u8]; 2],
    workbuf: &'p mut [i32],
    mcubuf: &'p mut [i16],
    pool: &'p mut [u8],
    input_func: &'i mut dyn JpegInput,
}

/// Zigzag-order to raster-order conversion table
#[rustfmt::skip]
const ZIG: [u8; 64] = [
     0,  1,  8, 16,  9,  2,  3, 10, 17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63,
];

macro_rules! f {
    ($num:expr) => {{
        ($num * 8192_f64) as u16
    }};
}

/// Input scale factor of Arai algorithm
/// (scaled up 16 bits for fixed point operations)
#[rustfmt::skip]
const IPSF: [u16; 64] = [
    f!(1.00000), f!(1.38704), f!(1.30656),       f!(1.17588), f!(1.00000), f!(0.78570), f!(0.54120),       f!(0.27590),
    f!(1.38704), f!(1.92388), f!(1.81226),       f!(1.63099), f!(1.38704), f!(1.08979), f!(0.75066),       f!(0.38268),
    f!(1.30656), f!(1.81226), f!(1.70711),       f!(1.53636), f!(1.30656), f!(1.02656), f!(FRAC_1_SQRT_2), f!(0.36048),
    f!(1.17588), f!(1.63099), f!(1.53636),       f!(1.38268), f!(1.17588), f!(0.92388), f!(0.63638),       f!(0.32442),
    f!(1.00000), f!(1.38704), f!(1.30656),       f!(1.17588), f!(1.00000), f!(0.78570), f!(0.54120),       f!(0.27590),
    f!(0.78570), f!(1.08979), f!(1.02656),       f!(0.92388), f!(0.78570), f!(0.61732), f!(0.42522),       f!(0.21677),
    f!(0.54120), f!(0.75066), f!(FRAC_1_SQRT_2), f!(0.63638), f!(0.54120), f!(0.42522), f!(0.29290),       f!(0.14932),
    f!(0.27590), f!(0.38268), f!(0.36048),       f!(0.32442), f!(0.27590), f!(0.21678), f!(0.14932),       f!(0.07612),
];

impl<'i, 'p> JDEC<'i, 'p> {
    /// Allocate a memory block from memory pool
    /// `self`: decompressor object reference
    /// `ndata` number of `T` items to allocate
    fn alloc_slice<T>(&mut self, ndata: usize) -> Result<&'p mut [T], Error> {
        let ndata_bytes = ndata * mem::size_of::<T>();
        let ndata_aligned = (ndata_bytes + 3) & !3;
        if self.pool.len() < ndata_aligned {
            // Err: not enough memory
            return Err(Error::MemoryPool);
        }

        // SAFETY:
        //  - Memory is valid because it comes from a valid slice.
        //  - Memory is initialized because here we consider integers always
        //    initialized.
        //  - The slices do not overlap and the original reference is overwritten,
        //    ensuring that the returned references are exclusive.
        unsafe {
            let data = slice::from_raw_parts_mut(self.pool.as_mut_ptr() as _, ndata);
            let newpool = slice::from_raw_parts_mut(
                self.pool.as_mut_ptr().add(ndata_aligned),
                self.pool.len() - ndata_aligned,
            );
            self.pool = newpool;
            Ok(data)
        }
    }

    fn jpeg_in(&mut self, inbuf_offset: Option<usize>, n_data: usize) -> usize {
        if let Some(offset) = inbuf_offset {
            let inbuf = &mut self.inbuf[offset..offset + n_data];
            self.input_func.read(Some(inbuf), n_data)
        } else {
            self.input_func.read(None, n_data)
        }
    }

    /// Create de-quantization and prescaling tables with a DQT segment
    /// `self`: decompressor object reference
    /// `ndata`: size of input data
    fn create_qt_tbl(&mut self, mut ndata: usize) -> Result<(), Error> {
        let mut i: u32;
        let mut d: u8;
        let mut data_idx = 0;
        while ndata != 0 {
            // Process all tables in the segment
            if ndata < 65 {
                // Err: table size is unaligned
                return Err(Error::InvalidData);
            }
            ndata -= 65;

            d = self.inbuf[data_idx]; // Get table property
            data_idx += 1;
            if d & 0xf0 != 0 {
                // Err: not 8-bit resolution
                return Err(Error::InvalidData);
            }
            i = (d & 3) as u32; // Get table ID

            // Allocate a memory block for the table
            // Register the table
            self.qttbl[i as usize] = self.alloc_slice(64)?;
            for zi in ZIG {
                // Load the table
                // Apply scale factor of Arai algorithm to the de-quantizers
                self.qttbl[i as usize][zi as usize] =
                    ((self.inbuf[data_idx] as u32) * IPSF[zi as usize] as u32) as i32;
                data_idx += 1;
            }
        }
        Ok(())
    }

    /// Create huffman code tables with a DHT segment
    /// `self`: decompressor object reference
    /// `ndata`: size of input data
    fn create_huffman_tbl(&mut self, mut ndata: usize) -> Result<(), Error> {
        let mut j: u32;
        let mut b: u32;
        let mut cls: usize;
        let mut num: usize;
        let mut np: usize;
        let mut d: u8;
        let mut hc: u16;
        let mut data_idx = 0;
        while ndata != 0 {
            // Process all tables in the segment
            if ndata < 17 {
                // Err: wrong data size
                return Err(Error::InvalidData);
            }
            ndata -= 17;
            d = self.inbuf[data_idx]; // Get table number and class
            data_idx += 1;
            if d & 0xee != 0 {
                // Err: invalid class/number
                return Err(Error::InvalidData);
            }
            cls = d as usize >> 4; // class = dc(0)/ac(1)
            num = d as usize & 0xf; // table number = 0/1
                                    // Allocate a memory block for the bit distribution table
            self.huffbits[num][cls] = self.alloc_slice(16)?;

            np = 0;
            for i in 0..16 {
                // Load number of patterns for 1 to 16-bit code
                // Get sum of code words for each code
                self.huffbits[num][cls][i] = self.inbuf[data_idx];
                np += self.inbuf[data_idx] as usize;
                data_idx += 1;
            }
            // Allocate a memory block for the code word table
            self.huffcode[num][cls] = self.alloc_slice(np)?;
            self.huffcode_len[num][cls] = np;

            // Re-build huffman code word table
            hc = 0;
            j = 0;
            for i in 0..16 {
                b = self.huffbits[num][cls][i] as u32;
                while b > 0 {
                    self.huffcode[num][cls][j as usize] = hc;
                    hc += 1;
                    j += 1;
                    b -= 1;
                }
                hc <<= 1;
            }
            if ndata < np {
                // Err: wrong data size
                return Err(Error::InvalidData);
            }
            ndata -= np;

            // Allocate a memory block for the decoded data
            self.huffdata[num][cls] = self.alloc_slice(np)?;

            // Load decoded data corresponds to each code word
            for i in 0..np {
                d = self.inbuf[data_idx];
                data_idx += 1;
                if cls == 0 && d > 11 {
                    return Err(Error::InvalidData);
                }
                self.huffdata[num][cls][i as usize] = d;
            }
            if JD_FASTDECODE == 2 {
                // Create fast huffman decode table
                let mut span: u32;
                let mut td: u32;
                let mut ti: u32;
                if cls != 0 {
                    // LUT for AC elements
                    self.hufflut_ac[num] = self.alloc_slice(HUFF_LEN as usize)?;
                    // Default value (0xFFFF: may be long code)
                    self.hufflut_ac[num].fill(0xffff);
                } else {
                    // LUT for DC elements
                    self.hufflut_dc[num] = self.alloc_slice(HUFF_LEN as usize)?;
                    // Default value (0xFF: may be long code)
                    self.hufflut_dc[num].fill(0xff);
                }
                let mut i = 0;

                // Create LUT
                for b in 0..HUFF_BIT {
                    j = self.huffbits[num][cls][b as usize] as u32;
                    while j != 0 {
                        // Index of input pattern for the code
                        ti = (self.huffcode[num][cls][i] << (((HUFF_BIT - 1) as u32) - b)) as u32
                            & HUFF_MASK;

                        if cls != 0 {
                            // b15..b8: code length, b7..b0: zero run and data length
                            td = self.huffdata[num][cls][i] as u32 | (b + 1) << 8;
                            i += 1;
                            span = 1 << ((HUFF_BIT - 1) - b);
                            while span != 0 {
                                span -= 1;
                                self.hufflut_ac[num][ti as usize] = td as u16;
                                ti += 1;
                            }
                        } else {
                            // b7..b4: code length, b3..b0: data length
                            td = self.huffdata[num][cls][i] as u32 | (b + 1) << 4;
                            i += 1;
                            span = 1 << ((HUFF_BIT - 1) - b);
                            while span != 0 {
                                span -= 1;
                                self.hufflut_dc[num][ti as usize] = td as u8;
                                ti += 1;
                            }
                        }
                        j -= 1;
                    }
                }
                // Code table offset for long code
                self.longofs[num][cls] = i as u8;
            }
        }
        Ok(())
    }

    /// Extract a huffman decoded data from input stream
    /// `self`: decompressor object reference
    /// `id`: table ID (0:Y, 1:C)
    /// `cls`: table class (0:DC, 1:AC)
    #[optimize(speed)]
    fn huffext(&mut self, id: usize, cls: usize) -> Result<i32, Error> {
        let mut dc: usize = self.dctr;
        let mut dp: usize = self.dptr;
        let mut d: u32;
        let mut flg: u32 = 0;
        let mut nc: u32;
        let mut bl: u32;
        let mut wbit: u32 = (self.dbit as i32 % 32) as u32;
        let mut w: u32 = self.wreg & ((1 << wbit) - 1);
        while wbit < 16 {
            // Prepare 16 bits into the working register
            if self.marker != 0 {
                d = 0xff; // Input stream has stalled for a marker. Generate
                          // stuff bits
            } else {
                if dc == 0 {
                    // Buffer empty, re-fill input buffer
                    dp = 0; // Top of input buffer
                    dc = self.jpeg_in(Some(0), JD_SZBUF);
                    if dc == 0 {
                        // Err: read error or wrong stream termination
                        return Err(Error::Input);
                    }
                }
                d = self.inbuf[dp] as u32;
                dp += 1;

                dc -= 1;
                if flg != 0 {
                    // In flag sequence?
                    flg = 0; // Exit flag sequence
                    if d != 0 {
                        // Not an escape of 0xFF but a marker
                        self.marker = d as u8;
                    }
                    d = 0xff;
                } else if d == 0xff {
                    // Is start of flag sequence?
                    // Enter flag sequence, get trailing byte
                    flg = 1;
                    continue;
                }
            }
            // Shift 8 bits in the working register
            w = w << 8 | d;
            wbit += 8;
        }
        self.dctr = dc;
        self.dptr = dp;
        self.wreg = w;

        let mut hb_idx = 0;
        let mut hc_idx = 0;
        let mut hd_idx = 0;

        if JD_FASTDECODE == 2 {
            // Table serch for the short codes
            d = w >> (wbit - HUFF_BIT); // Short code as table index
            if cls != 0 {
                // AC element
                d = self.hufflut_ac[id][d as usize] as u32; // Table decode
                if d != 0xffff {
                    // It is done if hit in short code
                    self.dbit = (wbit - (d >> 8)) as u8; // Snip the code length
                    return Ok((d & 0xff) as i32); // b7..0: zero run and
                                                  // following
                                                  // data bits
                }
            } else {
                // DC element
                d = self.hufflut_dc[id][d as usize] as u32; // Table decode
                if d != 0xff {
                    // It is done if hit in short code
                    self.dbit = (wbit - (d >> 4)) as u8; // Snip the code length
                    return Ok((d & 0xf) as i32); // b3..0: following data bits
                }
            }

            // Incremental serch for the codes longer than HUFF_BIT
            hb_idx = HUFF_BIT; // Bit distribution table
            hc_idx = self.longofs[id][cls]; // Code word table
            hd_idx = self.longofs[id][cls]; // Data table
            bl = (HUFF_BIT + 1) as u32;
        } else {
            // Incremental search for all codes
            bl = 1;
        }

        // Incremental search
        while bl <= 16 {
            nc = self.huffbits[id][cls][hb_idx as usize] as u32;
            hb_idx += 1;
            if nc != 0 {
                d = w >> (wbit - bl);
                loop {
                    // Search the code word in this bit length
                    if hc_idx as usize >= self.huffcode_len[id][cls] {
                        return Err(Error::InvalidData);
                    }
                    let val = self.huffcode[id][cls][hc_idx as usize];
                    if d == val as u32 {
                        // Matched?
                        self.dbit = (wbit - bl) as u8; // Snip the huffman code
                                                       // Return the decoded data
                        return Ok(self.huffdata[id][cls][hd_idx as usize] as i32);
                    }
                    hc_idx += 1;
                    hd_idx += 1;
                    nc -= 1;
                    if nc == 0 {
                        break;
                    }
                }
            }
            bl += 1;
        }

        // Err: code not found (may be collapted data)
        Err(Error::InvalidData)
    }

    /// Extract N bits from input stream
    /// `self`: decompressor object reference
    /// `nbit`: number of bits to extract (1 to 16)
    #[optimize(speed)]
    fn bitext(&mut self, nbit: u32) -> Result<i32, Error> {
        let mut dc: usize = self.dctr;
        let mut dp: usize = self.dptr;
        let mut d: u32;
        let mut flg: u32 = 0;
        let mut wbit: u32 = (self.dbit as i32 % 32) as u32;
        let mut w: u32 = self.wreg & ((1 << wbit) - 1);
        while wbit < nbit {
            // Prepare nbit bits into the working register
            if self.marker != 0 {
                d = 0xff; // Input stream stalled, generate stuff bits
            } else {
                if dc == 0 {
                    // Buffer empty, re-fill input buffer
                    dp = 0; // Top of input buffer
                    dc = self.jpeg_in(Some(0), JD_SZBUF);
                    if dc == 0 {
                        // Err: read error or wrong stream termination
                        return Err(Error::Input);
                    }
                }
                d = self.inbuf[dp] as u32;
                dp += 1;
                dc -= 1;
                if flg != 0 {
                    // In flag sequence?
                    flg = 0; // Exit flag sequence
                    if d != 0 {
                        // Not an escape of 0xFF but a marker
                        self.marker = d as u8;
                    }
                    d = 0xff;
                } else if d == 0xff {
                    // Is start of flag sequence?
                    flg = 1; // Enter flag sequence, get trailing byte
                    continue;
                }
            }
            w = w << 8 | d;
            wbit += 8;
        }
        self.wreg = w;
        self.dbit = (wbit - nbit) as u8;
        self.dctr = dc;
        self.dptr = dp;

        Ok((w >> ((wbit - nbit) % 32)) as i32)
    }

    /// Process restart interval
    /// `self`: decompressor object reference
    /// `rstn`: expected restart sequence number
    #[optimize(speed)]
    fn restart(&mut self, rstn: u16) -> Result<(), Error> {
        let mut dp = self.dptr;
        let mut dc: usize = self.dctr;
        let mut marker: u16;
        if self.marker != 0 {
            // Generate a maker if it has been detected
            marker = 0xff00 | self.marker as u16;
            self.marker = 0;
        } else {
            marker = 0;
            for _ in 0..2 {
                // Get a restart marker
                if dc == 0 {
                    // No input data is available, re-fill input buffer
                    dp = 0;
                    dc = self.jpeg_in(Some(0), JD_SZBUF);
                    if dc == 0 {
                        return Err(Error::Input);
                    }
                }
                // Get a byte
                let b = self.inbuf[dp] as u16;
                marker = marker << 8 | b;
                dp += 1;
                dc -= 1;
            }
            self.dptr = dp;
            self.dctr = dc;
        }

        // Check the marker
        if marker & 0xffd8 != 0xffd0 || marker & 7 != rstn & 7 {
            // Err: expected RSTn marker was not detected (may be collapted data)
            return Err(Error::InvalidData);
        }
        self.dbit = 0; // Discard stuff bits
                       // Reset DC offset
        self.dcv[0] = 0;
        self.dcv[1] = 0;
        self.dcv[2] = 0;
        Ok(())
    }

    /// Apply Inverse-DCT in Arai Algorithm
    /// `src`: input block data (de-quantized and pre-scaled for Arai Algorithm)
    /// `dst`: destination to store the block as byte array
    #[optimize(speed)]
    fn block_idct(src: &mut [i32], dst: &mut [i16]) {
        let m13: i32 = (SQRT_2 * 4096_f64) as i32;
        let m2: i32 = (1.08239f64 * 4096_f64) as i32;
        let m4: i32 = (2.61313f64 * 4096_f64) as i32;
        let m5: i32 = (1.84776f64 * 4096_f64) as i32;
        let mut v0: i32;
        let mut v1: i32;
        let mut v2: i32;
        let mut v3: i32;
        let mut v4: i32;
        let mut v5: i32;
        let mut v6: i32;
        let mut v7: i32;
        let mut t10: i32;
        let mut t11: i32;
        let mut t12: i32;
        let mut t13: i32;

        // Process columns
        for idx in 0..8 {
            // Get even elements
            v0 = src[idx];
            v1 = src[idx + 8 * 2];
            v2 = src[idx + 8 * 4];
            v3 = src[idx + 8 * 6];

            // Process the even elements
            t10 = v0 + v2;
            t12 = v0 - v2;
            t11 = ((v1 - v3) * m13) >> 12;
            v3 += v1;
            t11 -= v3;
            v0 = t10 + v3;
            v3 = t10 - v3;
            v1 = t11 + t12;
            v2 = t12 - t11;

            // Get odd elements
            v4 = src[idx + 8 * 7];
            v5 = src[idx + 8];
            v6 = src[idx + 8 * 5];
            v7 = src[idx + 8 * 3];

            // Process the odd elements
            t10 = v5 - v4;
            t11 = v5 + v4;
            t12 = v6 - v7;
            v7 += v6;
            v5 = ((t11 - v7) * m13) >> 12;
            v7 += t11;
            t13 = ((t10 + t12) * m5) >> 12;
            v4 = t13 - ((t10 * m2) >> 12);
            v6 = t13 - ((t12 * m4) >> 12) - v7;
            v5 -= v6;
            v4 -= v5;

            // Write-back transformed values
            src[idx] = v0 + v7;
            src[idx + 8 * 7] = v0 - v7;
            src[idx + 8] = v1 + v6;
            src[idx + 8 * 6] = v1 - v6;
            src[idx + 8 * 2] = v2 + v5;
            src[idx + 8 * 5] = v2 - v5;
            src[idx + 8 * 3] = v3 + v4;
            src[idx + 8 * 4] = v3 - v4;
        }

        // Process rows
        for idx in (0..64).step_by(8) {
            // Get even elements
            v0 = src[idx] + (128 << 8); // remove DC offset (-128) here
            v1 = src[idx + 2];
            v2 = src[idx + 4];
            v3 = src[idx + 6];

            // Process the even elements
            t10 = v0 + v2;
            t12 = v0 - v2;
            t11 = ((v1 - v3) * m13) >> 12;
            v3 += v1;
            t11 -= v3;
            v0 = t10 + v3;
            v3 = t10 - v3;
            v1 = t11 + t12;
            v2 = t12 - t11;

            // Get odd elements
            v4 = src[idx + 7];
            v5 = src[idx + 1];
            v6 = src[idx + 5];
            v7 = src[idx + 3];

            // Process the odd elements
            t10 = v5 - v4;
            t11 = v5 + v4;
            t12 = v6 - v7;
            v7 += v6;
            v5 = ((t11 - v7) * m13) >> 12;
            v7 += t11;
            t13 = ((t10 + t12) * m5) >> 12;
            v4 = t13 - ((t10 * m2) >> 12);
            v6 = t13 - ((t12 * m4) >> 12) - v7;
            v5 -= v6;
            v4 -= v5;

            // Descale the transformed values 8 bits and output a row
            dst[idx] = ((v0 + v7) >> 8) as i16;
            dst[idx + 7] = ((v0 - v7) >> 8) as i16;
            dst[idx + 1] = ((v1 + v6) >> 8) as i16;
            dst[idx + 6] = ((v1 - v6) >> 8) as i16;
            dst[idx + 2] = ((v2 + v5) >> 8) as i16;
            dst[idx + 5] = ((v2 - v5) >> 8) as i16;
            dst[idx + 3] = ((v3 + v4) >> 8) as i16;
            dst[idx + 4] = ((v3 - v4) >> 8) as i16;
        }
    }

    /// Load all blocks in an MCU into working buffer
    /// `self`: decompressor object reference
    #[optimize(speed)]
    fn mcu_load(&mut self) -> Result<(), Error> {
        let mut d: i32;
        let mut e: i32;
        let mut blk: u32;
        let mut bc: u32;
        let mut z: u32;
        let mut id: u32;
        let mut cmp: u32;
        let nby = (self.msx as i32 * self.msy as i32) as u32; // Number of Y blocks (1, 2 or 4)
        let mut mcu_buf_idx = 0; // Pointer to the first block of MCU
        blk = 0;
        while blk < nby + 2 {
            // Get nby Y blocks and two C blocks
            cmp = if blk < nby { 0 } else { blk - nby + 1 }; // Component number 0:Y, 1:Cb, 2:Cr
            if cmp != 0 && self.ncomp as i32 != 3 {
                // Clear C blocks if not exist (monochrome image)
                for i in 0..64 {
                    self.mcubuf[mcu_buf_idx + i] = 128;
                }
            } else {
                // Load Y/C blocks from input stream
                id = if cmp != 0 { 1 } else { 0 }; // Huffman table ID of this component

                // Extract a DC element from input stream
                d = self.huffext(id as usize, 0)?; // Extract a huffman coded data (bit length)
                bc = d as u32;
                d = self.dcv[cmp as usize] as i32; // DC value of previous block
                if bc != 0 {
                    // If there is any difference from previous block
                    e = self.bitext(bc)?; // Extract data bits
                    bc = 1 << (bc - 1); // MSB position
                    if e as u32 & bc == 0 {
                        e -= ((bc << 1) - 1) as i32; // Restore negative value
                                                     // if
                                                     // needed
                    }
                    d += e; // Get current value
                    self.dcv[cmp as usize] = d as i16; // Save current DC value
                                                       // for
                                                       // next block
                }
                // De-quantizer table ID for this component
                let dqidx = self.qtid[cmp as usize] as usize;
                if dqidx >= NUM_DEQUANTIZER_TABLES {
                    return Err(Error::InvalidData);
                }
                // De-quantize, apply scale factor of Arai algorithm and descale 8 bits
                let dfq = &self.qttbl[dqidx];
                self.workbuf[0] = (d * dfq[0]) >> 8;

                // Extract following 63 AC elements from input stream
                self.workbuf[1..64].fill(0); // Initialize all AC elements
                z = 1; // Top of the AC elements (in zigzag-order)
                loop {
                    // Extract a huffman coded value (zero runs and bit length)
                    d = self.huffext(id as usize, 1)?;
                    if d == 0 {
                        // EOB?
                        break;
                    }
                    bc = d as u32;
                    z += bc >> 4; // Skip leading zero run
                    if z >= 64 {
                        // Too long zero run
                        return Err(Error::InvalidData);
                    }
                    bc &= 0xf;
                    if bc != 0 {
                        // Bit length?
                        d = self.bitext(bc)?; // Extract data bits
                        bc = 1 << (bc - 1); // MSB position
                        if d as u32 & bc == 0 {
                            // Restore negative value if needed
                            d -= ((bc << 1) - 1) as i32;
                        }
                        let i = ZIG[z as usize] as u32; // Get raster-order index
                                                        // De-quantize, apply scale factor of Arai algorithm and descale 8 bits
                        let dqidx = self.qtid[cmp as usize] as usize;
                        if dqidx >= NUM_DEQUANTIZER_TABLES {
                            return Err(Error::InvalidData);
                        }
                        let dfq = &self.qttbl[dqidx];
                        self.workbuf[i as usize] = (d * dfq[i as usize]) >> 8;
                    }
                    z += 1;
                    if z >= 64 {
                        break;
                    }
                }

                // C components may not be processed if in grayscale output
                if JD_FORMAT != 2 || cmp == 0 {
                    // If no AC element or scale ratio is 1/8, IDCT can be omitted and the block is
                    // filled with DC value
                    if z == 1 || JD_USE_SCALE != 0 && self.scale == 3 {
                        d = (self.workbuf[0] / 256 + 128) as i32;
                        if JD_FASTDECODE >= 1 {
                            for i in 0..64 {
                                self.mcubuf[mcu_buf_idx + i] = d as i16;
                            }
                        } else {
                            self.mcubuf[..64].fill(d as i16);
                        }
                    } else {
                        // Apply IDCT and store the block to the MCU buffer
                        Self::block_idct(self.workbuf, &mut self.mcubuf[mcu_buf_idx..]);
                    }
                }
            }
            mcu_buf_idx += 64; // Next block
            blk += 1;
        }
        Ok(()) // All blocks have been loaded successfully
    }

    /// Output an MCU: Convert YCrCb to RGB and output it in RGB form
    /// `self`: decompressor object reference
    /// `x`: MCU location in the image
    /// `y`: MCU location in the image
    #[optimize(speed)]
    fn mcu_output(
        &mut self,
        mut x: u32,
        mut y: u32,
        output_func: &mut dyn JpegOutput,
    ) -> Result<(), Error> {
        // Adaptive accuracy for both 16-/32-bit systems
        let cvacc: i32 = if mem::size_of::<i32>() > 2 { 1024 } else { 128 };
        let mut yy: i32;
        let mut cb: i32;
        let mut cr: i32;
        let mut py_idx: usize;
        let mut pc_idx: usize;

        // MCU size (pixel)
        let mut mx = (self.msx as i32 * 8) as u32;
        let my = (self.msy as i32 * 8) as u32;

        // Output rectangular size (it may be clipped at right/bottom end of image)
        let mut rx = if (x + mx) <= self.width as u32 {
            mx
        } else {
            self.width as u32 - x
        };
        let mut ry = if (y + my) <= self.height as u32 {
            my
        } else {
            self.height as u32 - y
        };
        if JD_USE_SCALE != 0 {
            rx >>= self.scale;
            ry >>= self.scale;
            if rx == 0 || ry == 0 {
                // Skip this MCU if all pixel is to be rounded off
                return Ok(());
            }
            x >>= self.scale;
            y >>= self.scale;
        }
        let rect = Rect::from_top_left_and_size(
            Point::new(x as i16, y as i16),
            Offset::new(rx as i16, ry as i16),
        );

        // SAFETY: Aligning to u8 slice is safe, because the original slice is aligned
        // to 32 bits, therefore there are also no residuals (prefix/suffix).
        // The data in the slices are integers, so these are valid for both i32
        // and u8.
        let (_, workbuf, _) = unsafe { self.workbuf.align_to_mut::<u8>() };

        let mut pix_idx: usize = 0;
        let mut op_idx: usize;

        if JD_USE_SCALE == 0 || self.scale != 3 {
            // Not for 1/8 scaling
            if JD_FORMAT != 2 {
                // RGB output (build an RGB MCU from Y/C component)
                for iy in 0..my {
                    py_idx = 0;
                    pc_idx = 0;
                    if my == 16 {
                        // Double block height?
                        pc_idx += (64 * 4) + ((iy as usize >> 1) * 8);
                        if iy >= 8 {
                            py_idx += 64;
                        }
                    } else {
                        // Single block height
                        pc_idx += (mx * 8 + iy * 8) as usize;
                    }
                    py_idx += (iy * 8) as usize;
                    for ix in 0..mx {
                        cb = self.mcubuf[pc_idx] as i32 - 128; // Get Cb/Cr component and remove offset
                        cr = self.mcubuf[pc_idx + 64] as i32 - 128;
                        if mx == 16 {
                            // Double block width?
                            if ix == 8 {
                                // Jump to next block if double block height
                                py_idx += 64 - 8;
                            }
                            // Step forward chroma pointer every two pixels
                            pc_idx += (ix & 1) as usize;
                        } else {
                            // Single block width
                            // Step forward chroma pointer every pixel
                            pc_idx += 1;
                        }
                        // Get Y component
                        yy = self.mcubuf[py_idx] as i32;
                        py_idx += 1;
                        // R
                        workbuf[pix_idx] = (yy + (1.402f64 * cvacc as f64) as i32 * cr / cvacc)
                            .clamp(0, 255) as u8;
                        pix_idx += 1;
                        // G
                        workbuf[pix_idx] = (yy
                            - ((0.344f64 * cvacc as f64) as i32 * cb
                                + (0.714f64 * cvacc as f64) as i32 * cr)
                                / cvacc)
                            .clamp(0, 255) as u8;
                        pix_idx += 1;
                        // B
                        workbuf[pix_idx] = (yy + (1.772f64 * cvacc as f64) as i32 * cb / cvacc)
                            .clamp(0, 255) as u8;
                        pix_idx += 1;
                    }
                }
            } else {
                // Monochrome output (build a grayscale MCU from Y comopnent)

                for iy in 0..my {
                    py_idx = (iy * 8) as usize;
                    if my == 16 && iy >= 8 {
                        // Double block height?
                        py_idx += 64;
                    }
                    for ix in 0..mx {
                        if mx == 16 && ix == 8 {
                            // Double block width?
                            // Jump to next block if double block height
                            py_idx += 64 - 8;
                        }
                        // Get and store a Y value as grayscale
                        workbuf[pix_idx] = self.mcubuf[py_idx] as u8;
                        pix_idx += 1;
                        py_idx += 1;
                    }
                }
            }
            // Descale the MCU rectangular if needed
            if JD_USE_SCALE != 0 && self.scale != 0 {
                // Get averaged RGB value of each square corresponds to a pixel
                let s = (self.scale * 2) as u32; // Number of shifts for averaging
                let w = 1 << self.scale as u32; // Width of square
                let a = (mx - w) * (if JD_FORMAT != 2 { 3 } else { 1 }); // Bytes to skip for next line in the square
                op_idx = 0;
                for iy in (0..my).step_by(w as usize) {
                    for ix in (0..mx).step_by(w as usize) {
                        pix_idx = ((iy * mx + ix) * (if JD_FORMAT != 2 { 3 } else { 1 })) as usize;
                        let mut b = 0;
                        let mut g = 0;
                        let mut r = 0;
                        for _ in 0..w {
                            // Accumulate RGB value in the square
                            for _ in 0..w {
                                // Accumulate R or Y (monochrome output)
                                r += workbuf[pix_idx] as u32;
                                pix_idx += 1;
                                if JD_FORMAT != 2 {
                                    // Accumulate G
                                    g += workbuf[pix_idx] as u32;
                                    pix_idx += 1;
                                    // Accumulate B
                                    b += workbuf[pix_idx] as u32;
                                    pix_idx += 1;
                                }
                            }
                            pix_idx += a as usize;
                        }
                        // Put the averaged pixel value
                        // Put R or Y (monochrome output)
                        workbuf[op_idx] = (r >> s) as u8;
                        op_idx += 1;
                        if JD_FORMAT != 2 {
                            // RGB output?
                            // Put G
                            workbuf[op_idx] = (g >> s) as u8;
                            op_idx += 1;
                            // Put B
                            workbuf[op_idx] = (b >> s) as u8;
                            op_idx += 1;
                        }
                    }
                }
            }
        } else {
            // For only 1/8 scaling (left-top pixel in each block are the DC value of the
            // block) Build a 1/8 descaled RGB MCU from discrete components
            pix_idx = 0;
            pc_idx = (mx * my) as usize;
            cb = self.mcubuf[pc_idx] as i32 - 128; // Get Cb/Cr component and restore right level
            cr = self.mcubuf[pc_idx + 64] as i32 - 128;

            for iy in (0..my).step_by(8) {
                py_idx = 0;
                if iy == 8 {
                    py_idx = 64 * 2;
                }
                for _ in (0..mx).step_by(8) {
                    // Get Y component
                    yy = self.mcubuf[py_idx] as i32;
                    py_idx += 64;
                    if JD_FORMAT != 2 {
                        // R
                        workbuf[pix_idx] = (yy + (1.402f64 * cvacc as f64) as i32 * cr / cvacc)
                            .clamp(0, 255) as u8;
                        pix_idx += 1;
                        // G
                        workbuf[pix_idx] = (yy
                            - ((0.344f64 * cvacc as f64) as i32 * cb
                                + (0.714f64 * cvacc as f64) as i32 * cr)
                                / cvacc)
                            .clamp(0, 255) as u8;
                        //B
                        pix_idx += 1;
                        workbuf[pix_idx] = (yy + (1.772f64 * cvacc as f64) as i32 * cb / cvacc)
                            .clamp(0, 255) as u8;
                        pix_idx += 1;
                    } else {
                        workbuf[pix_idx] = yy as u8;
                        pix_idx += 1;
                    }
                }
            }
        }

        // Squeeze up pixel table if a part of MCU is to be truncated
        mx >>= self.scale as i32;
        if rx < mx {
            // Is the MCU spans right edge?
            let mut s_0_idx = 0;
            let mut d_idx = 0;
            for _ in 0..ry {
                for _ in 0..rx {
                    // Copy effective pixels
                    workbuf[d_idx] = workbuf[s_0_idx];
                    s_0_idx += 1;
                    d_idx += 1;
                    if JD_FORMAT != 2 {
                        workbuf[d_idx] = workbuf[s_0_idx];
                        s_0_idx += 1;
                        d_idx += 1;
                        workbuf[d_idx] = workbuf[s_0_idx];
                        s_0_idx += 1;
                        d_idx += 1;
                    }
                }
                // Skip truncated pixels
                s_0_idx += ((mx - rx) * (if JD_FORMAT != 2 { 3 } else { 1 })) as usize;
            }
        }

        // Convert RGB888 to RGB565 if needed
        if JD_FORMAT == 1 {
            let mut s_1_idx = 0;
            let mut d_0_idx = 0;
            let mut w_0: u16;
            for _ in 0..rx * ry {
                // RRRRR-----------
                w_0 = ((workbuf[s_1_idx] as i32 & 0xf8) << 8) as u16;
                s_1_idx += 1;
                // -----GGGGGG-----
                w_0 = (w_0 as i32 | (workbuf[s_1_idx] as i32 & 0xfc) << 3) as u16;
                s_1_idx += 1;
                // -----------BBBBB
                w_0 = (w_0 as i32 | workbuf[s_1_idx] as i32 >> 3) as u16;
                s_1_idx += 1;

                workbuf[d_0_idx] = (w_0 & 0xFF) as u8;
                workbuf[d_0_idx + 1] = (w_0 >> 8) as u8;
                d_0_idx += 2;
            }
        }

        // Output the rectangular
        // SAFETY: Aligning to u16 slice is safe, because the original slice is aligned
        // to 32 bits, therefore there are also no residuals (prefix/suffix).
        // The data in the slices are integers, so these are valid for both i32
        // and u16.
        let (_, bitmap, _) = unsafe { self.workbuf.align_to::<u16>() };
        let bitmap = &bitmap[..(rect.width() * rect.height()) as usize];
        if output_func.write(self, rect, bitmap) {
            Ok(())
        } else {
            Err(Error::Interrupted)
        }
    }

    pub fn mcu_height(&self) -> i16 {
        self.msy as i16 * 8
    }

    pub fn width(&self) -> i16 {
        self.width as i16
    }

    pub fn height(&self) -> i16 {
        self.height as i16
    }

    pub fn set_scale(&mut self, scale: u8) -> Result<(), Error> {
        if scale > (if JD_USE_SCALE != 0 { 3 } else { 0 }) {
            return Err(Error::Parameter);
        }
        self.scale = scale;
        Ok(())
    }

    /// Analyze the JPEG image and Initialize decompressor object
    pub fn new(input_func: &'i mut dyn JpegInput, pool: &'p mut [u8]) -> Result<Self, Error> {
        let mut jd = JDEC {
            dctr: 0,
            dptr: 0,
            inbuf: &mut [],
            dbit: 0,
            scale: 0,
            msx: 0,
            msy: 0,
            qtid: [0; 3],
            pool,
            dcv: [0; 3],
            rsc: 0,
            width: 0,
            height: 0,
            huffbits: [[&mut [], &mut []], [&mut [], &mut []]],
            huffcode: [[&mut [], &mut []], [&mut [], &mut []]],
            huffcode_len: [[0; 2]; 2],
            huffdata: [[&mut [], &mut []], [&mut [], &mut []]],
            qttbl: [&mut [], &mut [], &mut [], &mut []],
            wreg: 0,
            marker: 0,
            longofs: [[0; 2]; 2],
            hufflut_ac: [&mut [], &mut []],
            hufflut_dc: [&mut [], &mut []],
            workbuf: &mut [],
            rst: 0,
            ncomp: 0,
            nrst: 0,
            mcubuf: &mut [],
            input_func,
        };

        let mut marker: u16;
        let mut ofs: u32;
        let mut len: usize;

        // Allocate stream input buffer
        jd.inbuf = jd.alloc_slice(JD_SZBUF)?;

        // Find SOI marker
        marker = 0;
        ofs = marker as u32;
        loop {
            if jd.jpeg_in(Some(0), 1) != 1 {
                // Err: SOI was not detected
                return Err(Error::Input);
            }
            ofs += 1;
            marker = ((marker as i32) << 8 | jd.inbuf[0] as i32) as u16;
            if marker == 0xffd8 {
                break;
            }
        }
        loop {
            // Parse JPEG segments
            // Get a JPEG marker
            if jd.jpeg_in(Some(0), 4) != 4 {
                return Err(Error::Input);
            }
            // Marker
            marker = ((jd.inbuf[0] as i32) << 8 | jd.inbuf[1] as i32) as u16;
            // Length field
            len = ((jd.inbuf[2] as i32) << 8 | jd.inbuf[3] as i32) as usize;
            if len <= 2 || marker >> 8 != 0xff {
                return Err(Error::InvalidData);
            }
            len -= 2; // Segment content size
            ofs += (4 + len) as u32; // Number of bytes loaded

            match marker & 0xff {
                0xC0 => {
                    // SOF0 (baseline JPEG)
                    if len > JD_SZBUF {
                        return Err(Error::MemoryInput);
                    }
                    // Load segment data
                    if jd.jpeg_in(Some(0), len) != len {
                        return Err(Error::Input);
                    }
                    // Image width in unit of pixel
                    jd.width = ((jd.inbuf[3] as i32) << 8 | jd.inbuf[4] as i32) as u16;
                    // Image height in unit of pixel
                    jd.height = ((jd.inbuf[1] as i32) << 8 | jd.inbuf[2] as i32) as u16;
                    // Number of color components
                    jd.ncomp = jd.inbuf[5];
                    if jd.ncomp != 3 && jd.ncomp != 1 {
                        // Err: Supports only Grayscale and Y/Cb/Cr
                        return Err(Error::UnsupportedJpeg);
                    }
                    // Check each image component
                    for i in 0..jd.ncomp as usize {
                        // Get sampling factor
                        let b = jd.inbuf[7 + 3 * i];
                        if i == 0 {
                            // Y component
                            if b != 0x11 && b != 0x22 && b != 0x21 {
                                // Check sampling factor
                                // Err: Supports only 4:4:4, 4:2:0 or 4:2:2
                                return Err(Error::UnsupportedJpeg);
                            }
                            // Size of MCU [blocks]
                            jd.msx = (b as i32 >> 4) as u8;
                            jd.msy = (b as i32 & 15) as u8;
                        } else if b as i32 != 0x11 {
                            // Cb/Cr component
                            // Err: Sampling factor of Cb/Cr must be 1
                            return Err(Error::UnsupportedJpeg);
                        }
                        // Get dequantizer table ID for this component
                        jd.qtid[i] = jd.inbuf[8 + 3 * i];
                        if jd.qtid[i] as i32 > 3 {
                            // Err: Invalid ID
                            return Err(Error::UnsupportedJpeg);
                        }
                    }
                }
                0xDD => {
                    // DRI - Define Restart Interval
                    if len > JD_SZBUF {
                        return Err(Error::MemoryInput);
                    }
                    // Load segment data
                    if jd.jpeg_in(Some(0), len) != len {
                        return Err(Error::Input);
                    }
                    // Get restart interval (MCUs)
                    jd.nrst = ((jd.inbuf[0] as i32) << 8 | jd.inbuf[1] as i32) as u16;
                }
                0xC4 => {
                    // DHT - Define Huffman Tables
                    if len > JD_SZBUF {
                        return Err(Error::MemoryInput);
                    }
                    // Load segment data
                    if jd.jpeg_in(Some(0), len) != len {
                        return Err(Error::Input);
                    }
                    // Create huffman tables
                    jd.create_huffman_tbl(len)?;
                }
                0xDB => {
                    // DQT - Define Quantizer Tables
                    if len > JD_SZBUF {
                        return Err(Error::MemoryInput);
                    }
                    // Load segment data
                    if jd.jpeg_in(Some(0), len) != len {
                        return Err(Error::Input);
                    }
                    // Create de-quantizer tables
                    jd.create_qt_tbl(len)?;
                }
                0xDA => {
                    // SOS - Start of Scan
                    if len > JD_SZBUF {
                        return Err(Error::MemoryInput);
                    }
                    // Load segment data
                    if jd.jpeg_in(Some(0), len) != len {
                        return Err(Error::Input);
                    }
                    if jd.width == 0 || jd.height == 0 {
                        // Err: Invalid image size
                        return Err(Error::InvalidData);
                    }
                    if jd.inbuf[0] as i32 != jd.ncomp as i32 {
                        // Err: Wrong color components
                        return Err(Error::UnsupportedJpeg);
                    }
                    // Check if all tables corresponding to each components have been loaded
                    for i in 0..jd.ncomp as usize {
                        // Get huffman table ID
                        let b = jd.inbuf[2 + 2 * i];
                        if b != 0 && b != 0x11 {
                            // Err: Different table number for DC/AC element
                            return Err(Error::UnsupportedJpeg);
                        }
                        let n = if i != 0 { 1 } else { 0 }; // Component class

                        // Check huffman table for this component
                        if (jd.huffbits[n][0]).is_empty() || (jd.huffbits[n][1]).is_empty() {
                            // Err: Not loaded
                            return Err(Error::InvalidData);
                        }
                        // Check dequantizer table for this component
                        if (jd.qttbl[jd.qtid[i] as usize]).is_empty() {
                            // Err: Not loaded
                            return Err(Error::InvalidData);
                        }
                    }
                    // Allocate working buffer for MCU and pixel output
                    let n = jd.msy as i32 * jd.msx as i32; // Number of Y blocks in the MCU
                    if n == 0 {
                        // Err: SOF0 has not been loaded
                        return Err(Error::InvalidData);
                    }
                    len = (n * 64 * 3 + 64) as usize; // Allocate buffer for IDCT and RGB output
                    if len < 256 {
                        // but at least 256 byte is required for IDCT
                        len = 256;
                    }

                    jd.workbuf = jd.alloc_slice(len / 4)?;

                    // Allocate MCU working buffer
                    jd.mcubuf = jd.alloc_slice((n as usize + 2) * 64)?;

                    // Align stream read offset to JD_SZBUF
                    ofs %= JD_SZBUF as u32;
                    if ofs != 0 {
                        jd.dctr = jd.jpeg_in(Some(ofs as usize), (JD_SZBUF as u32 - ofs) as usize);
                    }
                    jd.dptr = (ofs - (if JD_FASTDECODE != 0 { 0 } else { 1 })) as usize;
                    return Ok(jd); // Initialization succeeded. Ready to
                                   // decompress the JPEG image.
                }
                // SOF1, SOF2, SOF3, SOF5, SOF6, SOF7, SOF9, SOF10, SOF11, SOF13, SOF14, SOF15, EOI
                0xC1 | 0xC2 | 0xC3 | 0xC5 | 0xC6 | 0xC7 | 0xC9 | 0xCA | 0xCB | 0xCD | 0xCF
                | 0xCE | 0xD9 => {
                    // Unsupported JPEG standard (may be progressive JPEG)
                    return Err(Error::UnsupportedJpeg);
                }
                _ => {
                    // Unknown segment (comment, exif or etc..)
                    // Skip segment data (null pointer specifies to remove data from the stream)
                    if jd.jpeg_in(None, len) != len {
                        return Err(Error::Input);
                    }
                }
            }
        }
    }

    /// Start to decompress the JPEG picture
    /// `scale`: output de-scaling factor (0 to 3)
    #[optimize(speed)]
    pub fn decomp(&mut self, output_func: &mut dyn JpegOutput) -> Result<(), Error> {
        let mx = (self.msx as i32 * 8) as u32; // Size of the MCU (pixel)
        let my = (self.msy as i32 * 8) as u32; // Size of the MCU (pixel)
        let mut y = 0;
        while y < self.height as u32 {
            // Vertical loop of MCUs
            let mut x = 0;
            while x < self.width as u32 {
                // Horizontal loop of MCUs
                if self.nrst != 0 && {
                    // Process restart interval if enabled
                    let val = self.rst;
                    self.rst += 1;
                    val == self.nrst
                } {
                    let val = self.rsc;
                    self.rsc += 1;
                    self.restart(val)?;
                    self.rst = 1;
                }
                // Load an MCU (decompress huffman coded stream, dequantize and apply IDCT)
                self.mcu_load()?;
                // Output the MCU (YCbCr to RGB, scaling and output)
                self.mcu_output(x, y, output_func)?;
                x += mx;
            }
            y += my;
        }
        Ok(())
    }
}

pub fn jpeg(data: &[u8], pos: Point, scale: u8) {
    let pool = unsafe { get_jpeg_work_buffer(0, true).buffer.as_mut_slice() };
    let mut out = PixelDataOutput(pos);
    let mut inp = BufferInput(data);
    if let Ok(mut jd) = JDEC::new(&mut inp, pool) {
        let _ = jd.set_scale(scale);
        let _ = jd.decomp(&mut out);
    }
}

pub fn jpeg_info(data: &[u8]) -> Option<(Offset, i16)> {
    let pool = unsafe { get_jpeg_work_buffer(0, true).buffer.as_mut_slice() };
    let mut inp = BufferInput(data);
    if let Ok(jd) = JDEC::new(&mut inp, pool) {
        let mcu_height = jd.mcu_height();
        if mcu_height > 16 {
            return None;
        }
        Some((Offset::new(jd.width(), jd.height()), mcu_height))
    } else {
        None
    }
}

pub fn jpeg_test(data: &[u8]) -> bool {
    let pool = unsafe { get_jpeg_work_buffer(0, true).buffer.as_mut_slice() };
    let mut inp = BufferInput(data);
    if let Ok(mut jd) = JDEC::new(&mut inp, pool) {
        if jd.mcu_height() > 16 {
            return false;
        }

        let mut out = BlackHoleOutput;
        let mut res = jd.decomp(&mut out);
        while res == Err(Error::Interrupted) {
            res = jd.decomp(&mut out);
        }
        res.is_ok()
    } else {
        false
    }
}

pub trait JpegInput {
    fn read(&mut self, buf: Option<&mut [u8]>, nread: usize) -> usize;
}

pub struct BufferInput<'i>(pub &'i [u8]);

impl<'i> JpegInput for BufferInput<'i> {
    fn read(&mut self, inbuf: Option<&mut [u8]>, n_data: usize) -> usize {
        let len = n_data.min(self.0.len());
        let (toread, newdata) = self.0.split_at(len);
        if let Some(inbuf) = inbuf {
            (inbuf[..len]).copy_from_slice(toread)
        }
        self.0 = newdata;
        len
    }
}

pub trait JpegOutput {
    /// Return `false` to interrupt.
    fn write(&mut self, jd: &JDEC, rect: Rect, pixels: &[u16]) -> bool;
}

pub struct BufferOutput<'o> {
    buffer: &'o mut BufferJpeg,
    buffer_width: i16,
    buffer_height: i16,
    current_line: i16,
    current_line_pix: i16,
}

impl<'o> BufferOutput<'o> {
    pub fn new(buffer: &'o mut BufferJpeg, buffer_width: i16, buffer_height: i16) -> Self {
        Self {
            buffer,
            buffer_width,
            buffer_height,
            current_line: 0,
            current_line_pix: 0,
        }
    }

    pub fn buffer(&mut self) -> &mut BufferJpeg {
        self.buffer
    }
}

impl<'o> JpegOutput for BufferOutput<'o> {
    fn write(&mut self, jd: &JDEC, rect: Rect, bitmap: &[u16]) -> bool {
        let w = rect.width();
        let h = rect.height();
        let x = rect.x0;

        if h > self.buffer_height {
            // unsupported height, call and let know
            return true;
        }

        let buffer_len = (self.buffer_width * self.buffer_height) as usize;

        for i in 0..h {
            for j in 0..w {
                let buffer_pos = ((x + j) + (i * self.buffer_width)) as usize;
                if buffer_pos < buffer_len {
                    self.buffer.buffer[buffer_pos] = bitmap[(i * w + j) as usize];
                }
            }
        }

        self.current_line_pix += w;

        if self.current_line_pix >= jd.width() {
            self.current_line_pix = 0;
            self.current_line += jd.mcu_height();
            // finished line, abort and continue later
            return false;
        }

        true
    }
}

pub struct PixelDataOutput(Point);

impl JpegOutput for PixelDataOutput {
    fn write(&mut self, _jd: &JDEC, rect: Rect, bitmap: &[u16]) -> bool {
        let pos = self.0;
        let r = rect.translate(pos.into());
        let clamped = r.clamp(constant::screen());
        set_window(clamped);
        for py in r.y0..r.y1 {
            for px in r.x0..r.x1 {
                let p = Point::new(px, py);
                if clamped.contains(p) {
                    let off = p - r.top_left();
                    let c = bitmap[(off.y * rect.width() + off.x) as usize];
                    pixeldata(c);
                }
            }
        }
        true
    }
}

pub struct BlackHoleOutput;

impl JpegOutput for BlackHoleOutput {
    fn write(&mut self, _jd: &JDEC, _rect: Rect, _bitmap: &[u16]) -> bool {
        true
    }
}
