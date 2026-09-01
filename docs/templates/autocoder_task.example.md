# EXAMPLE: Add unit test for config parser

Mode: EDIT ALLOWED, tightly scoped.

Worktree:
/path/to/repo

Hard constraints:
- Stay inside this worktree only.
- Do not inspect sibling worktrees or parent directories.
- Do not read .env, secrets, API keys, credentials, or private config files.
- Do not commit.
- Do not push.
- Do not delete files.
- Keep the patch small.
- Do not modify production runtime behavior.
- Do not call any API outside normal tool usage.

Allowed files:
- tests/test_config_parser.py
- src/config_parser.py

Goal:
Add a unit test for the config parser's YAML loading function.
The test should cover valid, missing, and malformed YAML inputs.
Do not change any production code.

Required behavior:
- New test file or new test functions only.
- Use pytest conventions (test_ prefix, assert).
- Do not mock; use temp files for real file I/O.

Testing commands:
1. py -3.11 -m pytest tests/test_config_parser.py -q --tb=short

Additional notes:
- OpenCode failure is treated as task failure even if deterministic tests pass.

Return format:
- Summary of what was created/changed.
- Test results output.
```

> **Runner bootstrap sequence (first-time use)**  
> 1. Create/edit `scripts/jarvis_auto_task.ps1`  
> 2. Manually review runner logic  
> 3. Run `.\scripts\jarvis_auto_task.ps1 -TaskFile ".\docs\templates\autocoder_task.example.md" -PrecheckOnly`  
> 4. Manually verify precheck output  
> 5. Manually commit the runner  
> 6. Only after commit, use runner for real automation tasks
