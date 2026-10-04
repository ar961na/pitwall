"""Turn `pytest -m task --junitxml=tasks.xml` into a Markdown progress table.

    pytest -m task --junitxml=tasks.xml; python scripts/task_scoreboard.py tasks.xml
CI appends the output to the job summary, so every push shows how far the tasks have come.
"""

import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

TITLES = {
    "test_task1_corners": "1 · Corner analysis",
    "test_task2_cliff": "2 · Cliff detection",
    "test_task3_splits": "3 · Time-series splits",
    "test_task4_reactive": "4 · Reactive SC policy",
    "test_task5_features": "5 · Leakage-free features",
    "test_task6_windows": "6 · Sequence windows",
}


def main(path: str) -> None:
    passed: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    for case in ET.parse(path).iter("testcase"):
        module = case.get("classname", "").split(".")[-1]
        if not module.startswith("test_task"):
            continue
        total[module] += 1
        if not any(child.tag in ("failure", "error", "skipped") for child in case):
            passed[module] += 1

    print("### Task scoreboard\n")
    print("| Task | Tests | Status |\n|------|-------|--------|")
    for module, title in TITLES.items():
        p, t = passed[module], total[module]
        status = "done" if t and p == t else ("in progress" if p else "not started")
        print(f"| {title} | {p}/{t} | {status} |")
    done = sum(1 for m in TITLES if total[m] and passed[m] == total[m])
    print(f"\n{done}/{len(TITLES)} tasks complete. Details: `docs/tasks/`.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tasks.xml")
