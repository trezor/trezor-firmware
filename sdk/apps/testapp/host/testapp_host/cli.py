"""Command-line frontend: one subcommand per block, every parameter a flag.

Only argument parsing lives here; the work is done by the library.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from trezorlib import exceptions, protobuf

from . import messages as m
from .client import ARTIFACTS, TestApp, connect, extras, props

SEVERITIES = {s.name.lower(): s for s in m.Severity}


def key_value(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"expected KEY=VALUE, got {text!r}")
    return key, value


def commitment(args: argparse.Namespace) -> m.Commitment:
    return m.Commitment.Final if args.final else m.Commitment.Step


def parsed_extras(args: argparse.Namespace) -> list[m.ExtraItem]:
    items = []
    for label, *pairs in args.extra or []:
        items.append((label, [key_value(p) for p in pairs]))
    return extras(items)


def parsed_props(args: argparse.Namespace) -> list[m.Property]:
    return props(args.prop or []) + props(args.prop_mono or [], mono=True)


def data_bytes(args: argparse.Namespace) -> bytes:
    if args.data_hex is not None:
        return bytes.fromhex(args.data_hex)
    return bytes(i % 256 for i in range(args.data_len))


def flow_steps(text: str) -> list[m.FlowStep]:
    if text.startswith("@"):
        text = Path(text[1:]).read_text()
    steps = json.loads(text)
    if not isinstance(steps, list):
        raise argparse.ArgumentTypeError("the flow is a JSON list of steps")
    return [protobuf.dict_to_proto(m.FlowStep, step) for step in steps]


# Each subcommand turns its flags into one request.
BUILDERS: dict[str, Callable[[argparse.Namespace], protobuf.MessageType]] = {
    "action": lambda a: m.ConfirmAction(
        title=a.title,
        action=a.action,
        description=a.description,
        subtitle=a.subtitle,
        commitment=commitment(a),
        br=a.br,
        extras=parsed_extras(a),
    ),
    "value": lambda a: m.ConfirmValue(
        title=a.title,
        value=a.value,
        kind=m.ValueKind.Address if a.address else m.ValueKind.Text,
        subtitle=a.subtitle,
        description=a.description,
        footer_hint=a.footer_hint,
        footer_warning=a.footer_warning,
        commitment=commitment(a),
        br=a.br,
        extras=parsed_extras(a),
    ),
    "data": lambda a: m.ConfirmData(
        title=a.title,
        data=data_bytes(a),
        subtitle=a.subtitle,
        br=a.br,
        extras=parsed_extras(a),
        cancel=a.cancel,
    ),
    "properties": lambda a: m.ConfirmProperties(
        title=a.title,
        props=parsed_props(a),
        subtitle=a.subtitle,
        commitment=commitment(a),
        br=a.br,
        extras=parsed_extras(a),
        cancel=a.cancel,
    ),
    "summary": lambda a: m.ConfirmSummary(
        title=a.title,
        amount_label=a.amount[0] if a.amount else None,
        amount=a.amount[1] if a.amount else None,
        fee_label=a.fee[0] if a.fee else None,
        fee=a.fee[1] if a.fee else None,
        br=a.br,
        extras=parsed_extras(a),
    ),
    "notice": lambda a: m.ShowNotice(
        severity=SEVERITIES[a.severity],
        title=a.title,
        content=a.content,
        br=a.br,
        extras=parsed_extras(a),
        cancel=a.cancel,
    ),
    "flow": lambda a: m.ConfirmLinearFlow(steps=a.steps),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testappctl",
        description="Drive one modui block on the device through the test app.",
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
    blocks = parser.add_subparsers(dest="block", required=True, metavar="BLOCK")

    def block(name: str, help: str) -> argparse.ArgumentParser:
        p = blocks.add_parser(name, help=help, description=help)
        p.add_argument(
            "--br", default=f"testapp/{name}", help="step name (default: %(default)s)"
        )
        return p

    def with_extras(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--extra",
            nargs="+",
            action="append",
            metavar=("LABEL", "KEY=VALUE"),
            help="an extra reachable from the menu; repeatable",
        )

    def with_commitment(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--final",
            action="store_true",
            help="Commitment::Final (hold) instead of Step",
        )

    def with_cancel(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--cancel", action="store_true", help="add a Cancel entry to the extras"
        )

    p = block("action", "modui::confirm_action")
    p.add_argument("--title", default="Confirm action")
    p.add_argument("--action", default="Do you really want to do this?")
    p.add_argument("--description")
    p.add_argument("--subtitle")
    with_commitment(p)
    with_extras(p)

    p = block("value", "modui::confirm_value")
    p.add_argument("--title", default="Confirm value")
    p.add_argument("--value", default="TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq")
    p.add_argument(
        "--address", action="store_true", help="ValueKind::Address instead of Text"
    )
    p.add_argument("--subtitle")
    p.add_argument("--description")
    footer = p.add_mutually_exclusive_group()
    footer.add_argument("--footer-hint")
    footer.add_argument("--footer-warning")
    with_commitment(p)
    with_extras(p)

    p = block("data", "modui::confirm_data")
    p.add_argument("--title", default="Confirm data")
    source = p.add_mutually_exclusive_group()
    source.add_argument("--data-hex", help="the bytes, as hex")
    source.add_argument(
        "--data-len",
        type=int,
        default=100,
        help="generate this many bytes (default: %(default)s)",
    )
    p.add_argument("--subtitle")
    with_extras(p)
    with_cancel(p)

    p = block("properties", "modui::confirm_properties")
    p.add_argument("--title", default="Confirm properties")
    p.add_argument(
        "--prop",
        type=key_value,
        action="append",
        metavar="KEY=VALUE",
        help="repeatable",
    )
    p.add_argument(
        "--prop-mono",
        type=key_value,
        action="append",
        metavar="KEY=VALUE",
        help="monospace; repeatable",
    )
    p.add_argument("--subtitle")
    with_commitment(p)
    with_extras(p)
    with_cancel(p)

    p = block("summary", "modui::confirm_summary")
    p.add_argument("--title", default="Summary")
    p.add_argument(
        "--amount", type=key_value, metavar="LABEL=VALUE", default=("Amount", "1.5 TRX")
    )
    p.add_argument(
        "--fee", type=key_value, metavar="LABEL=VALUE", default=("Fee", "0.1 TRX")
    )
    p.add_argument("--no-amount", dest="amount", action="store_const", const=None)
    p.add_argument("--no-fee", dest="fee", action="store_const", const=None)
    with_extras(p)

    p = block("notice", "modui::show_notice")
    p.add_argument("--severity", choices=list(SEVERITIES), default="info")
    p.add_argument("--title", default="Notice")
    p.add_argument("--content", default="Something worth knowing happened.")
    with_extras(p)
    with_cancel(p)

    p = block("progress", "modui::progress_with, paced from here")
    p.add_argument("--label", default="Working...")
    p.add_argument(
        "--total", type=int, help="total units; omit for an indeterminate progress"
    )
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--step-units", type=int, default=1)
    p.add_argument("--step-delay-ms", type=int, default=200)

    p = block("flow", "modui::confirm_linear_flow")
    p.add_argument(
        "steps",
        type=flow_steps,
        help='JSON list of steps, or @FILE; e.g. \'[{"confirm_action": {"title": "A", "action": "a", "br": "s/1"}}]\'',
    )

    return parser


def run_progress(app: TestApp, args: argparse.Namespace) -> None:
    with app.progress(args.label, total=args.total) as progress:
        for _ in range(args.steps):
            time.sleep(args.step_delay_ms / 1000)
            progress.step(args.step_units)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    session = connect()
    app = TestApp.load(session, args.artifacts, force_reload=not args.no_reload)
    print("Walk the screen on the device now.")
    try:
        if args.block == "progress":
            run_progress(app, args)
            print("Progress done.")
            return 0
        result = app.call(BUILDERS[args.block](args))
    except exceptions.TrezorFailure as e:
        print(f"Failure: {e}")
        return 1
    print(f"Reply: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
