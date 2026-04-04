# clipmd Automated Triage Workflow

**Goal:** Run fully unattended article triage—fetch, preprocess, apply domain rules, move articles to folders—with zero human or LLM intervention. Later, optionally categorize remaining articles.

**Status:** Specification (ready for implementation)

---

## Problem Statement

Current triage workflow requires human/LLM involvement at categorization step:

```
Fetch → Preprocess → Extract → [HUMAN DECIDES] → Move → Stats → Cleanup
```

This means:
- Triage can't run unattended (fetch sits waiting for categorization)
- Unmapped articles block the workflow
- High token usage (extract everything for LLM review)

---

## Solution: Separate Triage from Categorization

**Triage phase (fully automated, unattended):**
```
Fetch → Preprocess → Apply Domain Rules & Move → Cleanup → Stats
```

**Categorization phase (separate, on-demand):**
```
Extract from Staging → [LLM Categorizes] → Move to Final Folders
```

**Benefits:**
- ✅ Triage runs unattended (can schedule in cron)
- ✅ Articles with domain rules filed immediately
- ✅ Unmapped articles segregated in staging folder
- ✅ Zero human/LLM during triage
- ✅ LLM only categorizes when user decides to review staging folder
- ✅ Deterministic (same inputs = same results)

---

## New Command: `clipmd triage`

**Signature:**
```bash
clipmd triage [OPTIONS]
```

**Options:**
```
  --config PATH          Use specific config file
  --vault PATH           Override vault path
  --staging FOLDER       Override staging folder (default: from config)
  --no-domain-rules      Skip domain rule application (move everything to staging)
  --dry-run              Show what would move without moving
```

**Behavior:**

Runs fully unattended in four atomic steps:

1. **Fetch & Process**
   - Fetch all RSS sources from config
   - Process INBOX.md (clear after success)
   - Log summary

2. **Preprocess**
   - Deduplication (remove duplicate URLs, keep oldest)
   - URL cleaning (remove tracking parameters)
   - Filename sanitization
   - Log summary

3. **Apply Domain Rules & Move**
   - For each article:
     - Extract URL from frontmatter
     - Extract domain from URL
     - Check if domain matches a rule
     - If match: move to rule's target folder
     - If no match: move to staging folder
   - Send duplicates to Trash
   - Create folders as needed
   - Log summary

4. **Report & Cleanup**
   - Output statistics (count by folder)
   - Show warnings (folder size thresholds)
   - Triage complete

**Example output:**
```
$ clipmd triage
🔍 Triage starting...
✅ Fetched 27 articles from RSS (2 sources)
✅ Processed INBOX.md (5 articles)
✅ Preprocessed (removed 3 duplicates, cleaned URLs)

📁 Applying domain rules and moving...
  ✓ 20 articles moved to target folders (domain rules matched)
  ✓ 7 articles moved to 0-To-Categorize (staging)
  ✓ 3 duplicates sent to Trash

📊 Vault Statistics
  AI-Coding-Practices: 15 (+15)
  News: 7 (+7)
  Work: 3 (+3)
  0-To-Categorize: 9 (+9)

✅ Triage complete! Articles organized. 9 in staging for review.
```

**Key guarantees:**
- All articles moved (no files left in root)
- Duplicates cleaned up
- Duplicates recoverable in Trash
- Staging folder created if needed
- Domain rule folders created if needed
- Always completes (no blocking errors)

---

## Configuration

Add to `config.yaml`:

