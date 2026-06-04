"""
PDF Content HTML Generator
==========================

Generates HTML content for PDF reports with header/footer templates.
Converts HTML to PDF using pyhtml2pdf with proper header/footer support.
"""

import os
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import html

logger = logging.getLogger(__name__)

# Try to import PDF generation library
try:
    from pyhtml2pdf import converter
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pyhtml2pdf not available. Install with: pip install pyhtml2pdf")


def escape_html(text: Any) -> str:
    """Escape HTML special characters"""
    if text is None:
        return ""
    return html.escape(str(text))


def format_percentage(value: Any) -> str:
    """Format percentage value for display"""
    if value is None:
        return "N/A"
    try:
        if isinstance(value, (int, float)):
            return f"{value:.0f}%"
        # Try to extract number from string like "95% - GDPR 21.1.3"
        if isinstance(value, str) and "%" in value:
            return value
        return str(value)
    except:
        return str(value)


def generate_header_template(logo_path: Path, language: str = "en-US") -> str:
    """
    Generate header template HTML with logo embedded as base64.
    PAGE label is language-aware (EN: PAGE, PT: PÁGINA).
    
    Args:
        logo_path: Path to logo.png file
        language: Report language for PAGE label, e.g. "en-US" or "pt-BR"
        
    Returns:
        Header template HTML string
    """
    from .pdf_translations import translate_label
    page_label = translate_label("PAGE", language)
    # Encode logo as base64 so it works inside the headerTemplate context
    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    return f"""
<div style="
    -webkit-print-color-adjust: exact;
    width: 100%;
    padding: 0 74.4px;
    margin-top: 30px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 16px;
    font-family: Arial, Helvetica, sans-serif;
">
    <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
        <img src="data:image/png;base64,{logo_b64}" style="width: 22px; height: 26px; opacity: 0.7; display: block;">
        <span style="letter-spacing: 0.8px; font-size: 17px; font-weight: bold; color: #989bac; white-space: nowrap;">LEXA SHIELD</span>
    </div>
    <div style="flex: 1; height: 1px; background-color: #989bac; min-width: 20px;"></div>
    <div style="display: flex; align-items: center; border: 3px solid #989bac; flex-shrink: 0;">
        <span style="-webkit-print-color-adjust: exact; background-color: #989bac; color: #ffffff; padding: 1px 6px; font-size: 10px; display: block;">{page_label}</span>
        <span class="pageNumber" style="background-color: #ffffff; color: #6982a5; padding: 0 6px; font-size: 10px; display: block; min-width: 16px; text-align: center;"></span>
    </div>
</div>
"""


# Footer text by language (copyright line only; www.lexashield.com unchanged)
_FOOTER_COPYRIGHT_EN = "© Lexa Shield 2026. All rights reserved. Copying or distribution is prohibited."
_FOOTER_COPYRIGHT_PT = "© Lexa Shield 2026. Todos os direitos reservados. Proibida a cópia ou distribuição."


def generate_footer_template(language: str = "en-US") -> str:
    """
    Generate footer template HTML. Text is language-aware (en vs pt-BR).

    Args:
        language: Report language; any value accepted by ``normalize_language``
            (e.g. ``"en-US"``, ``"pt-BR"``, ``"Português"``).

    Returns:
        Footer template HTML string.
    """
    from .pdf_translations import normalize_language
    is_pt = normalize_language(language).lower().startswith("pt")
    copyright_text = _FOOTER_COPYRIGHT_PT if is_pt else _FOOTER_COPYRIGHT_EN
    return f"""
<div style="
    -webkit-print-color-adjust: exact;
    width: 100%;
    padding: 0 74.4px;
    margin-bottom: 30px;
    box-sizing: border-box;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10px;
    color: #989bac;
">
    <div style="flex-shrink: 0;">
        <span>{copyright_text}</span>
    </div>
    <div style="flex-shrink: 0;">
        <span>www.lexashield.com</span>
    </div>
</div>
"""


