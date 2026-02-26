from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Sequence

from memory_analyzer.core import (
    ALL_STRATEGIES,
    BEST_FIT,
    FIRST_FIT,
    WORST_FIT,
    block_rows,
    parse_size_list,
    run_all_strategies,
    run_strategy,
    to_comparison_rows,
)


SAMPLE_BLOCKS = [100, 500, 200, 300, 600]
SAMPLE_PROCESSES = [212, 417, 112, 426]


def render_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]

    for row in str_rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(value))

    def format_row(row: Sequence[str]) -> str:
        parts = [value.ljust(widths[i]) for i, value in enumerate(row)]
        return " | ".join(parts)

    separator = "-+-".join("-" * width for width in widths)
    output = [format_row(headers), separator]
    output.extend(format_row(row) for row in str_rows)
    return "\n".join(output)


def choose_input_mode() -> tuple[List[int], List[int]]:
    print("\nInput Mode")
    print("1. Sample input")
    print("2. Manual input")
    choice = input("Choose [1/2] (default 1): ").strip() or "1"

    if choice == "2":
        block_raw = input("Enter memory block sizes in KB (comma-separated): ").strip()
        process_raw = input("Enter process sizes in KB (comma-separated): ").strip()
        return parse_size_list(block_raw), parse_size_list(process_raw)

    return SAMPLE_BLOCKS.copy(), SAMPLE_PROCESSES.copy()


def choose_algorithms() -> List[str]:
    print("\nAlgorithms")
    print("1. First Fit")
    print("2. Best Fit")
    print("3. Worst Fit")
    print("4. All methods")
    choice = input("Choose [1/2/3/4] (default 4): ").strip() or "4"

    if choice == "1":
        return [FIRST_FIT]
    if choice == "2":
        return [BEST_FIT]
    if choice == "3":
        return [WORST_FIT]
    return ALL_STRATEGIES


def print_strategy_report(result) -> None:
    print(f"\n=== {result.strategy} ===")
    rows = block_rows(result)
    headers = list(rows[0].keys())
    table_rows = [list(row.values()) for row in rows]
    print(render_table(headers, table_rows))

    print("\nFragmentation Summary")
    print(f"Allocated Processes: {result.allocated_count}/{result.process_count}")
    print(f"Total Internal Fragmentation: {result.total_internal_frag} KB")
    print(f"Total Free Memory: {result.total_free} KB")
    print(f"Largest Free Block: {result.largest_free} KB")
    print(f"External Fragmentation: {result.external_frag} KB")

    if result.unallocated_processes:
        print("Unallocated Processes:", ", ".join(result.unallocated_processes))
    else:
        print("Unallocated Processes: None")


def print_comparison_report(results) -> None:
    print("\n=== Final Comparison ===")
    rows = to_comparison_rows(results)
    headers = list(rows[0].keys())
    table_rows = [list(row.values()) for row in rows]
    print(render_table(headers, table_rows))


def ask_export_csv(results) -> None:
    save = input("\nExport summary to CSV? [y/N]: ").strip().lower()
    if save not in {"y", "yes"}:
        return

    target = input("CSV path (default: allocation_report.csv): ").strip() or "allocation_report.csv"
    path = Path(target)
    write_csv(path, results)
    print(f"Report exported to: {path.resolve()}")


def write_csv(path: Path, results: Sequence) -> None:
    comparison = to_comparison_rows(results)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Memory Allocation & Fragmentation Analyzer"])
        writer.writerow([])
        writer.writerow(list(comparison[0].keys()))
        for row in comparison:
            writer.writerow(list(row.values()))

        for result in results:
            writer.writerow([])
            writer.writerow([result.strategy])
            rows = block_rows(result)
            writer.writerow(list(rows[0].keys()))
            for row in rows:
                writer.writerow(list(row.values()))


def run() -> None:
    print("Memory Allocation & Fragmentation Analyzer")
    print("-----------------------------------------")

    try:
        blocks, processes = choose_input_mode()
        algorithms = choose_algorithms()
    except ValueError as exc:
        print(f"\nInput error: {exc}")
        return

    print(f"\nBlocks (KB): {blocks}")
    print(f"Processes (KB): {processes}")

    if len(algorithms) == len(ALL_STRATEGIES):
        results = run_all_strategies(blocks, processes)
    else:
        results = [run_strategy(blocks, processes, algorithms[0])]

    for result in results:
        print_strategy_report(result)

    print_comparison_report(results)
    ask_export_csv(results)


if __name__ == "__main__":
    run()
