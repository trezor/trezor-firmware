from typing import *
from trezor import utils
T = TypeVar("T")


# rust/src/ui/model_mercury/layout.rs
class LayoutObj(Generic[T]):
    """Representation of a Rust-based layout object.
    see `trezor::ui::layout::obj::LayoutObj`.
    """
    def attach_timer_fn(self, fn: Callable[[int, int], None]) -> None:
        """Attach a timer setter function.
        The layout object can call the timer setter with two arguments,
        `token` and `deadline`. When `deadline` is reached, the layout object
        expects a callback to `self.timer(token)`.
        """
    if utils.USE_TOUCH:
        def touch_event(self, event: int, x: int, y: int) -> T | None:
            """Receive a touch event `event` at coordinates `x`, `y`."""
    if utils.USE_BUTTON:
        def button_event(self, event: int, button: int) -> T | None:
            """Receive a button event `event` for button `button`."""
    def progress_event(self, value: int, description: str) -> T | None:
        """Receive a progress event."""
    def usb_event(self, connected: bool) -> T | None:
        """Receive a USB connect/disconnect event."""
    def timer(self, token: int) -> T | None:
        """Callback for the timer set by `attach_timer_fn`.
        This function should be called by the executor after the corresponding
        deadline is reached.
        """
    def paint(self) -> bool:
        """Paint the layout object on screen.
        Will only paint updated parts of the layout as required.
        Returns True if any painting actually happened.
        """
    def request_complete_repaint(self) -> None:
        """Request a complete repaint of the screen.
        Does not repaint the screen, a subsequent call to `paint()` is required.
        """
    if __debug__:
        def trace(self, tracer: Callable[[str], None]) -> None:
            """Generate a JSON trace of the layout object.
            The JSON can be emitted as a sequence of calls to `tracer`, each of
            which is not necessarily a valid JSON chunk. The caller must
            reassemble the chunks to get a sensible result.
            """
        def bounds(self) -> None:
            """Paint bounds of individual components on screen."""
    def page_count(self) -> int:
        """Return the number of pages in the layout object."""
    def __del__(self) -> None:
        """Calls drop on contents of the root component."""


# rust/src/ui/model_mercury/layout.rs
class UiResult:
   """Result of a UI operation."""
   pass
CONFIRMED: UiResult
CANCELLED: UiResult
INFO: UiResult


# rust/src/ui/model_mercury/layout.rs
def disable_animation(disable: bool) -> None:
    """Disable animations, debug builds only."""


# rust/src/ui/model_mercury/layout.rs
def check_homescreen_format(data: bytes) -> bool:
    """Check homescreen format and dimensions."""


# rust/src/ui/model_mercury/layout.rs
def confirm_action(
    *,
    title: str,
    action: str | None,
    description: str | None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    prompt_screen: bool = False,
    prompt_title: str | None = None,
) -> LayoutObj[UiResult]:
    """Confirm action."""


# rust/src/ui/model_mercury/layout.rs
def confirm_emphasized(
    *,
    title: str,
    items: Iterable[str | tuple[bool, str]],
    verb: str | None = None,
) -> LayoutObj[UiResult]:
    """Confirm formatted text that has been pre-split in python. For tuples
    the first component is a bool indicating whether this part is emphasized."""


# rust/src/ui/model_mercury/layout.rs
def confirm_homescreen(
    *,
    title: str,
    image: bytes,
) -> LayoutObj[UiResult]:
    """Confirm homescreen."""


