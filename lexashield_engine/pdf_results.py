"""
PDF Results Module
==================

Engine-specific extraction of result rows for PDF reports.
Maps output fields to PDF template columns per engine (Standard, ISO 9001, Law).
Supports both flat result objects and result["additional_data"] where applicable.
"""

from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Engine detection
# ---------------------------------------------------------------------------


def get_engine_type(output: Dict[str, Any]) -> str:
    """
    Detect engine type from output for PDF result mapping.
    Returns: "standard" | "iso" | "law"
    """
    name = (output.get("Engine") or {}).get("Name", "")
    n = name.lower()
    if "iso" in n or "9001" in n:
        return "iso"
    if "law" in n or "compliance risk" in n:
        return "law"
    return "standard"


# ---------------------------------------------------------------------------
# Overview values (report-level; same structure, different source keys)
# ---------------------------------------------------------------------------


def get_overview_values(output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract report-level values for Overview/Results header.
    Handles Document vs document, Summary vs summary (Law may use lowercase).
    """
    document = output.get("Document") or output.get("document") or {}
    summary = output.get("Summary") or output.get("summary") or {}
    library = output.get("Library") or output.get("library") or {}
    report_metadata = output.get("Report Metadata", {})
    results = output.get("Results", [])

    document_title = (
        document.get("Title") or document.get("title") or "Document"
    )
    total_detections = summary.get("Total Detections") or summary.get("total_detections")
    total_warnings = summary.get("total_warnings")
    if total_detections is None:
        total_flags = len(results)
    elif total_warnings is not None:
        total_flags = int(total_detections) + int(total_warnings)
    else:
        total_flags = int(total_detections)

    library_name = (
        library.get("Name") or library.get("name")
        or report_metadata.get("Library Used", "N/A")
    )

    total_detections = int(total_detections) if total_detections is not None else total_flags
    passed_threshold = summary.get("Passed Threshold") or summary.get("passed_threshold")
    failed_threshold = summary.get("Failed Threshold") or summary.get("failed_threshold")
    if passed_threshold is not None:
        passed_threshold = int(passed_threshold)
    if failed_threshold is not None:
        failed_threshold = int(failed_threshold)

    return {
        "document_title": document_title,
        "total_flags": total_flags,
        "total_detections": total_detections,
        "passed_threshold": passed_threshold,
        "failed_threshold": failed_threshold,
        "library_name": library_name,
        "confirmed": failed_threshold,  # legacy alias
        "warning_count": None,  # derived per-engine below if needed
    }


# ---------------------------------------------------------------------------
# Standard Engine — result rows (flat: output.py merges additional_data into result)
# ---------------------------------------------------------------------------


def _rows_standard(
    output: Dict[str, Any],
    document_title: str,
    library_name: str,
) -> List[List[Tuple[str, str]]]:
    """
    Build list of (label_key, value) rows per flag for Standard Engine.
    Standard: result is flat (term, match_percentage, score, explanation, suggestion,
    tags, flagged_text, term_ID, scores, category). Reference = library_name per report.
    """
    results = output.get("Results", [])
    rows_list = []
    for result in results:
        # score 0-1 -> percentage; or match_percentage already 0-100
        match_pct = result.get("match_percentage")
        if match_pct is None and result.get("score") is not None:
            try:
                match_pct = round(float(result["score"]) * 100, 2)
            except (TypeError, ValueError):
                match_pct = None
        match_str = f"{match_pct:.0f}%" if match_pct is not None else "N/A"

        client_term = (
            result.get("flagged_text")
            or result.get("client_term")
            or result.get("sentence_text")
            or result.get("term")
            or "N/A"
        )
        reference = result.get("reference") or "N/A"
        term_id = (
            result.get("term_ID")
            or result.get("term_id")
            or result.get("id")
        )
        explanation = (
            result.get("explanation")
            or result.get("explanation_ENG")
            or "N/A"
        )
        observation = (
            result.get("observation")
            or "N/A"
        )
        suggestion = result.get("suggestions_ENG") or result.get("suggestion") or ""
        tags = result.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        tags_str = ", ".join(tags) if tags else ""

        row = [
            ("Document Name", document_title),
            ("Reference", reference),
            ("Client Term", client_term),
            ("Match Percentage (%)", match_str),
            ("ID of Term Flagged", str(term_id)),
            ("Explanation", explanation),
            ("Observation", observation),
            ("Suggestion", suggestion),
            ("Tags", tags_str),
        ]
        rows_list.append(row)
    return rows_list


# ---------------------------------------------------------------------------
# ISO 9001 Engine — result rows (flat result; optional additional_data)
# ---------------------------------------------------------------------------


def _rows_iso(
    output: Dict[str, Any],
    document_title: str,
    _library_name: str,
) -> List[List[Tuple[str, str]]]:
    """
    Build list of (label_key, value) rows per flag for ISO 9001 Engine.
    ISO: all fields at result top level (or in additional_data); many columns.
    """
    results = output.get("Results", [])
    rows_list = []
    for result in results:
        ad = result.get("additional_data") or {}

        def _v(*keys, default="N/A"):
            for k in keys:
                val = result.get(k, ad.get(k))
                if val not in (None, ""):
                    return val if isinstance(val, str) else str(val)
            return default

        reference = _v("clause_full_reference", "clause_id", "term", default="N/A")
        clause_title = _v("Título da Cláusula", "clause_title")
        status = _v("status")
        client_term = _v("Texto Matched (Snippet)", "evidence_preview", "client_term")
        match_pct = result.get("match_percentage") or result.get("match_pct")
        if match_pct is None:
            match_pct = result.get("score")
            if match_pct is not None:
                try:
                    match_pct = round(float(match_pct) * 100, 2)
                except (TypeError, ValueError):
                    match_pct = None
        match_str = f"{match_pct:.0f}%" if match_pct is not None else _v("% de confiança")
        clause_summary = _v("Resumo da Cláusula")
        evidence = _v("Evidência")
        recommendation = _v("Correção")
        required_sections = _v("Seções Requeridas")
        expected_keywords = _v("Palavras-Chaves Esperadas")
        expected_formatting = _v("Formatacão de Dados Esperados")
        approval_responsibility = _v("Quem é Responsavel para Aprovar")
        review_frequency = _v("Frequêcia de Revisão")
        examples_kpi = _v("Exemplos de KPI")
        potential_audit_question = _v("Tipos de Pergunta Possivel em uma Auditoria")

        row = [
            ("Document Name", document_title),
            ("Reference", reference),
            ("Clause Title", clause_title),
            ("Status", status),
            ("Client Term", client_term),
            ("Match Percentage (%)", match_str),
            ("Clause Summary", clause_summary),
            ("Evidence", evidence),
            ("Recommendation", recommendation),
            ("Required Sections", required_sections),
            ("Expected Keywords", expected_keywords),
            ("Expected Formatting", expected_formatting),
            ("Approval Responsibility", approval_responsibility),
            ("Review Frequency", review_frequency),
            ("Examples of KPIs", examples_kpi),
            ("Potential Audit Question", potential_audit_question),
        ]
        rows_list.append(row)

    return rows_list


# ---------------------------------------------------------------------------
# Law Engine — result rows (flat: client_text_snippet, law_name, term_ID, observations_ENG/PT, etc.)
# ---------------------------------------------------------------------------


def _rows_law(
    output: Dict[str, Any],
    document_title: str,
    _library_name: str,
    language: str,
) -> List[List[Tuple[str, str]]]:
    """
    Build list of (label_key, value) rows per flag for Law Engine.
    Law: result has client_text_snippet, match_percentage, term_ID, law_name,
    Clause_ENG/Clause_PT, observations_ENG/observations_PT, tags_ENG/tags_PT.
    """
    results = output.get("Results", [])
    is_pt = language.lower().startswith("pt")
    rows_list = []
    for result in results:
        reference = (
            result.get("Clause_PT")
            or result.get("Clause_ENG")
            or result.get("reference_PT")
            or result.get("reference_ENG")
            or result.get("Clauses_PT")
            or result.get("Clauses_ENG")
            or result.get("references_PT")
            or result.get("references_ENG")
            or result.get("Clause")
            or result.get("clause_ENG")
        ) or "N/A"

        client_term = result.get("client_text_snippet") or result.get("client_term") or "N/A"
        match_pct = result.get("match_percentage")
        match_str = f"{match_pct:.0f}%" if match_pct is not None else "N/A"
        term_id = result.get("term_ID") or result.get("term_id") or "N/A"
        observation = (
            (result.get("observations_PT") or result.get("observations_ENG"))
            if is_pt
            else (result.get("observations_ENG") or result.get("observations_PT"))
        ) or "N/A"
        tags_raw = result.get("tags_PT") if is_pt else result.get("tags_ENG")
        if tags_raw is None:
            tags_raw = result.get("tags_ENG") or result.get("tags_PT")
        if isinstance(tags_raw, list):
            tags_str = ", ".join(str(t) for t in tags_raw)
        else:
            tags_str = str(tags_raw) if tags_raw else ""

        row = [
            ("Document Name", document_title),
            ("Reference", reference),
            ("Client Term", client_term),
            ("Match Percentage (%)", match_str),
            ("ID of Term Flagged", str(term_id)),
            ("Observation", str(observation)),
            ("Tags", tags_str),
        ]
        rows_list.append(row)
    return rows_list


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_result_rows(
    output: Dict[str, Any],
) -> List[List[Tuple[str, str]]]:
    """
    Return one list per flag: each list is (label_key, value) pairs in PDF order.
    Label keys match pdf_translations (e.g. "Document Name", "Reference", "Client Term").
    """
    overview = get_overview_values(output)
    document_title = overview["document_title"]
    library_name = overview["library_name"]
    from .pdf_translations import get_display_language
    language = get_display_language(output)

    engine_type = get_engine_type(output)
    if engine_type == "iso":
        return _rows_iso(output, document_title, library_name)
    if engine_type == "law":
        return _rows_law(output, document_title, library_name, language)
    return _rows_standard(output, document_title, library_name)
