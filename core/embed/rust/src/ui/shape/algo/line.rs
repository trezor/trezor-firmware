/// Iterator providing points on a line (using bresenham's algorithm)
///
/// The iterator supplies coordinates of pixels relative to the
/// line's start point.
///
///  constraint: `du` >= `dv`, `start_u` < `du`
///
///  for p in line_points(du, dv, start_u) {
///     println!("{}, {}", p.u, p.v); // coordinates <0,radius>..<du-1, dv-1>
///     println!("{}", p.frac); // distance from the line <0..255>
///     println!("{}", p.first); // `v` has changed
///     println!("{}", p.last); // next `v` will change
///  }
///
///  `u` axis is the main and increments at each iteration.

pub fn line_points(du: i16, dv: i16, start_u: i16) -> LinePoints {
    let mut d = 2 * du - 2 * dv;
    let mut y = 0;

    for _ in 0..start_u {
        if d <= 0 {
            d += 2 * du - 2 * dv;
            y += 1;
        } else {
            d -= 2 * dv;
        }
    }

    LinePoints {
        du,
        dv,
        d,
        u: start_u,
        v: y,
        first: true,
    }
}

pub struct LinePoints {
    du: i16,
    dv: i16,
    d: i16,
    u: i16,
    v: i16,
    first: bool,
}

#[derive(Copy, Clone)]
pub struct LinePointsItem {
    pub u: i16,
    pub v: i16,
    pub frac: u8,
    pub first: bool,
    pub last: bool,
}

impl Iterator for LinePoints {
    type Item = LinePointsItem;

    #[inline(always)]
    fn next(&mut self) -> Option<Self::Item> {
        if self.u < self.du {
            let frac = if self.dv < self.du {
                255 - ((self.d + 2 * self.dv - 1) as i32 * 255 / (2 * self.du - 1) as i32) as u8
            } else {
                0
            };

            let next = LinePointsItem {
                u: self.u,
                v: self.v,
                frac,
                first: self.first,
                last: self.d <= 0,
            };

            if self.d <= 0 {
                self.d += 2 * self.du - 2 * self.dv;
                self.v += 1;
                self.first = true;
            } else {
                self.d -= 2 * self.dv;
                self.first = false;
            }

            self.u += 1;

            Some(next)
        } else {
            None
        }
    }
}
