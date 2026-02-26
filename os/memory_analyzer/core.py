from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


FIRST_FIT = "First Fit"
BEST_FIT = "Best Fit"
WORST_FIT = "Worst Fit"
ALL_STRATEGIES = [FIRST_FIT, BEST_FIT, WORST_FIT]


@dataclass
class Process:
    pid: str
    size: int
    allocated: bool = False
    block_id: Optional[int] = None


@dataclass
class MemoryBlock:
    block_id: int
    size: int
    status: str = "FREE"
    pid: Optional[str] = None
    requested_size: Optional[int] = None
    internal_frag: int = 0


@dataclass
class StrategyResult:
    strategy: str
    blocks: List[MemoryBlock]
    processes: List[Process]
    allocated_count: int
    total_internal_frag: int
    total_free: int
    largest_free: int
    external_frag: int

    @property
    def process_count(self) -> int:
        return len(self.processes)

    @property
    def unallocated_processes(self) -> List[str]:
        return [proc.pid for proc in self.processes if not proc.allocated]


def parse_size_list(raw: str) -> List[int]:
    text = raw.strip()
    if not text:
        raise ValueError("Provide at least one size value.")

    parsed_literal = _try_parse_literal_list(text)
    if parsed_literal is not None:
        return parsed_literal

    normalized = re.sub(r"(?i)\bkb\b", "", text).strip()
    normalized = normalized.strip("[](){}")
    tokens = [token for token in re.split(r"[\s,;]+", normalized) if token]

    values: List[int] = []
    for token in tokens:
        cleaned = token.strip().strip("[](){}")
        if not cleaned:
            continue

        if cleaned.lower().endswith("kb"):
            cleaned = cleaned[:-2].strip()

        if not re.fullmatch(r"[+-]?\d+", cleaned):
            raise ValueError(
                "Invalid input format. Use numbers separated by commas/spaces, "
                "e.g. 100, 500, 200 or [100, 500, 200]."
            )

        value = int(cleaned)
        if value <= 0:
            raise ValueError("Sizes must be positive integers.")
        values.append(value)

    if not values:
        raise ValueError("Provide at least one size value.")

    return values


def _try_parse_literal_list(text: str) -> Optional[List[int]]:
    if not text:
        return None

    if text[0] not in "[(" or text[-1] not in "])":
        return None

    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None

    if not isinstance(parsed, (list, tuple)):
        return None

    values: List[int] = []
    for item in parsed:
        if not isinstance(item, int):
            return None
        if item <= 0:
            raise ValueError("Sizes must be positive integers.")
        values.append(item)

    if not values:
        raise ValueError("Provide at least one size value.")

    return values


def validate_size_sequence(values: Sequence[int], label: str) -> List[int]:
    if not values:
        raise ValueError(f"{label} cannot be empty.")

    clean: List[int] = []
    for value in values:
        if not isinstance(value, int):
            raise ValueError(f"{label} must contain integers only.")
        if value <= 0:
            raise ValueError(f"{label} must contain positive integers only.")
        clean.append(value)

    return clean


def run_strategy(block_sizes: Sequence[int], process_sizes: Sequence[int], strategy: str) -> StrategyResult:
    block_sizes = validate_size_sequence(block_sizes, "Memory blocks")
    process_sizes = validate_size_sequence(process_sizes, "Processes")

    if strategy not in ALL_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    blocks = [MemoryBlock(block_id=i, size=size) for i, size in enumerate(block_sizes)]
    processes = [Process(pid=f"P{i + 1}", size=size) for i, size in enumerate(process_sizes)]

    for process in processes:
        block = _select_block(blocks, process, strategy)
        if block is None:
            continue

        block.status = "ALLOCATED"
        block.pid = process.pid
        block.requested_size = process.size
        block.internal_frag = block.size - process.size
        process.allocated = True
        process.block_id = block.block_id

    allocated_count = sum(1 for proc in processes if proc.allocated)
    total_internal = sum(block.internal_frag for block in blocks if block.status == "ALLOCATED")
    free_sizes = [block.size for block in blocks if block.status == "FREE"]
    total_free = sum(free_sizes)
    largest_free = max(free_sizes) if free_sizes else 0
    external_frag = total_free - largest_free if total_free > 0 else 0

    return StrategyResult(
        strategy=strategy,
        blocks=blocks,
        processes=processes,
        allocated_count=allocated_count,
        total_internal_frag=total_internal,
        total_free=total_free,
        largest_free=largest_free,
        external_frag=external_frag,
    )


def run_all_strategies(block_sizes: Sequence[int], process_sizes: Sequence[int]) -> List[StrategyResult]:
    return [run_strategy(block_sizes, process_sizes, strategy) for strategy in ALL_STRATEGIES]


def to_comparison_rows(results: Sequence[StrategyResult]) -> List[Dict[str, int | str]]:
    rows: List[Dict[str, int | str]] = []
    for result in results:
        rows.append(
            {
                "Method": result.strategy,
                "Allocated": f"{result.allocated_count}/{result.process_count}",
                "Total Internal Frag (KB)": result.total_internal_frag,
                "Total External Frag (KB)": result.external_frag,
                "Total Free (KB)": result.total_free,
                "Largest Free (KB)": result.largest_free,
            }
        )
    return rows


def block_rows(result: StrategyResult) -> List[Dict[str, int | str]]:
    rows: List[Dict[str, int | str]] = []
    for block in result.blocks:
        rows.append(
            {
                "Block ID": block.block_id,
                "Block Size (KB)": block.size,
                "Status": block.status,
                "PID": block.pid or "-",
                "Requested (KB)": block.requested_size if block.requested_size is not None else "-",
                "Internal Frag (KB)": block.internal_frag if block.status == "ALLOCATED" else "-",
            }
        )
    return rows


def _select_block(blocks: Sequence[MemoryBlock], process: Process, strategy: str) -> Optional[MemoryBlock]:
    candidates = [block for block in blocks if block.status == "FREE" and block.size >= process.size]
    if not candidates:
        return None

    if strategy == FIRST_FIT:
        return candidates[0]

    if strategy == BEST_FIT:
        return min(candidates, key=lambda block: (block.size, block.block_id))

    if strategy == WORST_FIT:
        return max(candidates, key=lambda block: (block.size, -block.block_id))

    return None
