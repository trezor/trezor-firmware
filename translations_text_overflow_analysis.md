# Translated text overflow — analysis and remediation plan

Audit of all four Rust UI layouts (`layout_bolt`, `layout_caesar`, `layout_delizia`,
`layout_eckhart`) plus the shared `ui/component` layer for places where translated
(or otherwise externally supplied) strings can overflow their bounds **without
detection**.

## Background — existing mitigations

- `TextLayout::render_text(text, target, must_fit)` in
  `core/embed/rust/src/ui/component/text/layout.rs` raises an overflow exception in
  `ui_debug` builds when `must_fit=true` and the text does not fit.
- `TextLayout::fit_text()` returns `LayoutFit` which callers can check.
- Paginating components (`Paragraphs`, `FormattedText`, eckhart `TextScreen`, ...)
  adapt page count to the content.
- `Marquee` scrolls text that does not fit (used by caesar `Title`, eckhart button
  subtexts).
- Per-layout string overrides in `core/translations/*.json` shorten strings for a
  given layout as a last resort.

## Cross-cutting gaps (affect all layouts)

### G1. The `must_fit` safety net is a no-op outside eckhart

`core/embed/rust/src/ui/layout/obj.rs:143-160` (`RootComponent::paint`): the overflow
flag set by `raise_overflow_exception()` is computed but **never raised** — line 158
has `// TODO: raise here, so we also test older layouts`. Only
`core/embed/rust/src/ui/flow/swipe.rs:301-323` (`SwipeFlow::paint`, used by eckhart
flows) actually converts it to `Error::OutOfRange`.

**Impact:** every `Label` (which always renders with `must_fit=true`,
`component/label.rs:110,136`) is effectively unchecked on bolt/delizia/caesar, even
in ui_debug device tests.

**Fix:** implement the TODO — raise in `RootComponent::paint`.

### G2. `shape::Text` has zero overflow awareness

`core/embed/rust/src/ui/shape/text.rs`: no bounds parameter, no clipping of its own
(line 91 has `// TODO: optimize text clipping`), no reporting. ~70+ direct call sites
across the layouts render with zero detection. The only net is pixel clipping at the
viewport edge — silent.

**Fix:** add a checked variant (`shape::Text::with_max_width(w)` or a
`checked_text()` helper) that calls `target.raise_overflow_exception()` under
`ui_debug` when `font.text_width(text) > max_width`. Where multi-line rendering is
acceptable, prefer replacing raw `shape::Text` with a `Label` (gets `must_fit=true`
and wraps automatically).

### G3. `Paragraphs::render` hardcodes `must_fit=false`; unpaginated use is silent

`component/text/paragraphs.rs:238`; `Checklist` is explicitly `SinglePage`
(`paragraphs.rs:752`). `FormattedText::render` (`text/formatted.rs:150-152`) has no
must_fit plumbing at all. When a host places such content and never paginates, only
page 1 renders; the rest is dropped with just `...`.

**Fix:** for components that are single-page by design, assert in `place()` under
`ui_debug` that `pager().total() == 1`; convert hosts to real pagination
(`SwipePage::vertical` + `.with_vertical_pages()` on delizia, `ButtonPage` on
bolt/caesar) where pagination is acceptable.

### G4. Production firmware has no runtime signal

Detection is entirely `#[cfg(feature = "ui_debug")]`-gated — by design, but it means
safety equals debug-build test coverage of every screen in every language.

---

## layout_caesar findings

