use easer::functions::Cubic;
use sys::time::Duration;

use crate::ui::component::attach_anim::{ease_in_out, fade_in, slide_in, AttachAnim};
use crate::ui::component::base::{AttachType, EventPropagation};
use crate::ui::component::{Component, Event, EventCtx, Paginate};
use crate::ui::constant::screen;
use crate::ui::display::Color;
use crate::ui::event::SwipeEvent;
use crate::ui::geometry::{Direction, Offset, Rect};
use crate::ui::lerp::Lerp;
use crate::ui::shape::{self, Renderer};
use crate::ui::util::Pager;

/// Duration of the attach animation of swiped content.
const ATTACH_DURATION: Duration = Duration::from_millis(500);
/// Duration of the fade-in at the start of the attach animation.
const ATTACH_FADE_DURATION: Duration = Duration::from_millis(200);

/// Attach animation of swiped content. Animates only vertical and initial
/// attaches.
pub fn attach_anim() -> AttachAnim {
    AttachAnim::new(ATTACH_DURATION)
}

/// Content offset during the attach animation: slides in vertically from
/// `distance` pixels away. An initial attach slides in from above.
pub fn attach_offset(anim: &AttachAnim, distance: i16) -> Offset {
    match anim.dir() {
        Some(dir @ (Direction::Up | Direction::Down)) => slide_in(dir, distance, anim.t()),
        Some(_) => Offset::zero(),
        None => slide_in(Direction::Down, distance, anim.t()),
    }
}

/// Content opacity during the attach animation.
pub fn attach_opacity(anim: &AttachAnim) -> u8 {
    fade_in(ease_in_out::<Cubic>(
        anim.window(Duration::ZERO, ATTACH_FADE_DURATION),
    ))
}

struct SwipeContext {
    progress: i16,
    dir: Direction,
    attach_anim: AttachAnim,
    show_attach_anim: bool,
}

impl SwipeContext {
    fn new() -> Self {
        Self {
            progress: 0,
            dir: Direction::Up,
            attach_anim: attach_anim(),
            show_attach_anim: true,
        }
    }

    fn get_params(&self, bounds: Rect) -> (Offset, Rect, u8) {
        let progress = f32::from(self.progress) / 1000.0;

        let shift = pareen::constant(0.0).seq_ease_out(
            0.0,
            easer::functions::Cubic,
            1.0,
            pareen::constant(1.0),
        );

        let y_offset = i16::lerp(0, 50, shift.eval(progress));

        let mut offset = Offset::zero();
        let mut clip = bounds;
        let mut mask = 0;

        if self.progress > 0 {
            match self.dir {
                Direction::Up => {
                    offset = Offset::y(-y_offset);
                    mask = u8::lerp(0, 255, shift.eval(progress));
                }
                Direction::Down => {
                    offset = Offset::y(y_offset);
                    clip = screen();
                    mask = u8::lerp(0, 255, shift.eval(progress));
                }
                _ => {}
            }
        } else {
            offset = attach_offset(&self.attach_anim, 20);
            mask = 255 - attach_opacity(&self.attach_anim);

            if offset.x == 0 && offset.y == 0 {
                clip = screen();
            }
        }

        (offset, clip, mask)
    }

    fn process_event(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
        animate: bool,
    ) -> EventPropagation {
        let show_attach_anim = self.show_attach_anim;
        self.attach_anim.event_filtered(ctx, event, |attach| {
            show_attach_anim
                && animate
                && matches!(
                    attach,
                    AttachType::Initial | AttachType::Swipe(Direction::Up | Direction::Down)
                )
        });

        if let Event::Attach(_) = event {
            self.progress = 0;
        }

        if let Event::Swipe(SwipeEvent::Move(dir, progress)) = event {
            match dir {
                Direction::Up | Direction::Down if animate => {
                    self.dir = dir;
                    self.progress = progress;
                }
                _ => {}
            }
            ctx.request_paint();
        }

        // no touch input while the content is animating in
        match event {
            Event::Touch(_) if self.attach_anim.is_active() => EventPropagation::Stop,
            _ => EventPropagation::Continue,
        }
    }
}

