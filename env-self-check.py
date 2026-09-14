#!/usr/bin/env python3
"""保留原运行命令；实际 Task 1 产物位于 tasks/task1/。"""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    runner = runpy.run_path(str(Path(__file__).resolve().parent / "run"))
    sys.exit(runner["main"](["task1", *sys.argv[1:]]))
