from datetime import datetime
from typing import Dict, Any, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text

console = Console()

def parse_date(timestamp: int) -> str:
    if not timestamp:
        return "Unknown date"
    dt = datetime.fromtimestamp(timestamp)
    delta = datetime.now() - dt
    
    if delta.days > 365:
        age = f"{delta.days // 365} years ago"
    elif delta.days > 30:
        age = f"{delta.days // 30} months ago"
    elif delta.days > 0:
        age = f"{delta.days} days ago"
    else:
        age = "Today"
    
    return f"{age} ({dt.strftime('%b %d, %Y')})"

def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "Unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {units[i]}"

def show_overview(users: List[Dict], deps: List[Dict], orphans: List[Dict]) -> None:
    console.print(f"\n[bold green]⬢ Homebrew Dependency Overview[/bold green]")
    console.print(f"Total packages: [bold]{len(users) + len(deps) + len(orphans)}[/bold]\n")
    
    if orphans:
        total_orphan_size = sum(o.get('size', 0) for o in orphans)
        table = Table(title=f"Safe to Remove (Orphaned Dependencies) - Recoverable: {format_size(total_orphan_size)}", title_style="bold green", show_header=True, header_style="bold magenta")
        table.add_column("Package", style="cyan")
        table.add_column("Version", justify="right")
        table.add_column("Size", justify="right", style="blue")
        table.add_column("Age", justify="right")
        
        for o in orphans:
            age = parse_date(o['time']).split('(')[0].strip()
            table.add_row(o['name'], str(o['version']), format_size(o.get('size', 0)), age)
            
        console.print(table)
        names = " ".join([o['name'] for o in orphans])
        console.print(f"[dim]To remove all: brew uninstall {names}[/dim]\n")
        
    if users:
        table = Table(title="User-Installed (Top-Level)", title_style="bold yellow", show_header=True)
        table.add_column("Package", style="cyan")
        table.add_column("Version", justify="right")
        table.add_column("Dependencies", justify="right")
        table.add_column("Size", justify="right", style="blue")
        table.add_column("Status", justify="center")
        
        for u in users:
            status_text = "[red]Outdated[/red]" if u.get('outdated') else "[green]Up-to-date[/green]"
            table.add_row(u['name'], str(u['version']), str(len(u['deps'])), format_size(u.get('size', 0)), status_text)
            
        console.print(table)
        
    console.print(f"\n[bold red]Dependencies (Required by others) - {len(deps)}[/bold red]")
    console.print(f"[dim]... {len(deps)} packages pulled in automatically.[/dim]")
    console.print(f"[dim]Run `brew-why explain <pkg>` to see what depends on them.[/dim]\n")

def show_orphans(orphans: List[Dict]) -> None:
    if not orphans:
        console.print("[bold green]✔ No orphaned dependencies found! You're clean.[/bold green]")
        return
        
    total_orphan_size = sum(o.get('size', 0) for o in orphans)
    table = Table(title=f"Safe to Remove (Orphaned Dependencies) - Recoverable: {format_size(total_orphan_size)}", title_style="bold green", show_header=True, header_style="bold magenta")
    table.add_column("Package", style="cyan")
    table.add_column("Version", justify="right")
    table.add_column("Size", justify="right", style="blue")
    table.add_column("Age", justify="right")
    
    for o in orphans:
        age = parse_date(o['time']).split('(')[0].strip()
        table.add_row(o['name'], str(o['version']), format_size(o.get('size', 0)), age)
        
    console.print(table)

def show_heaviest(all_data: List[Dict]) -> None:
    sorted_pkgs = sorted(all_data, key=lambda x: x.get('size', 0), reverse=True)[:15]
    
    table = Table(title="Top 15 Heaviest Packages", title_style="bold blue", show_header=True)
    table.add_column("Package", style="cyan")
    table.add_column("Type", justify="center")
    table.add_column("Size", justify="right", style="bold yellow")
    
    for p in sorted_pkgs:
        ptype = p.get('_category', "User" if p.get('requested') else "Dep")
        table.add_row(p['name'], ptype, format_size(p.get('size', 0)))
        
    console.print(table)

