"""DSPy-based LLM analysis modules for thesis content evaluation."""

import json
import logging
import re
from typing import List, Optional, Dict, Any, Union
import dspy
from pydantic import ValidationError
from langdetect import detect, LangDetectError
from pathlib import Path

from .data_models import (
    GrammarCorrectionError, 
    ContentPlausibilityError, 
    CitationFormatError,
    TextBlock,
    LocationHint,
    ErrorSeverity,
    ErrorType
)
from .config import get_settings

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect the language of a text block.
    
    Args:
        text: Text to analyze
        
    Returns:
        Language code ('english', 'german', etc.) or 'english' as fallback
    """
    if not text or len(text.strip()) < 10:
        return "english"  # Default fallback
    
    try:
        # Use langdetect to identify language
        detected = detect(text)
        
        # Map ISO codes to our training data keys
        language_mapping = {
            'en': 'english',
            'de': 'german',
        }
        
        return language_mapping.get(detected, 'english')
        
    except LangDetectError:
        logger.warning(f"Language detection failed for text: {text[:50]}...")
        return "english"  # Fallback to English


def try_load_compiled_module(module_name: str, language: str) -> Optional[dspy.Module]:
    """
    Try to load a compiled DSPy module for a specific language.
    
    Args:
        module_name: Name of the module (e.g., 'linguistic_analyzer')
        language: Language code (e.g., 'english', 'german')
        
    Returns:
        Compiled DSPy module if found, None otherwise
    """
    try:
        compiled_dir = Path("compiled_modules")
        if not compiled_dir.exists():
            return None
        
        module_file = compiled_dir / f"{module_name}_{language}.json"
        if not module_file.exists():
            return None
        
        # Load the compiled module
        # Note: This would need to be implemented based on DSPy's module loading API
        logger.info(f"Found compiled module: {module_file}")
        return None  # Placeholder - actual loading implementation needed
        
    except Exception as e:
        logger.warning(f"Failed to load compiled module {module_name}_{language}: {e}")
        return None


def safe_json_parse(response_text: str, expected_fields: List[str] = None) -> List[Dict[str, Any]]:
    """
    Safely parse JSON response with fallback strategies for malformed responses.
    
    Args:
        response_text: Raw LLM response text
        expected_fields: List of expected field names for validation
        
    Returns:
        List of parsed error dictionaries, empty list if parsing fails
    """
    if not response_text or not response_text.strip():
        logger.warning("Empty LLM response received")
        return []
    
    # Strategy 1: Direct JSON parsing
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
        else:
            logger.warning(f"Unexpected JSON structure: {type(parsed)}")
            return []
    except json.JSONDecodeError as e:
        logger.warning(f"Direct JSON parsing failed: {e}")
    
    # Strategy 2: Try to repair truncated JSON
    try:
        repaired = attempt_json_repair(response_text)
        if repaired:
            return repaired
    except Exception as e:
        logger.warning(f"JSON repair failed: {e}")
    
    # Strategy 3: Extract JSON from mixed content using regex
    try:
        extracted = extract_json_from_text(response_text)
        if extracted:
            return extracted
    except Exception as e:
        logger.warning(f"JSON extraction failed: {e}")
    
    # Strategy 4: Create minimal valid response
    logger.error(f"All JSON parsing strategies failed for response: {response_text[:200]}...")
    return []


def attempt_json_repair(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Attempt to repair truncated or malformed JSON responses.
    
    Args:
        text: Potentially malformed JSON text
        
    Returns:
        Parsed JSON list if repair successful, None otherwise
    """
    # Common repair strategies
    repairs = [
        # Add missing closing brackets
        lambda t: t + ']' if t.count('[') > t.count(']') else t,
        lambda t: t + '}' if t.count('{') > t.count('}') else t,
        
        # Remove trailing commas
        lambda t: re.sub(r',\s*([}\]])', r'\1', t),
        
        # Fix unterminated strings (common truncation issue)
        lambda t: t + '"' if t.count('"') % 2 == 1 else t,
        
        # Close incomplete final object
        lambda t: t + '"}]' if t.endswith('": "') else t,
        lambda t: t + '}]' if t.endswith(': ') else t,
    ]
    
    for repair_func in repairs:
        try:
            repaired_text = repair_func(text)
            parsed = json.loads(repaired_text)
            if isinstance(parsed, list):
                logger.info("Successfully repaired JSON response")
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            continue
    
    return None


