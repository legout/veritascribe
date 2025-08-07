"""
Data models for VeritaScribe Dashboard

Enhanced models that extend the original VeritaScribe error analysis with
status tracking, user management, and workflow capabilities.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path


class ErrorType(str, Enum):
    """Types of errors that can be detected."""
    CITATION_FORMAT = "citation_format"
    GRAMMAR = "grammar"
    CONTENT_PLAUSIBILITY = "content_plausibility"


class Severity(str, Enum):
    """Error severity levels."""
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"


class ErrorStatus(str, Enum):
    """Status tracking for error resolution workflow."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    NEEDS_REVIEW = "needs_review"


class ResolutionMethod(str, Enum):
    """How an error was resolved."""
    MANUAL_FIX = "manual_fix"
    AUTO_SUGGESTION = "auto_suggestion"
    STYLE_GUIDE_UPDATE = "style_guide_update"
    FALSE_POSITIVE = "false_positive"
    INTENTIONAL = "intentional"


class Location(BaseModel):
    """Location information for an error."""
    page_number: int
    bounding_box: List[float]
    paragraph_index: int


class TextBlock(BaseModel):
    """Text block information from the original analysis."""
    content: str
    page_number: int
    bounding_box: List[float]
    block_index: int
    word_count: int
    character_count: int


class BaseError(BaseModel):
    """Base error model from original VeritaScribe analysis."""
    error_type: ErrorType
    severity: Severity
    original_text: str
    suggested_correction: str
    explanation: str
    location: Location
    confidence_score: float
    
    # Citation-specific fields (optional)
    citation_style_expected: Optional[str] = None
    missing_elements: Optional[List[str]] = None
    
    # Grammar-specific fields (optional)
    grammar_rule: Optional[str] = None
    
    # Content-specific fields (optional)
    plausibility_issue: Optional[str] = None
    requires_fact_check: Optional[bool] = None


class ManagedError(BaseError):
    """Enhanced error model with management capabilities."""
    # Unique identifier for tracking
    error_id: str = Field(default_factory=lambda: f"err_{int(datetime.now().timestamp() * 1000000)}")
    
    # Status tracking
    status: ErrorStatus = ErrorStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Assignment and collaboration
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Resolution tracking
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_method: Optional[ResolutionMethod] = None
    resolution_notes: Optional[str] = None
    
    # User notes and comments
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Priority and categorization
    priority: int = Field(default=0, description="User-defined priority (higher = more important)")
    is_recurring: bool = Field(default=False, description="True if this error pattern appears elsewhere")
    
    def mark_resolved(self, resolved_by: str, method: ResolutionMethod, notes: str = "") -> None:
        """Mark error as resolved with metadata."""
        self.status = ErrorStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.resolved_by = resolved_by
        self.resolution_method = method
        self.resolution_notes = notes
        self.updated_at = datetime.now()
    
    def assign_to(self, user: str) -> None:
        """Assign error to a user."""
        self.assigned_to = user
        self.assigned_at = datetime.now()
        self.updated_at = datetime.now()
        if self.status == ErrorStatus.PENDING:
            self.status = ErrorStatus.IN_PROGRESS


class AnalysisResult(BaseModel):
    """Analysis result for a single text block with managed errors."""
    text_block: TextBlock
    errors: List[ManagedError]
    analysis_timestamp: datetime
    processing_time_seconds: float


class DocumentStats(BaseModel):
    """Statistics for a document analysis."""
    total_pages: int
    total_text_blocks: int
    total_words: int
    total_errors: int
    errors_by_type: Dict[ErrorType, int]
    errors_by_severity: Dict[Severity, int]
    errors_by_status: Dict[ErrorStatus, int]
    average_confidence: float
    most_problematic_pages: List[int]


class ProgressStats(BaseModel):
    """Progress tracking statistics."""
    total_errors: int
    pending_errors: int
    in_progress_errors: int
    resolved_errors: int
    dismissed_errors: int
    needs_review_errors: int
    
    completion_percentage: float
    resolution_velocity: float  # errors resolved per day
    average_resolution_time: float  # hours
    
    errors_by_assignee: Dict[str, int]
    bottleneck_error_types: List[ErrorType]


class FilterCriteria(BaseModel):
    """Criteria for filtering errors."""
    status: Optional[List[ErrorStatus]] = None
    error_type: Optional[List[ErrorType]] = None
    severity: Optional[List[Severity]] = None
    assigned_to: Optional[List[str]] = None
    page_range: Optional[tuple[int, int]] = None
    confidence_range: Optional[tuple[float, float]] = None
    date_range: Optional[tuple[datetime, datetime]] = None
    search_text: Optional[str] = None
    tags: Optional[List[str]] = None
    has_assignment: Optional[bool] = None


