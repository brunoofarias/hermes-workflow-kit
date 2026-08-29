from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RenderTests(unittest.TestCase):
    def run_script(self, script: str, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_example_renders_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "deployment"
            self.run_script(
                "render.py",
                "--config",
                str(ROOT / "deployment.example.json"),
                "--output",
                str(output),
            )
            manifest = json.loads((output / "generated-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["orchestrator"], "example-engineering-orchestrator")
            self.assertEqual(len(manifest["profiles"]), 5)
            self.assertEqual(len(manifest["boards"]), 1)
            self.run_script("validate.py", "--build", str(output))
            dry_run = self.run_script("install.py", "--build", str(output), "--dry-run", "--gateway")
            self.assertIn("gateway install", dry_run.stdout)
            self.assertIn("kanban boards create", dry_run.stdout)

    def test_secret_like_value_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = json.loads((ROOT / "deployment.example.json").read_text(encoding="utf-8"))
            config["unexpected_credential"] = "gh" + "p_" + "123456789012345678901234567890"
            path = Path(temp) / "deployment.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            result = self.run_script("validate.py", "--config", str(path), expected=2)
            self.assertIn("credential", result.stdout)

    def test_duplicate_profile_prefix_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = json.loads((ROOT / "deployment.example.json").read_text(encoding="utf-8"))
            second = json.loads(json.dumps(config["organizations"][0]))
            second["slug"] = "another-company"
            second["board"]["slug"] = "another-company"
            second["board"]["name"] = "Another Company"
            config["organizations"].append(second)
            path = Path(temp) / "deployment.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            result = self.run_script("validate.py", "--config", str(path), expected=2)
            self.assertIn("duplicate profile prefix", result.stdout)


if __name__ == "__main__":
    unittest.main()
