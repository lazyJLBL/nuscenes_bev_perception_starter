import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.path_utils import resolve_project_path

def test_resolve_project_path():
    # Relative path should be resolved
    resolved = resolve_project_path("data/nuscenes")
    assert os.path.isabs(resolved)
    
    # Absolute path should remain absolute
    if os.name == 'nt':
        abs_path = "C:\\data\\nuscenes"
    else:
        abs_path = "/data/nuscenes"
        
    assert resolve_project_path(abs_path) == abs_path
