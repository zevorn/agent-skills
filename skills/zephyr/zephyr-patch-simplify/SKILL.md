---
# SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission
# SPDX-License-Identifier: MIT
name: zephyr-patch-simplify
description: >-
  Simplify Zephyr code and changes by reducing LOC, state space, dead code,
  redundant abstractions, and duplicated facts while preserving required
  behavior. Use for cleanup, deduplication, deep-module refactoring,
  single-source-of-truth work, or narrowing over-generalized designs.
---

# Zephyr Patch Simplify

## Audit workflow

For every non-trivial task that writes to the workspace, choose a stable task
slug and keep agent-only records under:

```text
.zephyr-skills/<agent-task>/
├── audit.md        # Baseline, decisions, evidence, verification, and gaps
├── commands.md     # Redacted commands, working directories, and results
├── scripts/        # Intermediate debug documents, scripts, and harnesses
├── output/         # Non-Zephyr dependencies and temporary binaries
└── logs/           # Decisive build, test, runtime, or diagnostic logs
```

Put every generated intermediate debugging document, debug script, and
scaffolding or harness script, including Bash and Python scripts, under
`scripts/`, never in a build directory. Put non-Zephyr third-party source or
libraries acquired solely for the agent's task, and temporary binaries produced
by agent-only probes or tools, under `output/`. Do not copy normal Zephyr build
artifacts there. Keep other agent plans and temporary evidence in the same task
directory. In a Git worktree, add
`/.zephyr-skills/` to the repository-local exclude file returned by
`git rev-parse --git-path info/exclude` before writing audit artifacts. Preserve
existing entries, avoid duplicates, and verify before handoff that
`git status --short` contains no `.zephyr-skills/` paths. Keep Zephyr-native
build trees, binaries, and test outputs separate: honor a user-specified path,
otherwise use defaults such as configured `build.dir-fmt`, `build/`, or
`twister-out/`. Record the effective paths, do not stage `.zephyr-skills/`
unless requested, and report the task directory and unresolved gaps at handoff.

## Set the goal

Treat required behavior and soundness as hard constraints. Within that
boundary, optimize in this order:

1. Reduce source LOC and measure the result with `cloc`.
2. Reduce states, modes, fallbacks, and edge paths.
3. Merge equivalent abstractions and duplicated sources of truth.
4. Generalize only around demonstrated variation.

Prefer removing concepts, stored facts, states, or public APIs over moving the
same complexity into helpers. Do not count formatting or function extraction
as simplification.

## Establish the baseline

1. Record the comparison base, worktree status, scope, and current LOC. Do not
   rewrite or discard user changes.
2. List the behavior and configurations that must remain supported.
3. Inventory source files, public APIs, Kconfig, CMake, devicetree, tests,
   samples, and documentation in scope.
4. Trace production consumers with `rg`, build metadata, and local history.
   Treat a test-only consumer as evidence of a rule, not product use.
5. Use the same `cloc` scope and exclusions before and after. Exclude build
   output, vendored code, and temporary task artifacts.

## Find the excess model

Use these signals:

- A fact stored twice indicates a missing single source of truth. Keep one
  declaration and derive the other forms.
- Repeated control flow with real variation may be under-generalized. Share
  the stable policy, not unrelated mechanisms.
- Callbacks, registries, dynamic lifetime, or plugin selection with one real
  mode indicate over-generalization.
- A wrapper that mainly forwards calls or a descriptor that owns no behavior
  is a shallow module. Move policy, state, validation, and mechanism behind a
  smaller interface.
- Types, fields, or headers introduced before a consumer enlarge the model
  without explaining it. Introduce them with their first use and narrow their
  valid values.
- Compatibility and fallback paths are debt unless a current requirement
  depends on them.

Search declarations and uses across source, configuration, build files,
devicetree, tests, documentation, and history before calling code dead. A
public symbol with no production consumer is a deletion candidate, not proof.

## Choose an action

Classify each candidate as:

- **Delete**: no required behavior or production consumer depends on it.
- **Merge**: several modules split one invariant or workflow.
- **Deepen**: a wide interface leaks work that one module should own.
- **Derive**: repeated facts can come from one authoritative input.
- **Narrow**: unused modes or states can leave the supported contract.
- **Keep**: removing it would weaken required behavior or correctness.

Prefer the option that removes the most concepts with the fewest new rules.
Preserve ownership, lifetime, concurrency, error handling, and isolation
invariants while reducing code.

## Make the change

- For review-only requests, stop after evidence-backed findings and a proposed
  reduction plan.
- When implementation is requested, apply the smallest coherent reduction and
  preserve unrelated worktree changes.
- Remove orphaned includes, symbols, configuration, build entries, tests, and
  documentation with the deleted model.
- Do not add compatibility layers or generic helpers to make deletion easier.
- Do not rewrite history unless the user requests it.

## Verify and report

1. Re-run the affected builds and tests needed to prove retained behavior.
2. Run `git diff --check` and applicable source-style checks.
3. Search for orphaned consumers and stale configuration after deletion.
4. Re-run `cloc` with the exact baseline scope.

Report the outcome, baseline and final LOC, removed concepts, retained
behavior, verification evidence, and remaining gaps. Never present a lower LOC
as success when required behavior or correctness is unverified.
