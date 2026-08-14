# power_manager — organization & planned refactor

Status (2026-07-27): **build.rs hardening + directory reorg + backend-feature
collapse + fuel-gauge axis done**; the remaining `pmic.h`/`battery.h` *content*
narrowings (report-struct split, `battery.h` de-EKF) are still deferred to the
primary-cell gauge (see "Interface narrowings" below).

The per-backend Cargo features (`power_manager_npm1300` /
`power_manager_power_latch`) are gone: a board selects only a PMIC
(`pmic = "io/pmic_..."`) and the project opts into `power_manager`; the single
`managed` policy builds on top of whichever PMIC was chosen, deriving
`USE_CHARGER` from the PMIC's capability.

The fuel gauge is now its own selectable axis, mirroring the PMIC axis: the
board picks an implementation via `fuel_gauge = "io/fuel_gauge_..."` and build.rs
selects the sources with an "exactly one" guard. The interface header lives at
the chemistry-neutral `fuel_gauge/battery.h`; the `managed` policy speaks only to it
and never reaches into an implementation directory. Implementations:
`fuel_gauge/lifepo4/` (EKF, LiFePO4) and `fuel_gauge/mock/` (trivial "always
full/healthy" stub for ungauged boards, e.g. the T3T2 latch board). The mock is
the first alternative implementation validating the interface seam. Note this is
only the *physical* hoist: the header content is still EKF-shaped (`P` carried
as opaque estimator state), the de-EKF is co-designed with the primary-cell
gauge — see #2 below.

## Problem

The folder follows the shape of other `embed/io` modules (`touch/`, `display/`:
`inc/` + one subdir per variant + shared poll loose at the root) but breaks
their rule. Those modules hold **one kind of thing** (one device family, with
interchangeable variants). `power_manager/` crams in **four different kinds**:

| What                                   | Kind                | Lives in today            |
| -------------------------------------- | ------------------- | ------------------------- |
| PMIC drivers (npm1300, latch)          | hardware device     | `npm1300/`, `power_latch/`|
| Wireless charger (stwlc38)             | a *different* device| `stwlc38/`                |
| Fuel gauge / battery model             | an *algorithm*      | `battery/`                |
| Power-manager policy (state machine …) | orchestration       | **also** `npm1300/`       |

The load-bearing issue is the last row: `npm1300/` contains both the npm1300
**hardware driver** (`npm1300.c`) and the **chip-agnostic policy**
(`power_manager.c`, `power_states.c`, `power_monitoring.c`). Those state-machine
files touch zero npm1300 registers / I2C — they speak only to the `pmic_*`,
`bat_*`, `stwlc38_*` interfaces. The policy is already portable; it is just
mis-filed under a chip name.

## Principle: split by capability, not by chip

Three independently pluggable interfaces + one capability flag:

- **PMIC driver** (HW behind `pmic.h`): `npm1300`, `npm2100` (planned; replaces
  the latch for non-rechargeable), `power_latch` (transitional — delete once
  npm2100 lands).
- **Fuel gauge** (algorithm behind `battery.h`): `lifepo4` (current EKF),
  `primary` (planned; our own primary-cell estimator, distinct from the LiFePO
  one).
- **Wireless** (HW): `stwlc38` / none.
- **Charger**: a capability flag (`USE_CHARGER`), derived from the PMIC, gating
  the charging controller. npm1300 = on, npm2100 = off.

Consequence: **one `managed` policy core** serves both npm1300 (charger on) and
npm2100 (charger off). The dividing line is not "rechargeable vs
non-rechargeable = two policies" — once npm2100 (a real measuring PMIC, unlike
the dumb GPIO latch) is in scope, the difference collapses to the single
`USE_CHARGER` flag. The latch keeps its tiny `simple` policy only until npm2100
replaces it.

## Target layout

```
power_manager/
  inc/io/  power_manager.h  pmic.h                   # PUBLIC seams (have external consumers)
  power_manager_poll.{c,h}                           # shared internal, loose at root (cf. touch_poll.c)
  managed/                                           # the hardware policy (state machine); never names a chip
  unix/                                              # emulator policy (mocks the managed core)
  pmic/     pmic_charger.h  npm1300/  npm2100/  power_latch/  # HW behind pmic.h + internal charger ext
  fuel_gauge/  battery.h  lifepo4/  primary/         # pure algorithm behind internal battery.h
  wireless/  stwlc38/
```

`managed/` and `unix/` are the two policy implementations (hardware vs
emulator), mutually exclusive at build time. There is only one hardware policy,
so they sit as sibling directories rather than under a `policy/` wrapper (which
would nest a single child).

