import click

from . import master_diff


@click.group()
def cli():
    pass


@cli.command(name="master-diff")
def do_master_diff():
    master_diff.main()


if __name__ == "__main__":
    cli()