def show_audit(users: List[Dict], deps: List[Dict]) -> None:
    outdated_pkgs = [p for p in users + deps if p.get('outdated')]
    
    if not outdated_pkgs:
        console.print("[bold green]✔ All packages are up to date![/bold green]")
        return
        
    table = Table(title="Outdated Packages", title_style="bold red", show_header=True)
    table.add_column("Package", style="cyan")
    table.add_column("Type", justify="center")
    
    for p in outdated_pkgs:
        ptype = "User-installed" if p.get('requested') else "Dependency"
        table.add_row(p['name'], ptype)
        
    console.print(table)
    console.print("\n[dim]Run `brew upgrade` to update these packages.[/dim]")

def show_single(pkg: str, info: Dict, uses: List[str], is_leaf: bool, requested: bool) -> None:
    version = info.get('versions', {}).get('stable', 'unknown')
    installed = info.get('installed', [{}])[0]
    time_installed = installed.get('time')
    
    deps = info.get('dependencies', [])
    age_str = parse_date(time_installed)
    
    is_safe = is_leaf and not requested
    is_user_leaf = is_leaf and requested
    
    if is_safe:
        status = "[bold green]✔ SAFE TO REMOVE — orphaned dependency[/bold green]"
    elif is_user_leaf:
        status = "[bold yellow]⚠ TOP-LEVEL — explicitly installed by you[/bold yellow]"
    else:
        status = f"[bold red]✖ REQUIRED — {', '.join(uses[:2])}{' and others' if len(uses) > 2 else ''} depend on it[/bold red]"
        
    details = Table.grid(padding=1)
    details.add_column(style="bold cyan", justify="right")
    details.add_column()
    
    details.add_row("Installed:", age_str)
    details.add_row("Requested:", "Yes" if requested else "No (pulled in automatically)")
    details.add_row("Depends on:", ", ".join(deps) if deps else "None")
    details.add_row("Used by:", f"{', '.join(uses) if uses else 'None'} ({len(uses)})")
    details.add_row("Status:", status)
    
    panel = Panel(details, title=f"[bold]{pkg} {version}[/bold]", expand=False, border_style="blue")
    console.print(panel)

def show_tree(pkg: str, tree_str: str) -> None:
    panel = Panel(tree_str.strip(), title=f"[bold cyan]Dependency Tree: {pkg}[/bold cyan]", expand=False)
    console.print(panel)

def _build_rich_tree(node_name: str, rev_graph: Dict[str, List[str]], current_tree: Tree, visited: set) -> None:
    if node_name in visited:
        current_tree.add(f"[dim]{node_name} (circular/already shown)[/dim]")
        return
        
    visited.add(node_name)
    users = rev_graph.get(node_name, [])
    
    for u in users:
        branch = current_tree.add(f"[cyan]{u}[/cyan]")
        _build_rich_tree(u, rev_graph, branch, visited.copy())

def show_reverse_tree(pkg: str, rev_graph: Dict[str, List[str]]) -> None:
    root = Tree(f"[bold green]Reverse Dependency Tree: {pkg}[/bold green]\n(Packages that depend on {pkg})")
    
    users = rev_graph.get(pkg, [])
    if not users:
        console.print(f"[bold yellow]No packages depend on {pkg}.[/bold yellow]")
        return
        
    for u in users:
        branch = root.add(f"[cyan]{u}[/cyan]")
        _build_rich_tree(u, rev_graph, branch, {pkg})
        
    console.print(root)

def show_stats(users: List[Dict], deps: List[Dict], orphans: List[Dict]) -> None:
    total_pkgs = len(users) + len(deps) + len(orphans)
    total_size = sum(p.get('size', 0) for p in users + deps + orphans)
    orphan_size = sum(p.get('size', 0) for p in orphans)
    outdated = sum(1 for p in users + deps + orphans if p.get('outdated'))

    table = Table(title="Homebrew Statistics", title_style="bold magenta", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="bold yellow")
    
    table.add_row("Total Packages", str(total_pkgs))
    table.add_row("User Installed", str(len(users)))
    table.add_row("Dependencies", str(len(deps)))
    table.add_row("Orphans (Safe to remove)", str(len(orphans)))
    table.add_row("Outdated Packages", str(outdated))
    table.add_row("Total Disk Usage", format_size(total_size))
    table.add_row("Potential Space Savings", format_size(orphan_size))

    console.print(table)

