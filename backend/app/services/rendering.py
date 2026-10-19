"""Render source PDF pages to PNG for admin review evidence."""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz


def render_page_bytes(pdf_path: str | Path, page: int, *, zoom: float = 2.0) -> bytes:
    """Render a single 1-based ``page`` and return PNG bytes (for on-demand evidence)."""
    doc = fitz.open(pdf_path)
    try:
        idx = page - 1
        if idx < 0 or idx >= len(doc):
            raise IndexError(f"page {page} out of range (1..{len(doc)})")
        pix = doc[idx].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")
    finally:
        doc.close()


def render_pages(
    pdf_path: str | Path,
    out_dir: str | Path,
    *,
    pages: list[int] | None = None,
    zoom: float = 2.0,
) -> list[str]:
    """Render 1-based ``pages`` (or all) to ``out_dir``; return written file paths."""
    pdf_path = Path(pdf_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    written: list[str] = []
    targets = [p - 1 for p in pages] if pages else range(len(doc))
    matrix = fitz.Matrix(zoom, zoom)
    for idx in targets:
        if idx < 0 or idx >= len(doc):
            continue
        pix = doc[idx].get_pixmap(matrix=matrix)
        dest = out / f"page_{idx + 1:03d}.png"
        pix.save(str(dest))
        written.append(str(dest))
    doc.close()
    return written

