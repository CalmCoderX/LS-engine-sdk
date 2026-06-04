"""
PDF Definitions Module
======================

Engine-specific definitions for PDF reports in English and Portuguese.
Used only for PDF generation, not saved in JSON or sent to backend.
"""

from typing import Dict, Optional

# ---------------------------------------------------------------------------
# ISO Engine Definitions
# ---------------------------------------------------------------------------

ISO_DEFINITIONS_EN = {
    "Analysis ID": "Unique identifier for this analysis report.",
    "Approval Responsibility": "Position or department responsible for formal approval.",
    "Clause Summary": "Summary of the clause requirements according to the standard.",
    "Clause Title": "Name or short description of the clause requirement.",
    "Client Term": "Excerpt from the document compared against the requirement.",
    "Compliance Signature": "A digital fingerprint that identifies the specific content analyzed in this report.",
    "Confirmed": "Number of clauses adequately addressed in the document.",
    "Disclaimer": "Legal notice explaining that the report is for informational purposes and is not a substitute for an audit or certification.",
    "Document Name": "Name or title of the analyzed document.",
    "Engine Name": "Name of the analysis system that generated this report.",
    "Engine Version": "Version of the analysis system used.",
    "Evidence": "Types of documents or records required by the standard to prove compliance.",
    "Examples of KPIs": "Suggested performance indicators to accompany the clause.",
    "Expected Formatting": "Recommended frequency for reviewing the document or process.",
    "Expected Keywords": "Terms commonly found in documents that meet the requirement.",
    "Explanation": "Expected format for documentation and records.",
    "Flags": "Number of clauses that require revision or are missing.",
    "Integrity Seal ID": "Cryptographic signature proving the report has not been modified.",
    "Language": "The language used by the analytics engine to process this report.",
    "Library Used": "Name of the reference library or rule set used in the analysis.",
    "Library Version": "Version of the reference library or rule set used.",
    "Match Percentage (%)": "The percentage of the text that meets the clause's requirement.",
    "Potential Audit Question": "Typical questions auditors may ask regarding this clause.",
    "Recommendation": "Guidance on corrections or improvements needed to comply with the clause.",
    "Reference": "Normative reference for the corresponding ISO clause.",
    "Report Generated on": "Date and time the report was generated.",
    "Required Sections": "Sections or items that should be included in the document.",
    "Review Frequency": "A cryptographic signature verifying that this report has not been altered or tampered with.",
    "Security Level": "Size of the cryptographic key used to protect the report (in bits).",
    "Status": "Analysis result: Fulfilled, under review, or absent.",
    "Total Flags": "Total number of clauses analyzed in the document.",
    "Verification Standard": "Cryptographic algorithm used to generate the report's integrity seal.",
}

ISO_DEFINITIONS_PT = {
    "Analysis ID": "Identificador único deste relatório de análise.",
    "Approval Responsibility": "Cargo ou área responsável pela aprovação formal.",
    "Clause Summary": "Resumo do que a cláusula exige conforme a norma.",
    "Clause Title": "Nome ou descrição curta do requisito da cláusula.",
    "Client Term": "Trecho do seu documento que foi comparado ao requisito.",
    "Compliance Signature": "Impressão digital que identifica o conteúdo exato analisado neste relatório.",
    "Confirmed": "Quantidade de cláusulas consideradas adequadamente atendidas no documento.",
    "Disclaimer": "Texto legal que explica que o relatório é informativo e não substitui auditoria ou certificação.",
    "Document Name": "Nome ou título do documento analisado.",
    "Engine Name": "Nome do sistema de análise que gerou este relatório.",
    "Engine Version": "Versão do sistema de análise utilizada.",
    "Evidence": "Tipos de documento ou registro que a norma exige para comprovar atendimento.",
    "Examples of KPIs": "Indicadores de desempenho sugeridos para acompanhar a cláusula.",
    "Expected Formatting": "Periodicidade recomendada para revisar o documento ou o processo.",
    "Expected Keywords": "Termos que costumam aparecer em documentos que atendem ao requisito.",
    "Explanation": "Formato esperado para documentação e registros.",
    "Flags": "Quantidade de cláusulas que precisam de revisão ou estão ausentes.",
    "Integrity Seal ID": "Assinatura criptográfica que comprova que o relatório não foi alterado.",
    "Language": "Idioma em que o motor de análise processou este relatório.",
    "Library Used": "Nome da biblioteca de referência ou conjunto de regras usado na análise.",
    "Library Version": "Versão da biblioteca de referência ou conjunto de regras usado.",
    "Match Percentage (%)": "Percentual em que seu texto atende ao requisito da cláusula.",
    "Potential Audit Question": "Perguntas típicas que auditores podem fazer sobre esta cláusula.",
    "Recommendation": "Orientações sobre o que corrigir ou melhorar para atender à cláusula.",
    "Reference": "Referência normativa da cláusula ISO correspondente.",
    "Report Generated on": "Data e hora em que o relatório foi gerado.",
    "Required Sections": "Seções ou itens que devem constar no documento.",
    "Review Frequency": "Uma assinatura criptográfica que comprova que este relatório não foi alterado ou adulterado.",
    "Security Level": "Tamanho da chave criptográfica usada para proteger o relatório, em bits.",
    "Status": "Resultado da análise: atendido, em revisão ou ausente.",
    "Total Flags": "Total de cláusulas analisadas no documento.",
    "Verification Standard": "Algoritmo criptográfico usado para criar o selo de integridade do relatório.",
}

