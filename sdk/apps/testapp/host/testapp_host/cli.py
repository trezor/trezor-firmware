"""Command-line frontend: one subcommand per layout, every parameter a flag.

Only argument parsing lives here; the work is done by the library.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from trezorlib import exceptions, protobuf

from . import messages as m
from .client import (
    ARTIFACTS,
    SHOWCASES,
    TestApp,
    address,
    amount,
    connect,
    data,
    extras,
    note,
    text,
    warning,
)

KINDS = {kind.name.lower(): kind for kind in m.FieldKind}

# Every field kind that takes a label, by the helper that builds it. A note and a
# warning are sentences, so they take no label and are handled apart.
LABELLED = {
    m.FieldKind.Text: text,
    m.FieldKind.Amount: amount,
    m.FieldKind.Address: address,
}


def parsed_field(spec: str) -> m.Field:
    """One fact as `KIND:LABEL=VALUE`, or `KIND:VALUE` for a note or warning."""
    kind_name, sep, rest = spec.partition(":")
    kind = KINDS.get(kind_name.lower())
    if not sep or kind is None:
        raise argparse.ArgumentTypeError(
            f"expected KIND:..., KIND one of {', '.join(KINDS)}; got {spec!r}"
        )
    if kind is m.FieldKind.Note:
        return note(rest)
    if kind is m.FieldKind.Warning:
        return warning(rest)
    label, sep, value = rest.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"expected KIND:LABEL=VALUE, got {spec!r}")
    if kind is m.FieldKind.Data:
        try:
            return data(label, bytes.fromhex(value))
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected hex bytes, got {value!r}")
    return LABELLED[kind](label, value)


def parsed_extras(args: argparse.Namespace) -> list[m.Extra]:
    items = []
    for label, *specs in args.extra or []:
        items.append((label, [parsed_field(spec) for spec in specs]))
    return extras(*items)


# Each subcommand turns its flags into one request.
BUILDERS: dict[str, Callable[[argparse.Namespace], protobuf.MessageType]] = {
    "review": lambda a: m.Review(
        step=a.step,
        title=a.title,
        fields=a.field or [],
        extras=parsed_extras(a),
        is_final=a.final,
    ),
    "danger": lambda a: m.Danger(step=a.step, title=a.title, fields=a.field or []),
    "details": lambda a: m.Details(step=a.step, title=a.title, fields=a.field or []),
    "stream-data": lambda a: m.StreamData(
        step=a.step, title=a.title, length=a.length, fail_at=a.fail_at
    ),
    "verify-address": lambda a: m.VerifyAddress(
        step=a.step, value=a.value, account=a.account, path=a.path
    ),
    "verify-pubkey": lambda a: m.VerifyPubkey(
        step=a.step, value=a.value, account=a.account, path=a.path
    ),
    "done": lambda a: m.Done(step=a.step, text=a.text),
    "showcase": lambda a: m.Showcase(name=a.name),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testappctl",
        description="Drive one modui layout on the device through the test app.",
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=ARTIFACTS,
        help="directory with the testapp build, its proof and the root packet (default: %(default)s)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="reuse an app image the device already has instead of loading afresh",
    )
    layouts = parser.add_subparsers(dest="layout", required=True, metavar="LAYOUT")

    def layout(
        name: str, help: str, title: str | None = None
    ) -> argparse.ArgumentParser:
        p = layouts.add_parser(name, help=help, description=help)
        p.add_argument(
            "--step",
            default=name,
            help="step name, relative to the app (default: %(default)s)",
        )
        if title is not None:
            p.add_argument("--title", default=title)
        return p

    def with_fields(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--field",
            type=parsed_field,
            action="append",
            metavar="KIND:LABEL=VALUE",
            help="a fact, repeatable; KIND:VALUE for a note or a warning",
        )

    def with_extras(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--extra",
            nargs="+",
            action="append",
            metavar=("LABEL", "KIND:LABEL=VALUE"),
            help="an extra reachable from the menu; repeatable",
        )

    p = layout("review", "modui::review", "Send")
    with_fields(p)
    with_extras(p)
    p.add_argument(
        "--final",
        action="store_true",
        help="confirm_final (hold) instead of confirm",
    )

    p = layout("danger", "modui::review(...).confirm_danger()", "Important")
    with_fields(p)

    p = layout("details", "modui::details", "Confirm message")
    with_fields(p)

    p = layout("stream-data", "a review with a data_source field", "Stream")
    p.add_argument("--length", type=int, default=1025)
    p.add_argument(
        "--fail-at",
        type=int,
        help="make the k-th read (1-based) fail, so the host sees the app's error",
    )

    p = layout("verify-address", "modui::verify_address")
    p.add_argument("--value", default="TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq")
    p.add_argument("--account", default="TRX #1")
    p.add_argument("--path", default="m/44'/195'/0'/0/0")

    p = layout("verify-pubkey", "modui::verify_pubkey")
    p.add_argument(
        "--value",
        default="tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U",
    )
    p.add_argument("--account", default="TRX #1")
    p.add_argument("--path", default="m/44'/195'/0'/0/0")

    p = layout("done", "modui::done", "Done")
    p.add_argument("--text", default="Transaction signed")

    p = layouts.add_parser(
        "progress",
        help="modui::progress, paced from here",
        description="modui::progress, paced from here",
    )
    p.add_argument("--label", default="Working...")
    p.add_argument(
        "--total", type=int, help="total units; omit for an indeterminate progress"
    )
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--step-units", type=int, default=1)
    p.add_argument("--step-delay-ms", type=int, default=200)
    p.add_argument(
        "--step-label",
        help="change the label under the bar before each step, as `LABEL i/n`",
    )

    p = layouts.add_parser(
        "showcase",
        help="one flow from the API reference's examples",
        description="one flow from the API reference's examples",
    )
    p.add_argument(
        "name",
        choices=SHOWCASES,
        metavar="NAME",
        help=", ".join(SHOWCASES),
    )

    return parser


def run_progress(app: TestApp, args: argparse.Namespace) -> None:
    with app.progress(args.label, total=args.total) as progress:
        for i in range(args.steps):
            time.sleep(args.step_delay_ms / 1000)
            if args.step_label is not None:
                progress.label(f"{args.step_label} {i + 1}/{args.steps}")
            progress.step(args.step_units)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    session = connect()
    app = TestApp.load(session, args.artifacts, force_reload=not args.no_reload)
    print("Walk the screen on the device now.")
    try:
        if args.layout == "progress":
            run_progress(app, args)
            print("Progress done.")
            return 0
        result = app.call(BUILDERS[args.layout](args))
    except exceptions.TrezorFailure as e:
        print(f"Failure: {e}")
        return 1
    print(f"Reply: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
