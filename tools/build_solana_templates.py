# !/usr/bin/env python3
import json
import os
import subprocess
import tempfile
from pathlib import Path

import click
from mako.template import Template
from munch import munchify, Munch

HERE = Path(__file__).parent
ROOT = HERE.parent.resolve()

TEMPLATES = (
    ROOT / "common" / "defs" / "solana" / "programs.md.mako",
    ROOT / "core" / "src" / "apps" / "solana" / "transaction" / "instructions.py.mako",
    ROOT / "tests" / "device_tests" / "solana" / "construct" / "instructions.py.mako",
    ROOT / "core" / "tests" / "test_apps.solana.predefined_transaction.py.mako",
)

PROGRAMS_JSON = ROOT / "common" / "defs" / "solana" / "programs.json"


def _silent_call(*args):
    subprocess.check_call(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def format(file: Path):
    _silent_call("isort", file)
    _silent_call("black", file)
    _silent_call("flake8", file, "--config", ROOT / "setup.cfg")


def render_single(template_path: Path, programs: Munch) -> str:
    template = Template(filename=str(template_path.resolve()))
    with tempfile.NamedTemporaryFile(mode="w", dir=template_path.parent) as f:
        f.write(str(template.render(programs=programs)))
        f.flush()

        # after flushing the contents, on-disk file will be formatted...
        if ".py" in template_path.suffixes:
            format(Path(f.name))
        # ...and we need to explicitly open it again to get the updated contents,
        # otherwise we get cached results?
        with open(f.name, "r") as new_f:
            return new_f.read()


@click.command()
@click.option(
    "-c", "--check", is_flag=True, help="Check if the templates are up to date"
)
def build_templates(check: bool):
    programs = munchify(json.loads(PROGRAMS_JSON.read_text()))
    prog_stat = PROGRAMS_JSON.stat()

    all_ok = True
    for template_path in TEMPLATES:
        assert template_path.suffix == ".mako"
        dest_path = template_path.with_suffix("")
        result = render_single(template_path, programs)

        if check:
            if result != dest_path.read_text():
                print(f"{dest_path} is out of date")
                all_ok = False

        else:
            tmpl_stat = template_path.stat()
            dest_path.write_text(result)
            os.utime(
                dest_path,
                ns=(
                    max(tmpl_stat.st_atime_ns, prog_stat.st_atime_ns),
                    max(tmpl_stat.st_mtime_ns, prog_stat.st_mtime_ns),
                ),
            )

    if not all_ok:
        raise click.ClickException("Some templates are out of date")


if __name__ == "__main__":
    build_templates()
