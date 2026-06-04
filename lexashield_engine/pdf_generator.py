"""
PDF Report Generator for LexaShield Engine SDK
===============================================

Main orchestrator for PDF report generation.
Coordinates cover page generation, content generation, and PDF merging.

The PDF structure includes:
- Cover page (with title overlay)
- Overview page (System Information, Security & Trust)
- Legal disclaimer (full page after overview)
- Results pages (with flags)
- Definitions page
- Last page template

All HTML classes and styles are preserved from the original template design.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile

from .pdf_cover import generate_cover_page
from .pdf_content import generate_content_pdf
from .pdf_merger import merge_pdfs

logger = logging.getLogger(__name__)


def generate_pdf_from_output(
    output: Dict[str, Any],
    output_path: Path,
    cover_template_path: Optional[Path] = None,
    last_page_template_path: Optional[Path] = None,
    logo_path: Optional[Path] = None,
    styles_path: Optional[Path] = None,
    document_title: Optional[str] = None
) -> Path:
    """
    Generate complete PDF report from engine output.
    
    This function orchestrates the full PDF generation process:
    1. Generates cover page with title overlay
    2. Generates content pages (Overview, Results, Definitions) with header/footer
    3. Merges cover + content + last page into final PDF
    
    Args:
        output: Complete output dictionary from format_complete_output()
        output_path: Path where final PDF should be saved
        cover_template_path: Path to cover page template PDF (optional)
        last_page_template_path: Path to last page template PDF (optional)
        logo_path: Path to logo.png file (optional, for header)
        styles_path: Path to styles.css file (optional)
        document_title: Title to display on cover page (optional, defaults to Document.Title)
    
    Returns:
        Path to generated PDF file
    
    Raises:
        ImportError: If required libraries are not installed
        FileNotFoundError: If template files are not found
        Exception: If PDF generation fails
    """
    
    # Determine paths to template files and assets (within SDK package)
    # English: cover-page-template.pdf, last-page-template.pdf
    # Portuguese (pt-BR): cover-page-template(pt-br).pdf, last-page-template(pt-br).pdf
    sdk_package_dir = Path(__file__).parent
    assets_dir = sdk_package_dir / "pdf_assets"
    cover_en = assets_dir / "cover-page-template.pdf"
    last_en = assets_dir / "last-page-template.pdf"
    cover_pt = assets_dir / "cover-page-template(pt-br).pdf"
    last_pt = assets_dir / "last-page-template(pt-br).pdf"

    from .pdf_translations import get_display_language
    language = get_display_language(output)
    is_pt = isinstance(language, str) and language.lower().startswith("pt")

    if cover_template_path is None:
        cover_template_path = cover_pt if (is_pt and cover_pt.exists()) else cover_en
    if last_page_template_path is None:
        last_page_template_path = last_pt if (is_pt and last_pt.exists()) else last_en
    
    if logo_path is None:
        logo_path = assets_dir / "logo.png"
    
    if styles_path is None:
        styles_path = assets_dir / "styles.css"
    
    # Get document title for cover page
    if document_title is None:
        document_title = output.get("Document", {}).get("Title", "Analysis Report")
    
    # Validate required files exist
    if not cover_template_path.exists():
        raise FileNotFoundError(f"Cover template not found: {cover_template_path}")
    if not last_page_template_path.exists():
        raise FileNotFoundError(f"Last page template not found: {last_page_template_path}")
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found: {logo_path}")
    if not styles_path.exists():
        raise FileNotFoundError(f"Styles file not found: {styles_path}")
    
    # Create temporary directory for intermediate files
    temp_dir = Path(tempfile.mkdtemp(prefix="pdf_gen_"))
    try:
        cover_pdf = temp_dir / "cover-page.pdf"
        content_pdf = temp_dir / "content.pdf"
        
        # Step 1: Generate cover page with title overlay
        logger.info("Generating cover page...")
        generate_cover_page(
            template_path=cover_template_path,
            output_path=cover_pdf,
            title_text=document_title,
            font_size=41
        )
        
        # Step 2: Generate content pages (Overview, Results, Definitions) with header/footer
        logger.info("Generating content pages...")
        generate_content_pdf(
            output=output,
            output_path=content_pdf,
            logo_path=logo_path,
            styles_path=styles_path
        )
        
        # Step 3: Merge all PDFs (cover + content + last page)
        logger.info("Merging PDFs...")
        merge_pdfs(
            pdf_paths=[cover_pdf, content_pdf, last_page_template_path],
            output_path=output_path
        )
        
        logger.info(f"PDF report generated successfully: {output_path}")
        return output_path
        
    finally:
        # Clean up temporary files
        try:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")
