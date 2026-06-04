"""
PDF Translations Module
========================

Bilingual translations for PDF report labels and column headers.
Supports English and Portuguese.
"""

# Header/footer and section labels (PAGE in header, FLAG in results)
PAGE_LABEL_EN = "PAGE"
PAGE_LABEL_PT = "PÁGINA"
FLAG_LABEL_EN = "FLAG"
FLAG_LABEL_PT = "AVISO"

# Column headers and labels for Overview page
OVERVIEW_LABELS_EN = {
    "PAGE": PAGE_LABEL_EN,
    "FLAG": FLAG_LABEL_EN,
    "Overview": "Overview",
    "Recommended Action": "Recommended Action",
    "System Information": "System Information",
    "Security & Trust": "Security & Trust",
    "Legal Disclaimer": "Legal Disclaimer:",
    "Analysis ID": "Analysis ID",
    "Report Generated on": "Report Generated on",
    "Engine Name": "Engine Name",
    "Engine Version": "Engine Version",
    "Library Used": "Library Used",
    "Library Version": "Library Version",
    "Language": "Language",
    "Compliance Signature": "Compliance Signature",
    "Integrity Seal ID": "Integrity Seal ID",
    "Verification Standard": "Verification Standard",
    "Security Level": "Security Level",
    "Important Notice": "Important Notice",
}

OVERVIEW_LABELS_PT = {
    "PAGE": PAGE_LABEL_PT,
    "FLAG": FLAG_LABEL_PT,
    "Overview": "Visão Geral",
    "Recommended Action": "Ação Recomendada",
    "System Information": "Informações do Sistema",
    "Security & Trust": "Segurança e Confiança",
    "Legal Disclaimer": "Aviso Legal:",
    "Analysis ID": "ID da Análise",
    "Report Generated on": "Relatório Gerado em",
    "Engine Name": "Nome do Motor",
    "Engine Version": "Versão do Motor",
    "Library Used": "Biblioteca Usada",
    "Library Version": "Versão da Biblioteca",
    "Language": "Idioma",
    "Compliance Signature": "Assinatura de Conformidade",
    "Integrity Seal ID": "ID do Selo de Integridade",
    "Verification Standard": "Padrão de Verificação",
    "Security Level": "Nível de Segurança",
    "Important Notice": "Aviso Importante",
}

# Column headers for Results page (Standard / Law)
RESULTS_LABELS_EN = {
    "Results": "Results",
    "Total Flags": "Total Flags",
    "Document Name": "Document Name",
    "Reference": "Reference",
    "Client Term": "Client Term",
    "Match Percentage (%)": "Match Percentage (%)",
    "ID of Term Flagged": "ID of Term Flagged",
    "Explanation": "Explanation",
    "Observation": "Observation",
    "Suggestion": "Suggestion",
    "Tags": "Tags",
    "Article": "Article",
    "Clause": "Clause",
    "Confirmed": "Confirmed",
    "Warning": "Warning",
    "Total de Avisos": "Total Notices",
    "Confirmado": "Confirmed",
    "Aviso": "Notice",
}

RESULTS_LABELS_PT = {
    "Results": "Resultados",
    "Total Flags": "Total de Alertas",
    "Document Name": "Nome do Documento",
    "Reference": "Referência",
    "Client Term": "Termo do Cliente",
    "Match Percentage (%)": "Porcentagem de Correspondência (%)",
    "ID of Term Flagged": "ID do Termo Sinalizado",
    "Explanation": "Explicação",
    "Observation": "Observação",
    "Suggestion": "Sugestão",
    "Tags": "Tags",
    "Article": "Artigo",
    "Clause": "Cláusula",
    "Confirmed": "Confirmado",
    "Warning": "Aviso",
    "Total de Avisos": "Total de Avisos",
    "Confirmado": "Confirmado",
    "Aviso": "Aviso",
}

# ISO 9001–specific result column labels (and definition term labels)
RESULTS_LABELS_ISO_EN = {
    "Clause Title": "Clause Title",
    "Status": "Status",
    "Clause Summary": "Clause Summary",
    "Evidence": "Evidence",
    "Recommendation": "Recommendation",
    "Required Sections": "Required Sections",
    "Expected Keywords": "Expected Keywords",
    "Expected Formatting": "Expected Formatting",
    "Approval Responsibility": "Approval Responsibility",
    "Review Frequency": "Review Frequency",
    "Examples of KPIs": "Examples of KPIs",
    "Potential Audit Question": "Potential Audit Question",
    "Flags": "Flags",
    "Disclaimer": "Disclaimer",
    "Explanation": "Explanation",
}