def generate_legal_disclaimer_page_html(output: Dict[str, Any]) -> str:
    """
    Full page with only the legal disclaimer (placed after the overview page).
    Kept separate so long text is not split awkwardly across pages.
    """
    from .pdf_translations import translate_label, get_display_language

    language = get_display_language(output)
    legal_disclaimer = output.get("Legal Disclaimer", "Legal Disclaimer - ENG")

    return f"""
    <div class="page-container legal-disclaimer-page">
        <div class="disclaimer disclaimer-standalone"><b>{translate_label("Legal Disclaimer", language)}</b> {escape_html(legal_disclaimer)}</div>
    </div>
    """


def generate_overview_page_html(output: Dict[str, Any]) -> str:
    """Generate HTML for overview page"""
    
    from .pdf_translations import translate_label
    
    # Extract values from output structure
    report_metadata = output.get("Report Metadata", {})
    engine = output.get("Engine", {})
    session = output.get("Session", {})
    signature = output.get("Signature", {})
    
    from .pdf_translations import get_display_language, language_code_to_display_name
    language = get_display_language(output)
    language_display = language_code_to_display_name(language, language)
    
    analysis_id = report_metadata.get("Analysis ID", "N/A")
    report_generated = report_metadata.get("Report Generated on", "N/A")
    engine_name = engine.get("Name", "N/A")
    engine_version = engine.get("Version", "N/A")
    library_name = report_metadata.get("Library Used", output.get("Library", {}).get("Name", "N/A"))
    library_version = report_metadata.get("Library Version", output.get("Library", {}).get("Version", "N/A"))
    
    compliance_signature = report_metadata.get("Compliance Signature", session.get("Hash", "N/A"))
    integrity_seal = signature.get("Value", "N/A")
    # Hide Integrity Seal ID row when value indicates an error (e.g. SIGNATURE_ERROR_*)
    show_integrity_seal = (
        integrity_seal and
        isinstance(integrity_seal, str) and
        "error" not in integrity_seal.lower()
    )
    integrity_seal_row = ""
    if show_integrity_seal:
        integrity_seal_row = f"""
            <tr>
                <td>{translate_label("Integrity Seal ID", language)}</td>
                <td>{escape_html(integrity_seal)}</td>
            </tr>"""
    verification_standard = signature.get("Algorithm", "RSA-PSS-SHA256")
    security_level = f"{signature.get('Key Size', 2048)} bits"
    important_notice_default = (
        "Qualquer modificação neste resultado invalidará a assinatura"
        if isinstance(language, str) and language.lower().startswith("pt")
        else "Any modification to this output will invalidate the signature"
    )
    important_notice = signature.get("Note", important_notice_default)
    
    return f"""
    <div class="page-container">
        <div class="page-title">{translate_label("Overview", language)}</div>

        <div class="explanation-text">
            {translate_label("intro", language)}
        </div>

        <div class="explanation-title">{translate_label("Recommended Action", language)}</div>
        <div class="explanation-text">
            {translate_label("recommended_action", language)}
        </div>

        <div class="explanation-title">{translate_label("System Information", language)}</div>

        <table>
            <tr>
                <td>{translate_label("Analysis ID", language)}</td>
                <td>{escape_html(analysis_id)}</td>
            </tr>
            <tr>
                <td>{translate_label("Report Generated on", language)}</td>
                <td>{escape_html(report_generated)}</td>
            </tr>
            <tr>
                <td>{translate_label("Engine Name", language)}</td>
                <td>{escape_html(engine_name)}</td>
            </tr>
            <tr>
                <td>{translate_label("Engine Version", language)}</td>
                <td>{escape_html(engine_version)}</td>
            </tr>
            <tr>
                <td>{translate_label("Library Used", language)}</td>
                <td>{escape_html(library_name)}</td>
            </tr>
            <tr>
                <td>{translate_label("Library Version", language)}</td>
                <td>{escape_html(library_version)}</td>
            </tr>
            <tr>
                <td>{translate_label("Language", language)}</td>
                <td>{escape_html(language_display)}</td>
            </tr>
        </table>

        <div class="explanation-title">{translate_label("Security & Trust", language)}</div>
        <table class="security-info-table">
            <tr>
                <td>{translate_label("Compliance Signature", language)}</td>
                <td>{escape_html(compliance_signature)}</td>
            </tr>
            {integrity_seal_row}
            <tr>
                <td>{translate_label("Verification Standard", language)}</td>
                <td>{escape_html(verification_standard)}</td>
            </tr>
            <tr>
                <td>{translate_label("Security Level", language)}</td>
                <td>{escape_html(security_level)}</td>
            </tr>
            <tr>
                <td>{translate_label("Important Notice", language)}</td>
                <td>{escape_html(important_notice)}</td>
            </tr>
        </table>
    </div>
    """


