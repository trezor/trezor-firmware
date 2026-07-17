use super::super::firmware::{Header, TextScreen, TextScreenMsg};
use crate::error::Error;
use crate::maybe_trace::MaybeTrace;
use crate::strutil::TString;
use crate::ui::component::text::paragraphs::{ParagraphSource, Paragraphs};
use crate::ui::component::{Component, ComponentExt, MsgMap};
use crate::ui::flow::base::{Decision, DecisionBuilder};
use crate::ui::flow::{FlowController, FlowMsg, Swipable, SwipeFlow};
use crate::ui::geometry::{Direction, LinearPlacement};

enum SinglePage {
    Show,
}

impl FlowController for SinglePage {
    #[inline]
    fn index(&'static self) -> usize {
        0
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        self.return_msg(msg)
    }
}

pub fn single_page<T>(layout: T) -> Result<SwipeFlow, Error>
where
    T: Component<Msg = FlowMsg> + Swipable + MaybeTrace + 'static,
{
    let mut flow = SwipeFlow::new(&SinglePage::Show)?;
    flow.add_page(&SinglePage::Show, layout)?;
    Ok(flow)
}

pub fn content_menu_info<'a, P>(
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    paragraphs: P,
) -> MsgMap<TextScreen<Paragraphs<P>>, impl Fn(TextScreenMsg) -> Option<FlowMsg>>
where
    P: ParagraphSource<'a> + 'a,
{
    TextScreen::new(
        paragraphs
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(title).with_close_button())
    .with_subtitle(subtitle.unwrap_or(TString::empty()))
    .map(|_| Some(FlowMsg::Cancelled))
}
