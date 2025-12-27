import os
import json
import logging
import re
import warnings
from datetime import datetime

logger = logging.getLogger("CoreUtils")

def load_json_list(filename):
    """Loads a list of strings from a JSON file in the data/ directory."""
    try:
        path = os.path.join("data", filename)
        if not os.path.exists(path):
            logger.warning(f"Config file not found: {path}")
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        return []

# REMOVED: normalize_user_string() - Use core.usernames.UsernameNormalizer.normalize() instead

def clean_int(val):
    try:
        return int(val)
    except:
        return 0

def get_unique_filename(filename):
    """
    Returns a unique filename if the target already exists (appends timestamp).
    Useful for avoiding PermissionError when Excel is open.
    """
    if not os.path.exists(filename):
        return filename
    
    # Try to rename? No, just return a new name to write to.
    # Check if we can write to it? 
    try:
        with open(filename, 'a'):
            pass
        return filename # It's writable
    except PermissionError:
        base, ext = os.path.splitext(filename)
        new_name = f"{base}_{int(datetime.now().timestamp())}{ext}"
        logger.warning(f"File {filename} is locked. Using {new_name} instead.")
        return new_name
    except Exception:
        return filename