pub struct SwipeContent<T> {
    inner: T,
    bounds: Rect,
    swipe_context: SwipeContext,
}

impl<T: Component> SwipeContent<T> {
    pub fn new(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            swipe_context: SwipeContext::new(),
        }
    }

    pub fn with_no_attach_anim(mut self) -> Self {
        self.swipe_context.show_attach_anim = false;
        self
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }

    fn process_event(&mut self, ctx: &mut EventCtx, event: Event, animate: bool) -> Option<T::Msg> {
        let propagate = self.swipe_context.process_event(ctx, event, animate);

        if matches!(propagate, EventPropagation::Continue) {
            self.inner.event(ctx, event)
        } else {
            None
        }
    }
}

impl<T: Component> Component for SwipeContent<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = self.inner.place(bounds);
        self.bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.process_event(ctx, event, true)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let (offset, clip, mask) = self.swipe_context.get_params(self.bounds);

        target.in_clip(clip, &|target| {
            target.with_origin(offset, &|target| {
                self.inner.render(target);
                shape::Bar::new(self.bounds)
                    .with_alpha(mask)
                    .with_fg(Color::black())
                    .with_bg(Color::black())
                    .render(target);
            });
        });
    }
}

impl<T: Paginate> Paginate for SwipeContent<T> {
    fn pager(&self) -> Pager {
        self.inner.pager()
    }

    fn change_page(&mut self, to_page: u16) {
        self.inner.change_page(to_page);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for SwipeContent<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SwipeContent");
        t.child("content", &self.inner);
    }
}

pub struct InternallySwipableContent<T>
where
    T: Component + Paginate,
{
    content: SwipeContent<T>,
    animate: bool,
}

impl<T> InternallySwipableContent<T>
where
    T: Component + Paginate,
{
    pub fn new(content: T) -> Self {
        Self {
            content: SwipeContent::new(content),
            animate: true,
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    fn should_animate_attach(&self, attach_type: AttachType) -> bool {
        let pager = self.content.inner.pager();
        let is_swipe_up = matches!(attach_type, AttachType::Swipe(Direction::Up));
        let is_swipe_down = matches!(attach_type, AttachType::Swipe(Direction::Down));

        if !self.content.swipe_context.show_attach_anim {
            return false;
        }

        if pager.is_first() && is_swipe_up {
            return true;
        }

        if pager.is_last() && is_swipe_down {
            return true;
        }

        false
    }

    fn should_animate_swipe(&self, swipe_direction: Direction) -> bool {
        let pager = self.content.inner.pager();
        let is_swipe_up = matches!(swipe_direction, Direction::Up);
        let is_swipe_down = matches!(swipe_direction, Direction::Down);

        if pager.is_last() && is_swipe_up {
            return true;
        }

        if pager.is_first() && is_swipe_down {
            return true;
        }

        false
    }
}

impl<T> Component for InternallySwipableContent<T>
where
    T: Component + Paginate,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.content.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let animate = match event {
            Event::Attach(attach_type) => self.should_animate_attach(attach_type),
            Event::Swipe(SwipeEvent::Move(dir, _)) => self.should_animate_swipe(dir),
            Event::Swipe(SwipeEvent::End(dir)) => self.should_animate_swipe(dir),
            _ => self.animate,
        };

        self.animate = animate;

        self.content.process_event(ctx, event, animate)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.content.render(target)
    }
}

impl<T> Paginate for InternallySwipableContent<T>
where
    T: Component + Paginate,
{
    fn pager(&self) -> Pager {
        self.content.pager()
    }

    fn change_page(&mut self, to_page: u16) {
        self.content.change_page(to_page);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for InternallySwipableContent<T>
where
    T: crate::trace::Trace + Component + Paginate,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("InternallySwipableContent");
        t.child("content", &self.content);
    }
}
