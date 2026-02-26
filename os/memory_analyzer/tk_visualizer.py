from __future__ import annotations

import random
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Sequence

from memory_analyzer.core import ALL_STRATEGIES, StrategyResult, block_rows, parse_size_list, run_all_strategies


SAMPLE_BLOCKS = [100, 500, 200, 300, 600]
SAMPLE_PROCESSES = [212, 417, 112, 426]


def _error_percentage(result: StrategyResult, total_memory: int) -> float:
    if total_memory <= 0:
        return 0.0
    wasted = result.total_internal_frag + result.external_frag
    return (wasted / total_memory) * 100.0


def _unallocated_percentage(result: StrategyResult) -> float:
    if result.process_count <= 0:
        return 0.0
    return (len(result.unallocated_processes) / result.process_count) * 100.0


class StrategyView(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=10)
        self._result: StrategyResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        canvas_wrap = ttk.Frame(self)
        canvas_wrap.pack(fill="both", expand=False)

        self.canvas = tk.Canvas(
            canvas_wrap,
            height=270,
            background="#f8fafc",
            highlightthickness=1,
            highlightbackground="#d4dbe7",
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        y_scroll = ttk.Scrollbar(canvas_wrap, orient="vertical", command=self.canvas.yview)
        y_scroll.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=y_scroll.set)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        legend = ttk.Frame(self)
        legend.pack(fill="x", pady=(7, 4))
        self._legend_chip(legend, "#34d399", "Requested")
        self._legend_chip(legend, "#f59e0b", "Internal Fragment")
        self._legend_chip(legend, "#d1d5db", "Free Block")

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, pady=(6, 0))

        self.table = ttk.Treeview(table_frame, show="headings", height=8)
        self.table.pack(side="left", fill="both", expand=True)

        table_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        table_scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=table_scroll.set)

        columns = [
            "Block ID",
            "Block Size (KB)",
            "Status",
            "PID",
            "Requested (KB)",
            "Internal Frag (KB)",
        ]
        self.table.configure(columns=columns)
        widths = [80, 120, 120, 80, 130, 140]
        for column, width in zip(columns, widths):
            self.table.heading(column, text=column)
            self.table.column(column, width=width, anchor="center")

        metrics_box = ttk.LabelFrame(self, text="Metrics", padding=(10, 8))
        metrics_box.pack(fill="x", pady=(10, 0))

        labels = [
            "Allocated Processes",
            "Total Internal Fragmentation",
            "Total Free Memory",
            "Largest Free Block",
            "External Fragmentation",
            "Unallocated Processes",
        ]
        self.metric_vars: Dict[str, tk.StringVar] = {}
        for row, label in enumerate(labels):
            var = tk.StringVar(value="-")
            self.metric_vars[label] = var
            ttk.Label(metrics_box, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)
            ttk.Label(metrics_box, textvariable=var).grid(row=row, column=1, sticky="w", pady=2)

    def _legend_chip(self, parent: ttk.Frame, color: str, text: str) -> None:
        chip = ttk.Frame(parent)
        chip.pack(side="left", padx=(0, 14))
        swatch = tk.Canvas(chip, width=12, height=12, highlightthickness=0, background=self.canvas["background"])
        swatch.create_rectangle(0, 0, 12, 12, fill=color, outline=color)
        swatch.pack(side="left", padx=(0, 5))
        ttk.Label(chip, text=text).pack(side="left")

    def render(self, result: StrategyResult) -> None:
        self._result = result
        self._draw_memory_map(result)
        self._fill_table(result)
        self._fill_metrics(result)

    def _fill_table(self, result: StrategyResult) -> None:
        self.table.delete(*self.table.get_children())
        for row in block_rows(result):
            values = [
                row["Block ID"],
                row["Block Size (KB)"],
                row["Status"],
                row["PID"],
                row["Requested (KB)"],
                row["Internal Frag (KB)"],
            ]
            self.table.insert("", "end", values=values)

    def _fill_metrics(self, result: StrategyResult) -> None:
        self.metric_vars["Allocated Processes"].set(f"{result.allocated_count}/{result.process_count}")
        self.metric_vars["Total Internal Fragmentation"].set(f"{result.total_internal_frag} KB")
        self.metric_vars["Total Free Memory"].set(f"{result.total_free} KB")
        self.metric_vars["Largest Free Block"].set(f"{result.largest_free} KB")
        self.metric_vars["External Fragmentation"].set(f"{result.external_frag} KB")
        if result.unallocated_processes:
            self.metric_vars["Unallocated Processes"].set(", ".join(result.unallocated_processes))
        else:
            self.metric_vars["Unallocated Processes"].set("None")

    def _on_canvas_resize(self, _event: tk.Event) -> None:
        if self._result is not None:
            self._draw_memory_map(self._result)

    def _draw_memory_map(self, result: StrategyResult) -> None:
        self.canvas.delete("all")
        if not result.blocks:
            return

        width = max(self.canvas.winfo_width(), 650)
        left_margin = 170
        right_margin = 20
        top_margin = 16
        block_height = 30
        row_gap = 20
        chart_width = max(width - left_margin - right_margin, 280)
        max_size = max(block.size for block in result.blocks)

        for index, block in enumerate(result.blocks):
            y0 = top_margin + index * (block_height + row_gap)
            y1 = y0 + block_height
            bar_width = chart_width * (block.size / max_size)
            x0 = left_margin
            x1 = left_margin + bar_width

            self.canvas.create_text(
                10,
                y0 + block_height / 2,
                anchor="w",
                text=f"B{block.block_id} ({block.size} KB)",
                fill="#263341",
                font=("Segoe UI", 9, "bold"),
            )

            if block.status == "FREE":
                self.canvas.create_rectangle(x0, y0, x1, y1, fill="#d1d5db", outline="#718096")
                self.canvas.create_text(
                    x0 + 6,
                    y0 + block_height / 2,
                    anchor="w",
                    text="FREE",
                    fill="#334155",
                    font=("Segoe UI", 9),
                )
            else:
                requested = block.requested_size or 0
                requested_width = bar_width * (requested / block.size)

                self.canvas.create_rectangle(x0, y0, x0 + requested_width, y1, fill="#34d399", outline="#0f766e")
                if requested_width < bar_width:
                    self.canvas.create_rectangle(x0 + requested_width, y0, x1, y1, fill="#f59e0b", outline="#b45309")
                self.canvas.create_rectangle(x0, y0, x1, y1, outline="#374151")

                self.canvas.create_text(
                    x0 + 6,
                    y0 + block_height / 2,
                    anchor="w",
                    text=f"{block.pid}: {requested} KB",
                    fill="#0f172a",
                    font=("Segoe UI", 9),
                )
                if block.internal_frag:
                    self.canvas.create_text(
                        x1 - 6,
                        y0 + block_height / 2,
                        anchor="e",
                        text=f"Frag {block.internal_frag} KB",
                        fill="#7c2d12",
                        font=("Segoe UI", 8),
                    )

            self.canvas.create_text(
                x1 + 7,
                y0 + block_height / 2,
                anchor="w",
                text=f"{block.size} KB",
                fill="#475569",
                font=("Segoe UI", 8),
            )

        total_height = top_margin + len(result.blocks) * (block_height + row_gap)
        self.canvas.configure(scrollregion=(0, 0, width, total_height + 8))


