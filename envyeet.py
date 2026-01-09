#!/usr/bin/env python3
"""envyeet: Merge environment variable files with intelligent key swapping."""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


VERSION = "0.1.0"


class EnvLine:
    """Represents a line in an environment file."""

    def __init__(
        self,
        raw: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        quote_style: Optional[str] = None,
        is_export: bool = False,
        is_comment: bool = False,
        is_empty: bool = False,
    ):
        self.raw = raw
        self.key = key
        self.value = value
        self.quote_style = quote_style
        self.is_export = is_export
        self.is_comment = is_comment
        self.is_empty = is_empty

    def __repr__(self) -> str:
        return f"EnvLine(key={self.key!r}, value={self.value!r}, quote_style={self.quote_style!r})"


def parse_env_file(
    filepath: str, verbose: bool = False
) -> Tuple[Dict[str, EnvLine], List[EnvLine]]:
    """Parse an environment file and return dict of key->EnvLine and list of all lines."""
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise ValueError(f"Environment file not found: {filepath}")
    except IOError as e:
        raise ValueError(f"Error reading file {filepath}: {e}")

    env_dict: Dict[str, EnvLine] = {}
    all_lines: List[EnvLine] = []

    env_line_pattern = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped or stripped == "":
            all_lines.append(EnvLine(raw=line, is_empty=True))
            continue

        if stripped.startswith("#"):
            all_lines.append(EnvLine(raw=line, is_comment=True))
            continue

        match = env_line_pattern.match(line)
        if match:
            key = match.group(1)
            value_part = match.group(2)

            quote_style = None
            value = value_part

            if (
                value_part.startswith("'")
                and value_part.endswith("'")
                and len(value_part) >= 2
            ):
                quote_style = "'"
                value = value_part[1:-1]
            elif (
                value_part.startswith('"')
                and value_part.endswith('"')
                and len(value_part) >= 2
            ):
                quote_style = '"'
                value = value_part[1:-1]

            is_export = line.strip().startswith("export ")

            env_line = EnvLine(
                raw=line,
                key=key,
                value=value,
                quote_style=quote_style,
                is_export=is_export,
            )
            env_dict[key] = env_line
            all_lines.append(env_line)
        else:
            if verbose:
                print(
                    f"Warning: Skipping malformed line {line_num} in {filepath}",
                    file=sys.stderr,
                )
            all_lines.append(EnvLine(raw=line, is_empty=True))

    return env_dict, all_lines


def generate_line(
    key: str,
    value: Optional[str],
    is_export: bool = False,
    quote_style: Optional[str] = None,
) -> str:
    """Generate an environment file line with appropriate quoting."""
    safe_value = value or ""
    if quote_style == "'":
        formatted_value = f"'{safe_value}'"
    elif quote_style == '"':
        formatted_value = f'"{safe_value}"'
    else:
        formatted_value = safe_value

    export_prefix = "export " if is_export else ""
    return f"{export_prefix}{key}={formatted_value}\n"


