"""Pydantic data models for structured thesis analysis data."""

from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ErrorSeverity(str, Enum):
    """Enumeration for error severity levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ErrorType(str, Enum):
    """Enumeration for different types of errors."""
    GRAMMAR = "grammar"
    CONTENT_PLAUSIBILITY = "content_plausibility"
    CITATION_FORMAT = "citation_format"
    STRUCTURE = "structure"
    STYLE = "style"


class LocationHint(BaseModel):
    """Represents the precise location of content or errors in a PDF document."""
    
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    bounding_box: Optional[tuple[float, float, float, float]] = Field(
        None, 
        description="Bounding box coordinates (x0, y0, x1, y1) if available"
    )
    paragraph_index: Optional[int] = Field(
        None, 
        ge=0, 
        description="Paragraph index within the page"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "page_number": 15,
                "bounding_box": [72.0, 400.0, 500.0, 450.0],
                "paragraph_index": 2
            }
        }


class BaseError(BaseModel):
    """Base model for all detected errors in thesis analysis."""
    
    error_type: ErrorType = Field(..., description="Type of error detected")
    severity: ErrorSeverity = Field(..., description="Severity level of the error")
    original_text: str = Field(..., min_length=1, description="Original problematic text")
    suggested_correction: Optional[str] = Field(
        None, 
        description="Suggested correction or improvement"
    )
    explanation: str = Field(
        ..., 
        min_length=10, 
        description="Detailed explanation of the issue"
    )
    location: LocationHint = Field(..., description="Location of the error in the document")
    confidence_score: float = Field(
        default=0.8, 
        ge=0.0, 
        le=1.0, 
        description="Confidence score for the error detection"
    )
    
    @field_validator('original_text')
    @classmethod
    def validate_original_text(cls, v: str) -> str:
        """Ensure original text is not just whitespace."""
        if not v.strip():
            raise ValueError("Original text cannot be empty or just whitespace")
        return v.strip()
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "error_type": "grammar",
                "severity": "medium",
                "original_text": "The results shows that",
                "suggested_correction": "The results show that",
                "explanation": "Subject-verb disagreement: 'results' is plural and requires the plural verb 'show'",
                "location": {
                    "page_number": 25,
                    "bounding_box": [100.0, 300.0, 400.0, 320.0]
                },
                "confidence_score": 0.95
            }
        }


class GrammarCorrectionError(BaseError):
    """Specific error type for grammatical issues."""
    
    error_type: Literal[ErrorType.GRAMMAR] = ErrorType.GRAMMAR
    grammar_rule: Optional[str] = Field(
        None, 
        description="Specific grammar rule that was violated"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "grammar",
                "severity": "high",
                "original_text": "Neither the students nor the professor were available",
                "suggested_correction": "Neither the students nor the professor was available",
                "explanation": "With 'neither...nor' constructions, the verb agrees with the subject closer to it",
                "grammar_rule": "subject-verb agreement with correlative conjunctions",
                "location": {"page_number": 10},
                "confidence_score": 0.9
            }
        }


class ContentPlausibilityError(BaseError):
    """Specific error type for content plausibility and logical consistency issues."""
    
    error_type: Literal[ErrorType.CONTENT_PLAUSIBILITY] = ErrorType.CONTENT_PLAUSIBILITY
    plausibility_issue: str = Field(
        ..., 
        description="Specific type of plausibility issue (factual, logical, consistency)"
    )
    requires_fact_check: bool = Field(
        default=False, 
        description="Whether this requires external fact-checking"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "content_plausibility",
                "severity": "high",
                "original_text": "The study was conducted in 2025 with data from 2026",
                "suggested_correction": "Check chronological consistency of study timeline",
                "explanation": "Timeline inconsistency: study cannot be conducted before data collection",
                "plausibility_issue": "chronological inconsistency",
                "requires_fact_check": False,
                "location": {"page_number": 5},
                "confidence_score": 0.85
            }
        }


class CitationFormatError(BaseError):
    """Specific error type for citation and referencing issues."""
    
    error_type: Literal[ErrorType.CITATION_FORMAT] = ErrorType.CITATION_FORMAT
    citation_style_expected: Optional[str] = Field(
        None, 
        description="Expected citation style (APA, MLA, Chicago, etc.)"
    )
    missing_elements: List[str] = Field(
        default_factory=list, 
        description="List of missing citation elements"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "citation_format",
                "severity": "medium",
                "original_text": "(Smith, 2020)",
                "suggested_correction": "(Smith, 2020, p. 15)",
                "explanation": "Direct quotes require page numbers in APA style",
                "citation_style_expected": "APA",
                "missing_elements": ["page_number"],
                "location": {"page_number": 12},
                "confidence_score": 0.8
            }
        }


class TextBlock(BaseModel):
    """Represents an extracted piece of text from a PDF with contextual information."""
    
    content: str = Field(..., min_length=1, description="The extracted text content")
    page_number: int = Field(..., ge=1, description="Page number where this text was found")
    bounding_box: Optional[tuple[float, float, float, float]] = Field(
        None, 
        description="Bounding box coordinates (x0, y0, x1, y1)"
    )
    block_index: int = Field(..., ge=0, description="Index of this block within the page")
    word_count: int = Field(default=0, ge=0, description="Number of words in this block")
    character_count: int = Field(default=0, ge=0, description="Number of characters in this block")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.word_count == 0:
            self.word_count = len(self.content.split())
        if self.character_count == 0:
            self.character_count = len(self.content)
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v.strip():
            raise ValueError("Text block content cannot be empty or just whitespace")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "This study examines the relationship between social media usage and academic performance among university students.",
                "page_number": 1,
                "bounding_box": [72.0, 600.0, 500.0, 650.0],
                "block_index": 0,
                "word_count": 16,
                "character_count": 120
            }
        }


class AnalysisResult(BaseModel):
    """Represents the analysis results for a specific text block."""
    
    text_block: TextBlock = Field(..., description="The analyzed text block")
    errors: List[Union[GrammarCorrectionError, ContentPlausibilityError, CitationFormatError]] = Field(
        default_factory=list, 
        description="List of errors found in this text block"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, 
        description="When this analysis was performed"
    )
    processing_time_seconds: Optional[float] = Field(
        None, 
        ge=0.0, 
        description="Time taken to analyze this block"
    )
    
    @property
    def error_count(self) -> int:
        """Total number of errors in this block."""
        return len(self.errors)
    
    @property
    def high_severity_count(self) -> int:
        """Number of high-severity errors."""
        return sum(1 for error in self.errors if error.severity == ErrorSeverity.HIGH)
    
    @property
    def has_errors(self) -> bool:
        """Whether this block has any errors."""
        return len(self.errors) > 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "text_block": {
                    "content": "The data was analyzed using SPSS software.",
                    "page_number": 15,
                    "block_index": 3
                },
                "errors": [
                    {
                        "error_type": "grammar",
                        "severity": "low",
                        "original_text": "The data was analyzed",
                        "suggested_correction": "The data were analyzed",
                        "explanation": "'Data' is plural and requires plural verb 'were'",
                        "location": {"page_number": 15}
                    }
                ],
                "analysis_timestamp": "2024-01-15T10:30:00",
                "processing_time_seconds": 2.5
            }
        }


class ThesisAnalysisReport(BaseModel):
    """Comprehensive report containing all analysis results for a thesis document."""
    
    document_name: str = Field(..., description="Name of the analyzed document")
    document_path: Optional[str] = Field(None, description="Path to the analyzed document")
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, 
        description="When the analysis was completed"
    )
    total_pages: int = Field(..., ge=1, description="Total number of pages in the document")
    total_text_blocks: int = Field(..., ge=0, description="Total number of text blocks analyzed")
    total_words: int = Field(default=0, ge=0, description="Total word count in the document")
    
    # Analysis results
    analysis_results: List[AnalysisResult] = Field(
        default_factory=list, 
        description="Detailed analysis results for each text block"
    )
    
    # Summary statistics
    total_errors: int = Field(default=0, ge=0, description="Total number of errors found")
    errors_by_type: Dict[str, int] = Field(
        default_factory=dict, 
        description="Count of errors by type"
    )
    errors_by_severity: Dict[str, int] = Field(
        default_factory=dict, 
        description="Count of errors by severity"
    )
    errors_by_page: Dict[int, int] = Field(
        default_factory=dict, 
        description="Count of errors by page number"
    )
    
    # Processing metadata
    total_processing_time_seconds: Optional[float] = Field(
        None, 
        ge=0.0, 
        description="Total time taken for analysis"
    )
    configuration_used: Optional[Dict[str, Any]] = Field(
        None, 
        description="Configuration settings used for this analysis"
    )
    
    # Token usage and cost tracking
    token_usage: Optional[Dict[str, int]] = Field(
        None,
        description="Token usage breakdown (prompt_tokens, completion_tokens, total_tokens)"
    )
    estimated_cost: Optional[float] = Field(
        None,
        ge=0.0,
        description="Estimated cost in USD for the analysis"
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        self._calculate_statistics()
    
    def _calculate_statistics(self):
        """Calculate summary statistics from analysis results."""
        self.total_errors = sum(result.error_count for result in self.analysis_results)
        self.total_text_blocks = len(self.analysis_results)
        self.total_words = sum(result.text_block.word_count for result in self.analysis_results)
        
        # Calculate errors by type
        type_counts = {}
        severity_counts = {}
        page_counts = {}
        
        for result in self.analysis_results:
            page_num = result.text_block.page_number
            page_error_count = len(result.errors)
            page_counts[page_num] = page_counts.get(page_num, 0) + page_error_count
            
            for error in result.errors:
                # Count by type
                error_type = error.error_type
                type_counts[error_type] = type_counts.get(error_type, 0) + 1
                
                # Count by severity
                severity = error.severity
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        self.errors_by_type = type_counts
        self.errors_by_severity = severity_counts
        self.errors_by_page = page_counts
    
    @property
    def error_rate(self) -> float:
        """Error rate as errors per 1000 words."""
        if self.total_words == 0:
            return 0.0
        return (self.total_errors / self.total_words) * 1000
    
    @property
    def pages_with_errors(self) -> int:
        """Number of pages that contain errors."""
        return len([page for page, count in self.errors_by_page.items() if count > 0])
    
    @property
    def average_errors_per_page(self) -> float:
        """Average number of errors per page."""
        if self.total_pages == 0:
            return 0.0
        return self.total_errors / self.total_pages
    
    def get_high_severity_errors(self) -> List[Union[GrammarCorrectionError, ContentPlausibilityError, CitationFormatError]]:
        """Get all high-severity errors across all blocks."""
        high_severity_errors = []
        for result in self.analysis_results:
            high_severity_errors.extend([
                error for error in result.errors 
                if error.severity == ErrorSeverity.HIGH
            ])
        return high_severity_errors
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_name": "bachelor_thesis.pdf",
                "total_pages": 50,
                "total_text_blocks": 150,
                "total_words": 12000,
                "total_errors": 25,
                "errors_by_type": {
                    "grammar": 15,
                    "citation_format": 8,
                    "content_plausibility": 2
                },
                "errors_by_severity": {
                    "high": 3,
                    "medium": 12,
                    "low": 10
                },
                "analysis_timestamp": "2024-01-15T11:45:00",
                "total_processing_time_seconds": 45.2
            }
        }