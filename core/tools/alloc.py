#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Dict, Protocol, TextIO, TypedDict

import click
from dominate import document
from dominate.tags import a, h3, meta, style, table, tbody, td, th, thead, tr
from dominate.util import raw

HERE = Path(__file__).resolve().parent


if TYPE_CHECKING:

    class LineAllocData(TypedDict):
        total_allocs: int
        total_calls: int
        avg_allocs: float

    # {filename:{lineno:LineAllocData}}
    alloc_data_dict = Dict[str, Dict[int, LineAllocData]]

    class SharedObject(Protocol):
        data: alloc_data_dict
        type: str


def parse_alloc_data(
    alloc_data: TextIO,
) -> alloc_data_dict:
    parsed_data: alloc_data_dict = {}
    for line in alloc_data:
        ident, allocs, calls = line.strip().split(" ")
        allocs = int(allocs)
        calls = int(calls)
        filename, lineno = ident.split(":")
        lineno = int(lineno)

        filedata = parsed_data.setdefault(filename, {})
        filedata[lineno] = {
            "total_allocs": allocs,
            "total_calls": calls,
            "avg_allocs": allocs / calls,
        }
    return parsed_data


@click.group()
@click.pass_context
@click.option("-a", "--alloc-data", type=click.File(), default="src/alloc_data.txt")
@click.option("-t", "--type", type=click.Choice(("total", "avg")), default="avg")
def cli(ctx: click.Context, alloc_data: TextIO, type: str):
    shared_obj: SharedObject = SimpleNamespace()  # type: ignore
    shared_obj.data = parse_alloc_data(alloc_data)
    shared_obj.type = type
    ctx.obj = shared_obj


def _normalize_filename(filename: str) -> str:
    if filename.startswith("src/"):
        return filename[4:]
    return filename


@cli.command()
@click.pass_obj
@click.argument("filename")
def annotate(obj: SharedObject, filename: str):
    filename = _normalize_filename(filename)

    if obj.type == "total":

        def alloc_str(line: LineAllocData) -> str:
            return str(line["total_allocs"])

    else:

        def alloc_str(line: LineAllocData) -> str:
            return f"{line['avg_allocs']:.2f}"

    filedata = obj.data[filename]

    linedata = {lineno: alloc_str(line) for lineno, line in filedata.items()}
    maxlen = max(len(l) for l in linedata.values())

    lineno = 0
    for line in open("src/" + filename):
        lineno += 1
        linecount = linedata.get(lineno, "")
        print(f"{linecount:>{maxlen}}  {line}", end="")


def _list(
    obj: SharedObject, sort_by: str = "avg_allocs", reverse: bool = False
) -> list[tuple[str, float, int]]:
    return sorted(
        (
            (
                filename,
                sum(line["avg_allocs"] for line in lines.values()),
                sum(line["total_allocs"] for line in lines.values()),
            )
            for filename, lines in obj.data.items()
        ),
        key=lambda x: x[1 if sort_by == "avg_allocs" else 2],
        reverse=reverse,
    )


@cli.command(name="list")
@click.pass_obj
@click.option("-r", "--reverse", is_flag=True)
def list_function(obj: SharedObject, reverse: bool):
    if obj.type == "total":
        field = "total_allocs"

        def format_num(l: tuple[str, float, int]) -> str:
            return f"{l[2]}"

    else:
        field = "avg_allocs"

        def format_num(l: tuple[str, float, int]) -> str:
            return f"{l[1]:.2f}"

    file_sums = _list(obj, field, reverse)

    maxlen = max(len(format_num(l)) for l in file_sums)
    for l in file_sums:
        num_str = format_num(l)
        filename = l[0]
        print(f"{num_str:>{maxlen}}  {filename}")


def get_biggest_line_allocations(
    obj: SharedObject, biggest_n: int
) -> list[tuple[str, float]]:
    all_allocs: dict[str, float] = {}
    for file, line_stats in obj.data.items():
        for line, stats in line_stats.items():
            all_allocs[f"{file}:{line}"] = stats["avg_allocs"]

    return sorted(all_allocs.items(), key=lambda x: x[1], reverse=True)[:biggest_n]


