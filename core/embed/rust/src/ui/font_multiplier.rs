/// Utilities to handle font scaling/magnifying/multiplying,
/// so that we do not need to store extra font data
/// because our flash space is limited.
/// For python implementation see `tools/snippets/font_multiplier.py`.
/// NOTE: was made to support 1BPP fonts, other sizes
/// will probably not work.
use super::geometry::Point;
use heapless::Vec;

/// Magnify the pixel size from byte vector, saving
/// result into a bit vector.
pub fn magnify_font<const M: usize, const N: usize>(
    magnification: u8,
    width: i32,
    height: i32,
    bytes: Vec<u8, M>,
    magnified_bits: &mut Vec<bool, N>,
) {
    if ![2, 4].contains(&magnification) {
        #[cfg(feature = "ui_debug")]
        panic!("Only supporting magnification 2 or 4");
    }

    let mut bits: Vec<bool, 128> = Vec::new();
    let bits_to_take = width * height;
    bytes_to_bits(bytes, &mut bits, bits_to_take);

    // TODO: how to handle this more automatically with all
    // the needed allocations for bigger magnifications?
    if magnification == 2 {
        double_the_bits(width, bits, magnified_bits);
    } else if magnification == 4 {
        let mut double_bits: Vec<bool, 512> = Vec::new();
        double_the_bits(width, bits, &mut double_bits);
        double_the_bits(width * 2, double_bits, magnified_bits);
    }
}

// Transform byte vector into bit vector.
fn bytes_to_bits<const M: usize, const N: usize>(
    bytes: Vec<u8, M>,
    bits: &mut Vec<bool, N>,
    bits_to_take: i32,
) {
    // Processing all but the last element first.
    let (last_byte, all_but_last) = bytes.split_last().unwrap();
    for byte in all_but_last {
        for i in (0..8).rev() {
            bits.push((byte >> i) & 1 == 1).unwrap();
        }
    }

    // Last element needs to be handled carefully,
    // to respect the number of bits to take.
    let missing_bits = bits_to_take - bits.len() as i32;
    // Taking either the right or left part of the last byte,
    // depending on its value (low or high).
    // TODO: cannot this be simplified?
    if (*last_byte as i32) < i32::pow(2, missing_bits as _) {
        for i in (0..missing_bits).rev() {
            bits.push((last_byte >> i) & 1 == 1).unwrap();
        }
    } else {
        for i in (8 - missing_bits..8).rev() {
            bits.push((last_byte >> i) & 1 == 1).unwrap();
        }
    };
}

/// Double the pixel size of the given vector of bits.
/// Save the result into supplied vector.
fn double_the_bits<const M: usize, const N: usize>(
    width: i32,
    bits: Vec<bool, M>,
    new_bits: &mut Vec<bool, N>,
) {
    // Pre-fill the appropriate amount of new bits with zeros
    // so that we can assign individual indexes later.
    for _ in 0..(4 * bits.len()) {
        new_bits.push(false).unwrap();
    }

    for (i, bit) in bits.iter().enumerate() {
        for new_index in new_indexes(i as _, width) {
            new_bits[new_index as usize] = *bit;
        }
    }
}

/// Map pixel index to (4) new indexes on a two times bigger size.
fn new_indexes(index: i32, width: i32) -> Vec<i32, 4> {
    let point = index_to_point(index, width);
    let points = scale_point_by_two(point);
    let new_width = 2 * width;
    points
        .iter()
        .map(|point| point_to_index(*point, new_width))
        .collect()
}

/// Return four adjacent Points from a given Point considering double size.
fn scale_point_by_two(point: Point) -> Vec<Point, 4> {
    let new_points = [
        (point.x * 2, point.y * 2),
        (point.x * 2 + 1, point.y * 2),
        (point.x * 2, point.y * 2 + 1),
        (point.x * 2 + 1, point.y * 2 + 1),
    ];
    new_points.iter().map(|(x, y)| Point::new(*x, *y)).collect()
}

/// Translate Point into index within a bit vector based on font width.
fn point_to_index(point: Point, width: i32) -> i32 {
    point.y * width + point.x
}

/// Translate index within a bit vector to a Point based on font width.
fn index_to_point(index: i32, width: i32) -> Point {
    Point::new(index % width, index / width)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bytes_to_bits_1() {
        let bytes: Vec<u8, 2> = Vec::from_slice(&[2, 3]).unwrap();
        let mut bits: Vec<bool, 16> = Vec::new();
        bytes_to_bits(bytes, &mut bits, 16);

        let expected: Vec<bool, 16> = Vec::from_slice(&[
            false, false, false, false, false, false, true, false, false, false, false, false,
            false, false, true, true,
        ])
        .unwrap();

        assert_eq!(bits, expected);
    }

    #[test]
    fn test_bytes_to_bits_2() {
        let bytes: Vec<u8, 2> = Vec::from_slice(&[2, 3]).unwrap();
        let mut bits: Vec<bool, 16> = Vec::new();
        bytes_to_bits(bytes, &mut bits, 14);

        let expected: Vec<bool, 14> = Vec::from_slice(&[
            false, false, false, false, false, false, true, false, false, false, false, false,
            true, true,
        ])
        .unwrap();

        assert_eq!(bits, expected);
    }

    #[test]
    fn test_bytes_to_bits_3() {
        let bytes: Vec<u8, 2> = Vec::from_slice(&[2, 32]).unwrap();
        let mut bits: Vec<bool, 16> = Vec::new();
        bytes_to_bits(bytes, &mut bits, 12);

        let expected: Vec<bool, 12> = Vec::from_slice(&[
            false, false, false, false, false, false, true, false, false, false, true, false,
        ])
        .unwrap();

        assert_eq!(bits, expected);
    }

    #[test]
    fn test_letter_k_to_bits() {
        const width: usize = 5;
        const height: usize = 7;
        let bytes: Vec<u8, 5> = Vec::from_slice(&[140, 169, 138, 74, 32]).unwrap();
        let mut bits: Vec<bool, 64> = Vec::new();
        bytes_to_bits(bytes, &mut bits, (width * height) as _);

        let expected: Vec<bool, { width * height }> = Vec::from_slice(&[
            true, false, false, false, true, true, false, false, true, false, true, false, true,
            false, false, true, true, false, false, false, true, false, true, false, false, true,
            false, false, true, false, true, false, false, false, true,
        ])
        .unwrap();

        assert_eq!(bits, expected);
    }

    #[test]
    fn test_double_bits() {
        let bits: Vec<bool, 4> = Vec::from_slice(&[true, false, true, true]).unwrap();
        let mut new_bits: Vec<bool, 16> = Vec::new();
        double_the_bits(2, bits, &mut new_bits);

        let expected: Vec<bool, 16> = Vec::from_slice(&[
            true, true, false, false, true, true, false, false, true, true, true, true, true, true,
            true, true,
        ])
        .unwrap();

        assert_eq!(new_bits, expected);
    }
}
