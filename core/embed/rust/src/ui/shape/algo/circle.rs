/// Iterator providing points for 1/8th of a circle (single octant)
///
/// The iterator supplies coordinates of pixels relative to the
/// circle's center point, along with an alpha value in
/// the range (0..255), indicating the proportion of the pixel
/// that lies inside the circle.
///
///  for p in circle_points(radius) {
///     println!("{}, {}", p.u, p.v); // coordinates <0,radius>..<see_below>
///     println!("{}", p.frac); // distance from the circle <0..255>
///     println!("{}", p.first); // `v` has changed
///     println!("{}", p.last); // next `v` will change
///  }
///
///  `u` axis is the main and increments at each iteration.
///
/// endpoint [t, t] or [t - 1, t] where t = radius * (1 / sqrt(2))

pub fn circle_points(radius: i16) -> CirclePoints {
    CirclePoints {
        radius,
        u: 0,
        v: radius,
        t1: radius / 16,
        first: true,
    }
}

pub struct CirclePoints {
    radius: i16,
    u: i16,
    v: i16,
    t1: i16,
    first: bool,
}

#[derive(Copy, Clone)]
pub struct CirclePointsItem {
    pub u: i16,
    pub v: i16,
    pub frac: u8,
    pub first: bool,
    pub last: bool,
}

impl Iterator for CirclePoints {
    type Item = CirclePointsItem;

    fn next(&mut self) -> Option<Self::Item> {
        if self.v >= self.u {
            let mut item = CirclePointsItem {
                u: self.u,
                v: self.v,
                frac: 255 - ((self.t1 as i32 * 255) / self.radius as i32) as u8,
                first: self.first,
                last: false,
            };

            self.first = false;
            self.u += 1;
            self.t1 += self.u;
            let t2 = self.t1 - self.v;
            if t2 >= 0 {
                self.t1 = t2;
                self.v -= 1;
                self.first = true;
            }

            item.last = item.v != self.v;

            Some(item)
        } else {
            None
        }
    }
}
