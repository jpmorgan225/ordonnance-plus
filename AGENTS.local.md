# Ordonnance+ — settings and conventions

## Pipeline settings

```
Merge mode:        local
Target branch:     master
Plan validation:   human
Ship confirmation: human
Story track:       auto
Flow threshold:    2
Design source:     internal
Design skill:      —
Design tool:       —
Test budget:       25
Verification mode: record
Full suite:        execute-end
E2E stage:         —
E2E scope:         nominal
E2E browsers:      —
Build stage:       —
Issue tracker:     —
Worktree root:     .worktrees/
```

## Project commands

```
Package manager:   pip
Test:              ./.venv/bin/python3 -m unittest discover -s tests
Typecheck:         —
E2E:               —
Build:             —
```

## Project conventions
- Monolithe FastAPI + Pydantic v2 + SQLite + Web UI Single-Page.
- Règle médicale fail-closed : aucune déduction de posologie, blocage si confiance douteuse.
