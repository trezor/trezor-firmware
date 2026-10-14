import click

from . import master_diff


@click.group()
def cli():
    pass


@cli.command(name="master-diff")
@click.argument("models", nargs=-1)
def do_master_diff(models: list[str] | None = None):
    master_diff.main(models=models)


if __name__ == "__main__":
    cli()
