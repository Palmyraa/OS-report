# PBL 2 - Memory Allocation & Fragmentation Analyzer (Python)

A Python app that simulates contiguous fixed-partition memory allocation for:

- First Fit
- Best Fit
- Worst Fit

It reports per-strategy block status, internal/external fragmentation, and a final efficiency comparison table.  
This project includes:

- CLI mode (`python -m memory_analyzer.cli`)
- Tkinter desktop visualizer (`python app.py` or `python tk_app.py`)

## Features

- Input memory blocks and process sizes in KB
  - accepted formats: `100, 500, 200`, `[100, 500, 200]`, `100 500 200`, `100KB, 500KB`
- Run one algorithm or all algorithms on the same input
- Per-strategy output:
  - memory block status table
  - total internal fragmentation
  - total free memory
  - largest free block
  - external fragmentation (`total_free - largest_free`)
- Final comparison table across methods
- Optional CSV export in CLI
- Tkinter visualization:
  - block-by-block memory allocation map for each algorithm
  - per-algorithm metrics panel
  - error percentage bar chart for First Fit, Best Fit, Worst Fit

## Project Structure

```text
app.py
requirements.txt
memory_analyzer/
  core.py
  cli.py
  tk_visualizer.py
tk_app.py
```

## Run Instructions

### 1) Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) CLI App

```bash
python -m memory_analyzer.cli
```

### 3) Tkinter Visualizer

```bash
python app.py
# or
python tk_app.py
```

The Tkinter app shows:
- allocation process visualization per block for all 3 algorithms
- comparison graph of error percentages

Error percentage used in the graph:
- `(Total Internal Fragmentation + External Fragmentation) / Total Memory * 100`

## Sample Run (Exact Values)

Use this sample input:

- Memory blocks (KB): `[100, 500, 200, 300, 600]`
- Processes (KB): `[212, 417, 112, 426]`

### First Fit

| Block ID | Block Size (KB) | Status    | PID | Requested (KB) | Internal Frag (KB) |
|---|---:|---|---|---:|---:|
| 0 | 100 | FREE      | -  | -   | -   |
| 1 | 500 | ALLOCATED | P1 | 212 | 288 |
| 2 | 200 | ALLOCATED | P3 | 112 | 88  |
| 3 | 300 | FREE      | -  | -   | -   |
| 4 | 600 | ALLOCATED | P2 | 417 | 183 |

- Allocated Processes: `3/4`
- Total Internal Fragmentation: `559 KB`
- Total Free Memory: `400 KB`
- Largest Free Block: `300 KB`
- External Fragmentation: `100 KB`
- Unallocated Processes: `P4`

### Best Fit

| Block ID | Block Size (KB) | Status    | PID | Requested (KB) | Internal Frag (KB) |
|---|---:|---|---|---:|---:|
| 0 | 100 | FREE      | -  | -   | -   |
| 1 | 500 | ALLOCATED | P2 | 417 | 83  |
| 2 | 200 | ALLOCATED | P3 | 112 | 88  |
| 3 | 300 | ALLOCATED | P1 | 212 | 88  |
| 4 | 600 | ALLOCATED | P4 | 426 | 174 |

- Allocated Processes: `4/4`
- Total Internal Fragmentation: `433 KB`
- Total Free Memory: `100 KB`
- Largest Free Block: `100 KB`
- External Fragmentation: `0 KB`
- Unallocated Processes: `None`

### Worst Fit

| Block ID | Block Size (KB) | Status    | PID | Requested (KB) | Internal Frag (KB) |
|---|---:|---|---|---:|---:|
| 0 | 100 | FREE      | -  | -   | -   |
| 1 | 500 | ALLOCATED | P2 | 417 | 83  |
| 2 | 200 | FREE      | -  | -   | -   |
| 3 | 300 | ALLOCATED | P3 | 112 | 188 |
| 4 | 600 | ALLOCATED | P1 | 212 | 388 |

- Allocated Processes: `3/4`
- Total Internal Fragmentation: `659 KB`
- Total Free Memory: `300 KB`
- Largest Free Block: `200 KB`
- External Fragmentation: `100 KB`
- Unallocated Processes: `P4`

### Final Comparison Table

| Method    | Allocated | Total Internal Frag (KB) | Total External Frag (KB) | Total Free (KB) | Largest Free (KB) |
|---|---|---:|---:|---:|---:|
| First Fit | 3/4 | 559 | 100 | 400 | 300 |
| Best Fit  | 4/4 | 433 | 0   | 100 | 100 |
| Worst Fit | 3/4 | 659 | 100 | 300 | 200 |
