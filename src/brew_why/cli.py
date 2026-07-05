import json
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from brew_why import core
from brew_why import brew
from brew_why import display

app = typer.Typer(
    name="brew-why",
    help="A beautiful CLI tool that explains Homebrew dependencies.",
    add_completion=False,
)
console = Console()

def setup_logging(debug: bool):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False, show_path=debug)]
    )

@app.command("overview")
def overview(
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Show an overview of all installed Homebrew packages."""
    setup_logging(debug)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        users, deps, orphans = core.get_all_data(progress)
        
    if json_output:
        console.print_json(data={"users": users, "deps": deps, "orphans": orphans})
        return
        
    display.show_overview(users, deps, orphans)

@app.command("explain")
def explain(
    package: str = typer.Argument(..., help="The package to explain"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Explain why a specific package is installed."""
    setup_logging(debug)
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            info_dict = core.get_info_cached([package], progress)
            info = info_dict.get(package)
            
            if not info:
                console.print(f"[bold red]Error:[/] {package} is not installed or not found.")
                raise typer.Exit(1)
                
            uses = brew.get_uses(package)
            leaves = brew.get_leaves()
            
        is_leaf = package in leaves
        requested = info.get('installed', [{}])[0].get('installed_on_request', False)
        
        display.show_single(package, info, uses, is_leaf, requested)
    except Exception as e:
        if debug:
            logging.exception(e)
        else:
            console.print(f"[bold red]Error:[/] {str(e)}")
        raise typer.Exit(1)

@app.command("orphans")
def orphans(
    clean: bool = typer.Option(False, "--clean", help="Prompt to uninstall orphaned packages"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """List all safe-to-remove packages."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        _, _, orphans_list = core.get_all_data(progress)
        
    display.show_orphans(orphans_list)
    
    if clean and orphans_list:
        names = [o['name'] for o in orphans_list]
        if typer.confirm(f"\nDo you want to uninstall these {len(names)} packages now?"):
            brew.uninstall_packages(names)

@app.command("tree")
def tree(
    package: str = typer.Argument(..., help="The package to show the tree for"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Show the dependency tree for a package."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        tree_str = brew.get_tree(package)
        
    display.show_tree(package, tree_str)

@app.command("cache-clear")
def cache_clear():
    """Clear the local JSON cache."""
    core.clear_cache()

# Typer by default uses the command names, but if we want `brew-why <pkg>` to work seamlessly
# without typing "explain", we can use a callback or define a custom logic in main.
# But using explicit subcommands like `brew-why explain <pkg>` is much better practice for production CLIs.
# Since the user requested `brew-why <pkg>` in the original prompt, Typer allows doing an implicit fallback,
# but it's cleaner to keep them as explicit commands for a production tool (like `brew info <pkg>`).
# I will implement an explicit command structure, but provide a default callback to handle bare `brew-why`.

@app.command("heaviest")
def heaviest(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """List the top 15 heaviest packages by disk size."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        users, deps, orphans = core.get_all_data(progress)
        
        for u in users:
            u['_category'] = "User"
        for d in deps:
            d['_category'] = "Dep"
        for o in orphans:
            o['_category'] = "Orphan"
            
        all_data = users + deps + orphans
        
    display.show_heaviest(all_data)

@app.command("audit")
def audit(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Audit installed packages for outdated versions."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        users, deps, orphans = core.get_all_data(progress)
        
    display.show_audit(users, deps)

@app.command("reverse-tree")
def reverse_tree(
    package: str = typer.Argument(..., help="The package to show reverse dependencies for"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Show the reverse dependency tree (what depends on this package)."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        rev_graph = core.build_reverse_graph()
        
    display.show_reverse_tree(package, rev_graph)

@app.command("dashboard")
def dashboard(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Launch the interactive Textual TUI dashboard."""
    setup_logging(debug)
    try:
        from brew_why.tui import BrewWhyApp
        app_instance = BrewWhyApp()
        app_instance.run()
    except ImportError:
        console.print("[bold red]Error:[/] The 'textual' package is required for the dashboard.")
        console.print("Please install it with: [cyan]pip install textual[/cyan]")
        raise typer.Exit(1)

import importlib.metadata
import subprocess
import os
import urllib.request
import json
import re

def version_callback(value: bool):
    if value:
        try:
            ver = importlib.metadata.version('brew-why')
        except Exception:
            ver = 'unknown'
        print(f"brew-why version {ver}")
        raise typer.Exit()

def _parse_version(v: str):
    return tuple(int(x) for x in re.findall(r'\d+', v))

def update_callback(value: bool):
    if value:
        console.print("[cyan]Checking PyPI for updates...[/cyan]")
        
        try:
            current_ver = importlib.metadata.version('brew-why')
        except Exception:
            current_ver = "0.0.0"
            
        latest_ver = None
        try:
            url = "https://pypi.org/pypi/brew-why/json"
            req = urllib.request.Request(url, headers={'User-Agent': 'brew-why-updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_ver = data.get("info", {}).get("version")
        except Exception:
            pass
            
        if not latest_ver:
            console.print("[yellow]Could not find 'brew-why' on PyPI (it might not be published yet).[/yellow]")
            install_script = os.path.expanduser("~/Desktop/brew-why/install.sh")
            if os.path.exists(install_script):
                console.print("[cyan]Falling back to local development script...[/cyan]")
                subprocess.run(["bash", install_script])
            raise typer.Exit()
            
        if _parse_version(latest_ver) > _parse_version(current_ver):
            console.print(f"[green]New version available: {latest_ver} (current: {current_ver})[/green]")
            console.print("[cyan]Upgrading via pipx...[/cyan]")
            subprocess.run(["pipx", "upgrade", "brew-why"])
        else:
            console.print(f"[green]You are already on the latest version ({current_ver}).[/green]")
            
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True, help="Show the application version."),
    update: bool = typer.Option(None, "--update", "--upgrade", callback=update_callback, is_eager=True, help="Update to the latest version from PyPI.")
):
    """
    brew-why: A beautiful CLI to explain Homebrew dependencies.
    """
    if ctx.invoked_subcommand is None:
        overview(json_output=False, debug=debug)
