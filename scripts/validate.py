#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import ConfigurationError, PLACEHOLDER_RE, ROOT, SECRET_PATTERNS, load_json, validate_deployment


PERSONAL_PATH_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
)
TEXT_SUFFIXES = {"", ".md", ".json", ".yaml", ".yml", ".py", ".tpl", ".txt"}


def source_files(root: Path):
    excluded = {".git", "build", "dist", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.name in {"deployment.json", "deployment.local.json"} or path.name.endswith(".local.json"):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in {".gitignore"}:
            yield path


def validate_source(root: Path) -> list[str]:
    errors: list[str] = []
    for path in source_files(root):
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {path.relative_to(root)}")
        for pattern in PERSONAL_PATH_PATTERNS:
            if pattern.search(text):
                errors.append(f"personal absolute path in {path.relative_to(root)}")
    return errors


def validate_build(build: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = build / "generated-manifest.json"
    if not manifest_path.exists():
        return [f"missing {manifest_path}"]
    manifest = load_json(manifest_path)
    profiles = manifest.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        return ["generated manifest has no profiles"]
    orchestrator_count = 0
    for item in profiles:
        profile_dir = build / item["path"]
        for required in ("distribution.yaml", "config.yaml", "SOUL.md"):
            path = profile_dir / required
            if not path.exists():
                errors.append(f"missing {path.relative_to(build)}")
                continue
            text = path.read_text(encoding="utf-8")
            if PLACEHOLDER_RE.search(text):
                errors.append(f"unresolved placeholder in {path.relative_to(build)}")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"possible secret in {path.relative_to(build)}")
        config_path = profile_dir / "config.yaml"
        if config_path.exists():
            config_text = config_path.read_text(encoding="utf-8")
            if "review_dispatch: false" not in config_text:
                errors.append(f"human-only review disabled in {config_path.relative_to(build)}")
            if item["role"] == "orchestrator":
                orchestrator_count += 1
                if "dispatch_in_gateway: true" not in config_text:
                    errors.append("orchestrator dispatcher is disabled")
            elif "dispatch_in_gateway: false" not in config_text:
                errors.append(f"worker dispatcher enabled in {config_path.relative_to(build)}")
        if item["role"] != "orchestrator":
            skill = profile_dir / "skills/workflow-handoff/SKILL.md"
            if not skill.exists():
                errors.append(f"missing workflow skill in {profile_dir.relative_to(build)}")
    if orchestrator_count != 1:
        errors.append(f"expected one orchestrator, found {orchestrator_count}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a Hermes Workflow Kit source or deployment")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--build", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    try:
        if args.source:
            errors.extend(validate_source(args.source.resolve()))
        if args.config:
            validate_deployment(load_json(args.config))
        if args.build:
            errors.extend(validate_build(args.build.resolve()))
        if not any((args.source, args.config, args.build)):
            errors.extend(validate_source(ROOT))
            validate_deployment(load_json(ROOT / "deployment.example.json"))
    except ConfigurationError as exc:
        errors.append(str(exc))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 2
    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