# ---------------------------------------------------------------------------
# Law Engine Definitions
# ---------------------------------------------------------------------------

LAW_DEFINITIONS_EN = {
    "Analysis ID": "A unique identifier assigned to this specific analysis report.",
    "Article": "The specific rule or standard clause identified during the analysis.",
    "Client Term": "The specific excerpt or phrase from the document that triggered the alert.",
    "Compliance Signature": "A unique digital fingerprint representing the specific content analyzed in this report.",
    "Document Name": "The name or title of the analyzed document.",
    "Engine Name": "The name of the system that performed the analysis and generated this report.",
    "Engine Version": "The specific version of the analysis engine used.",
    "ID of Term Flagged": "A unique identifier for the specific term or pattern detected.",
    "Integrity Seal ID": "A cryptographic signature ensuring the report's integrity and authenticity.",
    "Language": "The language setting utilized by the engine for this analysis.",
    "Library Used": "The name of the rule set or library used to perform the analysis.",
    "Library Version": "The specific version of the reference library or rule set used.",
    "Match Percentage (%)": "The degree of similarity between the analyzed text and the reference standard, expressed as a percentage.",
    "Observation": "A detailed description of the pattern or issue identified in the analyzed text.",
    "Reference": "The source library or rule set containing the matched standard.",
    "Security Level": "The bit-length of the cryptographic key used to secure this report.",
    "Suggestion": "Suggested actions or guidance for resolving the identified issue.",
    "Tags": "Labels used to classify the type or nature of the detected issue.",
    "Total Flags": "The total count of risk signals and suspicious patterns identified during the analysis.",
    "Verification Standard": "The cryptographic algorithm used to generate the report's integrity seal.",
}

LAW_DEFINITIONS_PT = {
    "Analysis ID": "Identificador único para este relatório específico de análise.",
    "Article": "A regra de referência ou cláusula de norma que foi correspondida.",
    "Client Term": "O texto ou frase específica do seu documento que acionou um alerta.",
    "Compliance Signature": "Uma impressão digital que identifica o conteúdo exato analisado neste relatório.",
    "Document Name": "O nome ou título do documento que foi analisado.",
    "Engine Name": "O nome do sistema de análise que gerou este relatório.",
    "Engine Version": "O número da versão do sistema de análise utilizado.",
    "ID of Term Flagged": "Identificador único do termo ou padrão específico que foi detectado.",
    "Integrity Seal ID": "Uma assinatura criptográfica que comprova que este relatório não foi alterado ou adulterado.",
    "Language": "A configuração de idioma utilizada pelo motor de análise para este relatório.",
    "Library Used": "O nome da biblioteca de referência ou conjunto de regras utilizado na análise.",
    "Library Version": "O número da versão da biblioteca de referência ou conjunto de regras utilizado.",
    "Match Percentage (%)": "O quanto o seu texto corresponde ao padrão de referência, em percentual.",
    "Observation": "Uma descrição do padrão ou problema detectado no texto analisado.",
    "Reference": "O nome da biblioteca de referência ou conjunto de regras que contém o padrão correspondido.",
    "Security Level": "A força da chave criptográfica utilizada para proteger este relatório, medida em bits.",
    "Suggestion": "Ação recomendada ou orientação para tratar o problema sinalizado.",
    "Tags": "Rótulos de categorização que classificam o tipo ou natureza do problema detectado.",
    "Total Flags": "O total de sinais de risco e padrões suspeitos detectados na análise.",
    "Verification Standard": "O algoritmo criptográfico utilizado para criar o selo de integridade deste relatório.",
}

# ---------------------------------------------------------------------------
# Standard Engine Definitions
# ---------------------------------------------------------------------------

