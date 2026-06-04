"""
PDF Merger
==========

Merges multiple PDF files into a single PDF report.
Used to combine cover page, content pages, and last page template.
"""

import logging
from pathlib import Path
from typing import List
from pypdf import PdfWriter

logger = logging.getLogger(__name__)


def merge_pdfs(
    pdf_paths: List[Path],
    output_path: Path
) -> Path:
    """
    Merge multiple PDF files into a single PDF.
    
    Args:
        pdf_paths: List of paths to PDF files to merge (in order)
        output_path: Path where merged PDF should be saved
        
    Returns:
        Path to generated merged PDF
        
    Raises:
        FileNotFoundError: If any input PDF file doesn't exist
        Exception: If PDF merging fails
    """
    # Validate all input files exist
    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    merger = PdfWriter()
    
    # Append all PDFs in order
    for pdf_path in pdf_paths:
        logger.debug(f"Merging PDF: {pdf_path}")
        merger.append(str(pdf_path))
    
    # Write merged PDF
    with open(output_path, "wb") as f:
        merger.write(f)
    
    logger.info(f"Merged {len(pdf_paths)} PDFs into: {output_path}")
    return output_path

