"""Command-line interface for pyinit."""

import typer

app = typer.Typer(
    name="pyinit",
    help="Command-line interface for pyinit.",
    no_args_is_help=True,
)


@app.command()
def hello(name: str = "world") -> None:
    """Print a greeting."""
    typer.echo(f"Hello, {name}!")


if __name__ == "__main__":
    app()