```yaml
# =============================================================================
# TRIAGE WORKFLOW
# =============================================================================
triage:
  # RSS sources to fetch
  rss_sources:
    - https://steipete.me/rss.xml
    - https://simonwillison.net/atom/everything/

  # Local inbox file (clears on success)
  inbox_file: INBOX.md

  # Folder for unmapped articles (articles without domain rule match)
  staging_folder: "0-To-Categorize"

  # Auto-apply domain rules during triage
  auto_apply_domain_rules: true

# =============================================================================
# DOMAIN RULES (applied during triage)
# =============================================================================
domain_rules:
  # AI & Coding
  addyosmani.com: AI-Coding-Practices
  blog.ziade.org: AI-Coding-Practices
  steipete.me: AI-Coding-Practices
  simonwillison.net: AI-Coding-Practices
  every.to: AI-Coding-Practices
  tn1ck.com: AI-Claude-Code
  anthropic.com: AI-Claude-Code
  claude.com: AI-Claude-Code

  # News & Current Events
  franceinfo.fr: News
  slate.fr: News
  nofi.media: News

  # Work & Productivity
  platformengineering.org: Work
  calnewport.com: Work
  zenhabits.net: Work

  # Tech Enthusiast
  arstechnica.com: Geek
  howtogeek.com: Geek
  dev.to: Geek
```

---

## Workflow Examples

### Example 1: Complete Automation (All Domain Rules Match)

All 27 articles match a domain rule:

```bash
$ clipmd triage

✅ Fetched 27 articles
✅ Preprocessed (0 duplicates)
✅ Applied domain rules

📁 Moving...
  ✓ 27 articles moved to folders (all matched domain rules)
  ✓ 0 articles in staging

📊 Stats
  AI-Coding-Practices: 15 (+15)
  News: 7 (+7)
  Work: 3 (+3)
  Geek: 2 (+2)

✅ Complete!

# That's it. Articles already organized.
```

### Example 2: Mixed (Some Need Categorization)

27 articles fetched, 20 match rules, 7 don't:

```bash
$ clipmd triage

✅ Fetched 27 articles
✅ Preprocessed (2 duplicates)
✅ Applied domain rules

📁 Moving...
  ✓ 20 articles moved to folders (matched domain rules)
  ✓ 7 articles moved to 0-To-Categorize (staging)
  ✓ 2 duplicates sent to Trash

📊 Stats
  AI-Coding-Practices: 12 (+12)
  News: 5 (+5)
  Work: 3 (+3)
  0-To-Categorize: 7 (+7)

✅ Complete! 7 articles in staging.

# Later, when ready to categorize:
$ clipmd extract 0-To-Categorize/ --max-chars 400
# [Copy to LLM for categorization]
$ clipmd move categorization.txt
# Articles now in final folders
```

### Example 3: Scheduled Triage (Cron)

```bash
# Add to crontab
0 6 * * * clipmd triage >> ~/.logs/clipmd.log 2>&1
```

Run every morning at 6 AM. No human interaction needed. Articles automatically organized.

---

## Later Workflow: Categorize Staged Articles

When you're ready to categorize articles in staging folder:

```bash
# Step 1: Extract metadata from staging folder
$ clipmd extract 0-To-Categorize/ --max-chars 400

# Output (to stdout):
# 1. article-1.md
#    Title: "Some article title"
#    URL: https://example.com/article
#    Description: First 400 chars...

# Step 2: Copy output to LLM
# [Paste into Claude or other LLM]
# [Get back categorization.txt]

# Step 3: Move to final folders
$ clipmd move categorization.txt

# Articles now filed in permanent folders
```

---

## Implementation Details

### Domain Rule Matching

For each article:

```
1. Extract URL from frontmatter (tries: source, url, link, original_url, clip_url)
2. Extract domain from URL (e.g., https://blog.example.com/article → example.com)
3. Check config.domain_rules for domain
4. If match: remember target folder
5. If no match: target is staging folder
6. Move article to target folder
```

**Subdomain handling:**
- Config rule: `example.com: Work`
- Matches: `example.com`, `blog.example.com`, `news.example.com`, etc.
- Implementation: strip to base domain, match parent

**Edge cases handled:**
- No URL in frontmatter → move to staging
- Malformed URL → move to staging
- Domain extraction fails → move to staging

### Folder Creation

If target folder doesn't exist:
- Create it automatically
- Log in stats
- Continue (no error)

### Duplicate Handling

Preprocess phase:
- Identifies duplicate URLs
- Keeps oldest version
- Moves newer versions to Trash
- Cache is updated

### Files Always Organized

After triage, every article is in one of three places:
1. Target folder (matched domain rule)
2. Staging folder (no domain rule match)
3. Trash (duplicate)