def generate_results_page_html(output: Dict[str, Any]) -> str:
    """
    Generate HTML for results page(s) using engine-specific field mapping.
    Overview (Total Flags, etc.) is the same; result rows come from pdf_results.
    """
    from .pdf_results import get_overview_values, get_result_rows, get_engine_type
    from .pdf_translations import translate_label

    from .pdf_translations import get_display_language
    language = get_display_language(output)

    overview = get_overview_values(output)
    total_flags = overview["total_flags"]
    is_iso = get_engine_type(output) == "iso"
    rows_list = get_result_rows(output)

    # For no-flag outputs, render only the explanatory text block (no summary table / flag cards)
    if total_flags == 0 or not rows_list:
        no_flags_html = f"""
    <div class="page-container">
        <div class="page-title">{translate_label("Results", language)}</div>
        <div class="results-no-flag-explain">
            <p>{escape_html(translate_label("results_no_flags_p1", language))}</p>
            <p>{escape_html(translate_label("results_no_flags_p2", language))}</p>
            <p>{escape_html(translate_label("results_no_flags_p3", language))}</p>
            <p>{escape_html(translate_label("results_no_flags_p4", language))}</p>
        </div>
    </div>
        """
        return no_flags_html

    html_parts = []
    html_parts.append("""
    <div class="page-container">
        <div class="page-title">""" + translate_label("Results", language) + """</div>

        <table>
    """)
    if is_iso:
        # ISO: 3 summary rows — Total de Avisos (Total Detections), Confirmado (Passed Threshold), Aviso (Failed Threshold)
        total_detections = overview["total_detections"] if overview.get("total_detections") is not None else total_flags
        passed = overview.get("passed_threshold")
        failed = overview.get("failed_threshold")
        html_parts.append("""
            <tr>
                <td>""" + translate_label("Total de Avisos", language) + """</td>
                <td>""" + str(total_detections) + """</td>
            </tr>""")
        if passed is not None:
            html_parts.append("""
            <tr>
                <td>""" + translate_label("Confirmado", language) + """</td>
                <td>""" + str(passed) + """</td>
            </tr>""")
        if failed is not None:
            html_parts.append("""
            <tr>
                <td>""" + translate_label("Aviso", language) + """</td>
                <td>""" + str(failed) + """</td>
            </tr>""")
    else:
        # Standard / Law: single Total Flags row
        html_parts.append("""
            <tr>
                <td>""" + translate_label("Total Flags", language) + """</td>
                <td>""" + str(total_flags) + """</td>
            </tr>""")
    html_parts.append("""
        </table>
    """)

    flag_label = translate_label("FLAG", language)
    for idx, row in enumerate(rows_list, 1):
        html_parts.append(f"""
        <div class="flag-order-number">{flag_label} {idx}</div>

        <table class="flag-result-table">
        """)
        # Optional columns: only show row when value exists (no row for empty Suggestion/Tags)
        optional_columns = frozenset({"Suggestion", "Tags"})
        for label_key, value in row:
            if value is None:
                value = ""
            value_str = str(value).strip()
            if label_key in optional_columns and not value_str:
                continue
            display_value = value_str or "N/A"
            html_parts.append(f"""
            <tr>
                <td>{translate_label(label_key, language)}</td>
                <td>{escape_html(display_value)}</td>
            </tr>
            """)
        html_parts.append("</table>")

    html_parts.append("</div>")
    return "\n".join(html_parts)


def generate_definitions_page_html(output: Dict[str, Any]) -> str:
    """Generate HTML for definitions page"""
    
    from .pdf_definitions import get_definitions_for_pdf
    from .pdf_translations import translate_label
    
    # Get language from output
    from .pdf_translations import get_display_language
    language = get_display_language(output)
    
    # Get definitions (from output if provided, otherwise engine-specific defaults)
    all_definitions = get_definitions_for_pdf(output)
    
    definitions_html = ""
    for term, definition in all_definitions.items():
        term_label = translate_label(term, language)
        definitions_html += f"""
            <tr>
                <td>{escape_html(term_label)}</td>
                <td>{escape_html(definition)}</td>
            </tr>
        """
    
    return f"""
    <div class="page-container">
        <div class="page-title">{translate_label("Definitions", language)}</div>

        <div class="explanation-text">
            {translate_label("definitions_intro", language)}
        </div>

        <table class="defenitions-table">
            {definitions_html}
        </table>
    </div>
    """


