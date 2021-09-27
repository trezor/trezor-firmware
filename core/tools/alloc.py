#!/usr/bin/env python3

from pathlib import Path
from types import SimpleNamespace
import click

HERE = Path(__file__).parent.resolve()


def parse_alloc_data(alloc_data):
    parsed_data = {}
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
def cli(ctx, alloc_data, type):
    ctx.obj = SimpleNamespace(data=parse_alloc_data(alloc_data), type=type)


def _normalize_filename(filename):
    if filename.startswith("src/"):
        return filename[4:]
    return filename


@cli.command()
@click.pass_obj
@click.argument("filename")
def annotate(obj, filename):
    filename = _normalize_filename(filename)

    if obj.type == "total":
        alloc_str = lambda line: str(line["total_allocs"])
    else:
        alloc_str = lambda line: f"{line['avg_allocs']:.2f}"

    filedata = obj.data[filename]

    linedata = {lineno: alloc_str(line) for lineno, line in filedata.items()}
    maxlen = max(len(l) for l in linedata.values())

    lineno = 0
    for line in open("src/" + filename):
        lineno += 1
        linecount = linedata.get(lineno, "")
        print(f"{linecount:>{maxlen}}  {line}", end="")


def _list(obj, sort_by="avg_allocs", reverse=False):
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


@cli.command()
@click.pass_obj
@click.option("-r", "--reverse", is_flag=True)
def list(obj, reverse):
    if obj.type == "total":
        field = "total_allocs"
        format_num = lambda l: f"{l[2]}"
    else:
        field = "avg_allocs"
        format_num = lambda l: f"{l[1]:.2f}"

    file_sums = _list(obj, field, reverse)

    maxlen = max(len(format_num(l)) for l in file_sums)
    for l in file_sums:
        num_str = format_num(l)
        filename = l[0]
        print(f"{num_str:>{maxlen}}  {filename}")


class HtmlTable:
    def __init__(self, f):
        self.f = f

    def __enter__(self):
        self.f.write("<table>")
        return self

    def __exit__(self, type, value, traceback):
        self.f.write("</table>")

    def tr(self, *tds):
        self.f.write("<tr>")
        for td in tds:
            if isinstance(td, tuple):
                self.f.write(f"<td {td[0]}><tt>{td[1]}</tt></td>")
            else:
                self.f.write(f"<td><tt>{td}</tt></td>")
        self.f.write("</tr>")


@cli.command()
@click.pass_obj
@click.argument("htmldir")
def html(obj, htmldir):
    file_sums = _list(obj, "total_allocs", reverse=True)
    style_grey = "style='color: grey'"
    style_right = "style='text-align: right'"

    with open(f"{htmldir}/index.html", "w") as f:
        f.write("<html>")
        f.write(
            f"<h3>Total allocations: {sum(total_sum for _, _, total_sum in file_sums)}</h3>"
        )
        with HtmlTable(f) as table:
            table.tr((style_right, "avg"), (style_right, "total"), "")
            for filename, avg_sum, total_sum in file_sums:
                table.tr(
                    (style_right, f"{avg_sum:.2f}"),
                    (style_right, total_sum),
                    f"<a href='{filename}.html'>{filename}</a>",
                )
        f.write("</html>")

    for filename in file_sums:
        filename = _normalize_filename(filename[0])
        htmlfile = Path(htmldir) / filename
        htmlfile.parent.mkdir(parents=True, exist_ok=True)

        with open(str(htmlfile) + ".html", "w") as f:
            filedata = obj.data[filename]
            f.write(f"<html><title>{filename}</title>")
            with HtmlTable(f) as table:
                table.tr(
                    (style_grey, "#"), (style_right, "avg"), (style_right, "total"), ""
                )

                lineno = 0
                for line in open(HERE.parent / "src" / filename):
                    line = line.rstrip("\n").replace(" ", "&nbsp;")
                    lineno += 1
                    total = filedata.get(lineno, {}).get("total_allocs", 0)
                    avg = filedata.get(lineno, {}).get("avg_allocs", 0)

                    table.tr(
                        (style_grey, lineno),
                        (style_right, f"{avg:.2f}"),
                        (style_right, total),
                        line,
                    )
            f.write("</html>")


if __name__ == "__main__":
    cli()