class ComparisonView(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=10)
        self._rows: List[Dict[str, float | str]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text=(
                "Error % = (Total Internal Fragmentation + External Fragmentation) "
                "/ Total Memory * 100"
            ),
        ).pack(anchor="w", pady=(0, 8))

        self.canvas = tk.Canvas(
            self,
            height=320,
            background="#f8fafc",
            highlightthickness=1,
            highlightbackground="#d4dbe7",
        )
        self.canvas.pack(fill="x", expand=False)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.table = ttk.Treeview(table_frame, show="headings", height=8)
        self.table.pack(side="left", fill="both", expand=True)

        table_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        table_scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=table_scroll.set)

        columns = [
            "Algorithm",
            "Error %",
            "Unallocated %",
            "Allocated",
            "Internal Frag (KB)",
            "External Frag (KB)",
        ]
        self.table.configure(columns=columns)
        widths = [130, 100, 120, 100, 150, 150]
        for column, width in zip(columns, widths):
            self.table.heading(column, text=column)
            self.table.column(column, width=width, anchor="center")

    def render(self, results: Sequence[StrategyResult], total_memory: int) -> None:
        rows: List[Dict[str, float | str]] = []
        for result in results:
            rows.append(
                {
                    "Algorithm": result.strategy,
                    "Error %": _error_percentage(result, total_memory),
                    "Unallocated %": _unallocated_percentage(result),
                    "Allocated": f"{result.allocated_count}/{result.process_count}",
                    "Internal Frag (KB)": result.total_internal_frag,
                    "External Frag (KB)": result.external_frag,
                }
            )

        self._rows = rows
        self._fill_table(rows)
        self._draw_chart(rows)

    def _fill_table(self, rows: Sequence[Dict[str, float | str]]) -> None:
        self.table.delete(*self.table.get_children())
        for row in rows:
            self.table.insert(
                "",
                "end",
                values=(
                    row["Algorithm"],
                    f"{float(row['Error %']):.2f}",
                    f"{float(row['Unallocated %']):.2f}",
                    row["Allocated"],
                    row["Internal Frag (KB)"],
                    row["External Frag (KB)"],
                ),
            )

    def _on_canvas_resize(self, _event: tk.Event) -> None:
        if self._rows:
            self._draw_chart(self._rows)

    def _draw_chart(self, rows: Sequence[Dict[str, float | str]]) -> None:
        self.canvas.delete("all")
        if not rows:
            return

        width = max(self.canvas.winfo_width(), 650)
        height = max(self.canvas.winfo_height(), 320)
        left = 65
        right = 20
        top = 20
        bottom = 52
        plot_height = height - top - bottom
        plot_width = width - left - right
        axis_y = height - bottom
        colors = ["#0ea5e9", "#10b981", "#f97316"]

        self.canvas.create_line(left, top, left, axis_y, fill="#475569", width=1.2)
        self.canvas.create_line(left, axis_y, width - right, axis_y, fill="#475569", width=1.2)

        for tick in range(0, 101, 20):
            y = axis_y - (tick / 100.0) * plot_height
            self.canvas.create_line(left - 4, y, left, y, fill="#64748b")
            self.canvas.create_text(left - 8, y, text=str(tick), anchor="e", fill="#475569", font=("Segoe UI", 8))
            if tick:
                self.canvas.create_line(left, y, width - right, y, fill="#e2e8f0")

        count = len(rows)
        slot = plot_width / max(count, 1)
        bar_width = min(90, slot * 0.5)

        for index, row in enumerate(rows):
            error_pct = float(row["Error %"])
            center_x = left + slot * (index + 0.5)
            x0 = center_x - bar_width / 2
            x1 = center_x + bar_width / 2
            y0 = axis_y - (error_pct / 100.0) * plot_height

            color = colors[index % len(colors)]
            self.canvas.create_rectangle(x0, y0, x1, axis_y, fill=color, outline=color)
            self.canvas.create_text(
                center_x,
                y0 - 8,
                text=f"{error_pct:.2f}%",
                anchor="s",
                fill="#1f2937",
                font=("Segoe UI", 9, "bold"),
            )
            self.canvas.create_text(
                center_x,
                axis_y + 18,
                text=str(row["Algorithm"]),
                anchor="n",
                fill="#334155",
                font=("Segoe UI", 9),
            )


class AllocationVisualizerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Memory Allocation Visualizer (Tkinter)")
        self.geometry("1240x860")
        self.minsize(1020, 700)
        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(10, 6))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        controls = ttk.LabelFrame(top, text="Input", padding=(12, 10))
        controls.pack(fill="x")

        self.blocks_var = tk.StringVar(value=", ".join(str(v) for v in SAMPLE_BLOCKS))
        self.processes_var = tk.StringVar(value=", ".join(str(v) for v in SAMPLE_PROCESSES))
        self.status_var = tk.StringVar(value="Press Enter or click Run Analysis.")

        ttk.Label(controls, text="Memory blocks (KB):").grid(row=0, column=0, sticky="w")
        blocks_entry = ttk.Entry(controls, textvariable=self.blocks_var, width=80)
        blocks_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(controls, text="Processes (KB):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.processes_var, width=80).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0)
        )

        button_row = ttk.Frame(controls)
        button_row.grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Button(button_row, text="Run Analysis", command=self.run_analysis).pack(side="left")
        ttk.Button(button_row, text="Use Sample Values", command=self.use_sample_values).pack(side="left", padx=(8, 0))
        
        random_frame = ttk.Frame(button_row)
        random_frame.pack(side="left", padx=(8, 0))
        ttk.Button(random_frame, text="Random Values", command=self.use_random_blocks).pack(side="left")
        ttk.Label(random_frame, text="Total (KB):").pack(side="left", padx=(8, 4))
        
        self.random_target_var = tk.StringVar(value="")
        ttk.Entry(random_frame, textvariable=self.random_target_var, width=10).pack(side="left")

        controls.columnconfigure(1, weight=1)

        ttk.Label(top, textvariable=self.status_var).pack(anchor="w", pady=(8, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self.strategy_views: Dict[str, StrategyView] = {}
        for strategy in ALL_STRATEGIES:
            view = StrategyView(self.notebook)
            self.notebook.add(view, text=strategy)
            self.strategy_views[strategy] = view

        self.comparison_view = ComparisonView(self.notebook)
        self.notebook.add(self.comparison_view, text="Error Comparison")

        self.bind("<Return>", self._on_enter_pressed)
        blocks_entry.focus_set()
        self.after(120, self.run_analysis)

    def _on_enter_pressed(self, _event: tk.Event) -> None:
        self.run_analysis()

    def use_sample_values(self) -> None:
        self.blocks_var.set(", ".join(str(v) for v in SAMPLE_BLOCKS))
        self.processes_var.set(", ".join(str(v) for v in SAMPLE_PROCESSES))
        self.run_analysis()

    def use_random_blocks(self) -> None:
        try:
            total_size_input = self.random_target_var.get().strip()
            
            # If the user enters a number in the box, split up to that total
            if total_size_input.isdigit():
                total_target = int(total_size_input)
                if total_target > 0:
                    num_blocks = random.randint(3, 8)
                    random_blocks = []
                    remaining = total_target
                    
                    for i in range(num_blocks - 1):
                        if remaining <= 10:
                            break
                        # Leave some for remaining blocks
                        max_val = max(10, remaining - (10 * (num_blocks - 1 - i)))
                        # Ensure we step in chunks of 5 or 10 for cleaner numbers
                        val = random.randint(5, max(5, int(max_val * 0.6)))
                        val = (val // 5) * 5
                        if val == 0: val = 5
                        
                        if val >= remaining:
                            break
                        
                        random_blocks.append(val)
                        remaining -= val
                    
                    if remaining > 0:
                        random_blocks.append(remaining)
                        
                    random.shuffle(random_blocks)
                    self.blocks_var.set(", ".join(str(v) for v in random_blocks))
                else:
                    self._generate_default_random_blocks()
            else:
                self._generate_default_random_blocks()
                
        except Exception:
            self._generate_default_random_blocks()
        
        self.run_analysis()

    def _generate_default_random_blocks(self) -> None:
        num_blocks = random.randint(4, 8)
        random_blocks = [random.randint(5, 80) * 10 for _ in range(num_blocks)]
        self.blocks_var.set(", ".join(str(v) for v in random_blocks))

    def run_analysis(self) -> None:
        try:
            block_sizes = parse_size_list(self.blocks_var.get())
            process_sizes = parse_size_list(self.processes_var.get())
        except ValueError as exc:
            self.status_var.set(f"Input error: {exc}")
            messagebox.showerror("Invalid Input", str(exc))
            return

        results = run_all_strategies(block_sizes, process_sizes)
        total_memory = sum(block_sizes)

        for result in results:
            self.strategy_views[result.strategy].render(result)

        self.comparison_view.render(results, total_memory)
        self.status_var.set(
            f"Computed all 3 algorithms | Blocks: {len(block_sizes)} | "
            f"Processes: {len(process_sizes)} | Total memory: {total_memory} KB"
        )


def run() -> None:
    app = AllocationVisualizerApp()
    app.mainloop()


if __name__ == "__main__":
    run()