STANDARD_DEFINITIONS_EN = {
    "Analysis ID": "Unique identifier for this specific analysis report.",
    "Client Term": "The specific text or phrase from your document that triggered a flag.",
    "Compliance Signature": "A fingerprint that identifies the exact content analyzed in this report.",
    "Document Name": "The name or title of the document that was analyzed.",
    "Engine Name": "The name of the analysis system that generated this report.",
    "Engine Version": "The version number of the analysis system used.",
    "ID of Term Flagged": "A unique identifier for the specific term or pattern that was detected.",
    "Integrity Seal ID": "A cryptographic signature that proves this report has not been altered or tampered with.",
    "Language": "The language setting used by the analysis engine for this report.",
    "Library Used": "The name of the reference library or rule set used for analysis.",
    "Library Version": "The version number of the reference library or rule set used.",
    "Match Percentage (%)": "How closely your text matches the reference pattern, as a percentage.",
    "Observation": "A description of what pattern or issue was detected in the analyzed text.",
    "Reference": "The name of the reference library or rule set that contains the matched pattern.",
    "Security Level": "The cryptographic key strength used to secure this report, measured in bits.",
    "Suggestion": "Recommended action or guidance for addressing the flagged issue.",
    "Tags": "Categorization labels that classify the type or nature of the detected issue.",
    "Total Flags": "The total number of risk signals and suspicious patterns detected in the analysis.",
    "Verification Standard": "The cryptographic algorithm used to create the integrity seal for this report.",
}

STANDARD_DEFINITIONS_PT = {
    "Analysis ID": "Identificador único para este relatório específico de análise.",
    "Client Term": "O texto ou frase específica do seu documento que acionou um alerta.",
    "Compliance Signature": "Uma impressão digital que identifica o conteúdo exato analisado neste relatório.",
    "Document Name": "O nome ou título do documento que foi analisado.",
    "Engine Name": "O nome do sistema de análise que gerou este relatório.",
    "Engine Version": "O número da versão do sistema de análise utilizado.",
    "ID of Term Flagged": "Identificador único do termo ou padrão específico que foi detectado.",
    "Integrity Seal ID": "Uma assinatura criptográfica que comprova que este relatório não foi alterado ou adulterado.",
    "Language": "A configuração de idioma utilizada pelo motor de análise para este relatório.",
    "Library Used": "O nome da biblioteca de referência ou conjunto de regras utilizado na análise.",
    "Library Version": "O número da versão da biblioteca de referência ou conjunto de regras utilizado.",
    "Match Percentage (%)": "O quanto o seu texto corresponde ao padrão de referência, em percentual.",
    "Observation": "Uma descrição do padrão ou problema detectado no texto analisado.",
    "Reference": "O nome da biblioteca de referência ou conjunto de regras que contém o padrão correspondido.",
    "Security Level": "A força da chave criptográfica utilizada para proteger este relatório, medida em bits.",
    "Suggestion": "Ação recomendada ou orientação para tratar o problema sinalizado.",
    "Tags": "Rótulos de categorização que classificam o tipo ou natureza do problema detectado.",
    "Total Flags": "O total de sinais de risco e padrões suspeitos detectados na análise.",
    "Verification Standard": "O algoritmo criptográfico utilizado para criar o selo de integridade deste relatório.",
}


def get_definitions_for_engine(
    engine_name: str,
    language: str = "en-US"
) -> Dict[str, str]:
    """
    Get definitions for a specific engine based on language.

    Args:
        engine_name: Name of the engine (e.g., "Shield Standard Engine", "Shield ISO Engine", "Shield Law Engine")
        language: Language code (e.g., "en-US", "pt-BR", "pt")

    Returns:
        Dictionary of term -> definition mappings
    """
    engine_lower = engine_name.lower()
    is_portuguese = language.lower().startswith("pt")

    if "iso" in engine_lower or "9001" in engine_lower:
        return ISO_DEFINITIONS_PT if is_portuguese else ISO_DEFINITIONS_EN
    elif "law" in engine_lower:
        return LAW_DEFINITIONS_PT if is_portuguese else LAW_DEFINITIONS_EN
    else:
        return STANDARD_DEFINITIONS_PT if is_portuguese else STANDARD_DEFINITIONS_EN


def get_definitions_from_output(output: Dict) -> Optional[Dict[str, str]]:
    """Extract definitions from output if provided by engine."""
    return output.get("Definitions")


def get_definitions_for_pdf(
    output: Dict,
    engine_name: Optional[str] = None
) -> Dict[str, str]:
    """
    Get definitions for PDF generation.
    Uses definitions from output if provided, otherwise falls back to engine-specific defaults.
    """
    definitions = get_definitions_from_output(output)
    if definitions:
        return definitions

    if engine_name is None:
        engine_name = output.get("Engine", {}).get("Name", "Standard Engine")

    from .pdf_translations import get_display_language
    language = get_display_language(output)

    return get_definitions_for_engine(engine_name, language)
