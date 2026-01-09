# envyeet CLI Specification

## Overview

**Name**: `envyeet`

**One-liner**: Merge environment variable files with intelligent key swapping and optional value injection.

**Purpose**: Safely merge one `.env` file into another by updating existing keys, with an option to inject new keys (squash mode).

---

## USAGE

```bash
# Merge source into target (output to stdout)
envyeet merge <source> <target>

# Merge and overwrite target file
envyeet merge <source> <target> --overwrite

# Merge with squashing (add new keys from source)
envyeet merge <source> <target> --squash

# Create a backup (auto-generated name)
envyeet backup <file>

# Create a backup with custom name
envyeet backup <file> --output <backup-file>
```

---

## Subcommands

### `envyeet merge <source> <target> [flags]`

Merge `<source>` env file into `<target>` env file.

**Behavior**:
- By default: Only updates keys in `<target>` that exist in `<source>`. Does NOT add new keys.
- With `--squash`: Updates existing keys AND adds new keys from `<source>` that don't exist in `<target>`.
- When both files have the same key: `<source>` value always wins (overwrites `<target>`).
- Output goes to stdout by default.
- Use `--overwrite` to write directly to `<target>` (destructive operation).
- Use `--output <file>` to write to a specific file instead of stdout.

**Idempotence**: Running the same merge command multiple times produces the same result.

**State changes**: 
- Without `--overwrite`: No files are modified.
- With `--overwrite`: Target file is modified in place.

### `envyeet backup <file> [flags]`

Create a backup of `<file>`.

**Behavior**:
- By default: Creates `<file>.bkp-TIMESTAMP` where TIMESTAMP is in ISO 8601 format (e.g., `.env.bkp-20250109T143000Z`).
- With `--output <file>`: Creates backup with custom filename.
- Backup is a complete copy of the original file.
- Does not modify the original file.
- Fails with error if the backup file already exists (no overwriting).

**Idempotence**: Without `--output`, each run creates a new unique backup file. With `--output`, requires unique filename each time.

**State changes**: Creates a new backup file; original file unchanged.

---

## Global Flags

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `-h, --help` | flag | no | - | Show help message and exit |
| `--version` | flag | no | - | Print version and exit |
| `-q, --quiet` | flag | no | `false` | Suppress non-error output |
| `-v, --verbose` | flag | no | `false` | Show detailed merge information |

### Merge-specific Flags

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--squash` | flag | no | `false` | Add new keys from source (default: only update existing) |
| `--output <file>` | path | no | stdout | Write output to specified file |
| `--overwrite` | flag | no | `false` | Write directly to target file (destructive) |
| `--dry-run` | flag | no | `false` | Show what would change without modifying files |

### Backup-specific Flags

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--output <file>` | path | no | `.bkp-TIMESTAMP` | Custom backup filename (must not exist) |

---

## I/O Contract

### Standard Output (stdout)
- **merge**: Contains the merged env file content (if not using `--output` or `--quiet`)
- **backup**: Path to the created backup file (if not `--quiet`)
- With `--quiet`: No output to stdout

### Standard Error (stderr)
- Error messages with clear context
- Warning messages (e.g., about malformed lines)
- Verbose/diagnostic information (with `--verbose`)

### TTY Detection
- Progress indicators shown only when stdout is a TTY
- No ANSI codes when `NO_COLOR` env var is set or `TERM=dumb`

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Generic failure (file I/O error, permission denied, etc.) |
| `2` | Invalid usage (missing args, invalid flag, file not found) |
| `3` | Malformed env file (unparseable content) |
| `4` | File exists error (when `--output` file or backup file already exists) |

---

## Safety Rules

### Destructive Operations
- `--overwrite` requires user confirmation when stdin is a TTY
- `--no-input` flag disables confirmation prompts
- `--force` flag skips confirmation in non-interactive mode

### File Safety
- Never overwrite without explicit user action (`--overwrite` flag)
- Warn before overwriting existing files with `--output`
- Suggest using `envyeet backup` before `--overwrite`

### Dry Run
- `--dry-run` flag shows exactly what would change
- Lists keys to be updated and (if `--squash`) keys to be added
- No files are modified

---

## Environment Variables

| Variable | Description | Precedence |
|----------|-------------|------------|
| `ENVYEET_QUIET` | Equivalent to `--quiet` | Flags override env |
| `ENVYEET_VERBOSE` | Equivalent to `--verbose` | Flags override env |
| `NO_COLOR` | Disable colored output | Always respected |

**Precedence**: Command-line flags > Environment variables > Defaults

---

## File Format Handling

### Supported Formats
- `KEY=VALUE` (standard .env format)
- `export KEY=VALUE` (shell-style exports)
- Quoted values: single quotes, double quotes, unquoted

### Quoting Style
- Preserves quoting style from `<source>` file for all values
- If a key exists only in `<target>` and not in `<source>`, preserves `<target>`'s quoting

### Comments and Empty Lines
- Preserves comments (lines starting with `#`)
- Preserves empty lines
- Order of keys follows `<target>`'s original order for existing keys
- New keys (when `--squash`) are appended at the end

### Malformed Lines
- Skips lines that don't match `KEY=VALUE` or `export KEY=VALUE` pattern
- Emits a warning to stderr for each skipped line (with `--verbose`)

