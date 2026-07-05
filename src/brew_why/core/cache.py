import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

from rich.progress import Progress

from brew_why.core.brew import run_brew

logger = logging.getLogger("brew_why")

CACHE_DIR = os.path.expanduser("~/.cache/brew-why")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")
CACHE_EXPIRY = 3600  # 1 hour

def clear_cache() -> None:
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        logger.info("Cache cleared.")

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
