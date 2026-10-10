"""Run customer evidence package checks without sharing modules with older versions."""
from pathlib import Path
import subprocess
import sys
import unittest


class CustomerMultisourcePackageTests(unittest.TestCase):
    def test_customer_package_integrity_and_regressions(self):
        package = Path(__file__).resolve().parents[1] / "research" / "multisource-v1.0.4.3"
        self.assertTrue((package / "manifest.json").is_file(), "Customer evidence package is missing")
        # -I removes ambient Python paths. Add this selected package explicitly;
        # its first test imports evidence before the older test-path bootstrap.
        bootstrap = (
            "import runpy, sys; from pathlib import Path; "
            "sys.path.insert(0, str(Path.cwd())); "
        )
        commands = (
            bootstrap + "runpy.run_path('verify_package.py', run_name='__main__')",
            bootstrap + "sys.argv = ['unittest', 'discover', '-s', 'tests', '-v']; "
            "runpy.run_module('unittest', run_name='__main__')",
        )
        for command in commands:
            result = subprocess.run(
                [sys.executable, "-I", "-c", command], cwd=package,
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