| # | Site | Issue | Suggested fix |
|---|------|-------|---------------|
| C1 | `component/button.rs:204-214` (width logic 92-150) | All `TR::buttons__*` verbs drawn as raw `shape::Text`; `split_left/right` clamp the area but text overruns the clamped button; fixed-width buttons can get negative offset_x | Width check in `Button::place`/render, raise in ui_debug; ellipsis fallback |
| C2 | `component/loader.rs:196-204`, `hold_to_confirm.rs:41-45` | Hold-to-confirm loader text: `split_right` clamps, `horz_center` goes negative, text spills past both edges | Fit check in `HoldToConfirm::place`/`Loader::render_loader`, raise in ui_debug |
| C3 | `component/homescreen.rs:101-123` | Notification bar text (incl. arbitrary `TString` from Python); the only width check decides icon visibility, not text fit | Measure vs screen; marquee (like `Title`) or assert in ui_debug |
| C4 | `component/share_words.rs:62-73` | Final page sentence (`share_words__wrote_down_all` + `words_in_order`) via `text_multiline` (must_fit=false); returned `LayoutFit` discarded — silent mid-sentence cut on a security-critical page | Check `LayoutFit`, raise in ui_debug; or `CutAndInsertEllipsisBoth` |
| C5 | `component/coinjoin_progress.rs:74-121` | `text_multiline`/`_bottom` with must_fit=false; on OutOfBounds renders anyway | Propagate/handle `LayoutFit::OutOfBounds` |
| C6 | `component/result.rs:55-90` | `message_bottom` height unbounded — Label bounds can extend below screen, so even must_fit cannot catch it | Clamp to screen bottom + explicit check |
| C7 | `bootloader/mod.rs:339`, `prodtest/mod.rs:48` | `vendor_str` (from firmware vendor header) and prodtest text — data-driven, unchecked | `debug_assert!(font.text_width(t) <= screen().width())` / checked helper |
| C8 | `component/input_methods/choice_item.rs:168,219-234` | Row buffer `unwrap!(rows.push)` panics on >3 rows; 3 tall rows can paint over the button strip | Bound height, raise in ui_debug; ellipsis on last row |
| C9 (B-class) | `component/error.rs`, `bl_confirm.rs`, `ConfirmHomescreen`, `progress.rs`, homescreen labels | `Label`-based: detected once G1 is fixed; production still clips | Covered by G1 |

## layout_bolt findings

| # | Site | Issue | Suggested fix |
|---|------|-------|---------------|
| B1 | `component/homescreen.rs:200-217` | Device label (user-defined, up to 32 chars) raw `shape::Text`, no check | Width check vs screen; marquee/truncate; ui_debug assert |
| B2 | `component/homescreen.rs:238-258` | Notification banner text wider than banner → overdraws icon, spills both sides | Measure first; marquee or assert |
| B3 | `component/homescreen.rs:99-106` | **Dead code:** `render_loader` builds the "locking device" shape but never calls `.render(target)`. Per decision: NOT touched | — |
| B4 | `component/homescreen.rs:363-393` | Lockscreen text stack (translated lock/tap strings + device label) centered, negative x possible | Width check + marquee/truncate |
| B5 | `component/keyboard/mnemonic.rs:122-127` | Prompt area is `Rect::snap`ped to the text's own `max_size()` — must_fit passes vacuously, text clipped at screen edge | Clamp area to screen before `place()` |
| B6 | `component/progress.rs:49-86` | Height derived from `\n` count only (wrapping ignored); runtime `update` doesn't re-place | Compute height with `fit_text`; re-place on update; assert in ui_debug |
| B7 | `ui_firmware.rs` Dialog flows (426-442, 496-534, 549-583, 735-768, 1207-1232), `dialog.rs:170-188` IconDialog, `show_checklist`, `number_input.rs`, `fido.rs:142-186`, `address_details.rs` | Non-paginated `Paragraphs`, must_fit=false → silent cut, pages unreachable | ui_debug assert `pager().total() == 1` in `place()`, or paginate |
| B8 | `bootloader/mod.rs:396-399`, `prodtest/mod.rs:47` | `vendor_str`, host-provided prodtest text — unchecked | Width assert helper |
| B9 | `component/button.rs:406` | `cancel_confirm_text` picks small button by `verb.len() <= 4` — byte length of a translated verb is a weak proxy for pixel width | Use `font.text_width` for the decision |

## layout_delizia findings

| # | Site | Issue | Suggested fix |
|---|------|-------|---------------|
| D1 | `component/button.rs:219-235` | `ButtonContent::Text` renders raw `shape::Text` with **no check at all**; `IconText` unsplittable case renders over-wide text unchecked (`ui/util.rs:56-57` leaves it to the caller) | Width check + raise in ui_debug; extend `split_two_lines` debug check to the no-break-point case |
| D2 | `component/footer.rs:276-323` | Footer instruction + description (`TR::instructions__*`, caller verbs) centered raw `shape::Text`, no check | Width check in ui_debug; `long_line_content_with_ellipsis` fallback |
| D3 | `component/homescreen.rs:98-128` | Banner grows to text width → banner+text overflow screen for wide translations | Clamp banner to screen; assert fit |
| D4 | `component/homescreen.rs:130-152, 964-972` | Instruction / "not connected" lines unchecked | Width check + assert |
| D5 | `component/homescreen.rs:573-578` | Same dead `render_loader` bug as bolt (missing `.render`). Per decision: NOT touched | — |
| D6 | ~15 unpaginated `Paragraphs` screens: `updatable_more_info.rs`, `fido.rs` (negative vertical_space hack), `number_input.rs`, `Checklist`, `show_error/info/mismatch/warning/simple/group_share_success`, flows `confirm_reset`, `prompt_backup`, `show_tutorial`, `continue_recovery_homepage`, `confirm_set_new_code`, `confirm_firmware_update`, `show_danger`, `confirm_fido`, `receive` | Content in plain `SwipeContent` without `SwipePage::vertical` + `.with_vertical_pages()` → pager reports >1 page but nothing can reach it; silent cut with `...` | Wrap in `SwipePage::vertical` + `.with_vertical_pages()` where pagination is acceptable; single-page fit assert where not |
| D7 | `component/progress.rs:43-61` | Same `\n`-count height bug as bolt | `fit_text`-based height |
| D8 | `bootloader/mod.rs:429-471` | `vendor_str` unchecked | Width check |

