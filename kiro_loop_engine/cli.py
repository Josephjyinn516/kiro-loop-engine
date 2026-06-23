"""CLI for the Kiro Loop Engine plugin.

Usage:
    kiro-loop init      # Scaffold loop engine files in current project
    kiro-loop run       # Manually trigger one processing cycle
    kiro-loop status    # Show pending/completed blocks in control file
    kiro-loop trace     # Show execution trace (Layer ④)
    kiro-loop stats     # Show memory statistics
    kiro-loop rollback  # Rollback to a previous state
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
        print("\nArchitecture layers active:")
        print("  Layer ①: Agent Loop (observe → decide → execute → verify → continue/stop)")
        print("  Layer ②: Verification Loop (auto-verify, retry ×3, escalate)")
        print("  Layer ③: Event-driven Loop (fileEdited hook)")
        print("  Layer ④: Hill-climbing Loop (trace + memory)")
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
    stats = engine.get_memory_stats()
    print(f"Cycle complete. Total cycles: {stats['total_cycles']}, "
          f"Blocks processed: {stats['total_blocks_processed']}, "
          f"Retries: {stats['total_retries']}")


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

    print(f"{'#':<4} {'Status':<14} {'Type':<16} {'Retries':<8} {'Title'}")
    print("-" * 80)
    for i, block in enumerate(blocks, 1):
        print(f"{i:<4} {block.status:<14} {block.type:<16} {block.retry_count:<8} {block.title[:40]}")

    # Summary
    pending = sum(1 for b in blocks if b.status == "pending")
    completed = sum(1 for b in blocks if b.status == "completed")
    failed = sum(1 for b in blocks if b.status == "failed")
    retrying = sum(1 for b in blocks if b.status == "retrying")
    escalated = sum(1 for b in blocks if b.status == "escalated")
    print(f"\nTotal: {len(blocks)} | Pending: {pending} | Completed: {completed} | "
          f"Failed: {failed} | Retrying: {retrying} | Escalated: {escalated}")


def cmd_trace(args: argparse.Namespace) -> None:
    """Show execution trace (Layer ④: Hill-climbing Loop)."""
    from kiro_loop_engine.engine import LoopEngine

    project_root = args.project_root or os.getcwd()
    engine = LoopEngine(project_root=project_root)

    traces = engine.get_trace()
    limit = args.limit or 20

    if not traces:
        print("No trace entries found. Run some blocks first.")
        return

    recent = traces[-limit:]
    print(f"Execution Trace (last {len(recent)} of {len(traces)} entries):")
    print("-" * 100)
    print(f"{'Timestamp':<22} {'Action':<10} {'Status':<10} {'Attempt':<8} {'Block Title'}")
    print("-" * 100)

    for entry in recent:
        print(f"{entry.timestamp:<22} {entry.action:<10} {entry.status:<10} "
              f"{entry.attempt:<8} {entry.block_title[:40]}")
        if entry.error:
            print(f"{'':>22} ERROR: {entry.error[:60]}")

    print(f"\nTotal traces: {len(traces)}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show memory statistics (Layer ④)."""
    from kiro_loop_engine.engine import LoopEngine

    project_root = args.project_root or os.getcwd()
    engine = LoopEngine(project_root=project_root)

    stats = engine.get_memory_stats()

    print("Loop Engine Memory Statistics (Layer ④: Hill-climbing)")
    print("=" * 50)
    print(f"  Total cycles:           {stats['total_cycles']}")
    print(f"  Total blocks processed: {stats['total_blocks_processed']}")
    print(f"  Total retries:          {stats['total_retries']}")
    print(f"  Total rollbacks:        {stats['total_rollbacks']}")
    print(f"  Last cycle:             {stats['last_cycle'] or 'never'}")

    if stats["failure_patterns"]:
        print("\n  Recurring failure patterns:")
        for pattern, count in sorted(stats["failure_patterns"].items(), key=lambda x: -x[1])[:5]:
            print(f"    [{count}x] {pattern[:70]}")


def cmd_rollback(args: argparse.Namespace) -> None:
    """Rollback to a previous state (Guardrail: 回滚点)."""
    from kiro_loop_engine.engine import LoopEngine

    project_root = args.project_root or os.getcwd()
    engine = LoopEngine(project_root=project_root)

    rollback_id = args.rollback_id
    if not rollback_id:
        # List available rollback points
        from kiro_loop_engine.constants import ROLLBACK_DIR
        rollback_dir = os.path.join(project_root, ROLLBACK_DIR)
        if not os.path.exists(rollback_dir):
            print("No rollback points available.")
            return

        points = [d for d in os.listdir(rollback_dir) if os.path.isdir(os.path.join(rollback_dir, d))]
        if not points:
            print("No rollback points available.")
            return

        print("Available rollback points:")
        for point in sorted(points, reverse=True)[:10]:
            print(f"  {point}")
        print("\nUse: kiro-loop rollback <rollback-id>")
        return

    restored = engine.rollback(rollback_id)
    if restored:
        print(f"Rolled back {len(restored)} file(s):")
        for f in restored:
            print(f"  - {f}")
    else:
        print(f"Rollback point '{rollback_id}' not found or empty.")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="kiro-loop",
        description="Kiro Loop Engine - Full Loop Engineering architecture for Kiro IDE",
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
    subparsers.add_parser("init", parents=[parent_parser], help="Scaffold loop engine files in project")

    # run
    subparsers.add_parser("run", parents=[parent_parser], help="Manually trigger one processing cycle")

    # status
    subparsers.add_parser("status", parents=[parent_parser], help="Show status of instruction blocks")

    # trace
    trace_parser = subparsers.add_parser("trace", parents=[parent_parser], help="Show execution trace")
    trace_parser.add_argument("--limit", type=int, default=20, help="Number of trace entries to show")

    # stats
    subparsers.add_parser("stats", parents=[parent_parser], help="Show memory statistics")

    # rollback
    rollback_parser = subparsers.add_parser("rollback", parents=[parent_parser], help="Rollback to previous state")
    rollback_parser.add_argument("rollback_id", nargs="?", default=None, help="Rollback point ID")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "init": cmd_init,
        "run": cmd_run,
        "status": cmd_status,
        "trace": cmd_trace,
        "stats": cmd_stats,
        "rollback": cmd_rollback,
    }

    func = commands.get(args.command)
    if func:
        func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