No files left in root directory.

---

## Error Handling

**Triage is non-blocking** — handles errors gracefully:

| Error | Behavior |
|-------|----------|
| RSS fetch fails | Log warning, continue with other sources |
| INBOX.md missing | Log warning, continue |
| Preprocess error | Log and skip that file, continue |
| URL extraction fails | Move to staging, log warning |
| Domain rule folder exists | Create if needed, continue |
| File move fails | Log and skip, continue with next |
| Staging folder missing | Create it, continue |

**No errors stop the workflow** — triage always completes and reports what succeeded/failed.

---

## Dry Run Mode

Test without moving files:

```bash
$ clipmd triage --dry-run

[Same output as normal triage, but with "WOULD" instead of "✓"]

📁 Would apply domain rules...
  ✓ 20 articles would move to folders
  ✓ 7 articles would move to staging
  ✓ 2 duplicates would be sent to Trash

✅ Dry run complete. Run without --dry-run to execute.
```

---

## Configuration Examples

### Minimal Config

```yaml
version: 1

triage:
  rss_sources:
    - https://example.com/feed.xml
  inbox_file: INBOX.md
  staging_folder: "0-To-Categorize"

domain_rules:
  example.com: Example-Folder
```

### Full Config with Many Rules

See the full `config.yaml` example in this spec.

---

## Backward Compatibility

- ✅ All existing commands unchanged (`fetch`, `preprocess`, `extract`, `move`, `stats`)
- ✅ Triage is new entry point, optional
- ✅ No modifications to config format (just adds `triage:` section)
- ✅ Existing workflows still work

---

## Implementation Roadmap

### Phase 1: Config Schema
- [ ] Add `triage:` section to config schema
- [ ] Validate RSS sources, inbox file path, staging folder
- [ ] Document defaults

### Phase 2: Domain Matching
- [ ] Extract domain from URL
- [ ] Implement subdomain matching (strip to base domain)
- [ ] Handle edge cases (malformed URLs, no domain)
- [ ] Write unit tests

### Phase 3: Triage Command
- [ ] Fetch RSS sources
- [ ] Process INBOX.md with `--clear-after`
- [ ] Call existing `preprocess` command
- [ ] Apply domain rules to each article
- [ ] Move articles (use existing move logic)
- [ ] Report statistics
- [ ] Write integration tests

### Phase 4: Polish
- [ ] Dry-run mode
- [ ] Better error messages
- [ ] Performance optimization
- [ ] Shell completion for triage options

---

## Testing Strategy

### Unit Tests
- Domain extraction from URL
- Domain rule matching (exact, subdomain)
- URL extraction from frontmatter
- Staging folder path handling

### Integration Tests
- Full triage workflow with mock RSS
- Domain rule application
- Folder creation
- Duplicate handling
- Statistics reporting
- Dry-run mode

### Manual Testing
- Real RSS feeds
- Real INBOX.md processing
- Real folder organization
- Scheduled runs (cron simulation)
- Long-running vault (check for edge cases)

---

## Success Criteria

✅ One-command triage: `clipmd triage`
✅ 100% unattended (no human/LLM interaction)
✅ Deterministic (same inputs = same results)
✅ All articles organized (no files left in root)
✅ Backward compatible (existing commands unchanged)
✅ Robust error handling (all errors non-blocking)
✅ Schedulable (can run in cron)
✅ Staging folder workflow clear and simple
✅ Optional LLM categorization later

---

## Migration Path (for existing users)

If you've been manually categorizing articles:

**Before:**
```bash
clipmd fetch --rss https://...
clipmd fetch --file ./INBOX.md --clear-after
clipmd preprocess
clipmd extract > categorization-input.txt
# [Manual categorization]
clipmd move categorization.txt
```

**After:**
```bash
# One command instead of all the above
clipmd triage

# If you want to review what's in staging:
clipmd extract 0-To-Categorize/ --max-chars 400
# [Optional LLM categorization if needed]
clipmd move categorization.txt
```

Much simpler. Triage runs whenever, staging folder holds unmapped articles.
