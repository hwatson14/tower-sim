from __future__ import annotations

import argparse
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pytest with duration reporting using the repo's test-tier defaults.",
    )
    parser.add_argument("--limit", type=int, default=20, help="Number of slowest tests to display.")
    parser.add_argument(
        "--include-expensive",
        action="store_true",
        help="Include tests marked expensive.",
    )
    parser.add_argument(
        "--include-slow",
        action="store_true",
        help="Include tests marked slow.",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional pytest arguments (paths, -k expressions, etc).",
    )
    args = parser.parse_args()

    marker_terms = []
    if not args.include_slow:
        marker_terms.append("not slow")
    if not args.include_expensive:
        marker_terms.append("not expensive")
    marker_expr = " and ".join(marker_terms)

    cmd = ["pytest", f"--durations={args.limit}"]
    if marker_expr:
        cmd.extend(["-m", marker_expr])
    cmd.extend(args.pytest_args)

    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
