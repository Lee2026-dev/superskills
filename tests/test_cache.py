import json
import time
from pathlib import Path
from skills_inventory.cache import CacheManager

def test_cache_save_load(tmp_path):
    cache_file = tmp_path / "cache.json"
    cm = CacheManager(cache_file)
    cm.set("/path/to/skill", {"mtime": 12345.0, "hash": "abc"})
    cm.save()
    
    cm2 = CacheManager(cache_file)
    assert cm2.get("/path/to/skill") == {"mtime": 12345.0, "hash": "abc"}

def test_cache_ttl(tmp_path):
    cache_file = tmp_path / "cache.json"
    cm = CacheManager(cache_file)
    path = "/path/to/skill"
    
    # Not expired
    cm.set(path, {"last_git_fetch_ts": time.time() - 100})
    assert not cm.is_git_fetch_expired(path, ttl_seconds=600)
    
    # Expired
    cm.set(path, {"last_git_fetch_ts": time.time() - 1000})
    assert cm.is_git_fetch_expired(path, ttl_seconds=600)

def test_cache_missing_entry(tmp_path):
    cache_file = tmp_path / "cache.json"
    cm = CacheManager(cache_file)
    assert cm.is_git_fetch_expired("/nonexistent") is True
