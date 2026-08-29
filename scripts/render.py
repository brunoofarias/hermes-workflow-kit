#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from common import (
    ConfigurationError,
    ROOT,
    env_yaml,
    environment_requirements,
    load_json,
    render_template,
    validate_deployment,
    write_text,
    yaml_quote,
)


ROLE_DESCRIPTIONS = {
    "po": "Technical PO that investigates demand, derives acceptance criteria and validates architecture from a product perspective.",
    "architect": "Architect that designs solutions, materializes execution graphs and validates integrated conformance.",
    "dev": "Developer that implements approved architecture units, tests, self-reviews and opens pull requests.",
    "qa": "Independent QA that repeats tests and validates units and integrations before architecture conformance.",
}


def profile_values(config: dict, profile_name: str, dispatch: bool) -> dict[str, object]:
    deployment = config["deployment"]
    model = deployment["model"]
    limits = deployment["limits"]
    return {
        "PROFILE_NAME": profile_name,
        "MODEL_NAME": model["name"],
        "MODEL_PROVIDER": model["provider"],
        "REASONING_EFFORT": model["reasoning_effort"],
        "DISPATCH_IN_GATEWAY": "true" if dispatch else "false",
        "MAX_IN_PROGRESS": limits["max_in_progress"],
        "MAX_PER_PROFILE": limits["max_in_progress_per_profile"],
        "FAILURE_LIMIT": limits["failure_limit"],
    }


def distribution_values(config: dict, name: str, description: str, requirements: list[dict]) -> dict[str, object]:
    deployment = config["deployment"]
    return {
        "PROFILE_NAME": name,
        "VERSION": deployment["version"],
        "DESCRIPTION_YAML": yaml_quote(description),
        "HERMES_REQUIRES_YAML": yaml_quote(deployment["hermes_requires"]),
        "AUTHOR_YAML": yaml_quote(deployment["author"]),
        "LICENSE_YAML": yaml_quote(deployment["license"]),
        "ENV_REQUIRES": env_yaml(requirements),
    }


def write_profile(
    output: Path,
    config: dict,
    name: str,
    description: str,
    soul_template: str,
    soul_values: dict[str, object],
    requirements: list[dict],
    dispatch: bool,
    skill_values: dict[str, object] | None,
) -> None:
    profile_dir = output / "profiles" / name
    write_text(
        profile_dir / "distribution.yaml",
        render_template(
            ROOT / "templates/profile/distribution.yaml.tpl",
            distribution_values(config, name, description, requirements),
        ),
    )
    write_text(
        profile_dir / "config.yaml",
        render_template(ROOT / "templates/profile/config.yaml.tpl", profile_values(config, name, dispatch)),
    )
    write_text(
        profile_dir / "SOUL.md",
        render_template(ROOT / f"templates/soul/{soul_template}.md.tpl", soul_values),
    )
    if skill_values is not None:
        write_text(
            profile_dir / "skills/workflow-handoff/SKILL.md",
            render_template(ROOT / "templates/skill/SKILL.md.tpl", skill_values),
        )


def render(config_path: Path, output: Path, force: bool = False) -> Path:
    config = load_json(config_path)
    validate_deployment(config)
    if output.exists():
        if not force:
            raise ConfigurationError(f"output already exists: {output}; pass --force to replace generated output")
        marker = output / "generated-manifest.json"
        if not marker.exists() and output.parent.resolve() != (ROOT / "build").resolve():
            raise ConfigurationError(f"refusing to replace unrecognized directory: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    deployment = config["deployment"]
    orchestrator = f"{deployment['slug']}-orchestrator"
    board_rules: list[str] = []
    profile_manifest: list[dict] = []
    boards_manifest: list[dict] = []

    for org in config["organizations"]:
        prefix = org["profile_prefix"]
        profiles = {role: f"{prefix}-{role}" for role in ("po", "architect", "dev", "qa")}
        board_rules.append(
            f"- Board `{org['board']['slug']}` ({org['display_name']}): "
            + ", ".join(f"`{name}`" for name in profiles.values())
            + "."
        )
        boards_manifest.append({**org["board"], "organization_slug": org["slug"]})
        requirements = environment_requirements(org)
        common = {
            "ORG_NAME": org["display_name"],
            "BOARD_SLUG": org["board"]["slug"],
            "PO_PROFILE": profiles["po"],
            "ARCHITECT_PROFILE": profiles["architect"],
            "DEV_PROFILE": profiles["dev"],
            "QA_PROFILE": profiles["qa"],
            "REVIEWER_LABEL": deployment["reviewer_label"],
            "AGENT_LANGUAGE": deployment["agent_language"],
        }
        skill_values = {"ORG_NAME": org["display_name"], "BOARD_SLUG": org["board"]["slug"]}
        for role, name in profiles.items():
            write_profile(
                output,
                config,
                name,
                f"{ROLE_DESCRIPTIONS[role]} Organization: {org['display_name']}.",
                role,
                common,
                requirements,
                False,
                skill_values,
            )
            profile_manifest.append(
                {
                    "name": name,
                    "role": role,
                    "organization_slug": org["slug"],
                    "board_slug": org["board"]["slug"],
                    "path": f"profiles/{name}",
                    "environment_requirements": requirements,
                }
            )

    orchestrator_values = {
        "DEPLOYMENT_NAME": deployment["display_name"],
        "BOARD_RULES": "\n".join(board_rules),
        "REVIEWER_LABEL": deployment["reviewer_label"],
        "AGENT_LANGUAGE": deployment["agent_language"],
        "MAX_IN_PROGRESS": deployment["limits"]["max_in_progress"],
        "MAX_PER_PROFILE": deployment["limits"]["max_in_progress_per_profile"],
    }
    write_profile(
        output,
        config,
        orchestrator,
        f"Neutral dispatcher for {deployment['display_name']} with human-only architecture and final reviews.",
        "orchestrator",
        orchestrator_values,
        [],
        True,
        None,
    )
    profile_manifest.insert(
        0,
        {
            "name": orchestrator,
            "role": "orchestrator",
            "organization_slug": None,
            "board_slug": None,
            "path": f"profiles/{orchestrator}",
            "environment_requirements": [],
        },
    )
    manifest = {
        "schema_version": 1,
        "deployment_slug": deployment["slug"],
        "version": deployment["version"],
        "orchestrator": orchestrator,
        "profiles": profile_manifest,
        "boards": boards_manifest,
    }
    write_text(output / "generated-manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    board_names = ", ".join("`" + board["slug"] + "`" for board in boards_manifest)
    write_text(
        output / "README.md",
        "# Generated Hermes deployment\n\n"
        "Generated from Hermes Workflow Kit. Do not add credentials to this directory.\n\n"
        f"Orchestrator: `{orchestrator}`\n\n"
        f"Boards: {board_names}\n",
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render portable Hermes profile distributions")
    parser.add_argument("--config", type=Path, default=ROOT / "deployment.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_json(args.config)
        default_output = ROOT / "build" / str(config.get("deployment", {}).get("slug", "deployment"))
        output = args.output or default_output
        rendered = render(args.config, output, args.force)
    except ConfigurationError as exc:
        print(f"error: {exc}")
        return 2
    print(f"Rendered deployment: {rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