class ThesisAnalysisReport(BaseModel):
    """Complete thesis analysis report with management capabilities."""
    document_name: str
    document_path: str
    analysis_timestamp: datetime
    total_pages: int
    total_text_blocks: int
    total_words: int
    
    analysis_results: List[AnalysisResult]
    document_stats: DocumentStats
    progress_stats: ProgressStats
    
    # Metadata
    created_by: Optional[str] = None
    last_modified: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"
    
    def get_all_errors(self) -> List[ManagedError]:
        """Get all errors from all analysis results."""
        errors = []
        for result in self.analysis_results:
            errors.extend(result.errors)
        return errors
    
    def get_filtered_errors(self, criteria: FilterCriteria) -> List[ManagedError]:
        """Get errors matching filter criteria."""
        errors = self.get_all_errors()
        
        # Apply filters
        if criteria.status:
            errors = [e for e in errors if e.status in criteria.status]
            
        if criteria.error_type:
            errors = [e for e in errors if e.error_type in criteria.error_type]
            
        if criteria.severity:
            errors = [e for e in errors if e.severity in criteria.severity]
            
        if criteria.assigned_to:
            errors = [e for e in errors if e.assigned_to in criteria.assigned_to]
            
        if criteria.page_range:
            min_page, max_page = criteria.page_range
            errors = [e for e in errors if min_page <= e.location.page_number <= max_page]
            
        if criteria.confidence_range:
            min_conf, max_conf = criteria.confidence_range
            errors = [e for e in errors if min_conf <= e.confidence_score <= max_conf]
            
        if criteria.search_text:
            search_lower = criteria.search_text.lower()
            errors = [e for e in errors if 
                     search_lower in e.original_text.lower() or
                     search_lower in e.suggested_correction.lower() or
                     search_lower in e.explanation.lower()]
            
        if criteria.tags:
            errors = [e for e in errors if any(tag in e.tags for tag in criteria.tags)]
            
        if criteria.has_assignment is not None:
            if criteria.has_assignment:
                errors = [e for e in errors if e.assigned_to is not None]
            else:
                errors = [e for e in errors if e.assigned_to is None]
        
        return errors
    
    def update_stats(self) -> None:
        """Recalculate document and progress statistics."""
        errors = self.get_all_errors()
        
        # Document stats
        error_counts_by_type = {error_type: 0 for error_type in ErrorType}
        error_counts_by_severity = {severity: 0 for severity in Severity}
        error_counts_by_status = {status: 0 for status in ErrorStatus}
        
        confidence_scores = []
        page_error_counts = {}
        
        for error in errors:
            error_counts_by_type[error.error_type] += 1
            error_counts_by_severity[error.severity] += 1
            error_counts_by_status[error.status] += 1
            confidence_scores.append(error.confidence_score)
            
            page = error.location.page_number
            page_error_counts[page] = page_error_counts.get(page, 0) + 1
        
        self.document_stats = DocumentStats(
            total_pages=self.total_pages,
            total_text_blocks=self.total_text_blocks,
            total_words=self.total_words,
            total_errors=len(errors),
            errors_by_type=error_counts_by_type,
            errors_by_severity=error_counts_by_severity,
            errors_by_status=error_counts_by_status,
            average_confidence=sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            most_problematic_pages=sorted(page_error_counts.keys(), 
                                        key=lambda p: page_error_counts[p], 
                                        reverse=True)[:5]
        )
        
        # Progress stats
        assignee_counts = {}
        resolved_times = []
        
        for error in errors:
            if error.assigned_to:
                assignee_counts[error.assigned_to] = assignee_counts.get(error.assigned_to, 0) + 1
            
            if error.resolved_at and error.created_at:
                resolution_time = (error.resolved_at - error.created_at).total_seconds() / 3600
                resolved_times.append(resolution_time)
        
        completion_percentage = (
            error_counts_by_status[ErrorStatus.RESOLVED] / len(errors) * 100 
            if errors else 100
        )
        
        self.progress_stats = ProgressStats(
            total_errors=len(errors),
            pending_errors=error_counts_by_status[ErrorStatus.PENDING],
            in_progress_errors=error_counts_by_status[ErrorStatus.IN_PROGRESS],
            resolved_errors=error_counts_by_status[ErrorStatus.RESOLVED],
            dismissed_errors=error_counts_by_status[ErrorStatus.DISMISSED],
            needs_review_errors=error_counts_by_status[ErrorStatus.NEEDS_REVIEW],
            completion_percentage=completion_percentage,
            resolution_velocity=0.0,  # TODO: Calculate based on time series data
            average_resolution_time=sum(resolved_times) / len(resolved_times) if resolved_times else 0,
            errors_by_assignee=assignee_counts,
            bottleneck_error_types=[]  # TODO: Calculate based on resolution times
        )
        
        self.last_modified = datetime.now()