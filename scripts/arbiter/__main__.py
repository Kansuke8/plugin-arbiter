import argparse
import sys
from pathlib import Path

from arbiter.detect import detect
from arbiter.report import to_markdown
from arbiter.scan import scan


def main(argv=None):
    parser = argparse.ArgumentParser(prog="arbiter", description="Report conflict candidates between Claude Code plugins.")
    parser.add_argument("--claude-home", default=Path.home() / ".claude", type=Path)
    parser.add_argument("--project", default=Path.cwd(), type=Path)
    parser.add_argument("--threshold", default=0.3, type=float, help="description similarity threshold (0-1)")
    args = parser.parse_args(argv)

    result = scan(args.claude_home, args.project)
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    sys.stdout.write(to_markdown(result, detect(result["sources"], args.threshold)))


if __name__ == "__main__":
    main()
