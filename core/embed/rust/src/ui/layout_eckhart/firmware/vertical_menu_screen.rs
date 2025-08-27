use crate::{
    strutil::TString,
    ui::{
        component::{
            swipe_detect::{SwipeConfig, SwipeSettings},
            text::{layout::LayoutFit, TextStyle},
            Component, Event, EventCtx, Label, SwipeDetect, TextLayout,
        },
        event::SwipeEvent,
        flow::Swipable,
        geometry::{Alignment2D, Direction, Offset, Rect},
        shape::{Renderer, ToifImage},
        util::{animation_disabled, Pager},
    },
};

use super::{constant::SCREEN, theme, Header, HeaderMsg, MenuItems, VerticalMenu, VerticalMenuMsg};

pub struct VerticalMenuScreen<T> {
    header: Header,
    /// Optional subtitle label
    subtitle: Option<Label<'static>>,
    /// Scrollable vertical menu
    menu: VerticalMenu<T>,
    /// Base position of the menu sliding window to scroll around
    offset_base: i16,
    /// Swipe detector
    swipe: Option<SwipeDetect>,
    /// Swipe configuration
    swipe_config: SwipeConfig,
}

pub enum VerticalMenuScreenMsg {
    Selected(usize),
    /// Left header button clicked
    Back,
    /// Right header button clicked
    Close,
    /// Menu item selected
    Menu,
}

impl<T: MenuItems> VerticalMenuScreen<T> {
    const TOUCH_SENSITIVITY_DIVIDER: i16 = 12;
    const SUBTITLE_STYLE: TextStyle = theme::TEXT_MEDIUM_GREY;
    const SUBTITLE_HEIGHT: i16 = 68;
    const SUBTITLE_DOUBLE_HEIGHT: i16 = 100;

    pub fn new(menu: VerticalMenu<T>) -> Self {
        Self {
            header: Header::new(TString::empty()),
            subtitle: None,
            menu,
            offset_base: 0,
            swipe: None,
            swipe_config: SwipeConfig::new()
                .with_swipe(Direction::Up, SwipeSettings::default())
                .with_swipe(Direction::Down, SwipeSettings::default()),
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        if !subtitle.is_empty() {
            self.subtitle =
                Some(Label::left_aligned(subtitle, Self::SUBTITLE_STYLE).vertically_centered());
        }
        self
    }

    /// Update swipe detection and buttons state based on menu size
    pub fn initialize_screen(&mut self, ctx: &mut EventCtx) {
        if animation_disabled() {
            self.swipe = Some(SwipeDetect::new());
            ctx.enable_swipe();
            // Set default position for the sliding window
            self.menu.set_offset(0);
            // Update the menu buttons state
            self.menu.update_button_states(ctx);
            return;
        }

        // Switch swiping on/off based on the menu fit
        self.swipe = if !self.menu.fits_area() {
            ctx.enable_swipe();
            Some(SwipeDetect::new())
        } else {
            ctx.disable_swipe();
            None
        };

        // Set default position for the sliding window
        self.menu.set_offset(0);
        // Update button states
        self.menu.update_button_states(ctx);
    }

    fn handle_swipe_event(&mut self, ctx: &mut EventCtx, event: Event) {
        // Relevant only for testing when the animations are disabled
        // The menu is scrollable until the last button is visible
        if animation_disabled() {
            // Handle swipes from the standalone swipe detector or ones coming from
            // the flow. These two are mutually exclusive and should not be triggered at the
            // same time.
            let direction = self
                .swipe
                .as_mut()
                .and_then(|swipe| swipe.event(ctx, event, self.swipe_config))
                .and_then(|e| match e {
                    SwipeEvent::End(dir @ (Direction::Up | Direction::Down)) => Some(dir),
                    _ => None,
                })
                .or(match event {
                    Event::Swipe(SwipeEvent::End(dir @ (Direction::Up | Direction::Down))) => {
                        Some(dir)
                    }
                    _ => None,
                });

            if let Some(dir) = direction {
                self.menu.scroll_item(dir);
                self.menu.update_button_states(ctx);
                ctx.request_paint();
            }
            return;
        }

        if let Some(swipe) = &mut self.swipe {
            // Handle swipe events from the standalone swipe detector or ones coming from
            // the flow. These two are mutually exclusive and should not be triggered at the
            // same time.
            let swipe_event = swipe.event(ctx, event, self.swipe_config).or(match event {
                Event::Swipe(e) => Some(e),
                _ => None,
            });

            match swipe_event {
                Some(SwipeEvent::Start(_) | SwipeEvent::End(_)) => {
                    // Lock the base position to scroll around
                    self.offset_base = self.menu.get_offset();
                }
                Some(SwipeEvent::Move(dir @ (Direction::Up | Direction::Down), delta)) => {
                    // Reduce swipe sensitivity
                    let delta = delta / Self::TOUCH_SENSITIVITY_DIVIDER;

                    let offset = match dir {
                        Direction::Up => self.offset_base + delta,
                        Direction::Down => self.offset_base - delta,
                        _ => unreachable!(), // Already matched Up or Down
                    };

                    self.menu.set_offset(offset);
                    self.menu.update_button_states(ctx);
                    ctx.request_paint();
                }
                _ => {}
            }
        }
    }

    fn render_overflow_arrow<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Do not render the arrow if animations are disabled
        if animation_disabled() {
            return;
        }

        // Render the down arrow if the menu overflows and can be scrolled further down
        if self.swipe.is_some() && !self.menu.is_max_offset() {
            ToifImage::new(SCREEN.bottom_center(), theme::ICON_CHEVRON_DOWN_MINI.toif)
                .with_align(Alignment2D::BOTTOM_CENTER)
                .with_fg(theme::GREY_LIGHT)
                .render(target);
        }
    }
}