def generate_content_html(
    output: Dict[str, Any],
    styles_path: Optional[Path] = None
) -> str:
    """
    Generate complete HTML for PDF content from engine output
    
    Args:
        output: Complete output dictionary from format_complete_output()
        styles_path: Path to styles.css file (optional, defaults to SDK package pdf_assets/styles.css)
    
    Returns:
        Complete HTML string ready for PDF conversion
    """
    
    # Validate styles file exists
    if not styles_path.exists():
        raise FileNotFoundError(f"Styles file not found: {styles_path}")
    
    # Read CSS styles
    css_content = styles_path.read_text(encoding='utf-8')
    
    # Generate page sections (overview first after cover; legal disclaimer on its own page next)
    overview_page = generate_overview_page_html(output)
    legal_disclaimer_page = generate_legal_disclaimer_page_html(output)
    results_page = generate_results_page_html(output)
    definitions_page = generate_definitions_page_html(output)
    
    # Combine all pages
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=8.5in, initial-scale=1.0">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
    <style>
    {css_content}
    </style>
</head>
<body>
    {overview_page}
    {legal_disclaimer_page}
    {results_page}
    {definitions_page}
</body>
</html>"""
    
    return html_content


def generate_content_pdf(
    output: Dict[str, Any],
    output_path: Path,
    logo_path: Optional[Path] = None,
    styles_path: Optional[Path] = None,
    temp_html_path: Optional[Path] = None
) -> Path:
    """
    Generate content PDF file from engine output (without cover/last page)
    
    Args:
        output: Complete output dictionary from format_complete_output()
        output_path: Path where PDF should be saved
        logo_path: Path to logo.png file (optional, for header)
        styles_path: Path to styles.css file (optional)
        temp_html_path: Temporary path for HTML file (optional, auto-generated if not provided)
    
    Returns:
        Path to generated content PDF file
    
    Raises:
        ImportError: If pyhtml2pdf is not installed
        Exception: If PDF generation fails
    """
    
    if not PDF_AVAILABLE:
        raise ImportError(
            "pyhtml2pdf is required for PDF generation. "
            "Install with: pip install pyhtml2pdf"
        )
    
    # Validate logo file exists
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo file not found: {logo_path}")
    
    # Validate styles file exists
    if not styles_path.exists():
        raise FileNotFoundError(f"Styles file not found: {styles_path}")
    
    # Get report language (library language preferred) for header/footer
    from .pdf_translations import get_display_language
    language = get_display_language(output)
    
    # Generate HTML
    html_content = generate_content_html(output, styles_path)
    
    # Write HTML to temporary file
    if temp_html_path is None:
        temp_html_path = output_path.parent / f"temp_{output_path.stem}.html"
    else:
        temp_html_path = Path(temp_html_path)
    
    temp_html_path.write_text(html_content, encoding='utf-8')
    
    try:
        # Generate header and footer templates (both are language-aware)
        header_template = generate_header_template(logo_path, language)
        footer_template = generate_footer_template(language)
        
        # Convert HTML to PDF with header/footer
        html_file_url = f"file:///{temp_html_path.absolute().as_posix()}"
        
        print_options = {
            "displayHeaderFooter": True,
            "headerTemplate": header_template,
            "footerTemplate": footer_template,
            "marginTop": 1,     # space reserved for the header on every page
            "marginBottom": 1,  # space reserved for the footer on every page
            "marginLeft": 0,
            "marginRight": 0,
            "printBackground": True,
        }
        
        converter.convert(
            html_file_url,
            str(output_path),
            install_driver=False,
            print_options=print_options,
        )
        
        logger.info(f"Content PDF generated successfully: {output_path}")
        
        # Clean up temporary HTML file
        if temp_html_path.exists():
            temp_html_path.unlink()
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate content PDF: {e}")
        # Clean up temporary HTML file even on error
        if temp_html_path.exists():
            temp_html_path.unlink()
        raise

