from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import unquote, urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

log = logging.getLogger("mewgent.wiki.scraper")

BASE_URL = "https://mewgenics.wiki.gg"
_HEADERS = {"User-Agent": "mewgent-wiki-scraper/1.0 (companion app)"}

MIN_IMAGE_DIM = 20


class WikiScraper:
    """Fetches Mewgenics wiki pages, extracts images and clean text."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers=_HEADERS,
            follow_redirects=True,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> WikiScraper:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def fetch_page(self, url: str) -> BeautifulSoup:
        log.info("Fetching %s", url)
        resp = self._client.get(url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    # ------------------------------------------------------------------
    # Image extraction
    # ------------------------------------------------------------------

    def extract_images(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """Return unique images from the main content area.

        Each dict has keys: ``name`` (sanitised filename) and ``url`` (absolute).
        SVGs and tiny navigation icons are excluded.
        """
        content = soup.select_one(".mw-parser-output")
        if content is None:
            return []

        seen: set[str] = set()
        results: list[dict[str, str]] = []

        for img in content.find_all("img"):
            src = img.get("src", "")
            if not src or not isinstance(src, str):
                continue

            base_name = _extract_base_filename(src)
            if not base_name or base_name.lower().endswith(".svg"):
                continue

            w = _int_attr(img, "width")
            h = _int_attr(img, "height")
            if w < MIN_IMAGE_DIM and h < MIN_IMAGE_DIM:
                continue

            if base_name in seen:
                continue
            seen.add(base_name)

            full_url = _full_image_url(src)
            results.append({"name": _sanitise_filename(base_name), "url": full_url})

        log.info("Found %d unique images", len(results))
        return results

    def download_images(
        self, images: list[dict[str, str]], output_dir: Path
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[Path] = []

        for img in images:
            dest = output_dir / img["name"]
            if dest.exists():
                log.debug("Skipping existing %s", dest.name)
                downloaded.append(dest)
                continue

            try:
                resp = self._client.get(img["url"])
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                downloaded.append(dest)
                log.debug("Downloaded %s (%d bytes)", dest.name, len(resp.content))
            except httpx.HTTPError as exc:
                log.warning("Failed to download %s: %s", img["url"], exc)

        log.info(
            "Downloaded %d / %d images to %s", len(downloaded), len(images), output_dir
        )
        return downloaded

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def extract_text(self, soup: BeautifulSoup, page_name: str) -> str:
        """Convert the main wiki content to clean markdown."""
        content = soup.select_one(".mw-parser-output")
        if content is None:
            return ""

        content = _clone_tag(content)
        _strip_wiki_chrome(content)

        markdown = md(
            str(content),
            heading_style="ATX",
            strip=["img"],
        )

        markdown = _clean_markdown(markdown, page_name)
        return markdown

    def save_text(self, text: str, page_name: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / f"{page_name}.md"
        dest.write_text(text, encoding="utf-8")
        log.info("Saved text to %s (%d chars)", dest, len(text))
        return dest


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _int_attr(tag: Tag, attr: str) -> int:
    val = tag.get(attr)
    if val is None or not isinstance(val, str):
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _extract_base_filename(src: str) -> str:
    """Get the original filename from a wiki image src.

    Thumb URLs look like ``/images/thumb/Fighter_Icon.png/81px-Fighter_Icon.png``
    Direct URLs look like ``/images/HOUSE_Appeal_Icon.png?b0bb32``
    """
    src = src.split("?")[0]
    if "/thumb/" in src:
        parts = src.split("/thumb/")[-1].split("/")
        return unquote(parts[0]) if parts else ""
    return unquote(src.rsplit("/", 1)[-1])


def _full_image_url(src: str) -> str:
    """Build the full-resolution image URL."""
    base_name = _extract_base_filename(src)
    return urljoin(BASE_URL, f"/images/{base_name}")


def _sanitise_filename(name: str) -> str:
    name = re.sub(r"[^\w.\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name


def _clone_tag(tag: Tag) -> Tag:
    """Deep-copy a BS4 tag to avoid mutating the original soup."""
    import copy

    return copy.copy(tag)


def _strip_wiki_chrome(content: Tag) -> None:
    """Remove non-content elements from the parsed HTML in-place."""
    selectors = [
        ".mw-editsection",
        "#toc",
        ".toc",
        ".navbox",
        ".catlinks",
        ".printfooter",
        ".mw-empty-elt",
        "script",
        "style",
        ".noprint",
    ]
    for sel in selectors:
        for el in content.select(sel):
            el.decompose()

    for el in content.find_all(string=re.compile(r"^Retrieved from")):
        parent = el.find_parent()
        if parent:
            for sibling in list(parent.next_siblings):
                if isinstance(sibling, Tag):
                    sibling.decompose()
            parent.decompose()

    for el in content.find_all(string=re.compile(r"^Loading")):
        parent = el.find_parent()
        if parent:
            parent.decompose()


def _clean_markdown(text: str, page_name: str) -> str:
    """Post-process the raw markdownify output."""
    title = page_name.replace("_", " ").title()
    lines = text.splitlines()

    cleaned: list[str] = []
    skip_incomplete_banner = True
    for line in lines:
        if line.strip().startswith("Retrieved from"):
            break
        if line.strip() == "Loading…":
            continue
        if skip_incomplete_banner:
            stripped = line.strip()
            if not stripped:
                continue
            if "page is incomplete" in stripped.lower():
                continue
            if "help **the mewgenics wiki**" in stripped.lower():
                continue
            if stripped.startswith("*Missing content:") or stripped.startswith(
                "***Missing content:"
            ):
                continue
            skip_incomplete_banner = False
        line = re.sub(r"\[([^\]]+)\]\(/wiki/[^\)]+\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\(#[^\)]+\)", r"\1", line)
        cleaned.append(line)

    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = result.strip()

    if not result.startswith(f"# {title}"):
        result = f"# {title}\n\n{result}"

    return result
