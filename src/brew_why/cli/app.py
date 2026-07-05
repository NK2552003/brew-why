import typer
from rich.console import Console

from brew_why.cli import commands
from brew_why.cli import updater

app = typer.Typer(
    name="brew-why",
    help="A beautiful CLI tool that explains Homebrew dependencies.",
    add_completion=False,
)

console = Console()

# Register commands
app.command(name="overview")(commands.overview)
app.command(name="explain")(commands.explain)
app.command(name="orphans")(commands.orphans)
app.command(name="tree")(commands.tree)
app.command(name="cache-clear")(commands.cache_clear)
app.command(name="heaviest")(commands.heaviest)
app.command(name="audit")(commands.audit)
app.command(name="reverse-tree")(commands.reverse_tree)
app.command(name="dashboard")(commands.dashboard)
app.command(name="stats")(commands.stats)
app.command(name="tidy")(commands.tidy)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    version: bool = typer.Option(None, "--version", "-v", callback=updater.version_callback, is_eager=True, help="Show the application version."),
    update: bool = typer.Option(None, "--update", "--upgrade", callback=updater.update_callback, is_eager=True, help="Update to the latest version from PyPI.")
):
    """
    brew-why: A beautiful CLI to explain Homebrew dependencies.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
