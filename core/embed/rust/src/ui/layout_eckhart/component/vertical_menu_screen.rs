use crate::{
    strutil::TString,
    ui::{
        component::{
            base::AttachType,
            swipe_detect::{SwipeConfig, SwipeSettings},
            Component, Event, EventCtx, SwipeDetect,
        },
        event::{SwipeEvent, TouchEvent},
        geometry::{Alignment2D, Direction, Offset, Rect},
        layout_eckhart::{
            component::{constant::screen, Header, HeaderMsg, VerticalMenu, VerticalMenuMsg},
            theme,
        },
        shape::{Renderer, ToifImage},
    },
};

pub struct VerticalMenuScreen {
    header: Header,
    /// Scrollable vertical menu
    menu: VerticalMenu,
    /// Base position of the menu sliding window to scroll around
    offset_base: i16,
    /// Swipe detector
    swipe: SwipeDetect,
    /// Swipe configuration
    swipe_config: SwipeConfig,
}

pub enum VerticalMenuScreenMsg {
    Selected(usize),
    /// Left header button clicked
    Back,
    /// Right header button clicked
    Close,
}

impl VerticalMenuScreen {
    pub fn new(menu: VerticalMenu) -> Self {
        Self {
            header: Header::new(TString::empty()),
            menu,
            offset_base: 0,
            swipe: SwipeDetect::new(),
            swipe_config: SwipeConfig::new()
                .with_swipe(Direction::Up, SwipeSettings::default())
                .with_swipe(Direction::Down, SwipeSettings::default()),
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    // Shift position of touch events in the menu area by an offset of the current
    // sliding window position
    fn shift_touch_event(&self, event: Event) -> Option<Event> {
        match event {
            Event::Touch(touch_event) => {
                let shifted_event = match touch_event {
                    TouchEvent::TouchStart(point) if self.menu.area().contains(point) => Some(
                        TouchEvent::TouchStart(point.ofs(Offset::y(self.menu.get_offset())).into()),
                    ),
                    TouchEvent::TouchMove(point) if self.menu.area().contains(point) => Some(
                        TouchEvent::TouchMove(point.ofs(Offset::y(self.menu.get_offset())).into()),
                    ),
                    TouchEvent::TouchEnd(point) if self.menu.area().contains(point) => Some(
                        TouchEvent::TouchEnd(point.ofs(Offset::y(self.menu.get_offset())).into()),
                    ),
                    _ => None, // Ignore touch events outside the bounds
                };
                shifted_event.map(Event::Touch)
            }
            _ => None, // Ignore other events
        }
    }

    /// Update menu buttons based on the current offset.
    pub fn update_menu(&mut self, ctx: &mut EventCtx) {
        self.menu.update_menu(ctx);
    }
}

impl Component for VerticalMenuScreen {
    type Msg = VerticalMenuScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), screen().height());
        debug_assert_eq!(bounds.width(), screen().width());

        let (header_area, menu_area) = bounds.split_top(Header::HEADER_HEIGHT);

        self.menu.place(menu_area);
        self.header.place(header_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update the menu when the screen is attached
        if let Event::Attach(AttachType::Initial) = event {
            self.update_menu(ctx);
        }

        match self.swipe.event(ctx, event, self.swipe_config) {
            Some(SwipeEvent::Start(_)) => {
                // Lock the base position to scroll around
                self.offset_base = self.menu.get_offset();
            }

            Some(SwipeEvent::End(_)) => {
                // Lock the base position to scroll around
                self.offset_base = self.menu.get_offset();
            }

            Some(SwipeEvent::Move(dir, delta)) => {
                // Decrease the sensitivity of the swipe
                let delta = delta / 10;
                // Scroll the menu based on the swipe direction
                match dir {
                    Direction::Up => {
                        self.menu.set_offset(self.offset_base + delta);
                        self.menu.update_menu(ctx);
                        return None;
                    }
                    Direction::Down => {
                        self.menu.set_offset(self.offset_base - delta);
                        self.menu.update_menu(ctx);
                        return None;
                    }
                    _ => {}
                }
            }
            _ => {}
        };

        if let Some(msg) = self.header.event(ctx, event) {
            match msg {
                HeaderMsg::Cancelled => return Some(VerticalMenuScreenMsg::Close),
                HeaderMsg::Back => return Some(VerticalMenuScreenMsg::Back),
                _ => {}
            }
        }

        // Shift touch events in the menu area by the current sliding window position
        if let Some(shifted) = self.shift_touch_event(event) {
            if let Some(msg) = self.menu.event(ctx, shifted) {
                match msg {
                    VerticalMenuMsg::Selected(i) => {
                        return Some(VerticalMenuScreenMsg::Selected(i))
                    }
                    _ => {}
                }
            }
        }

        // Handle shifted touch events in the menu
        if let Some(msg) = self.menu.event(ctx, event) {
            match msg {
                VerticalMenuMsg::Selected(i) => return Some(VerticalMenuScreenMsg::Selected(i)),
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.menu.render(target);

        // Render the down arrow if the menu  can be scrolled down
        if !self.menu.is_max_offset() {
            ToifImage::new(
                self.menu.area().bottom_center(),
                theme::ICON_CHEVRON_DOWN_MINI.toif,
            )
            .with_align(Alignment2D::BOTTOM_CENTER)
            .with_fg(theme::GREY_LIGHT)
            .render(target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalMenuScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalMenuScreen");
    }
}
