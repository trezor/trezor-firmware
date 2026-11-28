#!/usr/bin/env python3
"""Regenerate (or check) auto-generated files.

Independent steps run in parallel. The output of a step is shown only when it
fails, or with --verbose. After regenerating, the files that changed are listed.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import queue
import shlex
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


@dataclass
class Step:
    name: str
    gen: list[list[str]]
    # default: every gen command with `--check` appended
    check: list[list[str]] | None = None
    # steps whose outputs are inputs of this one
    after: tuple[str, ...] = ()

    def commands(self, check: bool) -> list[list[str]]:
        if not check:
            return self.gen
        if self.check is not None:
            return self.check
        return [cmd + ["--check"] for cmd in self.gen]


# Ordered by priority: steps on the critical path first.
# Everything importing trezorlib must wait for `protobuf` (trezorlib/messages.py).
STEPS = [
    Step(
        "protobuf",
        [["tools/build_protobuf"], ["rust/trezor-client/scripts/build_protos"]],
    ),
    Step("icons", [[PY, "core/tools/build_icons.py"]]),
    Step("solana_templates", [[PY, "tools/build_solana_templates.py"]]),
    Step(
        "templates",
        gen=[
            [PY, "core/translations/order.py"],
            [PY, "core/translations/cli.py", "gen"],
            ["core/tools/build_templates"],
        ],
        check=[
            [PY, "core/translations/order.py", "--check"],
            [PY, "core/translations/cli.py", "gen", "--check"],
            # fails if the stored merkle root is not up to date
            [PY, "core/translations/cli.py", "merkle-root"],
            ["core/tools/build_templates", "--check"],
        ],
        # qstrdefsport.h.mako lists all of core/src, including generated files
        after=("icons", "protobuf", "solana_templates"),
    ),
    Step(
        "mocks",
        gen=[[PY, "core/tools/build_mocks"]],
        check=[
            [PY, "core/tools/build_mocks", "--check"],
            ["flake8", "core/mocks/generated"],
        ],
        after=("templates",),
    ),
    Step(
        "vendorheader",
        [[PY, "core/tools/generate_vendorheader.py"]],
        after=("protobuf",),
    ),
    Step("bootloader_hashes", [["bootloader_hashes"]], after=("protobuf",)),
    Step("lsgen", [["lsgen"]]),
    Step(
        "tropic_config",
        [
            [PY, "core/tools/generate_tropic_model_config.py"],
            [PY, "core/tools/generate_tropic_config_docs.py"],
        ],
    ),
    Step("hsm_keys", [[PY, "core/tools/generate_hsm_keys.py"]]),
    Step("prodtest_error_codes", [[PY, "core/tools/prodtest_error_codes.py"]]),
    Step("certs", [[PY, "core/tools/generate_certificates.py"]]),
    Step(
        "python_doc",
        [[PY, "python/helper-scripts/make-options-rst.py"]],
        after=("protobuf", "hsm_keys"),
    ),
]

OK, FAILED, SKIPPED = "ok", "failed", "skipped"


def relative(text: str) -> str:
    return text.replace(f"{ROOT}/", "")


@dataclass
class Result:
    status: str
    duration: float = 0.0
    # (command, output) of every command that was run
    outputs: list[tuple[str, str]] = field(default_factory=list)
    # why the step failed or was skipped
    note: str = ""

    def text(self, commands: bool) -> str:
        parts = [f"$ {cmd}\n{out}" if commands else out for cmd, out in self.outputs]
        return relative("".join(parts)).rstrip()


class Runner:
    def __init__(self, check: bool) -> None:
        self.check = check
        self.cancelled = threading.Event()
        self.procs: set[subprocess.Popen[str]] = set()
        self.lock = threading.Lock()

    def run_step(self, step: Step) -> Result:
        start = time.monotonic()
        result = Result(OK)
        for cmd in step.commands(self.check):
            if self.cancelled.is_set():
                result.status = FAILED
                break
            shown = shlex.join("python" if arg == PY else arg for arg in cmd)
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                )
            except OSError as e:
                result.status, result.note = FAILED, f"{shown}: {e.strerror or e}"
                break
            with self.lock:
                self.procs.add(proc)
            output, _ = proc.communicate()
            with self.lock:
                self.procs.discard(proc)
            result.outputs.append((shown, output))
            if proc.returncode != 0:
                result.status = FAILED
                result.note = f"{shown}: exit code {proc.returncode}"
                break
        result.duration = time.monotonic() - start
        return result

    def cancel(self) -> None:
        self.cancelled.set()
        with self.lock:
            for proc in self.procs:
                proc.terminate()


def snapshot() -> dict[str, str] | None:
    """Hash every file that differs from HEAD. None outside of a git checkout."""
    try:
        status = subprocess.run(
            ["git", "status", "-z", "--porcelain", "--untracked-files=all"]
            + ["--ignore-submodules"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode(errors="surrogateescape")
    except (OSError, subprocess.CalledProcessError):
        return None
    files: dict[str, str] = {}
    entries = iter(status.split("\0"))
    for entry in entries:
        if not entry:
            continue
        xy, path = entry[:2], entry[3:]
        if "R" in xy or "C" in xy:
            next(entries, None)  # original path of a rename
        try:
            files[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        except OSError:
            files[path] = xy
    return files


class Reporter:
    SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, total: int, width: int, verbosity: int) -> None:
        self.total = total
        self.width = width
        self.verbosity = verbosity
        self.tty = sys.stdout.isatty()
        color = self.tty and not os.environ.get("NO_COLOR")
        self.marks = {
            OK: "\033[32m✓\033[0m" if color else "✓",
            FAILED: "\033[31m✗\033[0m" if color else "✗",
            SKIPPED: "\033[33m-\033[0m" if color else "-",
        }
        self.frame = 0
        self.status_shown = False

    def clear_status(self) -> None:
        if self.status_shown:
            sys.stdout.write("\r\033[K")
            self.status_shown = False

    def status(self, running: list[str], done: int, elapsed: float) -> None:
        if not self.tty:
            return
        self.clear_status()
        self.frame = (self.frame + 1) % len(self.SPINNER)
        line = (
            f"{self.SPINNER[self.frame]} [{done}/{self.total}] {elapsed:5.1f}s"
            f"  {', '.join(running)}"
        )
        columns = shutil.get_terminal_size().columns
        sys.stdout.write(line[: columns - 1])
        sys.stdout.flush()
        self.status_shown = True

    def step_done(self, name: str, result: Result) -> None:
        self.clear_status()
        line = f"{self.marks[result.status]} {name:<{self.width}}"
        if result.status == SKIPPED:
            line += " " * 8
        else:
            line += f"  {result.duration:5.2f}s"
        if result.note:
            line += f"  {result.note}"
        print(line)
        if self.verbosity and result.status == OK:
            details = result.text(commands=self.verbosity > 1)
            if details:
                print(textwrap.indent(details, "    "))
        sys.stdout.flush()

    def failure(self, name: str, result: Result) -> None:
        print(f"\n{self.marks[FAILED]} {name}")
        # the failing command is the last one shown, its exit code is in the note
        print(result.text(commands=True) if result.outputs else result.note)

    def changed_files(self, changed: list[str]) -> None:
        limit = len(changed) if self.verbosity else 10
        print("Changed files:")
        for path in changed[:limit]:
            print(f"    {path}")
        if len(changed) > limit:
            print(f"    ... and {len(changed) - limit} more (-v shows all)")


def main() -> int:
    names = [step.name for step in STEPS]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "steps",
        nargs="*",
        metavar="STEP",
        help=f"steps to run (default: all): {', '.join(names)}",
    )
    parser.add_argument(
        "-c", "--check", action="store_true", help="check, do not regenerate"
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="number of steps to run in parallel (default: number of CPUs)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="show details from every step, -vv also shows the commands",
    )
    args = parser.parse_args()
    unknown = [name for name in args.steps if name not in names]
    if unknown:
        parser.error(f"unknown steps: {', '.join(unknown)}")

    if not os.environ.get("IN_NIX_SHELL"):
        # e.g. a different clang-format version formats hsm_keys.h differently
        print("Warning: not running in nix-shell, results may differ from CI.")

    selected = [step for step in STEPS if not args.steps or step.name in args.steps]
    selected_names = {step.name for step in selected}
    runner = Runner(args.check)
    reporter = Reporter(
        len(selected), max(len(step.name) for step in selected), args.verbose
    )
    events: queue.Queue[tuple[str, Result]] = queue.Queue()
    pending = list(selected)
    running: list[str] = []
    results: dict[str, Result] = {}
    before = None if args.check else snapshot()
    start = time.monotonic()

    def work(step: Step) -> None:
        events.put((step.name, runner.run_step(step)))

    def finish(name: str, result: Result) -> None:
        results[name] = result
        reporter.step_done(name, result)

    def start_ready() -> None:
        for step in list(pending):
            deps = [d for d in step.after if d in selected_names]
            if any(d not in results for d in deps):
                continue
            failed = [d for d in deps if results[d].status != OK]
            # in check mode nothing is written, so a failed dependency does not matter
            if failed and not args.check:
                pending.remove(step)
                note = f"skipped, {', '.join(failed)} failed"
                finish(step.name, Result(SKIPPED, note=note))
                start_ready()
                return
            if len(running) < args.jobs:
                pending.remove(step)
                running.append(step.name)
                threading.Thread(target=work, args=(step,), daemon=True).start()

    try:
        start_ready()
        while running:
            try:
                name, result = events.get(timeout=0.1)
            except queue.Empty:
                reporter.status(running, len(results), time.monotonic() - start)
                continue
            running.remove(name)
            finish(name, result)
            start_ready()
    except KeyboardInterrupt:
        runner.cancel()
        reporter.clear_status()
        print("Interrupted.")
        return 130

    elapsed = time.monotonic() - start
    failed = [name for name, r in results.items() if r.status == FAILED]
    skipped = [name for name, r in results.items() if r.status == SKIPPED]
    for name in failed:
        reporter.failure(name, results[name])
    if failed:
        print()

    changes = ""
    after = snapshot() if before is not None else None
    if before is not None and after is not None:
        changed = sorted(
            path
            for path in before.keys() | after.keys()
            if before.get(path) != after.get(path)
        )
        if changed:
            reporter.changed_files(changed)
            changes = f"{len(changed)} file{'s' * (len(changed) != 1)} changed"
        else:
            changes = "no files changed"

    if not failed:
        print(
            f"All {len(results)} OK in {elapsed:.1f}s"
            + (f", {changes}." if changes else ".")
        )
        return 0
    print(
        f"{len(failed)} of {len(results)} steps failed in {elapsed:.1f}s: "
        + ", ".join(failed)
        + (f" (skipped: {', '.join(skipped)})" if skipped else "")
        + (f"; {changes}." if changes else ".")
    )
    if args.check:
        print('Run "make gen" to regenerate the files.')
    else:
        print(f"Re-run them with: tools/gen.py {' '.join(failed + skipped)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
