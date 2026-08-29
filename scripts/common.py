#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENV_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")

SECRET_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)

CORE_ENV_REQUIREMENTS = (
    {
        "name": "HWF_WORKSPACE_ROOTS",
        "description": "Allowed local workspace roots for this organization; never use their common parent as an implicit scope",
        "required": True,
    },
    {
        "name": "HWF_REPOSITORY_SCOPES",
        "description": "Allowed Git organizations, groups or namespaces for this organization",
        "required": True,
    },
    {
        "name": "HWF_TOOL_CONTEXT",
        "description": "Local instructions or paths selecting isolated Git, cloud and executor identities",
        "required": True,
    },
    {
        "name": "HWF_DEPLOY_POLICY",
        "description": "Actions reserved to humans and the deployment policy for this organization",
        "required": True,
    },
    {
        "name": "HWF_SOURCE_SYSTEM",
        "description": "External ticket/source system policy and whether agents may update it",
        "required": True,
    },
)


class ConfigurationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"top-level JSON value must be an object: {path}")
    return value


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def detect_secret(value: Any) -> str | None:
    for text in iter_strings(value):
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
    return None


def require_string(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def require_positive_int(mapping: dict[str, Any], key: str, context: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigurationError(f"{context}.{key} must be a positive integer")
    return value


def environment_requirements(org: dict[str, Any]) -> list[dict[str, Any]]:
    combined = [dict(item) for item in CORE_ENV_REQUIREMENTS]
    extras = org.get("additional_environment_requirements", [])
    if not isinstance(extras, list):
        raise ConfigurationError(
            f"organizations[{org.get('slug', '?')}].additional_environment_requirements must be an array"
        )
    combined.extend(extras)
    seen: set[str] = set()
    for index, item in enumerate(combined):
        if not isinstance(item, dict):
            raise ConfigurationError(f"environment requirement #{index + 1} must be an object")
        name = require_string(item, "name", f"environment requirement #{index + 1}")
        if not ENV_RE.fullmatch(name):
            raise ConfigurationError(f"invalid environment variable name: {name}")
        if name in seen:
            raise ConfigurationError(f"duplicate environment requirement: {name}")
        seen.add(name)
        require_string(item, "description", f"environment requirement {name}")
        required = item.get("required")
        if not isinstance(required, bool):
            raise ConfigurationError(f"environment requirement {name}.required must be boolean")
        unexpected = set(item) - {"name", "description", "required"}
        if unexpected:
            raise ConfigurationError(
                f"environment requirement {name} has unsupported fields: {', '.join(sorted(unexpected))}; values belong in a local file"
            )
    return combined


def validate_deployment(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise ConfigurationError("schema_version must be 1")
    if detect_secret(config):
        raise ConfigurationError("the deployment manifest appears to contain a credential; store values in deployment.local.json")

    deployment = config.get("deployment")
    if not isinstance(deployment, dict):
        raise ConfigurationError("deployment must be an object")
    deployment_slug = require_string(deployment, "slug", "deployment")
    if not SLUG_RE.fullmatch(deployment_slug):
        raise ConfigurationError("deployment.slug must be kebab-case")
    require_string(deployment, "display_name", "deployment")
    version = require_string(deployment, "version", "deployment")
    if not VERSION_RE.fullmatch(version):
        raise ConfigurationError("deployment.version must be semantic version syntax")
    require_string(deployment, "author", "deployment")
    require_string(deployment, "license", "deployment")
    require_string(deployment, "hermes_requires", "deployment")
    require_string(deployment, "reviewer_label", "deployment")
    require_string(deployment, "agent_language", "deployment")

    model = deployment.get("model")
    if not isinstance(model, dict):
        raise ConfigurationError("deployment.model must be an object")
    require_string(model, "provider", "deployment.model")
    require_string(model, "name", "deployment.model")
    effort = require_string(model, "reasoning_effort", "deployment.model")
    if effort not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
        raise ConfigurationError("deployment.model.reasoning_effort is unsupported")

    limits = deployment.get("limits")
    if not isinstance(limits, dict):
        raise ConfigurationError("deployment.limits must be an object")
    require_positive_int(limits, "max_in_progress", "deployment.limits")
    require_positive_int(limits, "max_in_progress_per_profile", "deployment.limits")
    require_positive_int(limits, "failure_limit", "deployment.limits")

    organizations = config.get("organizations")
    if not isinstance(organizations, list) or not organizations:
        raise ConfigurationError("organizations must be a non-empty array")
    org_slugs: set[str] = set()
    prefixes: set[str] = set()
    board_slugs: set[str] = set()
    for index, org in enumerate(organizations):
        context = f"organizations[{index}]"
        if not isinstance(org, dict):
            raise ConfigurationError(f"{context} must be an object")
        slug = require_string(org, "slug", context)
        prefix = require_string(org, "profile_prefix", context)
        if not SLUG_RE.fullmatch(slug) or not SLUG_RE.fullmatch(prefix):
            raise ConfigurationError(f"{context} slug and profile_prefix must be kebab-case")
        if slug in org_slugs:
            raise ConfigurationError(f"duplicate organization slug: {slug}")
        if prefix in prefixes:
            raise ConfigurationError(f"duplicate profile prefix: {prefix}")
        org_slugs.add(slug)
        prefixes.add(prefix)
        require_string(org, "display_name", context)
        board = org.get("board")
        if not isinstance(board, dict):
            raise ConfigurationError(f"{context}.board must be an object")
        board_slug = require_string(board, "slug", f"{context}.board")
        if not SLUG_RE.fullmatch(board_slug):
            raise ConfigurationError(f"{context}.board.slug must be kebab-case")
        if board_slug in board_slugs:
            raise ConfigurationError(f"duplicate board slug: {board_slug}")
        board_slugs.add(board_slug)
        require_string(board, "name", f"{context}.board")
        require_string(board, "description", f"{context}.board")
        icon = require_string(board, "icon", f"{context}.board")
        if len(icon) > 8:
            raise ConfigurationError(f"{context}.board.icon is too long")
        color = require_string(board, "color", f"{context}.board")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ConfigurationError(f"{context}.board.color must be #RRGGBB")
        environment_requirements(org)


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_template(path: Path, values: dict[str, Any]) -> str:
    content = path.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{{" + key + "}}", str(value))
    unresolved = sorted(set(PLACEHOLDER_RE.findall(content)))
    if unresolved:
        raise ConfigurationError(f"unresolved placeholders in {path}: {', '.join(unresolved)}")
    return content


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def env_yaml(requirements: list[dict[str, Any]]) -> str:
    if not requirements:
        return ""
    lines = ["env_requires:"]
    for item in requirements:
        lines.extend(
            [
                f"  - name: {item['name']}",
                f"    description: {yaml_quote(item['description'])}",
                f"    required: {'true' if item['required'] else 'false'}",
            ]
        )
    return "\n".join(lines)