RESULTS_LABELS_ISO_PT = {
    "Clause Title": "Título da Cláusula",
    "Status": "Status",
    "Clause Summary": "Resumo da Cláusula",
    "Evidence": "Evidência",
    "Recommendation": "Recomendação",
    "Required Sections": "Seções Requeridas",
    "Expected Keywords": "Palavras-Chaves Esperadas",
    "Expected Formatting": "Formatacão de Dados Esperados",
    "Approval Responsibility": "Quem é Responsavel para Aprovar",
    "Review Frequency": "Frequêcia de Revisão",
    "Examples of KPIs": "Exemplos de KPI",
    "Potential Audit Question": "Tipos de Pergunta Possivel em uma Auditoria",
    "Flags": "Aviso",
    "Disclaimer": "Aviso Importante",
    "Explanation": "Explicação",
}

# Definitions page labels
DEFINITIONS_LABELS_EN = {
    "Definitions": "Definitions",
    "definitions_intro": "This section explains the fields and terms used throughout your report to help you understand how results are generated and how to interpret each signal.",
}

DEFINITIONS_LABELS_PT = {
    "Definitions": "Definições",
    "definitions_intro": "Esta seção explica os campos e termos usados em todo o seu relatório para ajudá-lo a entender como os resultados são gerados e como interpretar cada sinal.",
}

# Overview page explanatory text
OVERVIEW_TEXT_EN = {
    "intro": "This report provides an automated analysis of submitted content to surface potential risk signals based on the selected Lexa Shield library. Results are intended to support informed human review by highlighting relevant patterns with transparency and traceability.",
    "recommended_action": "Findings should be reviewed by an appropriate human reviewer or authorized professional to assess context, relevance, and any required follow-up before action is taken.",
}

OVERVIEW_TEXT_PT = {
    "intro": "Este relatório fornece uma análise automatizada do conteúdo enviado para identificar possíveis sinais de risco com base na biblioteca Lexa Shield selecionada. Os resultados destinam-se a apoiar a revisão humana informada, destacando padrões relevantes com transparência e rastreabilidade.",
    "recommended_action": "Os achados devem ser revisados por um revisor humano apropriado ou profissional autorizado para avaliar o contexto, relevância e qualquer acompanhamento necessário antes que qualquer ação seja tomada.",
}

# Results page explanatory text for no-flag outputs
RESULTS_TEXT_EN = {
    "results_no_flags_p1": "No risk signals were identified based solely on the specific Lexa Shield libraries and shields enabled, the configured detection logic, and the content provided for analysis at the time of review. This result reflects automated pattern-based analysis and does not constitute a legal determination, regulatory approval, certification of compliance, guarantee, or assurance that the content is lawful, accurate, complete, or free from regulatory or legal exposure.",
    "results_no_flags_p2": "Lexa Shield is not a law firm, does not provide legal advice, and does not create an attorney-client relationship. Regulatory obligations vary by jurisdiction, industry, factual context, and evolving agency guidance, and certain risks may fall outside the scope, coverage, or technical capabilities of the enabled libraries or may not be detectable through automated analysis.",
    "results_no_flags_p3": "This output is provided for informational and decision-support purposes only and may not be relied upon as a substitute for independent legal or compliance review. Users remain solely responsible for independently reviewing, validating, and approving content and for ensuring compliance with applicable laws and regulations, including but not limited to FTC, FCC, consumer protection, advertising, privacy, and professional practice rules in the United States; LGPD, CDC, CLT, and related regulations in Brazil; and GDPR, ePrivacy, consumer protection, and other applicable European Union regulations.",
    "results_no_flags_p4": "All business, legal, and regulatory decisions are made at the user's own discretion and risk.",
}

RESULTS_TEXT_PT = {
    "results_no_flags_p1": "Nenhum sinal de risco foi identificado com base apenas nas bibliotecas e shields Lexa Shield habilitados, na lógica de detecção configurada e no conteúdo fornecido para análise no momento da revisão. Este resultado reflete análise automatizada baseada em padrões e não constitui determinação legal, aprovação regulatória, certificação de conformidade, garantia ou asseguração de que o conteúdo seja lícito, preciso, completo ou livre de exposição legal ou regulatória.",
    "results_no_flags_p2": "A Lexa Shield não é escritório de advocacia, não fornece aconselhamento jurídico e não cria relação advogado-cliente. As obrigações regulatórias variam por jurisdição, setor, contexto fático e orientações de órgãos reguladores em constante evolução, e certos riscos podem ficar fora do escopo, da cobertura ou das capacidades técnicas das bibliotecas habilitadas, ou podem não ser detectáveis por meio de análise automatizada.",
    "results_no_flags_p3": "Este resultado é fornecido apenas para fins informativos e de suporte à decisão e não deve ser utilizado como substituto de revisão jurídica ou de compliance independente. Os usuários permanecem exclusivamente responsáveis por revisar, validar e aprovar conteúdo de forma independente e por garantir conformidade com leis e regulamentos aplicáveis, incluindo, entre outros, FTC, FCC, regras de defesa do consumidor, publicidade, privacidade e prática profissional nos Estados Unidos; LGPD, CDC, CLT e normas relacionadas no Brasil; e GDPR, ePrivacy, defesa do consumidor e outras normas aplicáveis da União Europeia.",
    "results_no_flags_p4": "Todas as decisões de negócio, legais e regulatórias são tomadas por conta e risco exclusivo do usuário.",
}


