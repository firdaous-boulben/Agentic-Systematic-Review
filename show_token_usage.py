import csv
from pathlib import Path
from collections import defaultdict


FILE = Path(__file__).resolve().parent / "data" / "token_usage.csv"

if not FILE.exists():
    print("No token usage recorded yet.")
    raise SystemExit


stats = defaultdict(lambda: {
    "calls": 0,
    "input": 0,
    "output": 0,
    "total": 0,
    "uncounted": 0
})


with open(FILE, newline="", encoding="utf-8") as f:

    reader = csv.DictReader(f)

    for row in reader:

        key = (row["run_label"], row["agent"])

        stats[key]["calls"] += 1

        if row["status"] != "success":
            stats[key]["uncounted"] += 1
            continue

        stats[key]["input"] += int(row["input_tokens"])
        stats[key]["output"] += int(row["output_tokens"])
        stats[key]["total"] += int(row["total_tokens"])


print("\nGROQ TOKEN USAGE REPORT\n")

print(
    f"{'RUN':<15} {'AGENT':<30} "
    f"{'CALLS':<8} {'INPUT':<10} "
    f"{'OUTPUT':<10} {'TOTAL':<10} {'UNCOUNTED':<10}"
)

print("-" * 100)

totals = defaultdict(int)

for (run, agent), values in sorted(stats.items()):

    print(
        f"{run:<15} {agent:<30} "
        f"{values['calls']:<8} "
        f"{values['input']:<10} "
        f"{values['output']:<10} "
        f"{values['total']:<10} "
        f"{values['uncounted']:<10}"
    )

    totals[run] += values["total"]


print("-" * 100)

for run, total in sorted(totals.items()):
    print(f"{run}: {total:,} measured tokens")

if any(v["uncounted"] for v in stats.values()):
    print("\nWarning: Some requests have no usage data.")
    print("Totals may be incomplete.")