use super::super::theme::bootloader::{
    BLD_BG, BLD_FG, BUTTON_HEIGHT, BUTTON_OUTLINE, FONT_MENU_ITEM, FONT_PAGE_COUNTER,
    ICON_PAGE_SEPARATOR,
};
use super::buttons::{Button, ButtonPos, Buttons};
use crate::strutil::ShortString;
use crate::ui::component::{Component, Event, EventCtx, Pad};
use crate::ui::geometry::{Alignment, Alignment2D, Offset, Point, Rect};
use crate::ui::layout::simplified::ReturnToC;
use crate::ui::shape::{self, Renderer};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum MenuMsg {
    Close = 0xAABBCCDD,
    Reboot = 0x11223344,
    FactoryReset = 0x55667788,
}
impl ReturnToC for MenuMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

/// Items of the bootloader menu, see `MenuMsg::from_selection`.
pub const MENU_ITEMS: [&str; 2] = ["Reboot", "Factory reset"];

impl MenuMsg {
    pub fn from_selection(selection: MenuSelection) -> Option<Self> {
        Some(match selection {
            MenuSelection::Close => Self::Close,
            MenuSelection::Item(0) => Self::Reboot,
            MenuSelection::Item(_) => Self::FactoryReset,
        })
    }
}

#[derive(Copy, Clone)]
pub enum MenuSelection {
    /// The menu was closed by the cross on its first item
    Close,
    /// Index of the selected item
    Item(usize),
}

/// Context menu carousel showing one item at a time, with the same buttons as
/// the firmware `select_menu`. The cross on the first item closes the menu.
/// Items must fit on one line.
pub struct Menu<const N: usize> {
    pad: Pad,
    items: [&'static str; N],
    index: usize,
    item_area: Rect,
    buttons: Buttons,
}

impl<const N: usize> Menu<N> {
    pub fn new(items: [&'static str; N]) -> Self {
        let mut menu = Self {
            pad: Pad::with_background(BLD_BG).with_clear(),
            items,
            index: 0,
            item_area: Rect::zero(),
            buttons: Buttons::new(None, None, None),
        };
        menu.set_buttons();
        menu
    }

    fn set_buttons(&mut self) {
        let left = if self.index == 0 {
            Button::cancel()
        } else {
            Button::left_arrow()
        };
        let right = (self.index < N - 1).then_some(Button::right_arrow());
        self.buttons.set(Some(left), Some(Button::select()), right);
    }

    fn go_to(&mut self, ctx: &mut EventCtx, index: usize) {
        self.index = index;
        self.set_buttons();
        self.pad.clear();
        ctx.request_paint();
    }

    /// "current/total" page counter at the top right, like the firmware
    /// `ScrollBar`.
    fn render_page_counter<'s>(&self, target: &mut impl Renderer<'s>) {
        let font = FONT_PAGE_COUNTER;
        let current: ShortString = uformat!("{}", self.index + 1);
        let total: ShortString = uformat!("{}", N);
        let baseline = self.pad.area.top_right() + Offset::y(font.text_height() - 1);
        // One pixel gap on both sides of the separator
        let current_right =
            baseline.x - font.text_width(&total) - ICON_PAGE_SEPARATOR.toif.width() - 2;

        shape::Text::new(baseline, &total, font)
            .with_align(Alignment::End)
            .with_fg(BLD_FG)
            .render(target);
        shape::ToifImage::new(
            Point::new(current_right + 1, baseline.y),
            ICON_PAGE_SEPARATOR.toif,
        )
        .with_align(Alignment2D::BOTTOM_LEFT)
        .with_fg(BLD_FG)
        .render(target);
        shape::Text::new(Point::new(current_right, baseline.y), &current, font)
            .with_align(Alignment::End)
            .with_fg(BLD_FG)
            .render(target);
    }
}

impl<const N: usize> Component for Menu<N> {
    type Msg = MenuSelection;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (item_area, button_area) = bounds.split_bottom(BUTTON_HEIGHT);
        self.pad.place(bounds);
        self.item_area = item_area;
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.buttons.event(ctx, event)? {
            ButtonPos::Left if self.index == 0 => return Some(MenuSelection::Close),
            ButtonPos::Left => self.go_to(ctx, self.index - 1),
            ButtonPos::Right => self.go_to(ctx, self.index + 1),
            ButtonPos::Middle => return Some(MenuSelection::Item(self.index)),
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        self.buttons.render(target);
        if N > 1 {
            self.render_page_counter(target);
        }

        // The item is outlined, and inverted while the middle button is down
        let text = self.items[self.index];
        let font = FONT_MENU_ITEM;
        let text_size = Offset::new(font.visible_text_width(text), font.allcase_text_height());
        let text_area = Rect::from_center_and_size(self.item_area.center(), text_size);
        let outline = Rect::from_center_and_size(
            text_area.center() + Offset::y(1),
            text_size + Offset::uniform(2 * BUTTON_OUTLINE),
        );
        let inverse = self.buttons.pressed() == Some(ButtonPos::Middle);

        shape::Bar::new(outline)
            .with_radius(1)
            .with_bg(BLD_FG)
            .render(target);
        if !inverse {
            shape::Bar::new(outline.shrink(1))
                .with_radius(1)
                .with_bg(BLD_BG)
                .render(target);
        }

        let fg = if inverse { BLD_BG } else { BLD_FG };
        shape::Text::new(
            text_area.bottom_left() - Offset::x(font.start_x_bearing(text)),
            text,
            font,
        )
        .with_fg(fg)
        .render(target);
    }
}
