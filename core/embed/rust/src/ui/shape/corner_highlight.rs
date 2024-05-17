use crate::ui::{
    display::Color,
    geometry::{Alignment2D, Offset, Point, Rect},
    shape::{Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

#[derive(Clone, Copy)]
pub enum CornerPosition {
    TopLeft,
    TopRight,
    BotLeft,
    BotRight,
}

/// The shape placed in the corners highlihting important information within.
pub struct CornerHighlight {
    /// Base point, horizontal and vertical lines crossing `pos` create tangents
    /// to the shape
    pos: Point,
    /// Where is shape located, determines orientation of the shape
    corner: CornerPosition,
    /// Color of the shape - uniform and filled
    color: Color,
    /// Background color
    bg_color: Color,
    /// Outer radius
    r_outer: i16,
    /// Tail-end radius
    r_tail: i16,
    /// Inner radius
    r_inner: i16,
    /// Total lengths of the shape from the base point to the end of any tail
    length: i16,
    /// Thickness (default 3)
    thickness: i16,
    /// Alpha (default 255)
    alpha: u8,
    /// Helper point for working with rectangles, offset of `pos`
    pos_rect: Point,
}

impl CornerHighlight {
    pub fn new(pos: Point, corner: CornerPosition, color: Color, bg_color: Color) -> Self {
        Self {
            pos,
            corner,
            color,
            bg_color,
            r_outer: 3,
            r_tail: 1,
            r_inner: 1,
            length: 8,
            thickness: 3,
            alpha: 255,
            pos_rect: pos + Offset::rect_offset(corner),
        }
    }

    pub fn from_rect(rect: Rect, color: Color, bg_color: Color) -> (Self, Self, Self, Self) {
        let [top_left_corner, top_right_corner, bot_right_corner, bot_left_corner] =
            rect.corner_points();
        let top_left =
            CornerHighlight::new(top_left_corner, CornerPosition::TopLeft, color, bg_color);
        let top_right =
            CornerHighlight::new(top_right_corner, CornerPosition::TopRight, color, bg_color);
        let bot_left =
            CornerHighlight::new(bot_left_corner, CornerPosition::BotLeft, color, bg_color);
        let bot_right =
            CornerHighlight::new(bot_right_corner, CornerPosition::BotRight, color, bg_color);
        (top_left, top_right, bot_left, bot_right)
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }

    fn rect_visible_part_base(&self, p: Point) -> (Point, Point) {
        let (horizontal, vertical) = match self.corner {
            CornerPosition::TopLeft => (p + Offset::x(self.r_outer), p + Offset::y(self.r_outer)),
            CornerPosition::TopRight => (p - Offset::x(self.r_outer), p + Offset::y(self.r_outer)),
            CornerPosition::BotLeft => (p + Offset::x(self.r_outer), p - Offset::y(self.r_outer)),
            CornerPosition::BotRight => (p - Offset::x(self.r_outer), p - Offset::y(self.r_outer)),
        };
        (horizontal, vertical)
    }
}

impl Shape<'_> for CornerHighlight {
    fn bounds(&self) -> Rect {
        Rect::snap(
            self.pos_rect,
            Offset::uniform(self.length),
            self.corner.into(),
        )
    }

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache<'_>) {
        let align: Alignment2D = self.corner.into();

        // base circle
        let circle_center = self.pos + Offset::uniform(self.r_outer).rotate(self.corner);
        let circle_visible_part = Rect::snap(self.pos_rect, Offset::uniform(self.r_outer), align);
        in_clip(canvas, circle_visible_part, &|can| {
            can.fill_circle(circle_center, self.r_outer, self.color, self.alpha);
        });

        // rectangles (rounded) tailing from a corner
        let (rect_horz_base, rect_vert_base) = self.rect_visible_part_base(self.pos_rect);

        // vertical tail
        let rect_tail_vert = Rect::snap(
            self.pos_rect,
            Offset::new(self.thickness, self.length),
            align,
        );
        let rect_vert_visible_part = Rect::snap(
            rect_vert_base,
            Offset::new(self.thickness, self.length - self.r_outer),
            align,
        );
        in_clip(canvas, rect_vert_visible_part, &|can| {
            can.fill_round_rect(rect_tail_vert, self.r_tail, self.color, self.alpha)
        });

        // horizontal tail
        let rect_tail_horz = Rect::snap(
            self.pos_rect,
            Offset::new(self.length, self.thickness),
            align,
        );
        let rect_horz_visible_part = Rect::snap(
            rect_horz_base,
            Offset::new(self.length - self.r_outer, self.thickness),
            align,
        );
        in_clip(canvas, rect_horz_visible_part, &|can| {
            can.fill_round_rect(rect_tail_horz, self.r_tail, self.color, self.alpha)
        });

        // inner radius by a rectangle (shape color) and a circle (background color)
        let rect_outer_base = self.pos_rect + Offset::uniform(self.thickness).rotate(self.corner);
        let rect_outer_fill = Rect::snap(rect_outer_base, Offset::uniform(self.r_inner), align);
        let circle_cover_center =
            self.pos + Offset::uniform(self.thickness + self.r_inner).rotate(self.corner);
        in_clip(canvas, rect_outer_fill, &|can| {
            can.fill_rect(rect_outer_fill, self.color, self.alpha);
            can.fill_circle(circle_cover_center, self.r_inner, self.bg_color, self.alpha);
        });
    }

    fn cleanup(&mut self, _cache: &super::DrawingCache<'_>) {}
}

impl<'s> ShapeClone<'s> for CornerHighlight {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t::<CornerHighlight>()?;
        Some(clone.uninit.init(CornerHighlight { ..self }))
    }
}

// Helper functions

fn in_clip(canvas: &mut dyn Canvas, r: Rect, inner: &dyn Fn(&mut dyn Canvas)) {
    // TODO: like Renderer::in_clip, replace by Canvas::in_clip when done
    let original = canvas.set_clip(r);
    inner(canvas);
    canvas.set_viewport(original);
}

impl From<CornerPosition> for Alignment2D {
    fn from(corner: CornerPosition) -> Self {
        match corner {
            CornerPosition::TopLeft => Alignment2D::TOP_LEFT,
            CornerPosition::TopRight => Alignment2D::TOP_RIGHT,
            CornerPosition::BotLeft => Alignment2D::BOTTOM_LEFT,
            CornerPosition::BotRight => Alignment2D::BOTTOM_RIGHT,
        }
    }
}

impl Offset {
    fn rect_offset(corner: CornerPosition) -> Offset {
        match corner {
            CornerPosition::TopLeft => Offset::zero(),
            CornerPosition::TopRight => Offset::x(1),
            CornerPosition::BotLeft => Offset::y(1),
            CornerPosition::BotRight => Offset::uniform(1),
        }
    }

    /// If Offset `self` is calculated for TopLeft (x,y positive) then this
    /// function rotates the offset for other corners.
    fn rotate(&self, corner: CornerPosition) -> Offset {
        match corner {
            CornerPosition::TopLeft => Offset {
                x: self.x,
                y: self.y,
            },
            CornerPosition::TopRight => Offset {
                x: -self.x,
                y: self.y,
            },
            CornerPosition::BotLeft => Offset {
                x: self.x,
                y: -self.y,
            },
            CornerPosition::BotRight => Offset {
                x: -self.x,
                y: -self.y,
            },
        }
    }
}