Only `power_manager.h` and `pmic.h` live in the public `inc/io/` — they have
consumers outside the module (e.g. `boardloader` includes `<io/pmic.h>`). The
`battery.h` and `pmic_charger.h` seams are module-internal (no external
consumers) and sit next to their implementations, included via relative path
like `power_manager_poll.h`.

Rule of thumb, self-documenting: `pmic/*` is only hardware, `managed/` is only
orchestration and never mentions a chip, `fuel_gauge/*`/`wireless/*` are their
own kinds. Kept nested inside `power_manager/` rather than promoted to `io/`
peers — it is all one `io` crate, so promotion would only scatter tightly
coupled power code.

## Interface narrowings (pre-work)

1. **Trim `pmic.h`** into a core (init/deinit/suspend/resume/enter_shipmode/
   measure + report struct) vs a charger extension. npm2100 is a *boost* PMIC
   with no charger, so the charging surface is provably npm1300-specific.
   **DONE (2026-07-24):** charger surface moved to `pmic/pmic_charger.h`
   (limits + the 4 charger fns `pmic_set_charging` / `pmic_set_charging_limit` /
   `pmic_get_charging_limit` / `pmic_clear_charger_errors`); implemented only by
   npm1300; the latch driver dropped its no-op stubs. Callers: `managed`'s
   `power_manager_internal.h` + `power_monitoring.c`.

   **Buck/regulator control is NOT part of the charger extension.** It was
   conflated at first, but `pmic_set_buck_mode` had **zero** callers and the
   `pmic_buck_mode_t` type was used only inside npm1300.c — i.e. it was dead
   public API, not a cross-chip interface. Demoted to npm1300-private: renamed
   `npm1300_buck_mode_t` / `NPM1300_BUCK_MODE_*` / `npm1300_set_buck_mode` and
   moved into `pmic/npm1300/npm1300_defs.h`. If a policy ever needs to control
   regulator mode, promote it to an agnostic `<io/pmic_regulator.h>` with
   generic modes (AUTO / LOW_NOISE / HIGH_EFFICIENCY) rather than exposing
   buck-specific names — the PWM/PFM/AUTO modes are generic to switching
   regulators (buck *and* boost).

   The report **struct** was left whole (charger-only fields documented inline,
   populated only by charger-capable PMICs) — a physical struct split churns
   every consumer for little gain, so it is deferred. The charger extension will
   compile behind `USE_CHARGER` once npm2100 (managed policy, charger off)
   lands; today the policy/driver pairing already enforces it (only npm1300
   links the charger surface, only the `managed`+npm1300 build calls it).

2. **De-EKF-ify `battery.h`.** `fuel_gauge_state_t.P` (error covariance) and
   `pm_recovery_data_t.P` are Kalman-specific; replace with an opaque
   estimator-state blob so the primary-cell gauge can persist its own internals
   to backup RAM. Move `R`/`Q`/`P_init` tuning inside the `lifepo4` impl. Keep
   the chemistry OCV-curve helpers (`bat_meas_to_ocv`, `bat_soc_to_ocv`) out of
   the gauge-agnostic core — they are used mainly by the `soc_target` precharge
   controller in `power_monitoring.c`, which is charger logic that compiles out
   for npm2100 anyway.

   **Physical hoist + selectable axis: DONE (2026-07-27).** The interface header
   moved to the module-internal `fuel_gauge/battery.h` (included via relative
   path like the module's other internal header `power_manager_poll.h`, NOT via
   the public `inc/io/` - it has no external consumers, unlike `pmic.h`);
   `fuel_gauge` is now a build axis with a
   `mock` impl as the validating second implementation (see status header). The
   `P`-as-opaque-state contract is documented in `battery.h` and the mock simply
   ignores it — **no backup-RAM format change was made.**

   **The de-EKF content change itself is still DEFERRED to step 3** (decided
   2026-07-24). Rationale: (a) the opaque-state interface cannot be designed
   honestly from a single real estimator — it must be validated against the
   primary-cell gauge (the "don't abstract without a second implementation" rule
   from the buck demote above; the trivial mock does not exercise persisted
   estimator state, so it does not validate the blob layout); (b) it changes the
   versioned `pm_recovery_data_t` format, which needs a compile **and** an
   on-device test, not a blind edit. So the `P` → opaque-blob change is
   co-designed with the primary-cell gauge in step 3, where two real estimators
   validate it.

## Battery-critical (brownout) is voltage-domain and chemistry-dispatched

**DONE (2026-07-24).** Brownout protection must not depend on fuel-gauge
precision the chemistry can't deliver. The old inline logic in
`power_monitoring.c` cleared `battery_critical` on `soc_latched >= 2%` - a
threshold only the precise Li-ion EKF can honor; a low-precision primary-cell
gauge (npm2100) has no such resolution, and a primary cell never "recovers" by
recharging anyway.