def get_biggest_n_lines_for_each_file(
    obj: SharedObject, biggest_n: int
) -> dict[str, list[int]]:
    biggest_file_allocs: dict[str, list[int]] = {}
    for file, line_stats in obj.data.items():
        biggest = sorted(
            line_stats.items(), key=lambda x: x[1]["avg_allocs"], reverse=True
        )[:biggest_n]
        biggest_file_allocs[file] = [line for line, _stats in biggest]
    return biggest_file_allocs


@cli.command()
@click.pass_obj
@click.argument("htmldir")
def html(obj: SharedObject, htmldir: str):
    file_sums = _list(obj, "total_allocs", reverse=True)
    style_grey = "color: grey"
    style_red = "color: red;"
    style_blue = "color: blue;"
    style_right = "text-align: right;"
    css_smaller_mono = (
        "body { font-size: 80%; font-family: 'Courier New', Courier, monospace; }"
    )

    n_biggest = 50
    biggest_lines = get_biggest_line_allocations(obj, n_biggest)
    for location, avg_alloc in reversed(biggest_lines):
        # Prepending core/src so it can be opened via alt+click in VSCode
        print(f"{avg_alloc:.2f} core/src/{location}")

    # Create index.html - two tables
    doc = document(title="Firmware allocations")
    with doc.head:
        meta(charset="utf-8")
        style(css_smaller_mono)
    with doc:
        h3(f"{n_biggest} biggest allocations")
        with table():
            with thead():
                with tr():
                    th("alloc", style=style_right)
                    th("file:line")
            with tbody():
                for location, avg_alloc in biggest_lines:
                    filename, lineno = location.split(":")
                    with tr():
                        td(f"{avg_alloc:.2f}", style=style_right)
                        td(
                            a(
                                location,
                                href=f"{filename}.html#{lineno}",
                                target="_blank",
                            )
                        )
        h3(f"Total allocations: {sum(total_sum for _, _, total_sum in file_sums)}")
        with table():
            with thead():
                with tr():
                    th("avg", style=style_right)
                    th("total", style=style_right)
                    th("file")
            with tbody():
                for filename, avg_sum, total_sum in file_sums:
                    with tr():
                        td(f"{avg_sum:.2f}", style=style_right)
                        td(total_sum, style=style_right)
                        td(
                            a(
                                filename,
                                href=f"{filename}.html",
                                target="_blank",
                            )
                        )
    with open(f"{htmldir}/index.html", "w") as f:
        f.write(doc.render())

    # So we can highlight biggest allocations in each file
    biggest_n_lines_for_each_file = get_biggest_n_lines_for_each_file(obj, 5)

    # Create HTML for each file - one table in each
    for filename in file_sums:
        filename = _normalize_filename(filename[0])
        htmlfile = Path(htmldir) / filename
        htmlfile.parent.mkdir(parents=True, exist_ok=True)

        doc = document(title=filename)
        with doc.head:
            meta(charset="utf-8")
            style(css_smaller_mono)
        with doc:
            with table():
                with thead():
                    with tr():
                        th("#", style=style_grey)
                        th("avg", style=style_right)
                        th("total", style=style_right)
                        th("")
                with tbody():
                    lineno = 0
                    for line in open(HERE.parent / "src" / filename):
                        lineno += 1
                        line_info = obj.data[filename].get(lineno, {})
                        total = line_info.get("total_allocs", 0)
                        avg = line_info.get("avg_allocs", 0)

                        if lineno in biggest_n_lines_for_each_file[filename]:
                            row_style = style_red
                        elif avg > 0:
                            row_style = style_blue
                        else:
                            row_style = None

                        with tr(style=row_style, id=lineno):
                            td(lineno, style=style_grey)
                            td(f"{avg:.2f}", style=style_right)
                            td(total, style=style_right)
                            # Creating nonbreaking space, otherwise prefix
                            # whitespace is stripped
                            td(raw(line.rstrip("\n").replace(" ", "&nbsp;")))
        with open(str(htmlfile) + ".html", "w") as f:
            f.write(doc.render())


if __name__ == "__main__":
    cli()
