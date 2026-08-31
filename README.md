<div align="center">

<h1>Popper</h1>

<img src=".github/assets/logo.svg" alt="Popper logo: two agent-behavior cards, one crossed out in red, with the survivor feeding a rule" width="96">

**A local CLAUDE.md behavior compiler.**

<img src=".github/assets/hero.svg" alt="Fix the bug becomes an A/B behavior test: Should I start is crossed out, Fixed and tests pass survives, and Act first report after becomes the rule" width="920">

**Cross out the agent behavior you never want again. Keep the rule.**

[한국어](README.ko.md) · [Live explanation](https://brnyxx.github.io/popper/)

</div>

Popper shows two concrete ways your coding agent could behave. You cross out the wrong one; after 15 cross-outs, Popper compiles the surviving choices into local rules that Claude Code can load from `CLAUDE.md`.

> **Korean-first v1:** the session UI and generated rule text are Korean. The English README and site explain the product and installation honestly; an English runtime pack is not shipped yet.

**v1.3.0 · Python 3.10–3.14 · MIT · zero third-party Python runtime packages · zero runtime LLM, telemetry, or external-network calls**

## The whole product in one example

You keep asking Claude Code to fix a bug. It keeps stopping to ask for permission.

1. **Request:** `Fix the bug.`
2. **Two behaviors appear:** `Should I start?` / `Fixed. Tests pass. Here is what changed.`
3. **You cross out:** `Should I start?`
4. **Popper compiles:** `먼저 실행한 뒤 변경 내역을 요약해 보고한다.` — act first, then report the change.
5. **You enable one owned import line.** In a new Claude Code session, repeat the request and verify that the agent follows the compiled rule.

The “next response” above is the behavior contract written to `POPPER.md`, not a model benchmark or a guarantee about every model run. Popper makes the instruction explicit, local, inspectable, and reversible.

<details>
<summary><strong>Watch the real 15-cross-out browser session</strong> (1.6 MB GIF)</summary>
<br>
<img src=".github/assets/demo.gif" alt="The real Popper browser UI progressing from zero to fifteen cross-outs, compiling local rules, and completing the session" width="860">
</details>

## What 15 cross-outs specify

Popper is useful when an agent repeatedly:

- asks permission instead of taking an obvious next step;
- expands or shrinks scope in a way you dislike;
- skips tests or chooses the wrong testing order;
- over-documents or under-documents code;
- stops, retries, or self-heals errors differently from your preference;
- creates commits when you wanted the working tree left alone.

The product session directly compares six behavior axes:

| Axis | Concrete decision |
|---|---|
| Autonomy | ask first, announce then act, or act then report |
| Scope | strict request only, adjacent fix, or proactive cleanup |
| Test discipline | test first, test after, or only on request |
| Comments and docs | minimal, docstring only, or thorough explanation |
| Error behavior | stop, retry once, or self-heal |
| Commit style | conventional, narrative, or no automatic commit |

Two more axes—response language and verbosity—can land as **mined-prior defaults** when the product session did not collect direct strike evidence for them. They are labeled `mined-prior` and `untested` in `manifest.json` and queued for recheck; Popper does not claim that you selected them by striking.

The `3⁸ = 6,561` counter is the number of combinations across eight three-value axes. It is a progress visualization, not proof of accuracy. The evidence that matters is the recorded cross-out, the compiled rule, and its source label.

## What lands—and what does not

After the fifteenth cross-out, Popper atomically writes three owned artifacts under `~/.claude/popper/`:

| File | What you get |
|---|---|
| `POPPER.md` | Eight executable Korean rule lines for Claude Code |
| `manifest.json` | Rule value, evidence grade, source, provenance, and content hashes |
| `settings.popper.json` | A reviewable settings proposal |

Nothing is activated during the session. `enable` adds one receipt-owned `@import` line to `~/.claude/CLAUDE.md`; `rollback` removes only that occurrence. Your existing instructions remain yours.

## Try it as a local console tool

The shortest path uses the release wheel. Package installation contacts GitHub; the Popper session itself does not contact a model or external service.

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install \
  https://github.com/brnyxx/popper/releases/download/v1.3.0/popper-1.3.0-py3-none-any.whl
.venv/bin/popper doctor
.venv/bin/popper open
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install `
  https://github.com/brnyxx/popper/releases/download/v1.3.0/popper-1.3.0-py3-none-any.whl
.venv\Scripts\popper doctor
.venv\Scripts\popper open
```

Cross out the wrong behavior until the browser completes. Then:

```bash
popper enable --grant
popper status
```

Open a fresh Claude Code session and repeat the request that used to trigger the unwanted behavior. `popper rollback` returns activation to its prior state.

## Install inside Claude Code with checksums

Download `popper-plugin-1.3.0.zip`, `SHA256SUMS`, and `verify_checksums.py` from the [v1.3.0 release](../../releases/tag/v1.3.0). Keep all three in one directory and verify before extraction.

macOS or Linux:

```bash
python3 verify_checksums.py SHA256SUMS \
  --only popper-plugin-1.3.0.zip verify_checksums.py
DEST="$HOME/.local/share/popper-plugin-1.3.0"
test ! -e "$DEST" || { echo "destination already exists: $DEST" >&2; exit 1; }
python3 -m zipfile -e popper-plugin-1.3.0.zip "$DEST"
claude plugin marketplace add "$DEST"
claude plugin install popper@popper-marketplace
```

Windows PowerShell:

```powershell
py -3 verify_checksums.py SHA256SUMS `
  --only popper-plugin-1.3.0.zip verify_checksums.py
$Dest = Join-Path $env:LOCALAPPDATA "Popper\plugin-1.3.0"
if (Test-Path $Dest) { throw "destination already exists: $Dest" }
py -3 -m zipfile -e popper-plugin-1.3.0.zip $Dest
claude plugin marketplace add $Dest
claude plugin install popper@popper-marketplace
```

Start a fresh Claude Code session:

```text
/popper:popper doctor
/popper:popper open
```

After completion:

```text
/popper:popper enable
/popper:popper status
```

Open a new Claude Code session and retry the same kind of task. `/popper:popper rollback` removes Popper's owned import line. A source checkout can also be registered with `claude plugin marketplace add "$PWD"`.

## Commands by job

### Inside Claude Code

| You want to… | Command | Observable result |
|---|---|---|
| Start or continue | `/popper:popper open` | Resumes the only unfinished flow or opens a new 15-cross-out session |
| Resume one session | `/popper:popper resume SESSION_ID` | Replays that sealed session from its append-only events |
| Find sessions | `/popper:popper sessions` | Lists local sessions without deleting or rewriting them |
| Diagnose installation | `/popper:popper doctor` | Checks package data, seals, replay, landing integrity, and loopback binding |
| Inspect activation | `/popper:popper status` | Reports `inactive`, `active`, or `import-drift` |
| Revisit rules | `/popper:popper recheck` | Runs a manual 5–7-cross-out review; no daemon or polling |
| Run sealed validation | `/popper:popper validate` | Runs 13 discriminative slots and two mirrored probes |
| Activate or undo | `/popper:popper enable` / `/popper:popper rollback` | Adds or removes one receipt-owned import |

### Installed wheel

| You want to… | Command |
|---|---|
| Inspect one session as JSON | `popper sessions SESSION_ID --json` |
| Export instructions for another agent | `popper export --format agents --output AGENTS.md` |
| Create a portable snapshot | `popper data backup /safe/path/popper.zip` |
| Inspect a snapshot without extraction | `popper data inspect popper.zip --json` |
| Activate with explicit consent | `popper enable --grant` |

`python -m popper ...` is equivalent to `popper ...`.

## Why the local ledger matters

The engineering contracts translate into user-visible recovery:

- **Interrupted halfway?** Reopen or resume; accepted cross-outs are already durable.
- **Killed after the final cross-out?** Resume finalizes and lands the same output once.
- **Two sessions launched accidentally?** The second is rejected before it creates a competing session.
- **A file was manually changed?** Landing stops instead of overwriting it.
- **The browser submits an old pair?** Popper rejects the stale decision.
- **A rule becomes stale?** A seven-day recheck banner asks you to compare it again.
- **Want out?** Rollback removes only the import Popper can prove it owns.

Underneath, those guarantees use append-only JSONL, fsync, process locks, sealed fixture/session digests, deterministic replay, atomic replacement, and loopback Host/Origin checks.

## Boundaries

Popper owns `~/.claude/popper/` and never silently edits a project. During a session it does not:

- call an LLM or external service;
- collect telemetry, analytics, cookies, or browser storage;
- auto-update, auto-activate, or silently repair damaged evidence;
- treat survival as approval—the survivor is only “not falsified yet”;
- pretend mined-prior defaults came from your cross-outs;
- copy Paperthin's skill catalog or Ouroboros's orchestration runtime.

The Pages site follows the same boundary: bilingual static HTML/CSS, local assets, no JavaScript or analytics, and no remote runtime resources.

## Export, verify, update, and remove

Export rules without sharing the complete event history:

```bash
popper export --format markdown > POPPER.export.md
popper export --format agents --output AGENTS.md
popper export --format json > popper-rules.json
```

Verify downloaded release assets:

```bash
python3 verify_checksums.py SHA256SUMS \
  --only popper-plugin-1.3.0.zip verify_checksums.py
```

To move an older marketplace install to v1.3.0, extract into a fresh versioned directory, then re-register it:

```bash
DEST="$HOME/.local/share/popper-plugin-1.3.0"
python3 -m zipfile -e popper-plugin-1.3.0.zip "$DEST"
claude plugin marketplace remove popper-marketplace
claude plugin marketplace add "$DEST"
claude plugin update popper@popper-marketplace
```

Restart Claude Code and run `/popper:popper doctor` before removing the old versioned plugin directory. Events and landed rules live outside the plugin package.

To remove the plugin while keeping your evidence and rules:

```text
/popper:popper rollback
```

```bash
claude plugin uninstall popper@popper-marketplace
claude plugin marketplace remove popper-marketplace
rm -rf "$HOME/.local/share/popper-plugin-1.3.0"
```

`~/.claude/popper/` is user data and is deliberately retained. Back it up first; delete that directory only when you intentionally want to destroy the event history and generated rules.

## Development and release proof

```bash
python3 -m pip install -e '.[test,e2e,release]'
python3 -m pytest tests/ -q
python3 scripts/build_site.py \
  --output /tmp/popper-pages \
  --site-url "$POPPER_SITE_URL" \
  --repository-url "$POPPER_REPOSITORY_URL"
claude plugin validate .
```

CI covers Python 3.10–3.14, macOS/Linux/Windows, Chromium/Firefox/WebKit, a clean installed plugin, deterministic packages, and Pages contracts. Releases include wheel, sdist, plugin ZIP, standalone verifier, `SHA256SUMS`, and GitHub artifact provenance.

## Scope

Popper is deliberately narrow: a local behavior compiler for a frozen eight-axis catalog. It is not a general prompt manager, cloud profile, model evaluator, or autonomous-agent orchestrator.

The sealed preregistration lives in [`docs/prereg/prereg_sealed.json`](docs/prereg/prereg_sealed.json); the frozen axis-locality table lives in [`docs/axis_locality_table.md`](docs/axis_locality_table.md).

MIT © 2026 Brian Kim.
