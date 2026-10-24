# Adopting

Design notes for moving an existing tool onto `heimdall`, and for keeping each tool on a known version.

---

## Moving a Tool Over

A tool moves over on its own branch. The goal is identical behaviour, so every step is checkable.

1. Add `heimdall` as a dependency, pinned to a commit (see [Pinning](#pinning)).
2. Replace the import of the terminal module of the tool with `from heimdall import shell_interface`; call sites stay unchanged.
3. If the tool has flags beyond `--dry-run`, subclass `Config` with them.
4. Replace the entry point of the tool with a `ToolSpec` and a call to `run_cli`.
5. Delete the copy of the terminal layer that the tool kept.
6. Check: the tests of the tool pass unchanged, and the help output before and after lists the same commands, flags, and help text in the same order.

Some output changes by design and is not a regression: help separators become single tabs, the legend is generated, and printed commands are quoted where an argument contains spaces. A tool whose copy of the layer is older than this package also gains the newer features (dry-run styles, read-only runners) as part of the move.

A tool that uses its own plain-text logging moves its narration onto the output functions; anything specific to its subject, such as file actions, stays in the tool and calls the command runners.

---

## Pinning

| Rule | Detail | State |
|---|---|---|
| Pin by commit | each tool pins `heimdall` to a commit under `[tool.uv.sources]`, so a change here reaches a tool only when its pin moves | decided |
| Local development | a tool can override the pin with a path to a local checkout while developing against an unreleased change | decided |
| Changes here | additive where possible; a change that breaks a signature says so in its commit message | decided |
