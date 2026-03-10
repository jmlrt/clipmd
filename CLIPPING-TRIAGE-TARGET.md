# clipping-triage command: target state after TODO optimizations

This file describes the future state of the `.claude/commands/clipping-triage.md`
Claude Code slash command once all 8 items from the [Unattended Triage Optimization
Roadmap](TODO.md#unattended-triage-optimization-roadmap) are implemented.

**Goal**: the command runs fully unattended via `claude -p` with zero human prompts,
zero approval gates, and minimum LLM token usage.

---

## What each TODO item removes from the command

| TODO item | Current workaround in command | What disappears |
|-----------|-------------------------------|-----------------|
| `preprocess --auto-remove-dupes --yes` | Interactive duplicate prompts; `--no-dedupe` workaround docs | Entire "Duplicate Handling" section; interactive mode warnings |
| `duplicates --auto-resolve --strategy oldest-wins` | Manual `clipmd trash` calls per pair; frontmatter inspection loop | Step 1b manual resolution; multi-step duplicate logic |
| `extract` filename truncation fix | Secondary Glob/ls verification before every `move` | "Filename Matching" warning; "Verification before Stage 3" step |
| `fetch --file --clear-after` | Separate `echo "# INBOX" > ...` bash command | Manual INBOX reset; risk of double-fetch on crash |
| `move --skip-missing` | Manual pre-validation bash loop in Troubleshooting | "Step 3: Move validation" troubleshooting section |
| `extract` excludes files without frontmatter | `INBOX.md` exclusion CRITICAL warning; manual skip instruction | "System File Exclusion" section in Step 2 |
| Domain rules (`extract --apply-rules`) | LLM categorizes 100% of articles | Most articles pre-categorized; LLM only handles unknowns |
| `extract --format json` + `move --from-json` | Free-text `categorization.txt`; parsing fragility | All filename-matching complexity; free-text round-trip |

---

## Target command (full text)

Replace the content of `.claude/commands/clipping-triage.md` with the following:

---

```
Triage all articles from Clippings/ root folder into appropriate subfolders
using domain rules pre-categorization and Claude for ambiguous articles.

# Context

Articles saved via Obsidian Web Clipper (French/English) with YAML frontmatter.

**Approach**: Fully unattended pipeline — fetch, preprocess (with auto duplicate
removal), extract (domain rules pre-categorize known sources), Claude categorizes
remaining articles, move, report.

# Task Instructions

**CRITICAL - Setup**:
1. ALL clipmd commands must use absolute paths
   (`/Users/jmlrt/Documents/Obsidian/Perso/Clippings/`, not `Clippings/`)
2. Temporary files (articles.json, categorization.json) are created in vault
   root during the workflow and removed in Step 5

## Step 0: Fetch Articles

### Step 0a: Fetch from RSS feeds

```bash
clipmd fetch --rss https://steipete.me/rss.xml
clipmd fetch --rss https://simonwillison.net/atom/everything/
```

RSS feeds are checked for new articles since last fetch. Duplicates and
previously trashed articles are automatically skipped. Feed failures are
non-blocking.

### Step 0b: Fetch URLs from Clippings/INBOX.md

```bash
clipmd fetch --file /Users/jmlrt/Documents/Obsidian/Perso/Clippings/INBOX.md --clear-after
```

Fetches all markdown links from INBOX.md, then clears the file to empty. If fetch
fails partway (with errors), the file is NOT cleared — remaining URLs are preserved
for retry.

## Step 1: Preprocess

```bash
clipmd preprocess /Users/jmlrt/Documents/Obsidian/Perso/Clippings/ --auto-remove-dupes --yes
```

Fixes frontmatter, sanitizes filenames, adds date prefixes, and automatically
trashes duplicate URLs (keeping the oldest clip — the first intentional save).
Runs without prompts.

**Error handling**: If `clipmd preprocess` exits with a non-zero code, stop and
investigate before proceeding — running extract on partially processed files
produces unreliable metadata.

## Step 2: Extract & Categorize

```bash
clipmd extract /Users/jmlrt/Documents/Obsidian/Perso/Clippings/ \
  --folders --max-chars 400 --apply-rules --format json \
  > /Users/jmlrt/Documents/Obsidian/Perso/articles.json
```

`--apply-rules` pre-categorizes articles from known domains (korben.info,
journaldugeek.com, platform.claude.com, etc.) using the configured domain rules
file. Articles with matched rules have `"folder"` already set. Articles with
`"folder": null` require Claude categorization.

Claude reads `articles.json`, fills in the `"folder"` field for all articles
where it is `null`, and writes `categorization.json`:

```json
[
  {"file": "20260310-exact-filename.md", "folder": "Geek"},
  {"file": "20260310-another-article.md", "folder": "AI-Coding-Practices"},
  ...
]
```

**Rules**: Skip articles that already have a `"folder"` value — only categorize
where `"folder"` is `null`. See [Clippings/CLAUDE.md](../Clippings/CLAUDE.md)
for categorization guidelines and folder definitions.

## Step 3: Move

```bash
clipmd move --from-json /Users/jmlrt/Documents/Obsidian/Perso/categorization.json --skip-missing
```

Moves all articles to their assigned folders. Articles assigned `"TRASH"` are
sent to system Trash. Missing files emit a warning and are skipped; valid
entries are always processed.

## Step 4: Report

```bash
clipmd stats
```

Folder statistics, article counts, warnings (>45 or <10 articles per folder).

## Step 5: Cleanup

```bash
rm /Users/jmlrt/Documents/Obsidian/Perso/articles.json \
   /Users/jmlrt/Documents/Obsidian/Perso/categorization.json
```

# Troubleshooting

## Subfolder-to-subfolder moves

Use `clipmd move --source-dir /path/to/source/ --from-json categorization.json`.
Destination folders always resolve to vault root.

## Domain rules not matching expected sources

Check `.clipmd/domain-rules.yaml`. Run `clipmd discover-rules --dry-run` to see
suggested rules from existing vault categorization.
```

---

## Step-by-step diff from current command

### Step 0b — INBOX fetch

**Before** (2 commands, manual clear):
```bash
clipmd fetch --file /Users/jmlrt/Documents/Obsidian/Perso/Clippings/INBOX.md
echo "# INBOX" > /Users/jmlrt/Documents/Obsidian/Perso/Clippings/INBOX.md
```

**After** (1 command, atomic clear):
```bash
clipmd fetch --file /Users/jmlrt/Documents/Obsidian/Perso/Clippings/INBOX.md --clear-after
```

Also removes: the "CRITICAL: INBOX.md is a system file" warning from Step 2
(`extract` now auto-excludes files without frontmatter).

---

### Step 1 — Preprocess

**Before** (interactive, hangs unattended; required manual duplicate resolution):
```bash
clipmd preprocess /Users/jmlrt/Documents/Obsidian/Perso/Clippings/
# … then manually read frontmatter of each duplicate pair and call clipmd trash
```

**After** (fully non-interactive):
```bash
clipmd preprocess /Users/jmlrt/Documents/Obsidian/Perso/Clippings/ --auto-remove-dupes --yes
```

Removes: "Duplicate Handling" section, "Understanding Duplicates" section,
manual trash loop, and all interactive mode documentation.

---

### Step 2 — Extract

**Before**:
```bash
clipmd extract /Users/jmlrt/Documents/Obsidian/Perso/Clippings/ --folders --max-chars 400 > articles-metadata.txt
```
Then: secondary Glob verification to recover truncated filenames; INBOX.md
exclusion warning; manual review gate before Step 3; 100% of articles sent
to LLM.

**After**:
```bash
clipmd extract /Users/jmlrt/Documents/Obsidian/Perso/Clippings/ \
  --folders --max-chars 400 --apply-rules --format json \
  > /Users/jmlrt/Documents/Obsidian/Perso/articles.json
```

Removes:
- "Filename Matching" warning (filenames never truncated in JSON output)
- "Verification before Stage 3" Glob step
- "CRITICAL - System File Exclusion" (extract auto-excludes files without frontmatter)
- "Review and edit the file" approval gate (no longer needed)

Reduces: LLM token usage for well-known sources — only articles with
`"folder": null` need Claude categorization.

---

### Step 3 — Move

**Before**:
```bash
# Pre-validation loop (manual, required)
while IFS= read -r line; do
    fname=$(echo "$line" | sed 's/^[0-9]*\. [^ ]* - //')
    [[ -f "/Users/jmlrt/Documents/Obsidian/Perso/Clippings/$fname" ]] || echo "MISSING: $fname"
done < categorization.txt

clipmd move /Users/jmlrt/Documents/Obsidian/Perso/categorization.txt
```

**After**:
```bash
clipmd move --from-json /Users/jmlrt/Documents/Obsidian/Perso/categorization.json --skip-missing
```

Removes: entire "Step 3: Move validation" troubleshooting section.

---

### Step 5 — Cleanup

**Before**: `rm articles-metadata.txt categorization.txt`

**After**: `rm articles.json categorization.json`

---

## One-time setup required when implementing domain rules

When `--apply-rules` is first available, seed the rules file:

```bash
# Generate rule suggestions from existing vault categorization
clipmd discover-rules --min-articles 3 --min-confidence 0.9 --merge

# Review and apply
clipmd discover-rules --dry-run
```

Known high-confidence rules to seed manually if `discover-rules` is not yet
implemented:

```yaml
# .clipmd/domain-rules.yaml
rules:
  - domain: korben.info
    folder: Geek
  - domain: journaldugeek.com
    folder: Geek
  - domain: platform.claude.com
    folder: AI-Claude-Code
  - domain: steipete.me
    folder: AI-Coding-Practices
  - domain: dagger.io
    folder: AI-Coding-Practices
  - domain: lowendbox.com
    folder: Geek
  - domain: simonwillison.net
    folder: Work        # high-volume; content-based override still possible
```