Restructured so the decision lives in the chemistry-specific gauge behind
`bat_eval_critical(currently_critical, vbat, ibat, temp)` (battery.h). The
`managed` policy keeps only the chemistry-agnostic external-power override (USB
present ⇒ not brownout-critical) and otherwise delegates. Thresholds moved out
of `power_manager_internal.h` into the gauge.

- **LiFePO4** (current impl): unchanged behavior - undervoltage sets it and
  snaps SoC to empty; recovery is SOC-based, because the flat curve + large
  voltage relaxation make raw voltage misleading at rest, and the persisted SoC
  guards boot across hibernation.
- **Primary cells** (step 3): voltage hysteresis + sustained-time debounce,
  ideally on load-compensated voltage (`V_oc ≈ vbat + I·R`), anchored to the
  npm2100 boost dropout; or offloaded to the PMIC's hardware UVLO comparator.
  "Recovery" there means the dip was a transient load sag, not a recharge - no
  SoC precision required. The fuel gauge then only produces a coarse UI "%".

Principle: **safety/brownout = voltage domain (robust, gauge-independent);
user-facing fuel-% = gauge domain (precision varies).** Note this seam does not
yet change the latch experiment, which runs the LiFePO4 gauge - the voltage-
based path arrives with the primary-cell gauge.

## Emulator (`unix/`)

The emulator is exempt from the `pmic × fuel_gauge × charger` matrix. It is not
a driver: it is a complete top-level reimplementation of `power_manager.h` that
never touches `pmic.h`, the state machine, or the fuel gauge. `pm_get_state`
copies out a hand-set `emu_battery_state_t`; the Python test hook
`pm_set_emu_battery_state` injects a `pm_state_t` directly.

This matches the repo-wide convention: every `io/*/unix/` mocks its module's
*public API* via host facilities (`touch/unix` → SDL mouse → `touch.h`, etc.),
never the chip over a fake bus. So `unix/` is simply a third `pm_policy`
variant, peer to `managed/`/`simple/`, selected by `TREZOR_EMULATOR` and pulling
in no pmic/gauge/wireless leaves. One emulator serves all board variants because
it mocks the API, not the hardware — the npm1300/npm2100/latch differences all
live below `pmic.h`/`battery.h`, and the emulator sits above both.

Tradeoff to be aware of: the emulator therefore exercises **none** of the real
policy (state machine, fuel gauge, charging controller, jump detection,
backup-RAM recovery). Emulator/device tests validate the mock, not that logic.
For coverage of that logic — especially the new primary-cell gauge — use a
**native host unit test** linking the real `managed` core / `fuel_gauge/*`
(pure math) against a fake `pmic.h`. The host stubs this needs already exist
(`sys/time/unix`: rtc/systick/systimer; `sec/backup_ram/unix`), so running the
real core on the host is feasible without turning `unix/power_manager.c` into a
PMIC simulator.

Optional: gate the emulator's reported capabilities by `USE_CHARGER` so an
npm2100/latch-model emulator reports "no charging" like the real hardware,
instead of always presenting a charging-capable battery.

## build.rs

Replace the hand-written `else if cfg!(...)` backend ladder and the independent
`if cfg!(...)` PMIC blocks with a table + a "select exactly one" check, so a
mis-mapped or duplicate cfg becomes a clear build error instead of a silent
`bail_unsupported!()` fall-through (the T3T2 break at `build.rs:83`) or a
duplicate-symbol linker error.

## Sequencing

1. **build.rs table + validation** — unblocks the T3T2 build. **DONE.**
2. **Reorg** to the target layout + **`pmic.h`** trim (charger extension + buck
   demote). **DONE** (2a + 2b above). Low-risk: file moves, header split,
   include-path fixes, no behavior change. Still needs a nix build to confirm
   end-to-end (sandbox lacks the toolchain).
   - The **`battery.h` de-EKF + hoist** (narrowing #2) was pulled OUT of step 2
     and into step 3 — see that item's rationale. It is not a mechanical move;
     it needs the real second estimator to validate the interface and touches
     persisted backup-RAM format.
3. **npm2100 driver + primary-cell gauge** slot in as leaves — *and* co-design
   the `battery.h` de-EKF/hoist here, validated against both the `lifepo4` and
   `primary` estimators. Add `USE_CHARGER` (managed policy, charger off for
   npm2100). This is where the fuel-gauge interface becomes genuinely
   chemistry-neutral.

Step 2 was done *before* npm2100 / the custom gauge land — the cheapest the
structural move will ever be. The fuel-gauge interface work waits for step 3 on
purpose: abstracting it from one implementation would be a guess.
