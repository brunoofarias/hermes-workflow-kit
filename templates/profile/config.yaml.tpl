model:
  default: {{MODEL_NAME}}
  provider: {{MODEL_PROVIDER}}
agent:
  reasoning_effort: {{REASONING_EFFORT}}
  max_turns: 500
terminal:
  env_type: local
  cwd: "."
  home_mode: {{HOME_MODE}}
  lifetime_seconds: 300
kanban:
  dispatch_in_gateway: {{DISPATCH_IN_GATEWAY}}
  review_dispatch: false
  max_in_progress: {{MAX_IN_PROGRESS}}
  max_in_progress_per_profile: {{MAX_PER_PROFILE}}
  auto_promote_children: true
  failure_limit: {{FAILURE_LIMIT}}
