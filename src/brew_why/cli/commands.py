import logging
import subprocess

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler

from brew_why.core import cache, data, brew
from brew_why.ui import display

console = Console()

def setup_logging(debug: bool):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False, show_path=debug)]
    )

def overview(
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Show an overview of all installed Homebrew packages."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        users, deps, orphans = data.get_all_data(progress)
        
    if json_output:
        console.print_json(data={"users": users, "deps": deps, "orphans": orphans})
        return
        
    display.show_overview(users, deps, orphans)

def explain(
    package: str = typer.Argument(..., help="The package to explain"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Explain why a specific package is installed."""
    setup_logging(debug)
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            info_dict = cache.get_info_cached([package], progress)
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

def orphans(
    clean: bool = typer.Option(False, "--clean", help="Prompt to uninstall orphaned packages"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """List all safe-to-remove packages."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        _, _, orphans_list = data.get_all_data(progress)
        
    display.show_orphans(orphans_list)
    
    if clean and orphans_list:
        names = [o['name'] for o in orphans_list]
        if typer.confirm(f"\nDo you want to uninstall these {len(names)} packages now?"):
            brew.uninstall_packages(names)

def tree(
    package: str = typer.Argument(..., help="The package to show the tree for"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Show the dependency tree for a package."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        tree_str = brew.get_tree(package)
        
    display.show_tree(package, tree_str)

def cache_clear():
    """Clear the local JSON cache."""
    cache.clear_cache()

def heaviest(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """List the top 15 heaviest packages by disk size."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        users, deps, orphans_list = data.get_all_data(progress)
        
        for u in users:
            u['_category'] = "User"
        for d in deps:
            d['_category'] = "Dep"
        for o in orphans_list:
            o['_category'] = "Orphan"
            
        all_data = users + deps + orphans_list
        
    display.show_heaviest(all_data)

def audit(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Audit installed packages for outdated versions."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        users, deps, orphans_list = data.get_all_data(progress)
        
    display.show_audit(users, deps)

def reverse_tree(
    package: str = typer.Argument(..., help="The package to show reverse dependencies for"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Show the reverse dependency tree (what depends on this package)."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        rev_graph = data.build_reverse_graph()
        
    display.show_reverse_tree(package, rev_graph)

def dashboard(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Launch the interactive Textual TUI dashboard."""
    setup_logging(debug)
    try:
        from brew_why.ui.tui import BrewWhyApp
        app_instance = BrewWhyApp()
        app_instance.run()
    except ImportError:
        console.print("[bold red]Error:[/] The 'textual' package is required for the dashboard.")
        console.print("Please install it with: [cyan]pip install textual[/cyan]")
        raise typer.Exit(1)

def stats(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Show overall statistics of the Homebrew environment."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        users, deps, orphans_list = data.get_all_data(progress)
        
    display.show_stats(users, deps, orphans_list)

def tidy(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Interactive wizard to clean up orphaned dependencies and old caches."""
    setup_logging(debug)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        _, _, orphans_list = data.get_all_data(progress)
        
    if not orphans_list:
        console.print("[bold green]✔ Your system is already tidy! No orphaned packages found.[/bold green]")
    else:
        display.show_orphans(orphans_list)
        if typer.confirm(f"\nDo you want to safely uninstall these {len(orphans_list)} orphaned packages?"):
            names = [o['name'] for o in orphans_list]
            brew.uninstall_packages(names)
            console.print("[bold green]✔ Orphans removed.[/bold green]")
            
    if typer.confirm("\nDo you want to run `brew cleanup` to clear old cache files?"):
        console.print("[cyan]Running brew cleanup...[/cyan]")
        subprocess.run(["brew", "cleanup"])
        console.print("[bold green]✔ Cache cleaned.[/bold green]")
