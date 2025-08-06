"""Training data for DSPy prompt optimization with multi-language support."""

import dspy

# Multi-language training examples for DSPy few-shot optimization
TRAINING_DATA = {
    "english": {
        "grammar_examples": [
            dspy.Example(
                text_chunk="The results shows that our hypothesis was correct.",
                grammar_errors='[{"error_type":"grammar","severity":"medium","original_text":"The results shows","suggested_correction":"The results show","explanation":"Subject-verb disagreement: \'results\' is plural and requires the plural verb \'show\'","grammar_rule":"subject-verb agreement","confidence_score":0.95}]'
            ),
            dspy.Example(
                text_chunk="Neither the students nor the professor were available for the interview.",
                grammar_errors='[{"error_type":"grammar","severity":"high","original_text":"Neither the students nor the professor were available","suggested_correction":"Neither the students nor the professor was available","explanation":"With \'neither...nor\' constructions, the verb agrees with the subject closer to it (professor - singular)","grammar_rule":"subject-verb agreement with correlative conjunctions","confidence_score":0.9}]'
            ),
            dspy.Example(
                text_chunk="The data was analyzed using statistical methods and it showed significant trends.",
                grammar_errors='[{"error_type":"grammar","severity":"low","original_text":"The data was analyzed","suggested_correction":"The data were analyzed","explanation":"\'Data\' is typically treated as plural in formal academic writing","grammar_rule":"plural nouns","confidence_score":0.7}]'
            ),
            dspy.Example(
                text_chunk="This research aims to investigate the effects of climate change on biodiversity.",
                grammar_errors='[]'
            ),
            dspy.Example(
                text_chunk="Each of the participants have completed the survey successfully.",
                grammar_errors='[{"error_type":"grammar","severity":"medium","original_text":"Each of the participants have completed","suggested_correction":"Each of the participants has completed","explanation":"\'Each\' is singular and requires a singular verb form","grammar_rule":"indefinite pronouns","confidence_score":0.92}]'
            )
        ],
        
        "content_examples": [
            dspy.Example(
                text_chunk="The study was conducted in 2025 using data collected in 2026.",
                context="academic thesis",
                content_errors='[{"error_type":"content_plausibility","severity":"high","original_text":"The study was conducted in 2025 using data collected in 2026","suggested_correction":"Check chronological consistency of study timeline","explanation":"Timeline inconsistency: study cannot be conducted before data collection","plausibility_issue":"chronological inconsistency","requires_fact_check":false,"confidence_score":0.95}]'
            ),
            dspy.Example(
                text_chunk="The experiment showed a 150% improvement in efficiency, which is statistically significant.",
                context="academic thesis",
                content_errors='[{"error_type":"content_plausibility","severity":"medium","original_text":"150% improvement in efficiency","suggested_correction":"Verify the magnitude of improvement claimed","explanation":"A 150% improvement (2.5x efficiency gain) is unusually large and should be verified","plausibility_issue":"magnitude plausibility","requires_fact_check":true,"confidence_score":0.8}]'
            ),
            dspy.Example(
                text_chunk="The methodology follows established protocols from peer-reviewed literature.",
                context="academic thesis",
                content_errors='[]'
            ),
            dspy.Example(
                text_chunk="All participants were born on February 30th, ensuring demographic consistency.",
                context="academic thesis",
                content_errors='[{"error_type":"content_plausibility","severity":"high","original_text":"All participants were born on February 30th","suggested_correction":"February 30th does not exist - correct the date","explanation":"February 30th is not a valid date in any calendar system","plausibility_issue":"factual impossibility","requires_fact_check":false,"confidence_score":1.0}]'
            )
        ],
        
        "citation_examples": [
            dspy.Example(
                text_chunk="According to Smith 2020, climate change has significant impacts.",
                bibliography="Smith, J. (2020). Climate change impacts. Journal of Environmental Science, 15(3), 45-67.",
                citation_style="APA",
                citation_errors='[{"error_type":"citation_format","severity":"medium","original_text":"Smith 2020","suggested_correction":"(Smith, 2020)","explanation":"APA format requires parentheses and comma between author and year","citation_style_expected":"APA","missing_elements":["parentheses","comma"],"confidence_score":0.9}]'
            ),
            dspy.Example(
                text_chunk="Research shows clear evidence of the phenomenon (Johnson, 2019; Williams, 2021).",
                bibliography="Johnson, A. (2019). Evidence analysis. Academic Review, 12(4), 123-145.\nWilliams, B. (2021). Phenomenon studies. Research Quarterly, 8(2), 67-89.",
                citation_style="APA",
                citation_errors='[]'
            ),
            dspy.Example(
                text_chunk="The findings are supported by multiple studies (Brown et al 2018).",
                bibliography="Brown, C., Davis, E., & Miller, F. (2018). Multiple perspectives. Science Today, 25(7), 234-256.",
                citation_style="APA",
                citation_errors='[{"error_type":"citation_format","severity":"low","original_text":"Brown et al 2018","suggested_correction":"Brown et al., 2018","explanation":"Missing period after \'et al\' in APA format","citation_style_expected":"APA","missing_elements":["period"],"confidence_score":0.85}]'
            )
        ]
    },
    
    "german": {
        "grammar_examples": [
            dspy.Example(
                text_chunk="Die Forschung zeigen deutliche Ergebnisse in diesem Bereich.",
                grammar_errors='[{"error_type":"grammar","severity":"medium","original_text":"Die Forschung zeigen","suggested_correction":"Die Forschung zeigt","explanation":"Subjekt-Verb-Kongruenz: \'Forschung\' ist Singular und benötigt die Singularform \'zeigt\'","grammar_rule":"Subjekt-Verb-Kongruenz","confidence_score":0.95}]'
            ),
            dspy.Example(
                text_chunk="Der Wissenschaftler analysierte den Daten mit statistischen Methoden.",
                grammar_errors='[{"error_type":"grammar","severity":"medium","original_text":"den Daten","suggested_correction":"die Daten","explanation":"\'Daten\' ist Plural und benötigt den Artikel \'die\' im Akkusativ","grammar_rule":"Artikel-Kasus-Kongruenz","confidence_score":0.9}]'
            ),
            dspy.Example(
                text_chunk="Diese Untersuchung zielt darauf ab, die Auswirkungen des Klimawandels zu erforschen.",
                grammar_errors='[]'
            ),
            dspy.Example(
                text_chunk="Wegen dem schlechten Wetter wurde das Experiment verschoben.",
                grammar_errors='[{"error_type":"grammar","severity":"high","original_text":"Wegen dem schlechten Wetter","suggested_correction":"Wegen des schlechten Wetters","explanation":"\'Wegen\' erfordert den Genitiv, nicht den Dativ","grammar_rule":"Präposition-Kasus","confidence_score":0.95}]'
            ),
            dspy.Example(
                text_chunk="Die Resultate wurde durch mehrere Experten validiert.",
                grammar_errors='[{"error_type":"grammar","severity":"medium","original_text":"Die Resultate wurde","suggested_correction":"Die Resultate wurden","explanation":"\'Resultate\' ist Plural und benötigt die Pluralform \'wurden\'","grammar_rule":"Subjekt-Verb-Kongruenz","confidence_score":0.92}]'
            )
        ],
        
        "content_examples": [
            dspy.Example(
                text_chunk="Die Studie wurde 2025 durchgeführt mit Daten aus dem Jahr 2026.",
                context="wissenschaftliche Abschlussarbeit",
                content_errors='[{"error_type":"content_plausibility","severity":"high","original_text":"Die Studie wurde 2025 durchgeführt mit Daten aus dem Jahr 2026","suggested_correction":"Überprüfung der chronologischen Konsistenz der Studienzeitachse","explanation":"Zeitliche Inkonsistenz: Studie kann nicht vor der Datensammlung durchgeführt werden","plausibility_issue":"chronologische Inkonsistenz","requires_fact_check":false,"confidence_score":0.95}]'
            ),
            dspy.Example(
                text_chunk="Das Experiment zeigte eine Effizienzsteigerung von 200%, was statistisch signifikant ist.",
                context="wissenschaftliche Abschlussarbeit",
                content_errors='[{"error_type":"content_plausibility","severity":"medium","original_text":"eine Effizienzsteigerung von 200%","suggested_correction":"Überprüfung der behaupteten Verbesserungsgröße","explanation":"Eine 200%ige Steigerung (3-fache Effizienz) ist ungewöhnlich hoch und sollte verifiziert werden","plausibility_issue":"Größenordnungsplausibilität","requires_fact_check":true,"confidence_score":0.8}]'
            ),
            dspy.Example(
                text_chunk="Die Methodik folgt etablierten Protokollen aus der begutachteten Literatur.",
                context="wissenschaftliche Abschlussarbeit",
                content_errors='[]'
            )
        ],
        
        "citation_examples": [
            dspy.Example(
                text_chunk="Laut Schmidt 2020 hat der Klimawandel erhebliche Auswirkungen.",
                bibliography="Schmidt, J. (2020). Klimawandel-Auswirkungen. Zeitschrift für Umweltwissenschaften, 15(3), 45-67.",
                citation_style="APA",
                citation_errors='[{"error_type":"citation_format","severity":"medium","original_text":"Schmidt 2020","suggested_correction":"(Schmidt, 2020)","explanation":"APA-Format erfordert Klammern und Komma zwischen Autor und Jahr","citation_style_expected":"APA","missing_elements":["Klammern","Komma"],"confidence_score":0.9}]'
            ),
            dspy.Example(
                text_chunk="Die Forschung zeigt deutliche Belege für das Phänomen (Mueller, 2019; Weber, 2021).",
                bibliography="Mueller, A. (2019). Beleganalyse. Wissenschaftliche Rundschau, 12(4), 123-145.\nWeber, B. (2021). Phänomenstudien. Forschungsquarterly, 8(2), 67-89.",
                citation_style="APA",
                citation_errors='[]'
            ),
            dspy.Example(
                text_chunk="Die Befunde werden durch mehrere Studien gestützt (Klein et al 2018).",
                bibliography="Klein, C., Hoffmann, E., & Richter, F. (2018). Mehrere Perspektiven. Wissenschaft Heute, 25(7), 234-256.",
                citation_style="APA",
                citation_errors='[{"error_type":"citation_format","severity":"low","original_text":"Klein et al 2018","suggested_correction":"Klein et al., 2018","explanation":"Fehlender Punkt nach \'et al\' im APA-Format","citation_style_expected":"APA","missing_elements":["Punkt"],"confidence_score":0.85}]'
            )
        ]
    }
}

def get_training_examples(language: str, error_type: str) -> list:
    """
    Get training examples for a specific language and error type.
    
    Args:
        language: Language code ('english' or 'german')
        error_type: Type of error ('grammar', 'content', or 'citation')
        
    Returns:
        List of dspy.Example objects for the specified criteria
    """
    if language not in TRAINING_DATA:
        # Fallback to English if language not supported
        language = "english"
    
    language_data = TRAINING_DATA[language]
    
    # Map error types to data keys
    key_mapping = {
        "grammar": "grammar_examples",
        "content": "content_examples", 
        "citation": "citation_examples"
    }
    
    key = key_mapping.get(error_type)
    if key and key in language_data:
        return language_data[key]
    
    return []

def get_supported_languages() -> list:
    """Get list of supported languages for training."""
    return list(TRAINING_DATA.keys())

def get_all_examples_for_language(language: str) -> dict:
    """Get all training examples for a specific language."""
    if language not in TRAINING_DATA:
        language = "english"  # Fallback
    
    return TRAINING_DATA[language]