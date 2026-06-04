"""
PDF Cover Page Generator
========================

Generates a cover page by overlaying a title on a template PDF.
Handles text width calculation, line splitting, and PDF generation.
"""

import io
import logging
from pathlib import Path
from typing import Optional
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# Helvetica-Bold standard character widths (units at 1000pt per em)
# Used to calculate the exact text width for horizontal centering
HELVETICA_BOLD_WIDTHS = {
    ' ': 278,
    'A': 722, 'B': 722, 'C': 722, 'D': 778, 'E': 667, 'F': 611, 'G': 778,
    'H': 722, 'I': 278, 'J': 500, 'K': 722, 'L': 667, 'M': 833, 'N': 722,
    'O': 778, 'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722,
    'V': 667, 'W': 944, 'X': 667, 'Y': 667, 'Z': 611,
    'a': 556, 'b': 611, 'c': 556, 'd': 611, 'e': 556, 'f': 333, 'g': 611,
    'h': 611, 'i': 278, 'j': 278, 'k': 556, 'l': 278, 'm': 889, 'n': 611,
    'o': 611, 'p': 611, 'q': 611, 'r': 389, 's': 556, 't': 333, 'u': 611,
    'v': 556, 'w': 778, 'x': 556, 'y': 556, 'z': 500,
}


def get_text_width(text: str, font_size: float) -> float:
    """Return the exact width (pts) of text rendered in Helvetica-Bold."""
    units = sum(HELVETICA_BOLD_WIDTHS.get(c, 556) for c in text)
    return units * font_size / 1000.0


def split_text_into_two_lines(text: str, max_chars: int = 17) -> tuple[str, Optional[str]]:
    """
    Split text into two lines if it exceeds max_chars, without breaking words.
    Returns a tuple (line1, line2) or (text, None) if no split needed.
    """
    if len(text) <= max_chars:
        return (text, None)
    
    # Find the best split point (space) near the middle
    words = text.split()
    if len(words) == 1:
        # Single word longer than max_chars - can't split without breaking
        return (text, None)
    
    # Try to split near the middle
    mid_point = len(text) // 2
    best_split_idx = 0
    min_distance = float('inf')
    
    # Find the space closest to the middle
    current_pos = 0
    for i, word in enumerate(words[:-1]):  # Don't check after last word
        current_pos += len(word)
        distance = abs(current_pos - mid_point)
        if distance < min_distance:
            min_distance = distance
            best_split_idx = i + 1
        current_pos += 1  # Add space after word
    
    line1 = ' '.join(words[:best_split_idx])
    line2 = ' '.join(words[best_split_idx:])
    
    return (line1, line2)


def create_text_overlay_pdf(
    page_width: float,
    page_height: float,
    lines: list[str],
    font_size: float,
    y_baseline: float,
    line_spacing: float = 1.2
) -> bytes:
    """
    Build a minimal valid PDF in memory containing the given text lines:
      - Font   : Helvetica-Bold (built-in Type1, no embedding needed)
      - Color  : white  (1 1 1 rg)
      - Aligned: horizontally centered
      - y_baseline is measured from the bottom of the page (PDF convention)
      - lines: list of strings to render (e.g., ["LINE 1", "LINE 2"] or ["SINGLE LINE"])

    Returns the PDF as bytes so it can be loaded by PdfReader(BytesIO(...)).
    """
    # Filter out None values (for single-line case)
    lines = [line for line in lines if line is not None]
    
    if not lines:
        lines = [""]
    
    # Calculate vertical positioning
    # y_baseline is for the first (top) line
    # Line spacing is a multiplier of font_size
    line_height = font_size * line_spacing
    
    # Build content stream for all lines
    content_parts = [
        "BT\n",
        f"/F1 {font_size} Tf\n",
        "1 1 1 rg\n",  # white fill color
    ]
    
    for i, line in enumerate(lines):
        text_width = get_text_width(line, font_size)
        x = (page_width - text_width) / 2.0
        y = y_baseline - (i * line_height)  # First line at y_baseline, subsequent lines below
        
        # Use Tm (text matrix) for absolute positioning instead of Td (relative)
        # Tm format: a b c d e f Tm where (e, f) is the absolute position
        # Identity matrix: 1 0 0 1 e f Tm
        content_parts.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm\n")
        content_parts.append(f"({line}) Tj\n")
    
    content_parts.append("ET\n")
    content_stream = "".join(content_parts)
    stream_bytes = content_stream.encode("latin-1")

    # PDF object bodies
    catalog = b"<< /Type /Catalog /Pages 2 0 R >>"
    pages   = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    page    = (
        f"<< /Type /Page /Parent 2 0 R "
        f"/MediaBox [0 0 {page_width:.2f} {page_height:.2f}] "
        f"/Contents 4 0 R "
        f"/Resources << /Font << /F1 5 0 R >> >> >>"
    ).encode()
    content = (
        f"<< /Length {len(stream_bytes)} >>\nstream\n".encode()
        + stream_bytes
        + b"\nendstream"
    )
    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

    # Assemble body and record byte offsets for the xref table
    header  = b"%PDF-1.4\n"
    body    = b""
    offsets = []

    for i, data in enumerate([catalog, pages, page, content, font], start=1):
        offsets.append(len(header) + len(body))
        body += f"{i} 0 obj\n".encode() + data + b"\nendobj\n"

    xref_pos = len(header) + len(body)

    # Cross-reference table
    xref = b"xref\n0 6\n"
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()

    return header + body + xref + trailer


