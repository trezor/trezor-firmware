use crate::{
    strutil::TString,
    time::Instant,
    ui::{
        component::{
            swipe_detect::{SwipeConfig, SwipeSettings},
            text::{layout::LayoutFit, TextStyle},
            Component, Event, EventCtx, Label, LineBreaking, SwipeDetect, TextLayout,
        },
        display::Icon,
        event::SwipeEvent,
        flow::Swipable,
        geometry::{Alignment2D, Direction, Insets, Offset, Rect},
        shape::{Renderer, ToifImage},
        util::{animation_disabled, Pager},
    },
};

use super::{
    super::component::HapticMode, constant::SCREEN, theme, Header, HeaderMsg, MenuItems,
    ShortMenuVec, VerticalMenu, VerticalMenuMsg,
};

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
    /// Inertia scrolling state
    inertia: InertiaState,
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
    const TOUCH_SENSITIVITY_DIVIDER: i16 = 8;
    const SUBTITLE_STYLE: TextStyle =
        theme::TEXT_MEDIUM_GREY.with_line_breaking(LineBreaking::BreakAtWhitespace);
    const SUBTITLE_HEIGHT: i16 = 68;
    const SUBTITLE_DOUBLE_HEIGHT: i16 = 100;
    const SUBTITLE_PADDING: i16 = 20;
    const OVERFLOW_ARROW_Y_OFFSET: i16 = 18;
    const OVERFLOW_ARROW_ICON: Icon = theme::ICON_CHEVRON_DOWN_MINI;

    pub fn new(menu: VerticalMenu<T>) -> Self {
        Self {
            header: Header::new(TString::empty()),
            subtitle: None,
            menu,
            offset_base: 0,
            swipe: None,
            swipe_config: SwipeConfig::new()
                .with_swipe(Direction::Up, SwipeSettings::Default)
                .with_swipe(Direction::Down, SwipeSettings::Default),
            inertia: InertiaState::new(),
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
            // The menu shouldn't overlap the subtitle area
            self.menu.no_top_component_overlap();
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
        if !self.menu.fits_area() {
            ctx.enable_swipe();
            self.swipe = Some(SwipeDetect::new());
            // Delay haptic feedback to click for scrollable menus
            self.menu.set_haptic_mode(HapticMode::OnClick);
        } else {
            ctx.disable_swipe();
            self.swipe = None;
        }

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

        // Handle inertia animation frames
        if EventCtx::is_anim_frame(event) && self.inertia.is_active() {
            if let Some(displacement) = self.inertia.advance(ctx) {
                let current = self.menu.get_offset();
                // Perform addition in a wider type and clamp to the valid offset range
                let new_offset_i32 = current as i32 + displacement as i32;
                let new_offset = new_offset_i32.clamp(i16::MIN as i32, i16::MAX as i32) as i16;
                self.menu.set_offset(new_offset);

                // If we hit a boundary, stop coasting
                let clamped_offset = self.menu.get_offset();
                if clamped_offset != new_offset {
                    self.inertia.stop();
                }

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
                Some(SwipeEvent::Start(_)) => {
                    // Cancel any ongoing inertia on new touch
                    self.inertia.stop();
                    // Lock the base position to scroll around
                    self.offset_base = self.menu.get_offset();
                }
                Some(SwipeEvent::End(Direction::Up | Direction::Down)) => {
                    // Lock the base position
                    self.offset_base = self.menu.get_offset();
                    // Start coasting if velocity is sufficient
                    self.inertia.start_coast(ctx);
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

                    // Record clamped offset for velocity tracking
                    self.inertia.record_move(self.menu.get_offset());

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
            ToifImage::new(
                SCREEN
                    .bottom_center()
                    .ofs(Offset::y(Self::OVERFLOW_ARROW_Y_OFFSET).neg()),
                Self::OVERFLOW_ARROW_ICON.toif,
            )
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
                                .inset(Insets::new(
                                    Self::SUBTITLE_PADDING,
                                    theme::PADDING,
                                    Self::SUBTITLE_PADDING,
                                    theme::PADDING,
                                )),
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
            rest.outset(Insets::top(VerticalMenu::<ShortMenuVec>::BUTTON_TOP_SHRINK))
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
        self.subtitle.render(target);
        // Render overlapping components in correct order
        if self.header.pressed() {
            self.menu.render(target);
            self.header.render(target);
        } else {
            self.header.render(target);
            self.menu.render(target);
        }
        self.render_overflow_arrow(target);
    }
}

/// State for velocity-based inertia scrolling
struct InertiaState {
    /// Current scroll velocity in pixels per millisecond
    velocity: f32,
    /// Accumulated fractional offset not yet applied
    remainder: f32,
    /// Previous offset for velocity calculation
    last_offset: i16,
    /// Timestamp of last move event
    last_move_time: Option<Instant>,
    /// Timestamp of last animation frame
    last_frame_time: Option<Instant>,
}

impl InertiaState {
    /// Precomputed ln(FRICTION_PER_MS). ln(0.993) ≈ -0.00702
    const LN_FRICTION_PER_MS: f32 = -0.00702;

    /// Stop coasting below this (px/ms). 0.06 px/ms ~ 1.0 px/frame
    const MIN_VELOCITY: f32 = 0.06;

    /// Cap velocity at ~2.5 px/ms (~42 px/frame at 60fps).
    /// Prevents violent flings from overshooting the entire menu.
    const MAX_VELOCITY: f32 = 2.5;

    /// EMA smoothing. 0.4 gives a good balance: responsive to quick flicks
    /// while filtering jitter from noisy touch panels.
    const VELOCITY_SMOOTHING: f32 = 0.4;

    const fn new() -> Self {
        Self {
            velocity: 0.0,
            remainder: 0.0,
            last_offset: 0,
            last_move_time: None,
            last_frame_time: None,
        }
    }

    /// Reset all inertia state (e.g. on new touch)
    fn stop(&mut self) {
        *self = Self::new();
    }

    /// Record a move sample and update smoothed velocity
    fn record_move(&mut self, offset: i16) {
        let now = Instant::now();
        if let Some(prev_time) = self.last_move_time {
            let dt_ms = now.saturating_duration_since(prev_time).to_millis() as f32;
            if dt_ms > 0.0 {
                let delta = (offset - self.last_offset) as f32;
                let instant_velocity = delta / dt_ms;
                // Exponential moving average
                self.velocity = self.velocity * (1.0 - Self::VELOCITY_SMOOTHING)
                    + instant_velocity * Self::VELOCITY_SMOOTHING;
            }
        }
        self.last_offset = offset;
        self.last_move_time = Some(now);
    }

    /// Check if coasting should start and request the first frame if so
    fn start_coast(&mut self, ctx: &mut EventCtx) {
        let now = Instant::now();
        if let Some(last_move) = self.last_move_time {
            let idle_ms = now.saturating_duration_since(last_move).to_millis() as f32;
            // If movement stopped before finger-up, don't launch inertia from stale speed.
            if idle_ms > 50.0 {
                self.stop();
                return;
            }
        }

        // Clamp velocity
        self.velocity = self.velocity.clamp(-Self::MAX_VELOCITY, Self::MAX_VELOCITY);

        if self.velocity.abs() >= Self::MIN_VELOCITY {
            self.last_frame_time = Some(now);
            self.remainder = 0.0;
            ctx.request_anim_frame();
        } else {
            self.stop();
        }
    }

    /// Returns true if currently coasting
    fn is_active(&self) -> bool {
        self.last_frame_time.is_some()
    }

    /// Advance the coasting by one frame. Returns the integer offset delta
    /// to apply, or None if coasting has stopped.
    fn advance(&mut self, ctx: &mut EventCtx) -> Option<i16> {
        let last_frame_time = self.last_frame_time?;
        let now = Instant::now();
        let dt_ms = now.saturating_duration_since(last_frame_time).to_millis() as f32;
        let dt_ms = dt_ms.min(100.0); // clamp to avoid excessive jumps on long delays

        // Apply velocity to get fractional displacement
        let displacement = self.velocity * dt_ms + self.remainder;
        // Clamp to i16 range before truncation to avoid saturating cast surprises
        let displacement = displacement.clamp(i16::MIN as f32, i16::MAX as f32);
        // Split into integer part (to apply) and fractional remainder (to accumulate)
        let int_displacement = displacement as i16;
        self.remainder = displacement - int_displacement as f32;

        // Apply friction: v *= friction^dt
        // First-order Taylor: a^dt ≈ 1 + dt*ln(a)
        let friction = 1.0 + Self::LN_FRICTION_PER_MS * dt_ms;
        self.velocity *= friction.max(0.0);

        self.last_frame_time = Some(now);

        if self.velocity.abs() < Self::MIN_VELOCITY {
            self.stop();
        } else {
            ctx.request_anim_frame();
        }

        Some(int_displacement)
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

#[cfg(test)]
mod tests {
    use super::{super::VerticalMenu, *};

    #[test]
    fn test_min_offset() {
        // The top of the overflow arrow must be less than the bottom padding to avoid
        // hiding the button content
        debug_assert!(
            VerticalMenuScreen::<ShortMenuVec>::OVERFLOW_ARROW_Y_OFFSET
                + VerticalMenuScreen::<ShortMenuVec>::OVERFLOW_ARROW_ICON
                    .toif
                    .height()
                < VerticalMenu::<ShortMenuVec>::TEST_MENU_ITEM_CONTENT_PADDING
        );
    }
}
