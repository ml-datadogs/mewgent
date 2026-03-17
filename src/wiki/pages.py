from __future__ import annotations

import logging
from pathlib import Path

from src.wiki.scraper import WikiScraper

log = logging.getLogger("mewgent.wiki.pages")

WIKI_PAGES: dict[str, str] = {
    "house": "https://mewgenics.wiki.gg/wiki/House",
    "classes": "https://mewgenics.wiki.gg/wiki/Classes",
    "stats": "https://mewgenics.wiki.gg/wiki/Stats",
    "breeding": "https://mewgenics.wiki.gg/wiki/Breeding",
}


def scrape_page(
    scraper: WikiScraper,
    name: str,
    url: str,
    output_dir: Path,
) -> None:
    """Scrape a single wiki page: extract text + download images."""
    log.info("Scraping page '%s' from %s", name, url)
    soup = scraper.fetch_page(url)

    text = scraper.extract_text(soup, name)
    scraper.save_text(text, name, output_dir / "text")

    images = scraper.extract_images(soup)
    scraper.download_images(images, output_dir / "images" / name)


def scrape_all(
    output_dir: Path,
    *,
    pages: list[str] | None = None,
) -> None:
    """Scrape all (or selected) wiki pages.

    Args:
        output_dir: Root directory for scraped data.
        pages: Optional list of page names to scrape. Defaults to all.
    """
    targets = WIKI_PAGES
    if pages:
        unknown = set(pages) - set(WIKI_PAGES)
        if unknown:
            log.warning("Unknown page names ignored: %s", unknown)
        targets = {k: v for k, v in WIKI_PAGES.items() if k in pages}

    if not targets:
        log.error("No valid pages to scrape")
        return

    with WikiScraper() as scraper:
        for name, url in targets.items():
            try:
                scrape_page(scraper, name, url, output_dir)
            except Exception:
                log.exception("Failed to scrape '%s'", name)

    log.info("Scraping complete. Output at %s", output_dir)
