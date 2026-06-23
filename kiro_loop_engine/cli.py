"""CLI for the Kiro Loop Engine plugin.

Usage:
    kiro-loop init     # Scaffold loop engine files in current project
    kiro-loop run      # Manually trigger one processing cycle
    kiro-loop status   # Show pending/completed blocks in control file
"""

from __future__ import annotations

import argparse
import os
import sys


def cmd_init(args: argparse.Namespace) -> None:
    """Scaffold loop engine files in the project."""
    from kiro_loop_engine.engine import LoopEngine

    project_root = args.project_root or os.getcwd()
    engine = LoopEngine(project_root=project_root)
    created = engine.setup()

    if created:
        print("Kiro Loop Engine initialized:")
        for key, path in created.items():
            print(f"  {key}: {path}")
    else:
        print("Loop engine files already exist. Nothing to create.")


def cmd_run(args: argparse.Namespace) -> None:
    """Manually trigger one processing cycle."""
    from kiro_loop_engine.engine import LoopEngine

    project_root = args.project_root or os.getcwd()
    engine = LoopEngine(project_root=project_root)

    control_file = engine.control_file_path
    if not os.path.exists(control_file):
        print(f"Control file not found: {control_file}")
        print("Run 'kiro-loop init' first to set up the loop engine.")
        sys.exit(1)

    print(f"Processing control file: {control_file}")
    engine.process_cycle()
    print("Cycle complete.")


def cmd_status(args: argparse.Namespace) -> None:
    """Show status of instruction blocks in the control file."""
    from kiro_loop_engine.engine import LoopEngine

    project_root = args.project_root or os.getcwd()
    engine = LoopEngine(project_root=project_root)

    control_file = engine.control_file_path
    if not os.path.exists(control_file):
        print(f"Control file not found: {control_file}")
        sys.exit(1)

    with open(control_file, "r", encoding="utf-8") as f:
        content = f.read()

    from kiro_loop_engine.parser import Parser

    parser = Parser()
    blocks = parser.parse(content)

    if not blocks:
        print("No instruction blocks found in control file.")
        return

    print(f"{'#':<4} {'Status':<12} {'Type':<16} {'Title'}")
    print("-" * 70)
    for i, block in enumerate(blocks, 1):
        print(f"{i:<4} {block.status:<12} {block.type:<16} {block.title[:40]}")

    # Summary
    pending = sum(1 for b in blocks if b.status == "pending")
    completed = sum(1 for b in blocks if b.status == "completed")
    failed = sum(1 for b in blocks if b.status == "failed")
    print(f"\nTotal: {len(blocks)} | Pending: {pending} | Completed: {completed} | Failed: {failed}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="kiro-loop",
        description="Kiro Loop Engine - File-driven automation plugin for Kiro IDE",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root directory (defaults to current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Shared argument for all subcommands
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--project-root", default=None,
        help="Project root directory (defaults to current directory)",
    )

    # init
    init_parser = subparsers.add_parser("init", parents=[parent_parser], help="Scaffold loop engine files in project")
    init_parser.set_defaults(func=cmd_init)

    # run
    run_parser = subparsers.add_parser("run", parents=[parent_parser], help="Manually trigger one processing cycle")
    run_parser.set_defaults(func=cmd_run)

    # status
    status_parser = subparsers.add_parser("status", parents=[parent_parser], help="Show status of instruction blocks")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
