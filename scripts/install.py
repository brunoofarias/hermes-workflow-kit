#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path

from common import ConfigurationError, load_json


def run(command: list[str], dry_run: bool, capture: bool = False) -> subprocess.CompletedProcess[str] | None:
    print("+ " + shlex.join(command))
    if dry_run:
        return None
    return subprocess.run(command, check=True, text=True, capture_output=capture)


def dotenv_value(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_local_envs(build: Path, manifest: dict, local_path: Path, profiles_root: Path, dry_run: bool) -> None:
    local = load_json(local_path)
    organizations = local.get("organizations")
    if not isinstance(organizations, dict):
        raise ConfigurationError("local file must contain an organizations object")
    for profile in manifest["profiles"]:
        org_slug = profile.get("organization_slug")
        if not org_slug:
            continue
        values = organizations.get(org_slug)
        if not isinstance(values, dict):
            raise ConfigurationError(f"local values missing for organization: {org_slug}")
        requirements = profile.get("environment_requirements", [])
        allowed = {item["name"] for item in requirements}
        unknown = set(values) - allowed
        if unknown:
            raise ConfigurationError(f"unknown local variables for {org_slug}: {', '.join(sorted(unknown))}")
        missing = [item["name"] for item in requirements if item["required"] and not str(values.get(item["name"], "")).strip()]
        if missing:
            raise ConfigurationError(f"required local variables missing for {org_slug}: {', '.join(missing)}")
        env_path = profiles_root / profile["name"] / ".env"
        print(f"+ write mode 0600 {env_path} ({len(values)} values; values hidden)")
        if dry_run:
            continue
        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for key in sorted(values):
            value = values[key]
            if not isinstance(value, str):
                raise ConfigurationError(f"local variable {org_slug}.{key} must be a string")
            lines.append(f"{key}={dotenv_value(value)}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(env_path, 0o600)


def install(args: argparse.Namespace) -> None:
    build = args.build.resolve()
    manifest = load_json(build / "generated-manifest.json")
    for profile in manifest["profiles"]:
        command = [args.hermes, "profile", "install", str(build / profile["path"]), "--alias", "-y"]
        if args.force:
            command.append("--force")
        run(command, args.dry_run)

    if args.local:
        write_local_envs(build, manifest, args.local.resolve(), args.profiles_root.expanduser(), args.dry_run)

    if not args.no_boards:
        existing: set[str] = set()
        if not args.dry_run:
            result = run(
                [args.hermes, "--profile", manifest["orchestrator"], "kanban", "boards", "list", "--json"],
                False,
                capture=True,
            )
            assert result is not None
            existing = {item["slug"] for item in json.loads(result.stdout)}
        for board in manifest["boards"]:
            if board["slug"] in existing:
                print(f"= board already exists: {board['slug']}")
                continue
            run(
                [
                    args.hermes,
                    "--profile",
                    manifest["orchestrator"],
                    "kanban",
                    "boards",
                    "create",
                    board["slug"],
                    "--name",
                    board["name"],
                    "--description",
                    board["description"],
                    "--icon",
                    board["icon"],
                    "--color",
                    board["color"],
                ],
                args.dry_run,
            )

    if args.gateway:
        run(
            [
                args.hermes,
                "--profile",
                manifest["orchestrator"],
                "gateway",
                "install",
                "--force",
                "--start-now",
                "--start-on-login",
            ],
            args.dry_run,
        )

    print("Installation plan completed" if args.dry_run else "Installation completed")
    if not args.local:
        print("Fill each installed profile's .env.EXAMPLE as .env, then authenticate providers locally.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install a generated Hermes workflow deployment")
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--hermes", default="hermes")
    parser.add_argument("--profiles-root", type=Path, default=Path.home() / ".hermes/profiles")
    parser.add_argument("--local", type=Path)
    parser.add_argument("--force", action="store_true", help="update existing profiles while preserving Hermes user data")
    parser.add_argument("--gateway", action="store_true", help="install/start the orchestrator gateway service")
    parser.add_argument("--no-boards", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        install(args)
    except (ConfigurationError, subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
