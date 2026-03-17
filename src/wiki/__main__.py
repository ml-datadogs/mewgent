"""CLI entry point: python -m src.wiki"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.utils.config_loader import PROJECT_ROOT
from src.wiki.pages import WIKI_PAGES, scrape_all


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mewgent-wiki",
        description="Scrape Mewgenics wiki pages for text and images.",
    )
    parser.add_argument(
        "--pages",
        nargs="*",
        choices=list(WIKI_PAGES),
        help="Specific pages to scrape (default: all).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "wiki_data",
        help="Output directory (default: wiki_data/).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    scrape_all(args.output_dir, pages=args.pages)


if __name__ == "__main__":
    main()