## layout_eckhart findings

| # | Site | Issue | Suggested fix |
|---|------|-------|---------------|
| E1 | `firmware/share_words.rs:310-318` | Share word in `FONT_SATOSHI_EXTRALIGHT_72` centered in fixed 332 px area, raw `shape::Text`, no width check, **no pagination by design** | Compare `font.text_width(w)` vs area width, raise in ui_debug; optionally smaller font |
| E2 | `component/button.rs:534-538` via `flow/confirm_fido.rs:111` | `single_line` menu item renders **host-supplied FIDO account names** unchecked (skips the `split_two_lines` fatal guard) | Width check + raise in ui_debug, or Marquee |
| E3 | `firmware/homescreen/header.rs:54-119` | Device-name label area sized from its own text (`Rect::snap`), never clamped → must_fit vacuous, long names run off-screen with the shadow | Clamp to remaining width; marquee/truncate/assert |
| E4 | `component/button.rs:674-684` | `HomeBar` text (`TR::lockscreen__unlock`, notifications) raw `shape::Text`, no check | Width check + raise |
| E5 | `firmware/hold_to_confirm.rs:236-240` | Header overlay `TR::instructions__continue_holding` raw `shape::Text`, no check | Width check vs `SCREEN.width() - PADDING`, raise |
| E6 | `component/button.rs:573-580` | Single-line `TextAndSubtext` main text unchecked (subtext has Marquee, main does not) | Same as E2 |
| E7 | `firmware/fido.rs:84` | `FidoCredential` is `SinglePage`; host app/account names clipped with `...` but unreachable | Propagate inner pager, or assert fit in ui_debug |
| E8 | `firmware/regulatory_screen.rs:296-311, 361-380` | Non-fitting text silently **not rendered at all**; icons drawn regardless of remaining space | Raise in the `_` branch (ui_debug); check icon space |
| E9 | `firmware/value_input_screen.rs:299-312` | Plural unit label (`TR::plurals__*`) unchecked | debug_assert width |

---

## Implementation plan

### Phase 1 — systemic infrastructure
1. `obj.rs`: implement the overflow-raise TODO in `RootComponent::paint` (mirror
   `SwipeFlow::paint`).
2. Checked single-line text helper in `shape/text.rs` (`with_max_width`) calling
   `raise_overflow_exception()` under `ui_debug`.
3. Single-page fit assertion helper for `Paragraphs`-based hosts (ui_debug
   `pager().total() == 1` check after `place()`).

### Phase 2 — per-layout application
- **eckhart:** E1-E9 as tabled; share_words is detection-only by design.
- **delizia:** D1-D4, D6-D8; paginate where sensible, assert where single-page by
  design.
- **bolt:** B1-B2, B4-B9 as tabled.
- **caesar:** C1-C8 as tabled.
- Where multi-line rendering is acceptable, prefer replacing raw `shape::Text` with
  a `Label` (auto-wrap + `must_fit=true`).
- Explicitly **not** touching the dead `render_loader` on bolt/delizia (B3/D5).

### Phase 3 — verification & fallout
1. Build test emulators (`-p test`) for all 4 models; run device/UI tests. The
   obj.rs raise will surface latent overflows — fix them (component adjustments
   first, lang-json shortening only as last resort).
2. `make -C core test_rust` + clippy; `make style_check` / typecheck.
3. Re-record affected UI fixtures with single-test `--ui=record` (never with
   `--ui-check-missing`).
4. Changelog entries per component where user-visible behavior changes.

### Risks
- obj.rs fallout is the big unknown: existing translations may already overflow
  Labels on bolt/delizia/caesar in ways tests never caught.
- Pagination conversions change swipe behavior → UI fixture updates and possibly
  flow-test adjustments.
