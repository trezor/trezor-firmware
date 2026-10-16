# Power management

This document describes how the power-management module (`core/embed/io/power_manager/`) is composed: the axes along which it varies per board, how a board selects an implementation, and the design rules that keep the pieces separable.

The module is built only for models with a battery — Trezor Safe 7 (`T3W1`, npm1300 + LiFePO4 + wireless) and the `T3T2` devkit (npm2100, primary cell, no charger). Models without one do not enable it.

## 1. Composition axes

The module is organized by *capability*, not by chip. A board's power hardware is described by a small set of independent choices:

| Axis | Interface | Implementations |
| ---- | --------- | --------------- |
| PMIC driver | `<io/pmic.h>` | `pmic/npm1300/` (charger, Li-ion), `pmic/npm2100/` (boost, primary cell) |
| Fuel gauge (state-of-charge estimator) | `fuel_gauge/battery.h` | `fuel_gauge/lifepo4/`, `fuel_gauge/mock/` |
| Wireless charger | `wireless/stwlc38/stwlc38.h` | `wireless/stwlc38/`, or none |
| Charger present | `pmic/pmic_charger.h` | capability flag, derived from the PMIC |

Above them sits a single hardware policy, `managed/`, which implements the public `<io/power_manager.h>` API: the power state machine, charging control, thermal limiting, suspend/hibernate handling, and state recovery from backup RAM. It talks only to the interfaces above and contains no chip-specific code — no PMIC registers, no I2C.

Separating the policy from the PMIC driver is the point of the split. A PMIC is a hardware device, a fuel gauge is an algorithm, a wireless charger is a *different* hardware device, and the policy is orchestration. Grouping any of them under a chip name welds unrelated kinds of thing together and makes the policy look chip-specific when it is not.

The charger is a capability flag rather than a fifth directory, because a PMIC without one — a boost regulator for primary cells, or a bare GPIO power latch — needs the same policy with the charging controller removed, not a policy of its own. This is why there is a single `managed` policy rather than one per chip, or one per battery chemistry.

## 2. Directory layout

```text
power_manager/
  inc/io/                   public headers: power_manager.h, pmic.h
  power_manager_poll.{c,h}  shared poll/event plumbing
  managed/                  hardware policy; never names a chip
    pm_core.{c,h}, pm_core_states.c   pure core: pipeline, state machine, recovery
    power_charging[_none].c   charger leaf, exactly one built per PMIC capability
    power_manager.c           glue: lock, timer, backup RAM, RTC, hardware
  tests/                    host unit test of the pure core (make -C ... tests)
  unix/                     emulator policy
  pmic/                     PMIC drivers behind pmic.h, plus pmic_charger.h
  fuel_gauge/               SoC estimators behind battery.h
  wireless/                 wireless-charger drivers
```

The rule is one *kind* of thing per directory. This mirrors the shape of other `embed/io` modules (`touch/`, `display/`: `inc/` plus one subdirectory per variant, with shared poll code loose at the root), while keeping each group to a single kind.

Only `power_manager.h` and `pmic.h` live in the public `inc/io/`, because they have consumers outside the module — the boardloader includes `<io/pmic.h>` to hold the power rail up before any policy exists. `fuel_gauge/battery.h` and `pmic/pmic_charger.h` are module-internal seams and sit next to their implementations, included by relative path like `power_manager_poll.h`.

The groups stay nested inside `power_manager/` rather than being promoted to `io/` peers: it is all one `io` crate, so promotion would scatter tightly coupled power code across the crate without buying any isolation.

## 3. Board selection and build-time wiring

A board declares its power hardware in the `[power_manager]` section of its board TOML:

```toml
[power_manager]
pmic       = "io/pmic_npm1300"
fuel_gauge = "io/fuel_gauge_lifepo4"
wireless   = "io/wireless_stwlc38"
```

Each value is a crate-qualified Cargo feature; the keys are only labels. The features reach every project whose `uses` list includes `power_manager`.