# rust/src/ui/model_mercury/layout.rs
def confirm_blob(
    *,
    title: str,
    data: str | bytes,
    description: str | None,
    extra: str | None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm byte sequence data."""


# rust/src/ui/model_mercury/layout.rs
def confirm_address(
    *,
    title: str,
    data: str | bytes,
    description: str | None,
    verb: str | None = "CONFIRM",
    extra: str | None,
    chunkify: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm address. Similar to `confirm_blob` but has corner info button
    and allows left swipe which does the same thing as the button."""


# rust/src/ui/model_mercury/layout.rs
def confirm_properties(
    *,
    title: str,
    items: list[tuple[str | None, str | bytes | None, bool]],
    hold: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm list of key-value pairs. The third component in the tuple should be True if
    the value is to be rendered as binary with monospace font, False otherwise."""


# rust/src/ui/model_mercury/layout.rs
def flow_confirm_reset_recover() -> LayoutObj[UiResult]:
    """Confirm TOS before recovery process."""


# rust/src/ui/model_mercury/layout.rs
def flow_confirm_reset_create() -> LayoutObj[UiResult]:
    """Confirm TOS before creating a wallet and have a user hold to confirm creation."""


# rust/src/ui/model_mercury/layout.rs
def flow_confirm_set_new_pin(
    *,
    title: str,
    description: str,
) -> LayoutObj[UiResult]:
    """Confirm new PIN setup with an option to cancel action."""


# rust/src/ui/model_mercury/layout.rs
def show_info_with_cancel(
    *,
    title: str,
    items: Iterable[Tuple[str, str]],
    horizontal: bool = False,
    chunkify: bool = False,
) -> LayoutObj[UiResult]:
    """Show metadata for outgoing transaction."""


# rust/src/ui/model_mercury/layout.rs
def confirm_value(
    *,
    title: str,
    value: str,
    description: str | None,
    subtitle: str | None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    info_button: bool = False,
    hold: bool = False,
    chunkify: bool = False,
    text_mono: bool = True,
) -> LayoutObj[UiResult]:
    """Confirm value. Merge of confirm_total and confirm_output."""


# rust/src/ui/model_mercury/layout.rs
def confirm_total(
    *,
    title: str,
    items: Iterable[tuple[str, str]],
    info_button: bool = False,
    cancel_arrow: bool = False,
) -> LayoutObj[UiResult]:
    """Transaction summary. Always hold to confirm."""


# rust/src/ui/model_mercury/layout.rs
def confirm_modify_output(
    *,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> LayoutObj[UiResult]:
    """Decrease or increase output amount."""


# rust/src/ui/model_mercury/layout.rs
def confirm_modify_fee(
    *,
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None,  # ignored
) -> LayoutObj[UiResult]:
    """Decrease or increase transaction fee."""


# rust/src/ui/model_mercury/layout.rs
def confirm_fido(
    *,
    title: str,
    app_name: str,
    icon_name: str | None,
    accounts: list[str | None],
) -> LayoutObj[int | UiResult]:
    """FIDO confirmation.
    Returns page index in case of confirmation and CANCELLED otherwise.
    """


# rust/src/ui/model_mercury/layout.rs
def show_error(
    *,
    title: str,
    button: str = "CONTINUE",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Error modal. No buttons shown when `button` is empty string."""


# rust/src/ui/model_mercury/layout.rs
def show_warning(
    *,
    title: str,
    button: str = "CONTINUE",
    value: str = "",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Warning modal. No buttons shown when `button` is empty string."""


# rust/src/ui/model_mercury/layout.rs
def show_success(
    *,
    title: str,
    button: str = "CONTINUE",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Success screen. Description is used in the footer."""


# rust/src/ui/model_mercury/layout.rs
def show_info(
    *,
    title: str,
    button: str = "CONTINUE",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Info modal. No buttons shown when `button` is empty string."""


# rust/src/ui/model_mercury/layout.rs
def show_mismatch(*, title: str) -> LayoutObj[UiResult]:
    """Warning modal, receiving address mismatch."""


# rust/src/ui/model_mercury/layout.rs
def show_simple(
    *,
    title: str | None,
    description: str = "",
    button: str = "",
) -> LayoutObj[UiResult]:
    """Simple dialog with text and one button."""


# rust/src/ui/model_mercury/layout.rs
def confirm_with_info(
    *,
    title: str,
    button: str,
    info_button: str,
    items: Iterable[tuple[int, str]],
) -> LayoutObj[UiResult]:
    """Confirm given items but with third button. Always single page
    without scrolling."""


# rust/src/ui/model_mercury/layout.rs
def confirm_more(
    *,
    title: str,
    button: str,
    items: Iterable[tuple[int, str]],
) -> LayoutObj[UiResult]:
    """Confirm long content with the possibility to go back from any page.
    Meant to be used with confirm_with_info."""


# rust/src/ui/model_mercury/layout.rs
def confirm_coinjoin(
    *,
    max_rounds: str,
    max_feerate: str,
) -> LayoutObj[UiResult]:
    """Confirm coinjoin authorization."""


# rust/src/ui/model_mercury/layout.rs
def request_pin(
    *,
    prompt: str,
    subprompt: str,
    allow_cancel: bool = True,
    wrong_pin: bool = False,
) -> LayoutObj[str | UiResult]:
    """Request pin on device."""


# rust/src/ui/model_mercury/layout.rs
def request_passphrase(
    *,
    prompt: str,
    max_len: int,
) -> LayoutObj[str | UiResult]:
    """Passphrase input keyboard."""


# rust/src/ui/model_mercury/layout.rs
def request_bip39(
    *,
    prompt: str,
    prefill_word: str,
    can_go_back: bool,
) -> LayoutObj[str]:
    """BIP39 word input keyboard."""


# rust/src/ui/model_mercury/layout.rs
def request_slip39(
    *,
    prompt: str,
    prefill_word: str,
    can_go_back: bool,
) -> LayoutObj[str]:
    """SLIP39 word input keyboard."""


# rust/src/ui/model_mercury/layout.rs
def select_word(
    *,
    title: str,
    description: str,
    words: Iterable[str],
) -> LayoutObj[int]:
    """Select mnemonic word from three possibilities - seed check after backup. The
   iterable must be of exact size. Returns index in range `0..3`."""


# rust/src/ui/model_mercury/layout.rs
def flow_prompt_backup() -> LayoutObj[UiResult]
"""Prompt a user to create backup with an option to skip."""


# rust/src/ui/model_mercury/layout.rs
def flow_show_share_words(
    *,
    title: str,
    subtitle: str,
    words: Iterable[str],
    description: str,
    text_info: Iterable[str],
    text_confirm: str,
    highlight_repeated: bool,
) -> LayoutObj[UiResult]:
    """Show wallet backup words preceded by an instruction screen and followed by
    confirmation."""


# rust/src/ui/model_mercury/layout.rs
def flow_request_number(
    *,
    title: str,
    count: int,
    min_count: int,
    max_count: int,
    description: Callable[[int], str] | None = None,
    info: Callable[[int], str] | None = None,
    br_code: ButtonRequestType,
    br_type: str,
) -> LayoutObj[tuple[UiResult, int]]:
    """Numer input with + and - buttons, description, and context menu with cancel and
    info."""


# rust/src/ui/model_mercury/layout.rs
def set_brightness(
    *,
    current: int | None = None
) -> LayoutObj[UiResult]:
    """Show the brightness configuration dialog."""


# rust/src/ui/model_mercury/layout.rs
def show_checklist(
    *,
    title: str,
    items: Iterable[str],
    active: int,
    button: str,
) -> LayoutObj[UiResult]:
    """Checklist of backup steps. Active index is highlighted, previous items have check
   mark next to them."""


# rust/src/ui/model_mercury/layout.rs
def confirm_recovery(
    *,
    title: str,
    description: str,
    button: str,
    recovery_type: RecoveryType,
    info_button: bool = False,
) -> LayoutObj[UiResult]:
    """Device recovery homescreen."""


# rust/src/ui/model_mercury/layout.rs
def select_word_count(
    *,
    recovery_type: RecoveryType,
) -> LayoutObj[int | str]:  # TT returns int
    """Select mnemonic word count from (12, 18, 20, 24, 33)."""


# rust/src/ui/model_mercury/layout.rs
def show_group_share_success(
    *,
    lines: Iterable[str]
) -> LayoutObj[UiResult]:
    """Shown after successfully finishing a group."""


# rust/src/ui/model_mercury/layout.rs
def show_remaining_shares(
    *,
    pages: Iterable[tuple[str, str]],
) -> LayoutObj[UiResult]:
    """Shows SLIP39 state after info button is pressed on `confirm_recovery`."""


# rust/src/ui/model_mercury/layout.rs
def show_progress(
    *,
    title: str,
    indeterminate: bool = False,
    description: str = "",
) -> LayoutObj[UiResult]:
    """Show progress loader. Please note that the number of lines reserved on screen for
   description is determined at construction time. If you want multiline descriptions
   make sure the initial description has at least that amount of lines."""


# rust/src/ui/model_mercury/layout.rs
def show_progress_coinjoin(
    *,
    title: str,
    indeterminate: bool = False,
    time_ms: int = 0,
    skip_first_paint: bool = False,
) -> LayoutObj[UiResult]:
    """Show progress loader for coinjoin. Returns CANCELLED after a specified time when
   time_ms timeout is passed."""


# rust/src/ui/model_mercury/layout.rs
def show_homescreen(
    *,
    label: str | None,
    hold: bool,
    notification: str | None,
    notification_level: int = 0,
    skip_first_paint: bool,
) -> LayoutObj[UiResult]:
    """Idle homescreen."""


# rust/src/ui/model_mercury/layout.rs
def show_lockscreen(
    *,
    label: str | None,
    bootscreen: bool,
    skip_first_paint: bool,
    coinjoin_authorized: bool = False,
) -> LayoutObj[UiResult]:
    """Homescreen for locked device."""


# rust/src/ui/model_mercury/layout.rs
def confirm_firmware_update(
    *,
    description: str,
    fingerprint: str,
) -> LayoutObj[UiResult]:
    """Ask whether to update firmware, optionally show fingerprint. Shared with bootloader."""


# rust/src/ui/model_mercury/layout.rs
def show_wait_text(message: str, /) -> LayoutObj[None]:
    """Show single-line text in the middle of the screen."""


# rust/src/ui/model_mercury/layout.rs
def flow_get_address(
    *,
    address: str | bytes,
    title: str,
    description: str | None,
    extra: str | None,
    chunkify: bool,
    address_qr: str | None,
    case_sensitive: bool,
    account: str | None,
    path: str | None,
    xpubs: list[tuple[str, str]],
    br_code: ButtonRequestType,
    br_type: str,
) -> LayoutObj[UiResult]:
    """Get address / receive funds."""


# rust/src/ui/model_mercury/layout.rs
def flow_warning_hi_prio(
    *,
    title: str,
    description: str,
    value: str = "",
) -> LayoutObj[UiResult]:
    """Warning modal with multiple steps to confirm."""


# rust/src/ui/model_mercury/layout.rs
def flow_confirm_output(
    *,
    title: str | None,
    address: str,
    amount: str,
    chunkify: bool,
    account: str | None,
    account_path: str | None,
    br_code: ButtonRequestType,
    br_type: str,
) -> LayoutObj[UiResult]:
    """Confirm recipient."""


# rust/src/ui/model_mercury/layout.rs
def flow_confirm_summary(
    *,
    title: str,
    items: Iterable[tuple[str, str]],
    account_items: Iterable[tuple[str, str]],
    fee_items: Iterable[tuple[str, str]],
    br_code: ButtonRequestType,
    br_type: str,
) -> LayoutObj[UiResult]:
    """Total summary and hold to confirm."""


# rust/src/ui/model_mercury/layout.rs
class BacklightLevels:
    """Backlight levels. Values dynamically update based on user settings."""
    MAX: ClassVar[int]
    NORMAL: ClassVar[int]
    LOW: ClassVar[int]
    DIM: ClassVar[int]
    NONE: ClassVar[int]
CONFIRMED: UiResult
CANCELLED: UiResult
INFO: UiResult


# rust/src/ui/model_tr/layout.rs
def disable_animation(disable: bool) -> None:
    """Disable animations, debug builds only."""


# rust/src/ui/model_tr/layout.rs
def check_homescreen_format(data: bytes) -> bool:
    """Check homescreen format and dimensions."""


# rust/src/ui/model_tr/layout.rs
def confirm_action(
    *,
    title: str,
    action: str | None,
    description: str | None,
    subtitle: str | None = None,
    verb: str = "CONFIRM",
    verb_cancel: str | None = None,
    hold: bool = False,
    hold_danger: bool = False,  # unused on TR
    reverse: bool = False,
    prompt_screen: bool = False,
    prompt_title: str | None = None,
) -> LayoutObj[UiResult]:
    """Confirm action."""


# rust/src/ui/model_tr/layout.rs
def confirm_homescreen(
    *,
    title: str,
    image: bytes,
) -> object:
    """Confirm homescreen."""


# rust/src/ui/model_tr/layout.rs
def confirm_blob(
    *,
    title: str,
    data: str | bytes,
    description: str | None,
    extra: str | None,
    verb: str = "CONFIRM",
    verb_cancel: str | None = None,
    hold: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm byte sequence data."""


# rust/src/ui/model_tr/layout.rs
def confirm_address(
    *,
    title: str,
    data: str,
    description: str | None,  # unused on TR
    extra: str | None,  # unused on TR
    verb: str = "CONFIRM",
    chunkify: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm address."""


# rust/src/ui/model_tr/layout.rs
def confirm_properties(
    *,
    title: str,
    items: list[tuple[str | None, str | bytes | None, bool]],
    hold: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm list of key-value pairs. The third component in the tuple should be True if
    the value is to be rendered as binary with monospace font, False otherwise.
    This only concerns the text style, you need to decode the value to UTF-8 in python."""


# rust/src/ui/model_tr/layout.rs
def confirm_reset_device(
    *,
    title: str,
    button: str,
) -> LayoutObj[UiResult]:
    """Confirm TOS before device setup."""


# rust/src/ui/model_tr/layout.rs
def confirm_backup() -> LayoutObj[UiResult]:
    """Strongly recommend user to do backup."""


# rust/src/ui/model_tr/layout.rs
def show_address_details(
    *,
    address: str,
    case_sensitive: bool,
    account: str | None,
    path: str | None,
    xpubs: list[tuple[str, str]],
) -> LayoutObj[UiResult]:
    """Show address details - QR code, account, path, cosigner xpubs."""


# rust/src/ui/model_tr/layout.rs
def confirm_value(
    *,
    title: str,
    description: str,
    value: str,
    verb: str | None = None,
    hold: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm value."""


# rust/src/ui/model_tr/layout.rs
def confirm_joint_total(
    *,
    spending_amount: str,
    total_amount: str,
) -> LayoutObj[UiResult]:
    """Confirm total if there are external inputs."""


# rust/src/ui/model_tr/layout.rs
def confirm_modify_output(
    *,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> LayoutObj[UiResult]:
    """Decrease or increase output amount."""


# rust/src/ui/model_tr/layout.rs
def confirm_output_address(
    *,
    address: str,
    address_label: str,
    address_title: str,
    chunkify: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm output address."""


# rust/src/ui/model_tr/layout.rs
def confirm_output_amount(
    *,
    amount: str,
    amount_title: str,
) -> LayoutObj[UiResult]:
    """Confirm output amount."""


# rust/src/ui/model_tr/layout.rs
def confirm_total(
    *,
    total_amount: str,
    fee_amount: str,
    fee_rate_amount: str | None,
    account_label: str | None,
    total_label: str,
    fee_label: str,
) -> LayoutObj[UiResult]:
    """Confirm summary of a transaction."""


# rust/src/ui/model_tr/layout.rs
def altcoin_tx_summary(
    *,
    amount_title: str,
    amount_value: str,
    fee_title: str,
    fee_value: str,
    items: Iterable[Tuple[str, str]],
    cancel_cross: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm details about altcoin transaction."""


# rust/src/ui/model_tr/layout.rs
def tutorial() -> LayoutObj[UiResult]:
    """Show user how to interact with the device."""


# rust/src/ui/model_tr/layout.rs
def confirm_modify_fee(
    *,
    title: str,  # ignored
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None,
) -> LayoutObj[UiResult]:
    """Decrease or increase transaction fee."""


# rust/src/ui/model_tr/layout.rs
def confirm_fido(
    *,
    title: str,
    app_name: str,
    icon_name: str | None,  # unused on TR
    accounts: list[str | None],
) -> LayoutObj[int | UiResult]:
    """FIDO confirmation.
    Returns page index in case of confirmation and CANCELLED otherwise.
    """


# rust/src/ui/model_tr/layout.rs
def multiple_pages_texts(
    *,
    title: str,
    verb: str,
    items: list[str],
) -> LayoutObj[UiResult]:
    """Show multiple texts, each on its own page."""


# rust/src/ui/model_tr/layout.rs
def show_warning(
    *,
    button: str,
    warning: str,
    description: str,
) -> LayoutObj[UiResult]:
    """Warning modal with middle button and centered text."""


# rust/src/ui/model_tr/layout.rs
def show_info(
    *,
    title: str,
    description: str = "",
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Info modal."""


# rust/src/ui/model_tr/layout.rs
def show_passphrase() -> LayoutObj[UiResult]:
    """Show passphrase on host dialog."""


# rust/src/ui/model_tr/layout.rs
def show_mismatch(*, title: str) -> LayoutObj[UiResult]:
    """Warning modal, receiving address mismatch."""


# rust/src/ui/model_tr/layout.rs
def confirm_with_info(
    *,
    title: str,
    button: str,
    info_button: str,  # unused on TR
    items: Iterable[Tuple[int, str | bytes]],
    verb_cancel: str | None = None,
) -> LayoutObj[UiResult]:
    """Confirm given items but with third button. Always single page
    without scrolling."""


# rust/src/ui/model_tr/layout.rs
def confirm_more(
    *,
    title: str,
    button: str,
    items: Iterable[tuple[int, str | bytes]],
) -> object:
    """Confirm long content with the possibility to go back from any page.
    Meant to be used with confirm_with_info."""


# rust/src/ui/model_tr/layout.rs
def confirm_coinjoin(
    *,
    max_rounds: str,
    max_feerate: str,
) -> LayoutObj[UiResult]:
    """Confirm coinjoin authorization."""


# rust/src/ui/model_tr/layout.rs
def request_pin(
    *,
    prompt: str,
    subprompt: str,
    allow_cancel: bool = True,  # unused on TR
    wrong_pin: bool = False,  # unused on TR
) -> LayoutObj[str | UiResult]:
    """Request pin on device."""


# rust/src/ui/model_tr/layout.rs
def request_passphrase(
    *,
    prompt: str,
    max_len: int,  # unused on TR
) -> LayoutObj[str | UiResult]:
    """Get passphrase."""


# rust/src/ui/model_tr/layout.rs
def request_bip39(
    *,
    prompt: str,
    prefill_word: str,
    can_go_back: bool,
) -> LayoutObj[str]:
    """Get recovery word for BIP39."""


# rust/src/ui/model_tr/layout.rs
def request_slip39(
    *,
    prompt: str,
    prefill_word: str,
    can_go_back: bool,
) -> LayoutObj[str]:
   """SLIP39 word input keyboard."""


# rust/src/ui/model_tr/layout.rs
def select_word(
    *,
    title: str,  # unused on TR
    description: str,
    words: Iterable[str],
) -> LayoutObj[int]:
   """Select mnemonic word from three possibilities - seed check after backup. The
   iterable must be of exact size. Returns index in range `0..3`."""


# rust/src/ui/model_tr/layout.rs
def show_share_words(
    *,
    share_words: Iterable[str],
) -> LayoutObj[UiResult]:
    """Shows a backup seed."""


# rust/src/ui/model_tr/layout.rs
def request_number(
    *,
    title: str,
    count: int,
    min_count: int,
    max_count: int,
    description: Callable[[int], str] | None = None,  # unused on TR
) -> LayoutObj[tuple[UiResult, int]]:
   """Number input with + and - buttons, description, and info button."""


# rust/src/ui/model_tr/layout.rs
def show_checklist(
    *,
    title: str,  # unused on TR
    items: Iterable[str],
    active: int,
    button: str,
) -> LayoutObj[UiResult]:
   """Checklist of backup steps. Active index is highlighted, previous items have check
   mark next to them."""


# rust/src/ui/model_tr/layout.rs
def confirm_recovery(
    *,
    title: str,  # unused on TR
    description: str,
    button: str,
    recovery_type: RecoveryType,
    info_button: bool,  # unused on TR
    show_info: bool,
) -> LayoutObj[UiResult]:
   """Device recovery homescreen."""


# rust/src/ui/model_tr/layout.rs
def select_word_count(
    *,
    recovery_type: RecoveryType,  # unused on TR
) -> LayoutObj[int | str]:
   """Select mnemonic word count from (12, 18, 20, 24, 33)."""


# rust/src/ui/model_tr/layout.rs
def show_group_share_success(
    *,
    lines: Iterable[str],
) -> LayoutObj[int]:
   """Shown after successfully finishing a group."""


# rust/src/ui/model_tr/layout.rs
def show_progress(
    *,
    description: str,
    indeterminate: bool = False,
    title: str | None = None,
) -> LayoutObj[UiResult]:
   """Show progress loader. Please note that the number of lines reserved on screen for
   description is determined at construction time. If you want multiline descriptions
   make sure the initial description has at least that amount of lines."""


# rust/src/ui/model_tr/layout.rs
def show_progress_coinjoin(
    *,
    title: str,
    indeterminate: bool = False,
    time_ms: int = 0,
    skip_first_paint: bool = False,
) -> LayoutObj[UiResult]:
   """Show progress loader for coinjoin. Returns CANCELLED after a specified time when
   time_ms timeout is passed."""


# rust/src/ui/model_tr/layout.rs
def show_homescreen(
    *,
    label: str | None,
    hold: bool,  # unused on TR
    notification: str | None,
    notification_level: int = 0,
    skip_first_paint: bool,
) -> LayoutObj[UiResult]:
    """Idle homescreen."""


# rust/src/ui/model_tr/layout.rs
def show_lockscreen(
    *,
    label: str | None,
    bootscreen: bool,
    skip_first_paint: bool,
    coinjoin_authorized: bool = False,
) -> LayoutObj[UiResult]:
    """Homescreen for locked device."""


# rust/src/ui/model_tr/layout.rs
def confirm_firmware_update(
    *,
    description: str,
    fingerprint: str,
) -> None:
    """Ask whether to update firmware, optionally show fingerprint. Shared with bootloader."""


# rust/src/ui/model_tr/layout.rs
def show_wait_text(message: str, /) -> None:
    """Show single-line text in the middle of the screen."""


# rust/src/ui/model_tr/layout.rs
class BacklightLevels:
    """Backlight levels. Values dynamically update based on user settings."""
    MAX: ClassVar[int]
    NORMAL: ClassVar[int]
    LOW: ClassVar[int]
    DIM: ClassVar[int]
    NONE: ClassVar[int]
from trezor import utils
T = TypeVar("T")


# rust/src/ui/model_tt/layout.rs
class LayoutObj(Generic[T]):
    """Representation of a Rust-based layout object.
    see `trezor::ui::layout::obj::LayoutObj`.
    """
    def attach_timer_fn(self, fn: Callable[[int, int], None]) -> None:
        """Attach a timer setter function.
        The layout object can call the timer setter with two arguments,
        `token` and `deadline`. When `deadline` is reached, the layout object
        expects a callback to `self.timer(token)`.
        """
    if utils.USE_TOUCH:
        def touch_event(self, event: int, x: int, y: int) -> T | None:
            """Receive a touch event `event` at coordinates `x`, `y`."""
    if utils.USE_BUTTON:
        def button_event(self, event: int, button: int) -> T | None:
            """Receive a button event `event` for button `button`."""
    def progress_event(self, value: int, description: str) -> T | None:
        """Receive a progress event."""
    def usb_event(self, connected: bool) -> T | None:
        """Receive a USB connect/disconnect event."""
    def timer(self, token: int) -> T | None:
        """Callback for the timer set by `attach_timer_fn`.
        This function should be called by the executor after the corresponding
        deadline is reached.
        """
    def paint(self) -> bool:
        """Paint the layout object on screen.
        Will only paint updated parts of the layout as required.
        Returns True if any painting actually happened.
        """
    def request_complete_repaint(self) -> None:
        """Request a complete repaint of the screen.
        Does not repaint the screen, a subsequent call to `paint()` is required.
        """
    if __debug__:
        def trace(self, tracer: Callable[[str], None]) -> None:
            """Generate a JSON trace of the layout object.
            The JSON can be emitted as a sequence of calls to `tracer`, each of
            which is not necessarily a valid JSON chunk. The caller must
            reassemble the chunks to get a sensible result.
            """
        def bounds(self) -> None:
            """Paint bounds of individual components on screen."""
    def page_count(self) -> int:
        """Return the number of pages in the layout object."""
    def button_request(self) -> tuple[int, str] | None:
        """Return (code, type) of button request made during the last event or timer pass."""
    def __del__(self) -> None:
        """Calls drop on contents of the root component."""


# rust/src/ui/model_tt/layout.rs
class UiResult:
   """Result of a UI operation."""
   pass
CONFIRMED: UiResult
CANCELLED: UiResult
INFO: UiResult


# rust/src/ui/model_tt/layout.rs
def disable_animation(disable: bool) -> None:
    """Disable animations, debug builds only."""


# rust/src/ui/model_tt/layout.rs
def check_homescreen_format(data: bytes) -> bool:
    """Check homescreen format and dimensions."""


# rust/src/ui/model_tt/layout.rs
def confirm_action(
    *,
    title: str,
    action: str | None,
    description: str | None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    prompt_screen: bool = False,
    prompt_title: str | None = None,
) -> LayoutObj[UiResult]:
    """Confirm action."""


# rust/src/ui/model_tt/layout.rs
def confirm_emphasized(
    *,
    title: str,
    items: Iterable[str | tuple[bool, str]],
    verb: str | None = None,
) -> LayoutObj[UiResult]:
    """Confirm formatted text that has been pre-split in python. For tuples
    the first component is a bool indicating whether this part is emphasized."""


# rust/src/ui/model_tt/layout.rs
def confirm_homescreen(
    *,
    title: str,
    image: bytes,
) -> LayoutObj[UiResult]:
    """Confirm homescreen."""


# rust/src/ui/model_tt/layout.rs
def confirm_blob(
    *,
    title: str,
    data: str | bytes,
    description: str | None,
    extra: str | None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm byte sequence data."""


# rust/src/ui/model_tt/layout.rs
def confirm_address(
    *,
    title: str,
    data: str | bytes,
    description: str | None,
    verb: str | None = "CONFIRM",
    extra: str | None,
    chunkify: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm address. Similar to `confirm_blob` but has corner info button
    and allows left swipe which does the same thing as the button."""


# rust/src/ui/model_tt/layout.rs
def confirm_properties(
    *,
    title: str,
    items: list[tuple[str | None, str | bytes | None, bool]],
    hold: bool = False,
) -> LayoutObj[UiResult]:
    """Confirm list of key-value pairs. The third component in the tuple should be True if
    the value is to be rendered as binary with monospace font, False otherwise."""


# rust/src/ui/model_tt/layout.rs
def confirm_reset_device(
    *,
    title: str,
    button: str,
) -> LayoutObj[UiResult]:
    """Confirm TOS before device setup."""


# rust/src/ui/model_tt/layout.rs
def show_address_details(
    *,
    qr_title: str,
    address: str,
    case_sensitive: bool,
    details_title: str,
    account: str | None,
    path: str | None,
    xpubs: list[tuple[str, str]],
) -> LayoutObj[UiResult]:
    """Show address details - QR code, account, path, cosigner xpubs."""


# rust/src/ui/model_tt/layout.rs
def show_info_with_cancel(
    *,
    title: str,
    items: Iterable[Tuple[str, str]],
    horizontal: bool = False,
    chunkify: bool = False,
) -> LayoutObj[UiResult]:
    """Show metadata for outgoing transaction."""


# rust/src/ui/model_tt/layout.rs
def confirm_value(
    *,
    title: str,
    value: str,
    description: str | None,
    subtitle: str | None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    info_button: bool = False,
    hold: bool = False,
    chunkify: bool = False,
    text_mono: bool = True,
) -> LayoutObj[UiResult]:
    """Confirm value. Merge of confirm_total and confirm_output."""


# rust/src/ui/model_tt/layout.rs
def confirm_total(
    *,
    title: str,
    items: Iterable[tuple[str, str]],
    info_button: bool = False,
    cancel_arrow: bool = False,
) -> LayoutObj[UiResult]:
    """Transaction summary. Always hold to confirm."""


# rust/src/ui/model_tt/layout.rs
def confirm_modify_output(
    *,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> LayoutObj[UiResult]:
    """Decrease or increase output amount."""


# rust/src/ui/model_tt/layout.rs
def confirm_modify_fee(
    *,
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None,  # ignored
) -> LayoutObj[UiResult]:
    """Decrease or increase transaction fee."""


# rust/src/ui/model_tt/layout.rs
def confirm_fido(
    *,
    title: str,
    app_name: str,
    icon_name: str | None,
    accounts: list[str | None],
) -> LayoutObj[int | UiResult]:
    """FIDO confirmation.
    Returns page index in case of confirmation and CANCELLED otherwise.
    """


# rust/src/ui/model_tt/layout.rs
def show_error(
    *,
    title: str,
    button: str = "CONTINUE",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Error modal. No buttons shown when `button` is empty string."""


# rust/src/ui/model_tt/layout.rs
def show_warning(
    *,
    title: str,
    button: str = "CONTINUE",
    value: str = "",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Warning modal. No buttons shown when `button` is empty string."""


# rust/src/ui/model_tt/layout.rs
def show_success(
    *,
    title: str,
    button: str = "CONTINUE",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Success modal. No buttons shown when `button` is empty string."""


# rust/src/ui/model_tt/layout.rs
def show_info(
    *,
    title: str,
    button: str = "CONTINUE",
    description: str = "",
    allow_cancel: bool = False,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """Info modal. No buttons shown when `button` is empty string."""


# rust/src/ui/model_tt/layout.rs
def show_mismatch(*, title: str) -> LayoutObj[UiResult]:
    """Warning modal, receiving address mismatch."""


# rust/src/ui/model_tt/layout.rs
def show_simple(
    *,
    title: str | None,
    description: str = "",
    button: str = "",
) -> LayoutObj[UiResult]:
    """Simple dialog with text and one button."""


# rust/src/ui/model_tt/layout.rs
def confirm_with_info(
    *,
    title: str,
    button: str,
    info_button: str,
    items: Iterable[tuple[int, str | bytes]],
) -> LayoutObj[UiResult]:
    """Confirm given items but with third button. Always single page
    without scrolling."""


# rust/src/ui/model_tt/layout.rs
def confirm_more(
    *,
    title: str,
    button: str,
    items: Iterable[tuple[int, str | bytes]],
) -> LayoutObj[UiResult]:
    """Confirm long content with the possibility to go back from any page.
    Meant to be used with confirm_with_info."""


# rust/src/ui/model_tt/layout.rs
def confirm_coinjoin(
    *,
    max_rounds: str,
    max_feerate: str,
) -> LayoutObj[UiResult]:
    """Confirm coinjoin authorization."""


# rust/src/ui/model_tt/layout.rs
def request_pin(
    *,
    prompt: str,
    subprompt: str,
    allow_cancel: bool = True,
    wrong_pin: bool = False,
) -> LayoutObj[str | UiResult]:
    """Request pin on device."""


# rust/src/ui/model_tt/layout.rs
def request_passphrase(
    *,
    prompt: str,
    max_len: int,
) -> LayoutObj[str | UiResult]:
    """Passphrase input keyboard."""


# rust/src/ui/model_tt/layout.rs
def request_bip39(
    *,
    prompt: str,
    prefill_word: str,
    can_go_back: bool,
) -> LayoutObj[str]:
    """BIP39 word input keyboard."""


# rust/src/ui/model_tt/layout.rs
def request_slip39(
    *,
    prompt: str,
    prefill_word: str,
    can_go_back: bool,
) -> LayoutObj[str]:
    """SLIP39 word input keyboard."""


# rust/src/ui/model_tt/layout.rs
def select_word(
    *,
    title: str,
    description: str,
    words: Iterable[str],
) -> LayoutObj[int]:
    """Select mnemonic word from three possibilities - seed check after backup. The
   iterable must be of exact size. Returns index in range `0..3`."""


# rust/src/ui/model_tt/layout.rs
def show_share_words(
    *,
    title: str,
    pages: Iterable[str],
) -> LayoutObj[UiResult]:
    """Show mnemonic for backup. Expects the words pre-divided into individual pages."""


# rust/src/ui/model_tt/layout.rs
def request_number(
    *,
    title: str,
    count: int,
    min_count: int,
    max_count: int,
    description: Callable[[int], str] | None = None,
) -> LayoutObj[tuple[UiResult, int]]:
    """Number input with + and - buttons, description, and info button."""


# rust/src/ui/model_tt/layout.rs
def set_brightness(
    *,
    current: int | None = None
) -> LayoutObj[UiResult]:
    """Show the brightness configuration dialog."""


# rust/src/ui/model_tt/layout.rs
def show_checklist(
    *,
    title: str,
    items: Iterable[str],
    active: int,
    button: str,
) -> LayoutObj[UiResult]:
    """Checklist of backup steps. Active index is highlighted, previous items have check
   mark next to them."""


# rust/src/ui/model_tt/layout.rs
def confirm_recovery(
    *,
    title: str,
    description: str,
    button: str,
    recovery_type: RecoveryType,
    info_button: bool = False,
) -> LayoutObj[UiResult]:
    """Device recovery homescreen."""


# rust/src/ui/model_tt/layout.rs
def select_word_count(
    *,
    recovery_type: RecoveryType,
) -> LayoutObj[int | str]:  # TT returns int
    """Select mnemonic word count from (12, 18, 20, 24, 33)."""


# rust/src/ui/model_tt/layout.rs
def show_group_share_success(
    *,
    lines: Iterable[str]
) -> LayoutObj[UiResult]:
    """Shown after successfully finishing a group."""


# rust/src/ui/model_tt/layout.rs
def show_remaining_shares(
    *,
    pages: Iterable[tuple[str, str]],
) -> LayoutObj[UiResult]:
    """Shows SLIP39 state after info button is pressed on `confirm_recovery`."""


# rust/src/ui/model_tt/layout.rs
def show_progress(
    *,
    description: str,
    indeterminate: bool = False,
    title: str | None = None,
) -> LayoutObj[UiResult]:
    """Show progress loader. Please note that the number of lines reserved on screen for
   description is determined at construction time. If you want multiline descriptions
   make sure the initial description has at least that amount of lines."""


# rust/src/ui/model_tt/layout.rs
def show_progress_coinjoin(
    *,
    title: str,
    indeterminate: bool = False,
    time_ms: int = 0,
    skip_first_paint: bool = False,
) -> LayoutObj[UiResult]:
    """Show progress loader for coinjoin. Returns CANCELLED after a specified time when
   time_ms timeout is passed."""


# rust/src/ui/model_tt/layout.rs
def show_homescreen(
    *,
    label: str | None,
    hold: bool,
    notification: str | None,
    notification_level: int = 0,
    skip_first_paint: bool,
) -> LayoutObj[UiResult]:
    """Idle homescreen."""


# rust/src/ui/model_tt/layout.rs
def show_lockscreen(
    *,
    label: str | None,
    bootscreen: bool,
    skip_first_paint: bool,
    coinjoin_authorized: bool = False,
) -> LayoutObj[UiResult]:
    """Homescreen for locked device."""


# rust/src/ui/model_tt/layout.rs
def confirm_firmware_update(
    *,
    description: str,
    fingerprint: str,
) -> LayoutObj[UiResult]:
    """Ask whether to update firmware, optionally show fingerprint. Shared with bootloader."""


# rust/src/ui/model_tt/layout.rs
def show_wait_text(message: str, /) -> LayoutObj[None]:
    """Show single-line text in the middle of the screen."""


# rust/src/ui/model_tt/layout.rs
class BacklightLevels:
    """Backlight levels. Values dynamically update based on user settings."""
    MAX: ClassVar[int]
    NORMAL: ClassVar[int]
    LOW: ClassVar[int]
    DIM: ClassVar[int]
    NONE: ClassVar[int]
