import json
import logging
import subprocess
from typing import List, Dict, Any, Optional

logger = logging.getLogger("brew_why")

def run_brew(args: List[str], json_output: bool = False) -> Any:
    """Executes a brew command and returns parsed JSON or a list of output lines."""
    cmd_str = "brew " + " ".join(args)
    logger.debug(f"Running command: {cmd_str}")
    
    try:
        result = subprocess.run(["brew"] + args, capture_output=True, text=True, check=True)
        if json_output:
            return json.loads(result.stdout)
        return [line for line in result.stdout.strip().split('\n') if line]
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command: {cmd_str}\n{e.stderr}")
        raise RuntimeError(f"Homebrew command failed: {cmd_str}") from e
    except FileNotFoundError as e:
        logger.error("Homebrew is not installed or not in PATH.")
        raise RuntimeError("Homebrew not found.") from e

def get_installed() -> List[str]:
    """Returns a list of all installed formulae."""
    return run_brew(["list", "--formula"])

def get_leaves() -> List[str]:
    """Returns a list of top-level installed formulae."""
    return run_brew(["leaves"])

def get_uses(pkg: str) -> List[str]:
    """Returns what other installed packages use the specified package."""
    return run_brew(["uses", "--installed", pkg])

def get_tree(pkg: str) -> str:
    """Returns the raw text dependency tree for a package."""
    try:
        result = subprocess.run(["brew", "deps", "--tree", pkg], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return e.stdout or e.stderr

def get_all_deps() -> List[str]:
    """Returns the full dependency graph for all installed packages."""
    return run_brew(["deps", "--installed"])

def get_cellar() -> str:
    """Returns the path to the Homebrew Cellar."""
    res = run_brew(["--cellar"])
    return res[0] if res else ""

def get_outdated() -> Dict[str, Any]:
    """Returns outdated packages as parsed JSON."""
    return run_brew(["outdated", "--json=v2"], json_output=True)

def uninstall_packages(pkgs: List[str]) -> None:
    """Uninstalls the specified packages."""
    logger.info(f"Uninstalling: {', '.join(pkgs)}")
    subprocess.run(["brew", "uninstall"] + pkgs, check=False)
