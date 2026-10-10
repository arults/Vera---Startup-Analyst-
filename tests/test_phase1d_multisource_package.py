"""Run the versioned evidence package in a separate interpreter during root CI."""
from pathlib import Path
import subprocess
import sys
import unittest


class MultisourcePackageTests(unittest.TestCase):
    def test_versioned_package_integrity_and_regressions(self):
        package = Path(__file__).resolve().parents[1] / "research" / "multisource-v1.0.3.1"
        self.assertTrue((package / "manifest.json").is_file(), "Evidence package is missing")
        for arguments in (
            ["verify_package.py"],
            ["-I", "-m", "unittest", "discover", "-s", "tests", "-v"],
        ):
            result = subprocess.run(
                [sys.executable, *arguments], cwd=package,
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