def generate_cover_page(
    template_path: Path,
    output_path: Path,
    title_text: str,
    font_size: float = 41,
    y_from_top: Optional[float] = None
) -> Path:
    """
    Add title_text to the first page of template PDF and write to output PDF.
    If title_text has more than 17 characters, it will be split into 2 lines.

    Parameters
    ----------
    template_path : Path to the cover page template PDF
    output_path   : Path where the cover page PDF should be saved
    title_text    : The text to add (e.g. "CLIENT DOC TITLE")
    font_size     : Point size — adjust to match the look you want
    y_from_top    : Fraction from the TOP of the page where the text center sits
                    If None, automatically uses 0.325 for 1 line, 0.29 for 2 lines
                    0.0 = top edge, 1.0 = bottom edge
    
    Returns
    -------
    Path to generated cover page PDF
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Cover page template not found: {template_path}")
    
    reader = PdfReader(template_path)
    writer = PdfWriter()

    cover      = reader.pages[0]
    page_w     = float(cover.mediabox.width)
    page_h     = float(cover.mediabox.height)

    # Split text into lines if needed
    line1, line2 = split_text_into_two_lines(title_text, max_chars=17)
    lines = [line1] if line2 is None else [line1, line2]
    
    # Automatically adjust y_from_top based on number of lines if not provided
    num_lines = len(lines)
    if y_from_top is None:
        if num_lines == 1:
            y_from_top = 0.325  # 1 line case
        else:
            y_from_top = 0.29   # 2 lines case
    
    logger.debug(f"Cover page: {num_lines} lines, y_from_top={y_from_top}")
    
    # Calculate vertical positioning
    # y_from_top refers to the center of the text block
    line_spacing = 1.2
    line_height = font_size * line_spacing
    
    if line2 is None:
        # Single line: y_baseline is at the center point
        text_block_height = font_size
        y_baseline = page_h * (1.0 - y_from_top)
    else:
        # Two lines: center the block, then calculate baseline for first line
        text_block_height = font_size + line_height  # first line + spacing to second line
        block_center_y = page_h * (1.0 - y_from_top)
        y_baseline = block_center_y + (text_block_height / 2.0) - font_size

    logger.debug(f"Cover page size: {page_w:.1f} x {page_h:.1f} pt")
    logger.debug(f"Title lines: {lines}")
    logger.debug(f"Font size: {font_size} pt, Y baseline: {y_baseline:.1f} pt")

    # Build the overlay and merge it on top of the cover page
    overlay_bytes  = create_text_overlay_pdf(page_w, page_h, lines, font_size, y_baseline, line_spacing)
    overlay_reader = PdfReader(io.BytesIO(overlay_bytes))
    cover.merge_page(overlay_reader.pages[0])

    writer.add_page(cover)

    # Keep all remaining pages unchanged
    for page in reader.pages[1:]:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    logger.info(f"Cover page generated: {output_path}")
    return output_path

