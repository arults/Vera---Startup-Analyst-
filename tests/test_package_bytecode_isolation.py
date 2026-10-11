"""Reproduce isolated-interpreter bytecode writes using synthetic packages only."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPERS = {
    "test_phase1d_multisource_package.py": "multisource-v1.0.3.1",
    "test_phase1d_customer_multisource_package.py": "multisource-v1.0.4.3",
}


class PackageBytecodeIsolationTests(unittest.TestCase):
    def fixture(self, root, wrapper, package_name, *, verifier_fails=False, test_fails=False):
        (root / "tests").mkdir(parents=True)
        shutil.copyfile(ROOT / "tests" / wrapper, root / "tests" / wrapper)
        package = root / "research" / package_name
        (package / "tests").mkdir(parents=True)
        (package / "manifest.json").write_text("{}\n")
        (package / "synthetic_module.py").write_text("VALUE = 42\n")
        (package / "verify_package.py").write_text(
            "import synthetic_module\nassert synthetic_module.VALUE == 42\n" +
            ("raise RuntimeError('synthetic verifier failure')\n" if verifier_fails else ""))
        (package / "tests/test_synthetic.py").write_text(
            "import sys, unittest\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
            "import synthetic_module\n"
            "class Synthetic(unittest.TestCase):\n"
            f"    def test_value(self): self.assertEqual(synthetic_module.VALUE, {41 if test_fails else 42})\n")
        return package

    def run_wrapper(self, root):
        return subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            text=True, capture_output=True, timeout=30)

    def test_fixed_wrappers_leave_synthetic_source_bytewise_unchanged(self):
        for wrapper, package in WRAPPERS.items():
            with self.subTest(wrapper=wrapper), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, wrapper, package)
                before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                result = self.run_wrapper(root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                self.assertEqual(before, after)
                self.assertFalse(list(root.rglob("*.pyc")))

    def test_isolated_flag_ignores_environment_until_explicit_B(self):
        for flags, expected_cache in ((["-I"], True), (["-I", "-B"], False)):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "synthetic_module.py").write_text("VALUE = 42\n")
                code = "import sys; sys.path.insert(0, sys.argv[1]); import synthetic_module"
                result = subprocess.run([sys.executable, *flags, "-c", code, str(root)],
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(bool(list(root.rglob("*.pyc"))), expected_cache)

    def test_verifier_failure_still_propagates(self):
        for wrapper, package in WRAPPERS.items():
            with self.subTest(wrapper=wrapper), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, wrapper, package, verifier_fails=True)
                result = self.run_wrapper(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("synthetic verifier failure", result.stderr)

    def test_nested_regression_failure_still_propagates(self):
        for wrapper, package in WRAPPERS.items():
            with self.subTest(wrapper=wrapper), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, wrapper, package, test_fails=True)
                result = self.run_wrapper(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("42 != 41", result.stderr)


if __name__ == "__main__":
    unittest.main()