def merge_env_files(
    source: str,
    target: str,
    squash: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> List[str]:
    """Merge source env file into target env file."""
    source_dict, _ = parse_env_file(source, verbose)
    target_dict, target_lines = parse_env_file(target, verbose)

    updated_keys: List[str] = []
    added_keys: List[str] = []
    output_lines: List[str] = []

    for line in target_lines:
        if line.key and line.key in source_dict:
            source_line = source_dict[line.key]
            new_line = generate_line(
                line.key,
                source_line.value,
                is_export=line.is_export or source_line.is_export,
                quote_style=source_line.quote_style,
            )
            output_lines.append(new_line)
            updated_keys.append(line.key)
        else:
            output_lines.append(line.raw)

    if squash:
        for key, source_line in source_dict.items():
            if key not in target_dict:
                new_line = generate_line(
                    key,
                    source_line.value,
                    is_export=source_line.is_export,
                    quote_style=source_line.quote_style,
                )
                output_lines.append(new_line)
                added_keys.append(key)

    if dry_run:
        if verbose:
            if updated_keys:
                print(f"Keys to update: {', '.join(updated_keys)}", file=sys.stderr)
            if added_keys:
                print(f"Keys to add: {', '.join(added_keys)}", file=sys.stderr)
            if not updated_keys and not added_keys:
                print("No changes would be made", file=sys.stderr)

    return output_lines


def backup_file(
    filepath: str, output: Optional[str] = None, quiet: bool = False
) -> str:
    """Create a backup of the environment file."""
    source_path = Path(filepath)

    if not source_path.exists():
        raise ValueError(f"File not found: {filepath}")

    if output:
        backup_path = Path(output)
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = Path(f"{filepath}.bkp-{timestamp}")

    if backup_path.exists():
        raise ValueError(f"Backup file already exists: {backup_path}")

    import shutil

    shutil.copy2(filepath, backup_path)

    if not quiet:
        print(str(backup_path))

    return str(backup_path)


def is_tty() -> bool:
    """Check if stdout is a TTY."""
    return sys.stdout.isatty()


def prompt_confirmation(message: str) -> bool:
    """Prompt user for yes/no confirmation."""
    if not is_tty():
        return False

    try:
        response = input(f"{message} [y/N]: ").strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def write_output(
    content: List[str],
    filepath: Optional[str] = None,
    quiet: bool = False,
    force: bool = False,
) -> None:
    """Write content to file or stdout."""
    output = "".join(content)

    if filepath:
        if Path(filepath).exists():
            if is_tty() and not force:
                if not prompt_confirmation(f"Overwrite {filepath}?"):
                    print("Aborted", file=sys.stderr)
                    sys.exit(1)
        with open(filepath, "w") as f:
            f.write(output)
        if not quiet:
            print(f"Written to {filepath}")
    else:
        if not quiet:
            print(output, end="")


def cmd_merge(args: argparse.Namespace) -> None:
    """Handle the merge subcommand."""
    try:
        merged_lines = merge_env_files(
            args.source,
            args.target,
            squash=args.squash,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        if args.dry_run:
            return

        force = getattr(args, "force", False) or getattr(args, "no_input", False)
        if args.overwrite:
            write_output(merged_lines, args.target, args.quiet, force)
        elif args.output:
            write_output(merged_lines, args.output, args.quiet, force)
        else:
            write_output(merged_lines, None, args.quiet)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2 if "not found" in str(e) else 1)


def cmd_backup(args: argparse.Namespace) -> None:
    """Handle the backup subcommand."""
    try:
        backup_file(args.file, args.output, args.quiet)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2 if "not found" in str(e) else 4)


def main() -> None:
    """Main entry point for envyeet CLI."""
    parser = argparse.ArgumentParser(
        prog="envyeet",
        description="Merge environment variable files with intelligent key swapping and optional value injection.",
    )
    parser.add_argument("--version", action="version", version=VERSION)

    global_flags = parser.add_argument_group("Global flags")
    global_flags.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress non-error output"
    )
    global_flags.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed merge information"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    merge_parser = subparsers.add_parser(
        "merge", help="Merge source env file into target env file"
    )
    merge_parser.add_argument("source", help="Source environment file")
    merge_parser.add_argument("target", help="Target environment file")
    merge_parser.add_argument(
        "--squash",
        action="store_true",
        help="Add new keys from source (default: only update existing)",
    )
    merge_parser.add_argument("--output", help="Write output to specified file")
    merge_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Write directly to target file (destructive)",
    )
    merge_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    merge_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts",
    )
    merge_parser.add_argument(
        "--no-input",
        action="store_true",
        help="Disable confirmation prompts (alias for --force)",
    )

    backup_parser = subparsers.add_parser(
        "backup", help="Create a backup of an environment file"
    )
    backup_parser.add_argument("file", help="File to backup")
    backup_parser.add_argument(
        "--output", help="Custom backup filename (must not exist)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "merge":
        cmd_merge(args)
    elif args.command == "backup":
        cmd_backup(args)


if __name__ == "__main__":
    main()