def normalize_language(lang: str) -> str:
    """
    Normalize any language value to a canonical form.

    Args:
        lang: Raw language value from engine output.

    Returns:
        Normalized language code, e.g. ``"pt-BR"`` or ``"en-US"``.
    """
    if not lang:
        return "en-US"

    normalized = lang.strip().lower()
    if normalized in ("português", "portuguese", "portugues"):
        return "pt-BR"
    if normalized in ("english", "inglês", "ingles"):
        return "en-US"

    if normalized.startswith("pt"):
        return "pt-BR"
    if normalized.startswith("en"):
        return "en-US"

    return lang.strip()


def get_labels(language: str = "en-US") -> dict:
    """
    Get all labels for a specific language.
    Includes Standard/Law and ISO-specific result column labels.

    Args:
        language: Language code or display name; any value accepted by
            ``normalize_language`` (e.g. ``"en-US"``, ``"pt-BR"``, ``"Português"``).

    Returns:
        Dictionary containing all labels for the language.
    """
    is_portuguese = normalize_language(language).lower().startswith("pt")
    
    if is_portuguese:
        return {
            **OVERVIEW_LABELS_PT,
            **RESULTS_LABELS_PT,
            **RESULTS_LABELS_ISO_PT,
            **DEFINITIONS_LABELS_PT,
            **OVERVIEW_TEXT_PT,
            **RESULTS_TEXT_PT,
        }
    else:
        return {
            **OVERVIEW_LABELS_EN,
            **RESULTS_LABELS_EN,
            **RESULTS_LABELS_ISO_EN,
            **DEFINITIONS_LABELS_EN,
            **OVERVIEW_TEXT_EN,
            **RESULTS_TEXT_EN,
        }


def language_code_to_display_name(code: str, ui_language: str = "en-US") -> str:
    """
    Map a locale/language code (or display name) to a human-readable name for
    the overview table.  Accepts both codes (``"pt-BR"``, ``"en-US"``) and
    display names (``"Português"``, ``"English"``), normalizing via
    ``normalize_language`` first.

    Args:
        code: Language code or display name from engine output.
        ui_language: The UI language used to choose the display name locale.

    Returns:
        Human-readable language name, e.g. ``"English"`` or ``"Português"``.
    """
    if not code:
        return "N/A"
    normalized = normalize_language(str(code).strip())
    ui_is_pt = normalize_language(str(ui_language)).lower().startswith("pt")
    if normalized.lower().startswith("en"):
        return "Inglês" if ui_is_pt else "English"
    if normalized.lower().startswith("pt"):
        return "Português" if ui_is_pt else "Portuguese"
    return str(code).strip()


def get_display_language(output: dict) -> str:
    """
    Return a normalized BCP-47-style language code for report rendering.

    Prefers Library language over Report Metadata / Engine language so the
    PDF UI follows the law-pack/library language rather than the submitted
    text language.  Always returns a code understood by ``normalize_language``
    (e.g. ``"pt-BR"`` or ``"en-US"``), regardless of whether the engine stored
    a display name (``"Português"``) or a locale code (``"pt-BR"``).

    Args:
        output: Full engine output dict (Report Metadata, Engine, Library, …).

    Returns:
        Normalized language code, e.g. ``"pt-BR"`` or ``"en-US"``.
    """
    lib_lang = output.get("Library") or {}
    if isinstance(lib_lang, dict):
        lang = lib_lang.get("Language")
        if lang:
            return normalize_language(str(lang))
    raw = (
        output.get("Report Metadata", {}).get("Language")
        or output.get("Engine", {}).get("Language")
        or "en-US"
    )
    return normalize_language(str(raw))


def translate_label(key: str, language: str = "en-US", default: str = None) -> str:
    """
    Translate a label key to the specified language.

    Args:
        key: Label key (e.g., ``"Overview"``, ``"Total Flags"``).
        language: Language code or display name; normalized via ``get_labels``.
        default: Fallback value when key is not found (uses key itself if omitted).

    Returns:
        Translated label string.
    """
    labels = get_labels(language)
    return labels.get(key, default or key)