PMIC and fuel gauge are *required* axes: for each, `build.rs` collects the enabled implementations into a table and requires exactly one, so a missing, mistyped, or duplicated selection is a build error that names the axis instead of a silent fallback or a duplicate-symbol link failure. Each table entry carries its own source list, so a half-wired implementation cannot fall through to another one. Wireless is *optional* — zero or one — so a board that omits the `wireless` key simply leaves `USE_WIRELESS_CHARGER` unset.

The module exposes its configuration to C through these defines:

- `USE_PMIC` — a PMIC driver is present.
- `USE_POWER_MANAGER` — the full policy is present.
- `USE_WIRELESS_CHARGER` — a wireless charger is present. Never set for the emulator, whose driver would need the STM32 HAL.
- `USE_CHARGER` — the selected PMIC has an integrated charger.

Two build shapes exist. The boardloader is *PMIC-only*: it maps `power_manager` to just the PMIC driver, since it must hold the rail up before any policy exists. The bootloader, kernel, firmware, and prodtest take the full policy.

### Board tunables

Numbers that describe the board or its battery pack do not live in the policy. The board header defines them, and the policy (`power_manager_internal.h`, or `power_charging.c` for the charger's own) requires them with an `#error` naming the missing one, so a new board cannot silently inherit another product's battery figures:

| Define | Meaning | Required when |
| ------ | ------- | ------------- |
| `BATTERY_LOW_SOC_PERCENT` | SoC at or below which power-save mode starts | always |
| `PM_POWER_SAVE_BACKLIGHT_LIMIT` | backlight cap in power-save mode | always |
| `PM_SUSPEND_CURRENT_MA`, `PM_HIBERNATION_CURRENT_MA` | board drain in each low-power mode, for fuel-gauge compensation | `USE_RTC` |
| `BATTERY_CHARGING_CURRENT_MAX_MA` | the pack's maximum charging current | charger leaf (`USE_CHARGER`) |
| `BATTERY_CHARGE_TEMP_BANDS` | `{max_temp_C, current factor}` derating bands, ascending | charger leaf (`USE_CHARGER`) |

The line between the two kinds: a constant that would change if the same policy ran on a different board or pack is a tunable; a constant that describes the state machine itself (sampling period, shutdown timeout, stabilization timeout, auto-hibernate timeout, the thermal debounce) stays in the policy. The charger's accepted current range is a property of the chip and lives in its driver (`NPM1300_CHARGING_LIMIT_MIN/MAX`); the pack's maximum is a board tunable, and the driver checks at compile time that the one fits inside the other. The policy learns the chip's minimum through `pmic_charging_limit_min()` so it can reject a requested limit the charger could never honour.

## 4. Core and glue

`managed/` is split in two along the line between *deciding* and *doing*.

**The core** (`pm_core.h`, `pm_core.c`, `pm_core_states.c`, and the charger leaf) is pure: every step is a function of the core's state, an input and a time. `pm_core_sample()` takes a PMIC sample and a millisecond tick and runs the whole per-sample pipeline — power-source detection, brownout, the fuel gauge, the charging controller, the state machine. `pm_core_request()` feeds a suspend / hibernate / turn-on request into the state machine. Both return a `pm_actions_t` describing what must now happen in the world: notify listeners, cap the backlight, set the charger's limit and enable state, enter ship mode, persist the recovery data and power off. The core never calls a timer, a lock, backup RAM, the RTC, telemetry or a driver. Time only ever arrives as an argument, so the shutdown timeout and the thermal debounce are deadlines compared against the tick instead of hardware timers. Elapsed real time for self-discharge compensation arrives the same way, as seconds, in `pm_core_init()` and `pm_core_resume()`.

**The glue** (`power_manager.c`) implements `<io/power_manager.h>` by driving the core with real time and real samples and carrying out the actions. It owns the interrupt lock, the sampling timer, the recovery data's version and RTC timestamp, the auto-hibernate RTC event, telemetry, and the hardware sub-drivers. It also builds the core's `pm_config_t` from the board tunables. Nothing in the glue decides policy; everything in it owns a side effect.

The charger leaf keeps the same discipline with two marked exceptions: `pm_charging_init()` asks the charger driver for its minimum limit once, and `pm_charging_apply()` is the leaf's own glue, the one function that carries the controller's decision to the charger. That keeps `USE_CHARGER` out of `power_manager.c` as before.

What the split buys is `tests/pm_core_test.c`: a host program that links the core against a fake fuel gauge and a fake charger, advances a fake clock, and walks the policy through cold boot, turn-on, the low-battery threshold, brownout with the shutdown timeout, charging with thermal derating and fault clearing, the suspend cycle, recovery and inheritance. The same logic that ships on the device runs there, with no emulator, in well under a second. Run it with `make -C core/embed/io/power_manager/tests`.

The rule: a constant or a decision belongs in the core; a clock, a lock, a bus or a persistent store belongs in the glue. If a change to `managed/` needs a new `#include <sys/...>` or `<io/...>` in a core file, it is going in the wrong half.

## 5. The PMIC report is chip-neutral

`pmic_report_t` is the only data that crosses from a PMIC driver into the policy, so it carries no raw register values. Each driver decodes its own registers into fields that mean the same thing on every chip: measurements (`vbat`, `vsys`, `ibat`, `ntc_temp`, `die_temp`), *what this chip can measure* (`ibat_valid`, `ntc_present`), and decoded status (`vbus_present`, `ntc_disconnected`, `battery_disconnected`, `charge_complete`, `charger_fault`, `cc_phase`, `cv_phase`).

The capability flags are the important part. A boost regulator for primary cells has no current sense and no thermistor; it says so with `ibat_valid = false` and `ntc_present = false` rather than reporting zero current or an "NTC disconnected" fault for a thermistor that was never wired. The policy treats "absent" and "disconnected" differently: only a *present* NTC that reads open is a fault, and only a *valid* current reading drives the charging-limited detector or the idle/discharging distinction. Charger flags are simply false on a chip without a charger.

This is what lets one policy serve every PMIC without knowing which one it has. If a field is tempting to add as a raw register, decode it in the driver instead.

## 6. The charger capability

The charger is the only part of the policy that depends on which PMIC is fitted, so it is isolated as a **leaf**: a pair of alternative sources in `managed/`, of which `build.rs` compiles exactly one on the PMIC's charger capability:

- `power_charging.c` — the real leaf for a charger-capable PMIC (npm1300): the charging controller, the thermal (charging-current) limiter with its board-supplied derating bands, the charging-limited detector, and the leaf's half of the public charging API (the glue validates and locks, the leaf changes the state). It is the only policy file that includes `pmic_charger.h`.
- `power_charging_none.c` — the leaf for a PMIC without a charger (npm2100): every entry point is a no-op or a rejection. Enabling, disabling and the SoC target are accepted and ignored; `pm_charging_set_max_current()` is rejected rather than reported as applied, because it never would be.

The rest of the policy calls the leaf unconditionally through a small internal interface (`pm_charging_init`, `pm_charging_step`, `pm_charging_active`, `pm_charging_update_limited`, the `pm_charging_set_*` requests and `pm_charging_apply`), so **`USE_CHARGER` does not appear in any shared policy source**. It survives only as the build-time selector of the leaf and as the gate for prodtest's charging commands.

Everything else is unconditional. The state machine is complete on every build, including `PM_STATE_CHARGING`: a PMIC without a charger never reports an external power source, so the state is unreachable rather than compiled out. `pm_usb_is_connected()` reports VBUS presence on every board, because external-power detection is a PMIC measurement, not a charger feature. The reported state (`charging_status`, `charging_limited`, `temp_control_active`) is computed by the monitoring tick on every build, so `pm_get_state()` is a pure snapshot with no build-time special cases.

The leaf is a pair of ordinary sources rather than weak default symbols on purpose. A weak no-op is a silent fallback: if the real leaf ever failed to be compiled in, the device would quietly stop charging. With two explicit sources, a mis-wired selection is a duplicate- or missing-symbol link error, the same failure mode the "exactly one" checks in `build.rs` give for the PMIC and fuel-gauge axes.

The rule this encodes: gate a capability by giving its leaf a no-op implementation, never by punching a hole in shared logic. A hole in the state table or a getter that returns a different answer per build is a second behaviour to test; a no-op leaf is not.

Regulator and buck-mode control are deliberately *not* part of this extension. The npm1300's buck-mode control has no cross-chip consumer, so it lives as an npm1300-private detail in `pmic/npm1300/npm1300_defs.h`. Should a policy ever need regulator control, it should get an agnostic interface with generic modes (auto / low-noise / high-efficiency), which apply to switching regulators in general, rather than exposing buck-specific names through `pmic.h`.

## 7. Fuel gauge

`fuel_gauge/battery.h` is the chemistry-neutral seam between the policy and a concrete estimator. The policy speaks only to this header and never reaches into an implementation directory.

The estimator's internal state `P` is opaque to the policy: it is persisted to backup RAM and handed back verbatim, but never interpreted. In the `lifepo4` implementation it is the error covariance of an extended Kalman filter; an estimator without a covariance ignores it.

`fuel_gauge/lifepo4/` is the reference implementation, an EKF estimator for LiFePO4 cells. `fuel_gauge/mock/` reports a permanently full, healthy cell and exists for boards with no gauged battery.

## 8. Battery-critical (brownout)

Brownout protection is a *voltage-domain* concern and is deliberately kept out of the fuel gauge's precision budget, since not every chemistry can support a precise state-of-charge threshold.

The policy keeps only the chemistry-agnostic part: if external power is present, the device is not brownout-critical. Everything else — the set and clear thresholds, and the hysteresis between them — is delegated to the gauge through `bat_eval_critical()`, which knows what its cell and its own precision can actually support.

For LiFePO4, undervoltage sets the condition and snaps the state-of-charge estimate to empty, and recovery is state-of-charge based: the flat discharge curve and large voltage relaxation make raw voltage misleading at rest, so only a genuine charge clears the latch, and the persisted state-of-charge is what prevents a false boot after hibernation. A low-precision primary-cell gauge would instead use voltage hysteresis with a sustained-time debounce, where "recovery" means the dip was a transient load sag rather than a recharge — which needs no state-of-charge precision at all.

The principle: brownout belongs to the voltage domain, where it is robust and gauge-independent; the user-facing battery percentage belongs to the gauge domain, where precision varies by chemistry.

## 9. Emulator

The emulator is exempt from the composition matrix. `unix/` is not a driver but a complete reimplementation of `power_manager.h` on the host: `pm_get_state()` copies out a hand-set emulator state, and `pm_set_emu_battery_state()` — exposed to Python through `trezorio` — injects it. This matches the convention of every other `io/*/unix/`, which mocks its module's *public API* using host facilities rather than simulating the chip over a fake bus. One emulator therefore serves every board variant, because the npm1300, fuel-gauge, and wireless differences all live below `pmic.h` and `battery.h`, and the emulator sits above both.

The tradeoff is that the emulator exercises **none** of the real policy: not the state machine, the fuel gauge, the charging controller, or backup-RAM recovery. Emulator and device tests validate the mock, not that logic. That logic is covered instead by the host test of the pure core (section 4), which needs no emulator. Running the real core *inside* the emulator, over a fake PMIC driven from the debuglink, is the remaining step; the core/glue split makes it a matter of writing a `unix/` glue rather than restructuring the policy.

## 10. Design rules

These are the rules the layout above is meant to enforce. They are worth re-reading before widening any of the interfaces.

- **One kind of thing per directory.** `pmic/*` is only hardware; `managed/` is only orchestration and never mentions a chip; `fuel_gauge/*` and `wireless/*` are their own kinds.
- **Do not abstract from a single implementation.** Buck-mode control stayed npm1300-private because nothing else consumed it, and `battery.h` still carries `P` explicitly instead of an opaque state blob because there is only one real estimator to design that blob against — and because changing it changes the versioned backup-RAM recovery format, which needs an on-device test rather than a blind edit.
- **Decide in the core, do in the glue.** The core takes time as an argument and returns actions; anything that needs a clock, a lock, a bus or a store is glue. The host test is the check.
- **A capability only some hardware has becomes a flag on the existing policy,** not a policy of its own, and the flag gates a no-op leaf, not a hole in shared logic. `USE_CHARGER` is the worked example.
- **Decode in the driver, never in the policy.** `pmic_report_t` carries meanings, not registers, and says what it cannot measure instead of reporting zeros.
- **Brownout decisions belong to the voltage domain; battery percentages belong to the gauge.**
