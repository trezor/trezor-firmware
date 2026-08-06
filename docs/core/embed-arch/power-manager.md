# Power management

This document describes how the power-management module (`core/embed/io/power_manager/`) is composed: the axes along which it varies per board, how a board selects an implementation, and the design rules that keep the pieces separable.

The module is built only for models with a battery — currently Trezor Safe 7 (`T3W1`). Models without one do not enable it.

## 1. Composition axes

The module is organized by *capability*, not by chip. A board's power hardware is described by a small set of independent choices:

| Axis | Interface | Implementations |
| ---- | --------- | --------------- |
| PMIC driver | `<io/pmic.h>` | `pmic/npm1300/` |
| Fuel gauge (state-of-charge estimator) | `fuel_gauge/battery.h` | `fuel_gauge/lifepo4/`, `fuel_gauge/mock/` |
| Wireless charger | `wireless/stwlc38/stwlc38.h` | `wireless/stwlc38/`, or none |
| Charger present | `pmic/pmic_charger.h` | capability flag, derived from the PMIC |

Above them sits a single hardware policy, `managed/`, which implements the public `<io/power_manager.h>` API: the power state machine, charging control, thermal limiting, suspend/hibernate handling, and state recovery from backup RAM. It talks only to the interfaces above and contains no chip-specific code — no PMIC registers, no I2C.

Separating the policy from the PMIC driver is the point of the split. A PMIC is a hardware device, a fuel gauge is an algorithm, a wireless charger is a *different* hardware device, and the policy is orchestration. Grouping any of them under a chip name welds unrelated kinds of thing together and makes the policy look chip-specific when it is not.

The charger is a capability flag rather than a fifth directory, because a PMIC without one — a boost regulator for primary cells, or a bare GPIO power latch — needs the same policy with the charging controller removed, not a policy of its own. This is why there is a single `managed` policy rather than one per chip, or one per battery chemistry.

## 2. Directory layout

```
power_manager/
  inc/io/                   public headers: power_manager.h, pmic.h
  power_manager_poll.{c,h}  shared poll/event plumbing
  managed/                  hardware policy (state machine); never names a chip
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

For each selectable axis, `build.rs` collects the enabled implementations into a table and requires exactly one. A missing, mistyped, or duplicated selection is therefore a build error that names the axis, instead of a silent fallback or a duplicate-symbol link failure. Each table entry carries its own source list, so a half-wired implementation cannot fall through to another one.

The module exposes its configuration to C through these defines:

- `USE_PMIC` — a PMIC driver is present.
- `USE_POWER_MANAGER` — the full policy is present.
- `USE_WIRELESS_CHARGER` — a wireless charger is present. Never set for the emulator, whose driver would need the STM32 HAL.
- `USE_CHARGER` — the selected PMIC has an integrated charger.

Two build shapes exist. The boardloader is *PMIC-only*: it maps `power_manager` to just the PMIC driver, since it must hold the rail up before any policy exists. The bootloader, kernel, firmware, and prodtest take the full policy.

## 4. The charger capability

With `USE_CHARGER` off, the policy does not reference the charger extension at all: `pmic_charger.h` is not included, its charging-current bounds are not defined, the charging controller compiles to a no-op, the thermal controller compiles out entirely (it exists only to limit *charging* current by temperature), and `pm_charging_set_max_current()` rejects the request rather than reporting success for a limit that would never be applied. The rest of the public charging API still exists and does nothing. A chargerless PMIC therefore simply does not implement the extension, and nothing in `managed/` looks for it.

Regulator and buck-mode control are deliberately *not* part of this extension. The npm1300's buck-mode control has no cross-chip consumer, so it lives as an npm1300-private detail in `pmic/npm1300/npm1300_defs.h`. Should a policy ever need regulator control, it should get an agnostic interface with generic modes (auto / low-noise / high-efficiency), which apply to switching regulators in general, rather than exposing buck-specific names through `pmic.h`.

## 5. Fuel gauge

`fuel_gauge/battery.h` is the chemistry-neutral seam between the policy and a concrete estimator. The policy speaks only to this header and never reaches into an implementation directory.

The estimator's internal state `P` is opaque to the policy: it is persisted to backup RAM and handed back verbatim, but never interpreted. In the `lifepo4` implementation it is the error covariance of an extended Kalman filter; an estimator without a covariance ignores it.

`fuel_gauge/lifepo4/` is the reference implementation, an EKF estimator for LiFePO4 cells. `fuel_gauge/mock/` reports a permanently full, healthy cell and exists for boards with no gauged battery.

## 6. Battery-critical (brownout)

Brownout protection is a *voltage-domain* concern and is deliberately kept out of the fuel gauge's precision budget, since not every chemistry can support a precise state-of-charge threshold.

The policy keeps only the chemistry-agnostic part: if external power is present, the device is not brownout-critical. Everything else — the set and clear thresholds, and the hysteresis between them — is delegated to the gauge through `bat_eval_critical()`, which knows what its cell and its own precision can actually support.

For LiFePO4, undervoltage sets the condition and snaps the state-of-charge estimate to empty, and recovery is state-of-charge based: the flat discharge curve and large voltage relaxation make raw voltage misleading at rest, so only a genuine charge clears the latch, and the persisted state-of-charge is what prevents a false boot after hibernation. A low-precision primary-cell gauge would instead use voltage hysteresis with a sustained-time debounce, where "recovery" means the dip was a transient load sag rather than a recharge — which needs no state-of-charge precision at all.

The principle: brownout belongs to the voltage domain, where it is robust and gauge-independent; the user-facing battery percentage belongs to the gauge domain, where precision varies by chemistry.

## 7. Emulator

The emulator is exempt from the composition matrix. `unix/` is not a driver but a complete reimplementation of `power_manager.h` on the host: `pm_get_state()` copies out a hand-set emulator state, and `pm_set_emu_battery_state()` — exposed to Python through `trezorio` — injects it. This matches the convention of every other `io/*/unix/`, which mocks its module's *public API* using host facilities rather than simulating the chip over a fake bus. One emulator therefore serves every board variant, because the npm1300, fuel-gauge, and wireless differences all live below `pmic.h` and `battery.h`, and the emulator sits above both.

The tradeoff is that the emulator exercises **none** of the real policy: not the state machine, the fuel gauge, the charging controller, or backup-RAM recovery. Emulator and device tests validate the mock, not that logic. Covering it is a job for a native host unit test that links the real `managed/` and `fuel_gauge/` code (largely pure math) against a fake `pmic.h`; the host stubs such a test needs already exist in `sys/time/unix` and `sec/backup_ram/unix`.

## 8. Design rules

These are the rules the layout above is meant to enforce. They are worth re-reading before widening any of the interfaces.

- **One kind of thing per directory.** `pmic/*` is only hardware; `managed/` is only orchestration and never mentions a chip; `fuel_gauge/*` and `wireless/*` are their own kinds.
- **Do not abstract from a single implementation.** Buck-mode control stayed npm1300-private because nothing else consumed it, and `battery.h` still carries `P` explicitly instead of an opaque state blob because there is only one real estimator to design that blob against — and because changing it changes the versioned backup-RAM recovery format, which needs an on-device test rather than a blind edit.
- **A capability only some hardware has becomes a flag on the existing policy,** not a policy of its own. `USE_CHARGER` is the worked example.
- **Brownout decisions belong to the voltage domain; battery percentages belong to the gauge.**
