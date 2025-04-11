use crate::{
    strutil::TString,
    ui::{
        component::{
            swipe_detect::{SwipeConfig, SwipeSettings},
            Component, Event, EventCtx, SwipeDetect,
        },
        event::SwipeEvent,
        flow::Swipable,
        geometry::{Alignment2D, Direction, Rect},
        shape::{Renderer, ToifImage},
        util::Pager,
    },
};

use super::{constant::SCREEN, theme, Header, HeaderMsg, VerticalMenu, VerticalMenuMsg};

pub struct VerticalMenuScreen {
    header: Header,
    /// Scrollable vertical menu
    menu: VerticalMenu,
    /// Base position of the menu sliding window to scroll around
    offset_base: i16,
    /// Used to enable swipe detection only when the menu does not fit its area
    swipe_enabled: bool,
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
    const TOUCH_SENSITIVITY_DIVIDER: i16 = 15;
    pub fn new(menu: VerticalMenu) -> Self {
        Self {
            header: Header::new(TString::empty()),
            menu,
            offset_base: 0,
            swipe_enabled: false,
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

    /// Update swipe detection and buttons state based on menu size
    pub fn initialize_screen(&mut self, ctx: &mut EventCtx) {
        if !self.menu.fits_area() {
            // Enable swipe
            self.swipe_enabled = true;
            self.swipe_config = SwipeConfig::new()
                .with_swipe(Direction::Up, SwipeSettings::default())
                .with_swipe(Direction::Down, SwipeSettings::default());
            ctx.enable_swipe();

            // Update the menu buttons state
            self.menu.update_menu(ctx);
        } else {
            // Disable swipe
            self.swipe_enabled = false;
            ctx.disable_swipe();
        }
    }
}

impl Component for VerticalMenuScreen {
    type Msg = VerticalMenuScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, menu_area) = bounds.split_top(Header::HEADER_HEIGHT);

        self.header.place(header_area);
        self.menu.place(menu_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update the screen after the menu fit is calculated
        // This is needed to enable swipe detection only when the menu does not fit
        if let Event::Attach(_) = event {
            self.initialize_screen(ctx);
        }

        // Handle swipe events if swipe is enabled (menu does not fit)
        if self.swipe_enabled {
            // Handle swipe events from the standalone swipe detector or ones coming from
            // the flow. These two are mutually exclusive and should not be triggered at the
            // same time.
            let swipe_event = self
                .swipe
                .event(ctx, event, self.swipe_config)
                .or(match event {
                    Event::Swipe(e) => Some(e),
                    _ => None,
                });

            match swipe_event {
                Some(SwipeEvent::Start(_) | SwipeEvent::End(_)) => {
                    // Lock the base position to scroll around
                    self.offset_base = self.menu.get_offset();
                }
                Some(SwipeEvent::Move(dir, delta)) => {
                    // Decrease the sensitivity of the swipe
                    let delta = delta / Self::TOUCH_SENSITIVITY_DIVIDER;
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
            }
        }

        if let Some(msg) = self.header.event(ctx, event) {
            match msg {
                HeaderMsg::Cancelled => return Some(VerticalMenuScreenMsg::Close),
                HeaderMsg::Back => return Some(VerticalMenuScreenMsg::Back),
                _ => {}
            }
        }

        if let Some(VerticalMenuMsg::Selected(i)) = self.menu.event(ctx, event) {
            return Some(VerticalMenuScreenMsg::Selected(i));
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.menu.render(target);

        // Render the down arrow if the menu overflows and can be scrolled further down
        if !self.menu.fits_area() && !self.menu.is_max_offset() {
            ToifImage::new(SCREEN.bottom_center(), theme::ICON_CHEVRON_DOWN_MINI.toif)
                .with_align(Alignment2D::BOTTOM_CENTER)
                .with_fg(theme::GREY_LIGHT)
                .render(target);
        }
    }
}

#[cfg(feature = "micropython")]
impl Swipable for VerticalMenuScreen {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.swipe_config
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalMenuScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalMenuScreen");
        t.child("Header", &self.header);
        t.child("Menu", &self.menu);
    }
}
