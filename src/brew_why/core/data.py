import os
from typing import List, Dict, Any, Tuple

from rich.progress import Progress

from brew_why.core.brew import get_installed, get_leaves, get_cellar, get_all_deps, get_outdated
from brew_why.core.cache import get_info_cached

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

def get_outdated_cached() -> List[str]:
    """Fetches outdated packages."""
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
