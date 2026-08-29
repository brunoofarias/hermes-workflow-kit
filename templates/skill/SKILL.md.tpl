---
name: workflow-handoff
description: Enforce the generated PO, Architecture, DEV and QA handoff protocol for board {{BOARD_SLUG}}.
---

# Workflow handoff protocol

Use this protocol only on board `{{BOARD_SLUG}}` for {{ORG_NAME}}.

Every task handoff must preserve:

- `stage`
- organization/tenant
- parent architecture task id
- `unit_id` when applicable
- workspace and repository
- executor/model used
- acceptance criteria and their status
- evidence, commands and exact commits
- PR links
- dependency and return task ids
- residual risks and required human action

Never infer permission to cross an organization boundary. Never move a task to review when required validation is missing. Only architecture approval and final integrated delivery use human review.

Before the first use of Git, cloud, deployment, ticketing, or executor tooling in every task, run the identity checks specified by `HWF_TOOL_CONTEXT`. Compare the effective account, organization and tenant with the task organization. If a check fails, is unavailable, or returns a different identity, block the task and request human intervention. Never log in, refresh credentials, or fall back to another identity autonomously.
