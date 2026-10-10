"""Default-discovery shim for the versioned bounded research-admission package."""
from pathlib import Path
import importlib.util

def load_tests(loader, tests, pattern):
    root = Path(__file__).resolve().parents[1]
    path = root / 'data/phase1d/cp10/canonical-admission-v1/tests/test_admission_adapter.py'
    spec = importlib.util.spec_from_file_location('bounded_admission_tests', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)
