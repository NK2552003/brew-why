import importlib.metadata
import subprocess
import os
import urllib.request
import json
import re

import typer
from rich.console import Console

console = Console()

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
