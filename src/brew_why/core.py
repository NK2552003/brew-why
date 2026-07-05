import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

from rich.progress import Progress, SpinnerColumn, TextColumn

from brew_why.brew import run_brew, get_installed, get_leaves, get_cellar, get_all_deps, get_outdated

logger = logging.getLogger("brew_why")

CACHE_DIR = os.path.expanduser("~/.cache/brew-why")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")
CACHE_EXPIRY = 3600  # 1 hour

def clear_cache() -> None:
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        logger.info("Cache cleared.")

def get_package_size(pkg: str, cellar: str) -> int:
    pkg_dir = os.path.join(cellar, pkg)
    total_size = 0
    if not os.path.exists(pkg_dir):
        return 0
    for dirpath, _, filenames in os.walk(pkg_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp) and os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_info_cached(pkgs: List[str], progress: Progress = None) -> Dict[str, Any]:
    """Fetches formula info using ThreadPoolExecutor and caches it locally."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = {}
    
    if os.path.exists(CACHE_FILE):
        if time.time() - os.path.getmtime(CACHE_FILE) < CACHE_EXPIRY:
            try:
                with open(CACHE_FILE, 'r') as f:
                    cache = json.load(f)
            except json.JSONDecodeError:
                pass
                
    results = {}
    to_fetch = []
    
    for pkg in pkgs:
        if pkg in cache:
            results[pkg] = cache[pkg]
        else:
            to_fetch.append(pkg)
            
    if to_fetch:
        logger.debug(f"Fetching info for {len(to_fetch)} un-cached packages.")
        
        def fetch(pkg: str) -> Tuple[str, Any]:
            try:
                res = run_brew(["info", "--json=v2", pkg], json_output=True)
                return pkg, res['formulae'][0] if res and 'formulae' in res and res['formulae'] else None
            except Exception as e:
                logger.error(f"Failed to fetch {pkg}: {e}")
                return pkg, None

        task_id = None
        if progress:
            task_id = progress.add_task(f"Fetching {len(to_fetch)} packages...", total=len(to_fetch))
            
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch, pkg): pkg for pkg in to_fetch}
            for future in as_completed(futures):
                pkg, data = future.result()
                if data:
                    results[pkg] = data
                    cache[pkg] = data
                if progress and task_id is not None:
                    progress.advance(task_id)
                    
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
            
    return results

def get_outdated_cached() -> List[str]:
    """Fetches outdated packages."""
    # We can just fetch it directly, it's fairly fast, but let's keep it simple
    try:
        data = get_outdated()
        return [item['name'] for item in data.get('formulae', [])]
    except Exception:
        return []

def build_reverse_graph() -> Dict[str, List[str]]:
    """Builds a reverse dependency graph from brew deps --installed."""
    lines = get_all_deps()
    rev_graph = {}
    for line in lines:
        if not line or ':' not in line:
            continue
        pkg, deps_str = line.split(':', 1)
        pkg = pkg.strip()
        deps = [d.strip() for d in deps_str.split() if d.strip()]
        for d in deps:
            if d not in rev_graph:
                rev_graph[d] = []
            rev_graph[d].append(pkg)
    return rev_graph

def get_all_data(progress: Progress = None) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Retrieves and categorizes all installed packages into users, deps, and orphans."""
    all_pkgs = get_installed()
    leaves = set(get_leaves())
    cellar = get_cellar()
    outdated_list = set(get_outdated_cached())
    
    info = get_info_cached(all_pkgs, progress=progress)
    
    users = []
    deps = []
    orphans = []
    
    for pkg in all_pkgs:
        pkg_info = info.get(pkg, {})
        installed = pkg_info.get('installed', [{}])[0]
        requested = installed.get('installed_on_request', False)
        
        is_leaf = pkg in leaves
        is_orphan = is_leaf and not requested
        is_user = is_leaf and requested
        
        size_bytes = get_package_size(pkg, cellar)
        is_outdated = pkg in outdated_list
        
        item = {
            'name': pkg,
            'version': pkg_info.get('versions', {}).get('stable', 'unknown'),
            'time': installed.get('time'),
            'requested': requested,
            'deps': pkg_info.get('dependencies', []),
            'size': size_bytes,
            'outdated': is_outdated
        }
        
        if is_orphan:
            orphans.append(item)
        elif is_user:
            users.append(item)
        else:
            deps.append(item)
            
    return users, deps, orphans