---

## Merge Behavior - Visual Examples

**Important**: When merging `<source>` into `<target>`, `<source>` values **always win** (override `<target>` values).

### Example 1: Basic Merge (no `--squash`)

**Command**: `envyeet merge .env.staging .env`

**Source file (.env.staging)**:
```bash
# Staging database config
DATABASE_URL="postgresql://staging-db:5432/app"
REDIS_HOST="staging-redis"
DEBUG=false

# Staging-only key (won't be added)
STAGING_FEATURE_ENABLED=true
```

**Target file (.env)**:
```bash
# Production database config
DATABASE_URL="postgresql://prod-db:5432/app"
API_KEY="prod-key-123"
REDIS_HOST="prod-redis"
DEBUG=true
```

**Output (merged)**:
```bash
# Production database config
DATABASE_URL="postgresql://staging-db:5432/app"  # ← Updated from source
API_KEY="prod-key-123"  # ← Kept from target (not in source)
REDIS_HOST="staging-redis"  # ← Updated from source
DEBUG=false  # ← Updated from source
```

**What happened**:
- ✅ `DATABASE_URL` updated (value from source)
- ✅ `REDIS_HOST` updated (value from source)
- ✅ `DEBUG` updated (value from source)
- ✅ `API_KEY` kept (only in target)
- ❌ `STAGING_FEATURE_ENABLED` NOT added (not in target, no `--squash`)

---

### Example 2: Merge with `--squash`

**Command**: `envyeet merge .env.staging .env --squash`

**Same source and target files as above**

**Output (merged with squash)**:
```bash
# Production database config
DATABASE_URL="postgresql://staging-db:5432/app"  # ← Updated from source
API_KEY="prod-key-123"  # ← Kept from target (not in source)
REDIS_HOST="staging-redis"  # ← Updated from source
DEBUG=false  # ← Updated from source
STAGING_FEATURE_ENABLED=true  # ← ADDED from source (squash mode)
```

**What happened**:
- ✅ All the updates from Example 1
- ✅ `STAGING_FEATURE_ENABLED` **added** (exists in source, not in target, `--squash` enabled)

---

### Example 3: Quoting Style Preservation

**Command**: `envyeet merge .env.local .env`

**Source file (.env.local)**:
```bash
export DATABASE_URL='postgresql://localhost:5432/app'
export DEBUG=false
export TIMEOUT=30
```

**Target file (.env)**:
```bash
export DATABASE_URL="postgresql://remote:5432/app"
export DEBUG="true"
export TIMEOUT="60"
export API_KEY="secret"
```

**Output (merged)**:
```bash
export DATABASE_URL='postgresql://localhost:5432/app'  # ← Source's single quotes
export DEBUG=false  # ← Source's unquoted style
export TIMEOUT=30  # ← Source's unquoted style
export API_KEY="secret"  # ← Target's quotes preserved (key not in source)
```

**What happened**:
- ✅ All values from `<source>` adopted `<source>`'s quoting style
- ✅ Keys only in `<target>` kept their original quoting style

---

### Example 4: Overwrite Scenario

**Command**: `envyeet merge .env.staging .env --overwrite`

**Before**:
- `.env` contains production settings
- `.env.staging` contains staging settings

**After**:
- `.env` file is **permanently modified** with merged content
- Original `.env` is lost unless backed up first
- Always run `envyeet backup .env` before `--overwrite`!

---

## Examples

### Basic Merge (stdout)
```bash
# Show merged .env.local with .env
envyeet merge .env.local .env
```

### Merge and Overwrite
```bash
# Backup first, then merge
envyeet backup .env
envyeet merge .env.local .env --overwrite
# Will prompt: "Overwrite .env? [y/N]"
```

### Merge with Squashing
```bash
# Update existing keys AND add new keys from .env.local
envyeet merge .env.local .env --squash --overwrite
```

### Dry Run Before Action
```bash
# See what would change
envyeet merge .env.local .env --dry-run --verbose
# Output:
# Keys to update: DATABASE_URL, API_KEY
# Keys to add (squash): DEBUG_MODE
```

### Merge to New File
```bash
# Create merged file without touching originals
envyeet merge .env.local .env --output .env.merged
```

### Backup Workflow
```bash
# Create backup before destructive operation
envyeet backup .env
# Output: /path/to/.env.bkp-20250109T143000Z

envyeet merge .env.staging .env --overwrite
```

### Custom Backup Name
```bash
# Create backup with custom filename
envyeet backup .env --output .env.backup
# Output: /path/to/.env.backup

# If .env.backup already exists, fails with error:
# Error: Backup file already exists: .env.backup
```

### Script-Friendly Usage
```bash
# Non-interactive merge with no prompts
envyeet merge .env.ci .env --overwrite --no-input --force
```

### Quiet Mode
```bash
# Merge silently (errors still go to stderr)
envyeet merge .env.prod .env --overwrite --quiet
```

---

## Future Enhancements (Out of Scope for MVP)

- Support for multiple source files: `envyeet merge .env.* .env`
- Diff mode: `envyeet diff <source> <target>`
- Validation mode: check for required keys
- Template support: `${VAR}` substitution
- Config file support: `.envyeet.yaml` for default flags