impl<T: MenuItems> Component for VerticalMenuScreen<T> {
    type Msg = VerticalMenuScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);

        let menu_area = if let Some(subtitle) = &mut self.subtitle {
            // Choose appropriate height for the subtitle
            let subtitle_height = if let LayoutFit::OutOfBounds { .. } =
                subtitle.text().map(|text| {
                    TextLayout::new(Self::SUBTITLE_STYLE)
                        .with_bounds(
                            Rect::from_size(Offset::new(bounds.width(), Self::SUBTITLE_HEIGHT))
                                .inset(theme::SIDE_INSETS),
                        )
                        .fit_text(text)
                }) {
                Self::SUBTITLE_DOUBLE_HEIGHT
            } else {
                Self::SUBTITLE_HEIGHT
            };

            let (subtitle_area, rest) = rest.split_top(subtitle_height);
            subtitle.place(subtitle_area.inset(theme::SIDE_INSETS));
            rest
        } else {
            rest
        };

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

        if let Some(msg) = self.header.event(ctx, event) {
            match msg {
                HeaderMsg::Cancelled => return Some(VerticalMenuScreenMsg::Close),
                HeaderMsg::Back => return Some(VerticalMenuScreenMsg::Back),
                HeaderMsg::Menu => return Some(VerticalMenuScreenMsg::Menu),
            }
        }

        if let Some(VerticalMenuMsg::Selected(i)) = self.menu.event(ctx, event) {
            return Some(VerticalMenuScreenMsg::Selected(i));
        }

        self.handle_swipe_event(ctx, event);
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.subtitle.render(target);
        self.menu.render(target);
        self.render_overflow_arrow(target);
    }
}

#[cfg(feature = "micropython")]
impl<T: MenuItems> Swipable for VerticalMenuScreen<T> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.swipe_config
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl<T: MenuItems> crate::trace::Trace for VerticalMenuScreen<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalMenuScreen");
        t.child("Header", &self.header);
        t.child("Menu", &self.menu);
    }
}