def extract_json_from_text(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Extract JSON arrays/objects from mixed text content.
    
    Args:
        text: Text that may contain JSON content
        
    Returns:
        Extracted JSON list if found, None otherwise
    """
    # Look for JSON array patterns
    array_pattern = r'\[[\s\S]*?\]'
    matches = re.findall(array_pattern, text)
    
    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, list):
                logger.info("Successfully extracted JSON array from mixed content")
                return parsed
        except json.JSONDecodeError:
            continue
    
    # Look for individual JSON objects and combine them
    object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    object_matches = re.findall(object_pattern, text)
    
    if object_matches:
        try:
            objects = []
            for match in object_matches:
                parsed = json.loads(match)
                if isinstance(parsed, dict):
                    objects.append(parsed)
            
            if objects:
                logger.info(f"Successfully extracted {len(objects)} JSON objects from mixed content")
                return objects
        except json.JSONDecodeError:
            pass
    
    return None


class LinguisticAnalysisSignature(dspy.Signature):
    """DSPy signature for grammar and linguistic analysis with language awareness."""
    
    text_chunk: str = dspy.InputField(description="Text chunk to analyze for grammatical issues")
    language: str = dspy.InputField(description="Language of the text (e.g., 'english', 'german')", default="english")
    
    grammar_errors: str = dspy.OutputField(
        description="CRITICAL: Return ONLY valid JSON array format. Each error object must have: "
                   "error_type='grammar', severity ('high'|'medium'|'low'), "
                   "original_text, suggested_correction, explanation, grammar_rule (optional), "
                   "confidence_score (0.0-1.0). Return empty array [] if no errors found. "
                   "Apply language-specific grammar rules based on the specified language. "
                   "Example: [{'error_type':'grammar','severity':'high','original_text':'text','suggested_correction':'corrected','explanation':'reason','confidence_score':0.9}]"
    )


class ContentValidationSignature(dspy.Signature):
    """DSPy signature for content plausibility and logical consistency analysis with language awareness."""
    
    text_chunk: str = dspy.InputField(description="Text chunk to analyze for content plausibility issues")
    context: str = dspy.InputField(description="Additional context about the document type and subject", default="academic thesis")
    language: str = dspy.InputField(description="Language of the text (e.g., 'english', 'german')", default="english")
    
    content_errors: str = dspy.OutputField(
        description="CRITICAL: Return ONLY valid JSON array format. Each error object must have: "
                   "error_type='content_plausibility', severity ('high'|'medium'|'low'), "
                   "original_text, suggested_correction, explanation, plausibility_issue, "
                   "requires_fact_check (true|false), confidence_score (0.0-1.0). "
                   "Return empty array [] if no errors found. "
                   "Consider language-specific academic conventions and cultural context. "
                   "Example: [{'error_type':'content_plausibility','severity':'medium','original_text':'text','suggested_correction':'better','explanation':'reason','requires_fact_check':false,'confidence_score':0.8}]"
    )


class CitationAnalysisSignature(dspy.Signature):
    """DSPy signature for citation format and completeness analysis with language awareness."""
    
    text_chunk: str = dspy.InputField(description="Text chunk to analyze for citation issues")
    bibliography: str = dspy.InputField(description="Full bibliography section if available", default="")
    citation_style: str = dspy.InputField(description="Expected citation style (APA, MLA, Chicago, etc.)", default="APA")
    language: str = dspy.InputField(description="Language of the text (e.g., 'english', 'german')", default="english")
    
    citation_errors: str = dspy.OutputField(
        description="CRITICAL: Return ONLY valid JSON array format. Each error object must have: "
                   "error_type='citation_format', severity ('high'|'medium'|'low'), "
                   "original_text, suggested_correction, explanation, "
                   "citation_style_expected, missing_elements (array), confidence_score (0.0-1.0). "
                   "Return empty array [] if no errors found. "
                   "Apply language-specific citation conventions and academic standards. "
                   "Example: [{'error_type':'citation_format','severity':'high','original_text':'Smith 2020','suggested_correction':'(Smith, 2020)','explanation':'Missing comma in APA format','citation_style_expected':'APA','missing_elements':['comma'],'confidence_score':0.95}]"
    )


class LinguisticAnalyzer(dspy.Module):
    """DSPy module for grammar and linguistic analysis."""
    
    def __init__(self):
        super().__init__()
        self.analyzer = dspy.ChainOfThought(LinguisticAnalysisSignature)
        self.settings = get_settings()
    
    def forward(self, text_block: TextBlock, language: str = None) -> List[GrammarCorrectionError]:
        """
        Analyze text block for grammatical issues with language awareness.
        
        Args:
            text_block: TextBlock to analyze
            language: Language of the text (auto-detected if not provided)
            
        Returns:
            List of GrammarCorrectionError objects
        """
        try:
            # Detect language if not provided
            if language is None:
                language = detect_language(text_block.content)
            
            # Try to load compiled module first
            compiled_module = try_load_compiled_module("linguistic_analyzer", language)
            if compiled_module:
                logger.debug(f"Using compiled module for {language}")
                # Use compiled module - implementation would depend on DSPy API
                # For now, fall back to regular module
            
            # Call DSPy module with language context
            response = self.analyzer(
                text_chunk=text_block.content,
                language=language
            )
            
            # Parse JSON response with robust error handling
            errors_data = safe_json_parse(response.grammar_errors, ['error_type', 'severity', 'original_text'])
            
            # Convert to Pydantic models
            grammar_errors = []
            for error_dict in errors_data:
                try:
                    # Add location information
                    error_dict['location'] = {
                        'page_number': text_block.page_number,
                        'bounding_box': text_block.bounding_box,
                        'paragraph_index': text_block.block_index
                    }
                    
                    # Ensure error_type is set correctly
                    error_dict['error_type'] = ErrorType.GRAMMAR
                    
                    # Create GrammarCorrectionError
                    error = GrammarCorrectionError(**error_dict)
                    grammar_errors.append(error)
                    
                except ValidationError as e:
                    logger.warning(f"Invalid grammar error format: {e}")
                    continue
            
            logger.debug(f"Found {len(grammar_errors)} grammar errors in block {text_block.block_index} ({language})")
            return grammar_errors
            
        except Exception as e:
            logger.error(f"Error in linguistic analysis: {e}")
            return []


class ContentValidator(dspy.Module):
    """DSPy module for content plausibility and logical consistency analysis."""
    
    def __init__(self):
        super().__init__()
        self.validator = dspy.ChainOfThought(ContentValidationSignature)
        self.settings = get_settings()
    
    def forward(self, text_block: TextBlock, context: str = "academic thesis", language: str = None) -> List[ContentPlausibilityError]:
        """
        Analyze text block for content plausibility issues with language awareness.
        
        Args:
            text_block: TextBlock to analyze
            context: Additional context about the document
            language: Language of the text (auto-detected if not provided)
            
        Returns:
            List of ContentPlausibilityError objects
        """
        try:
            # Detect language if not provided
            if language is None:
                language = detect_language(text_block.content)
            
            # Try to load compiled module first
            compiled_module = try_load_compiled_module("content_validator", language)
            if compiled_module:
                logger.debug(f"Using compiled module for {language}")
                # Use compiled module - implementation would depend on DSPy API
            
            # Call DSPy module with language context
            response = self.validator(
                text_chunk=text_block.content,
                context=context,
                language=language
            )
            
            # Parse JSON response with robust error handling
            errors_data = safe_json_parse(response.content_errors, ['error_type', 'severity', 'original_text'])
            
            # Convert to Pydantic models
            content_errors = []
            for error_dict in errors_data:
                try:
                    # Add location information
                    error_dict['location'] = {
                        'page_number': text_block.page_number,
                        'bounding_box': text_block.bounding_box,
                        'paragraph_index': text_block.block_index
                    }
                    
                    # Ensure error_type is set correctly
                    error_dict['error_type'] = ErrorType.CONTENT_PLAUSIBILITY
                    
                    # Create ContentPlausibilityError
                    error = ContentPlausibilityError(**error_dict)
                    content_errors.append(error)
                    
                except ValidationError as e:
                    logger.warning(f"Invalid content error format: {e}")
                    continue
            
            logger.debug(f"Found {len(content_errors)} content errors in block {text_block.block_index} ({language})")
            return content_errors
            
        except Exception as e:
            logger.error(f"Error in content validation: {e}")
            return []


class CitationChecker(dspy.Module):
    """DSPy module for citation format and completeness analysis."""
    
    def __init__(self):
        super().__init__()
        self.checker = dspy.ChainOfThought(CitationAnalysisSignature)
        self.settings = get_settings()
    
    def forward(
        self, 
        text_block: TextBlock, 
        bibliography: str = "", 
        citation_style: str = "APA",
        language: str = None
    ) -> List[CitationFormatError]:
        """
        Analyze text block for citation issues with language awareness.
        
        Args:
            text_block: TextBlock to analyze
            bibliography: Full bibliography section if available
            citation_style: Expected citation style
            language: Language of the text (auto-detected if not provided)
            
        Returns:
            List of CitationFormatError objects
        """
        try:
            # Detect language if not provided
            if language is None:
                language = detect_language(text_block.content)
            
            # Try to load compiled module first
            compiled_module = try_load_compiled_module("citation_checker", language)
            if compiled_module:
                logger.debug(f"Using compiled module for {language}")
                # Use compiled module - implementation would depend on DSPy API
            
            # Call DSPy module with language context
            response = self.checker(
                text_chunk=text_block.content,
                bibliography=bibliography,
                citation_style=citation_style,
                language=language
            )
            
            # Parse JSON response with robust error handling
            errors_data = safe_json_parse(response.citation_errors, ['error_type', 'severity', 'original_text'])
            
            # Convert to Pydantic models
            citation_errors = []
            for error_dict in errors_data:
                try:
                    # Add location information
                    error_dict['location'] = {
                        'page_number': text_block.page_number,
                        'bounding_box': text_block.bounding_box,
                        'paragraph_index': text_block.block_index
                    }
                    
                    # Ensure error_type is set correctly
                    error_dict['error_type'] = ErrorType.CITATION_FORMAT
                    
                    # Set citation style if not provided
                    if 'citation_style_expected' not in error_dict:
                        error_dict['citation_style_expected'] = citation_style
                    
                    # Create CitationFormatError
                    error = CitationFormatError(**error_dict)
                    citation_errors.append(error)
                    
                except ValidationError as e:
                    logger.warning(f"Invalid citation error format: {e}")
                    continue
            
            logger.debug(f"Found {len(citation_errors)} citation errors in block {text_block.block_index} ({language})")
            return citation_errors
            
        except Exception as e:
            logger.error(f"Error in citation checking: {e}")
            return []


class AnalysisOrchestrator:
    """Orchestrates multiple analysis modules for comprehensive text evaluation."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize analysis modules based on configuration
        self.linguistic_analyzer = LinguisticAnalyzer() if self.settings.grammar_analysis_enabled else None
        self.content_validator = ContentValidator() if self.settings.content_analysis_enabled else None
        self.citation_checker = CitationChecker() if self.settings.citation_analysis_enabled else None
        
        logger.info("Analysis orchestrator initialized with enabled modules: "
                   f"Grammar: {self.settings.grammar_analysis_enabled}, "
                   f"Content: {self.settings.content_analysis_enabled}, "
                   f"Citation: {self.settings.citation_analysis_enabled}")
    
    def analyze_text_block(
        self, 
        text_block: TextBlock,
        bibliography: str = "",
        citation_style: str = "APA",
        context: str = "academic thesis"
    ) -> List[Union[GrammarCorrectionError, ContentPlausibilityError, CitationFormatError]]:
        """
        Perform comprehensive analysis on a text block using all enabled modules.
        
        Args:
            text_block: TextBlock to analyze
            bibliography: Full bibliography section if available
            citation_style: Expected citation style
            context: Document context for content analysis
            
        Returns:
            List of all detected errors from all analysis modules
        """
        all_errors = []
        
        try:
            # Detect language for this text block
            detected_language = detect_language(text_block.content)
            logger.debug(f"Detected language for block {text_block.block_index}: {detected_language}")
            
            # Grammar analysis
            if self.linguistic_analyzer:
                try:
                    grammar_errors = self.linguistic_analyzer(text_block, language=detected_language)
                    all_errors.extend(grammar_errors)
                except Exception as e:
                    logger.error(f"Grammar analysis failed for block {text_block.block_index}: {e}")
            
            # Content validation
            if self.content_validator:
                try:
                    content_errors = self.content_validator(text_block, context, language=detected_language)
                    all_errors.extend(content_errors)
                except Exception as e:
                    logger.error(f"Content validation failed for block {text_block.block_index}: {e}")
            
            # Citation checking
            if self.citation_checker:
                try:
                    citation_errors = self.citation_checker(text_block, bibliography, citation_style, language=detected_language)
                    all_errors.extend(citation_errors)
                except Exception as e:
                    logger.error(f"Citation checking failed for block {text_block.block_index}: {e}")
            
            logger.debug(f"Total errors found in block {text_block.block_index}: {len(all_errors)}")
            return all_errors
            
        except Exception as e:
            logger.error(f"Analysis orchestration failed for block {text_block.block_index}: {e}")
            return []
    
    def batch_analyze_blocks(
        self,
        text_blocks: List[TextBlock],
        bibliography: str = "",
        citation_style: str = "APA",
        context: str = "academic thesis"
    ) -> Dict[int, List[Union[GrammarCorrectionError, ContentPlausibilityError, CitationFormatError]]]:
        """
        Analyze multiple text blocks in batch.
        
        Args:
            text_blocks: List of TextBlock objects to analyze
            bibliography: Full bibliography section if available
            citation_style: Expected citation style
            context: Document context for content analysis
            
        Returns:
            Dictionary mapping block index to list of errors
        """
        results = {}
        
        for i, text_block in enumerate(text_blocks):
            logger.debug(f"Analyzing block {i+1}/{len(text_blocks)}")
            
            errors = self.analyze_text_block(
                text_block, 
                bibliography, 
                citation_style, 
                context
            )
            
            results[text_block.block_index] = errors
        
        total_errors = sum(len(errors) for errors in results.values())
        logger.info(f"Batch analysis completed: {total_errors} total errors found across {len(text_blocks)} blocks")
        
        return results


def create_analysis_orchestrator() -> AnalysisOrchestrator:
    """Factory function to create and configure an AnalysisOrchestrator."""
    return AnalysisOrchestrator()


def test_analysis_modules():
    """Test function to verify analysis modules are working correctly."""
    from .pdf_processor import create_test_pdf
    from .pdf_processor import PDFProcessor
    import tempfile
    import os
    
    try:
        # Create a test PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            test_pdf_path = tmp_file.name
        
        create_test_pdf(test_pdf_path)
        
        # Process the PDF
        processor = PDFProcessor()
        text_blocks = processor.extract_text_blocks_from_pdf(test_pdf_path)
        
        # Test analysis
        orchestrator = create_analysis_orchestrator()
        
        if text_blocks:
            test_block = text_blocks[0]
            errors = orchestrator.analyze_text_block(test_block)
            
            print(f"Test analysis completed:")
            print(f"- Analyzed block with {len(test_block.content)} characters")
            print(f"- Found {len(errors)} errors")
            
            for error in errors[:3]:  # Show first 3 errors
                print(f"  - {error.error_type}: {error.original_text[:50]}...")
        
        # Cleanup
        os.unlink(test_pdf_path)
        
        return True
        
    except Exception as e:
        logger.error(f"Test analysis failed: {e}")
        return False