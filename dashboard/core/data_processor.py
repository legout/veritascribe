"""
Data Processing Utilities for VeritaScribe Dashboard

Handles loading, parsing, and converting VeritaScribe JSON reports
into the enhanced dashboard data models with error management capabilities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Union
import uuid

from .models import (
    ThesisAnalysisReport, AnalysisResult, ManagedError, TextBlock,
    Location, ErrorType, Severity, ErrorStatus, DocumentStats, ProgressStats
)


class DataProcessor:
    """Processes VeritaScribe JSON reports into dashboard-compatible models."""
    
    @staticmethod
    def load_json_report(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load JSON report from file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Report file not found: {path}")
        
        try:
            with open(path, 'r',) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {path}: {e}")
    
    @staticmethod
    def convert_original_error_to_managed(error_data: Dict[str, Any]) -> ManagedError:
        """Convert original error format to ManagedError with enhanced fields."""
        
        # Extract location information
        location_data = error_data.get("location", {})
        location = Location(
            page_number=location_data.get("page_number", 1),
            bounding_box=location_data.get("bounding_box", [0, 0, 0, 0]),
            paragraph_index=location_data.get("paragraph_index", 0)
        )
        
        # Map error type
        error_type_str = error_data.get("error_type", "grammar")
        try:
            error_type = ErrorType(error_type_str)
        except ValueError:
            # Default to grammar if unknown type
            error_type = ErrorType.GRAMMAR
        
        # Map severity
        severity_str = error_data.get("severity", "medium")
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.MEDIUM
        
        # Create managed error with default status
        managed_error = ManagedError(
            error_type=error_type,
            severity=severity,
            original_text=error_data.get("original_text", ""),
            suggested_correction=error_data.get("suggested_correction", ""),
            explanation=error_data.get("explanation", ""),
            location=location,
            confidence_score=error_data.get("confidence_score", 0.0),
            status=ErrorStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            
            # Citation-specific fields
            citation_style_expected=error_data.get("citation_style_expected"),
            missing_elements=error_data.get("missing_elements"),
            
            # Grammar-specific fields  
            grammar_rule=error_data.get("grammar_rule"),
            
            # Content-specific fields
            plausibility_issue=error_data.get("plausibility_issue"),
            requires_fact_check=error_data.get("requires_fact_check")
        )
        
        return managed_error
    
    @staticmethod
    def convert_text_block(block_data: Dict[str, Any]) -> TextBlock:
        """Convert text block data to TextBlock model."""
        return TextBlock(
            content=block_data.get("content", ""),
            page_number=block_data.get("page_number", 1),
            bounding_box=block_data.get("bounding_box", [0, 0, 0, 0]),
            block_index=block_data.get("block_index", 0),
            word_count=block_data.get("word_count", 0),
            character_count=block_data.get("character_count", 0)
        )
    
    @staticmethod
    def convert_json_to_analysis_report(json_data: Dict[str, Any]) -> ThesisAnalysisReport:
        """Convert original JSON format to enhanced ThesisAnalysisReport."""
        
        # Extract basic document information
        document_name = json_data.get("document_name", "Unknown Document")
        document_path = json_data.get("document_path", "")
        
        # Parse timestamp
        timestamp_str = json_data.get("analysis_timestamp", "")
        try:
            analysis_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            analysis_timestamp = datetime.now()
        
        # Extract document stats
        total_pages = json_data.get("total_pages", 1)
        total_text_blocks = json_data.get("total_text_blocks", 0)
        total_words = json_data.get("total_words", 0)
        
        # Process analysis results
        analysis_results = []
        original_results = json_data.get("analysis_results", [])
        
        for result_data in original_results:
            # Convert text block
            text_block_data = result_data.get("text_block", {})
            text_block = DataProcessor.convert_text_block(text_block_data)
            
            # Convert errors to managed errors
            managed_errors = []
            original_errors = result_data.get("errors", [])
            
            for error_data in original_errors:
                managed_error = DataProcessor.convert_original_error_to_managed(error_data)
                managed_errors.append(managed_error)
            
            # Parse analysis timestamp for this result
            result_timestamp_str = result_data.get("analysis_timestamp", timestamp_str)
            try:
                result_timestamp = datetime.fromisoformat(result_timestamp_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                result_timestamp = analysis_timestamp
            
            analysis_result = AnalysisResult(
                text_block=text_block,
                errors=managed_errors,
                analysis_timestamp=result_timestamp,
                processing_time_seconds=result_data.get("processing_time_seconds", 0.0)
            )
            analysis_results.append(analysis_result)
        
        # Create the report
        report = ThesisAnalysisReport(
            document_name=document_name,
            document_path=document_path,
            analysis_timestamp=analysis_timestamp,
            total_pages=total_pages,
            total_text_blocks=total_text_blocks,
            total_words=total_words,
            analysis_results=analysis_results,
            document_stats=DocumentStats(  # Will be recalculated
                total_pages=total_pages,
                total_text_blocks=total_text_blocks,
                total_words=total_words,
                total_errors=0,
                errors_by_type={},
                errors_by_severity={},
                errors_by_status={},
                average_confidence=0.0,
                most_problematic_pages=[]
            ),
            progress_stats=ProgressStats(  # Will be recalculated
                total_errors=0,
                pending_errors=0,
                in_progress_errors=0,
                resolved_errors=0,
                dismissed_errors=0,
                needs_review_errors=0,
                completion_percentage=0.0,
                resolution_velocity=0.0,
                average_resolution_time=0.0,
                errors_by_assignee={},
                bottleneck_error_types=[]
            ),
            created_by=json_data.get("created_by"),
            last_modified=datetime.now(),
            version=json_data.get("version", "1.0")
        )
        
        # Calculate statistics
        report.update_stats()
        
        return report
    
    @staticmethod
    def load_and_convert_report(file_path: Union[str, Path]) -> ThesisAnalysisReport:
        """Load JSON report and convert to ThesisAnalysisReport."""
        json_data = DataProcessor.load_json_report(file_path)
        return DataProcessor.convert_json_to_analysis_report(json_data)
    
    @staticmethod
    def export_report_to_json(report: ThesisAnalysisReport) -> Dict[str, Any]:
        """Convert ThesisAnalysisReport back to JSON format."""
        # Convert to dictionary format suitable for JSON export
        analysis_results = []
        
        for result in report.analysis_results:
            # Convert text block
            text_block = {
                "content": result.text_block.content,
                "page_number": result.text_block.page_number,
                "bounding_box": result.text_block.bounding_box,
                "block_index": result.text_block.block_index,
                "word_count": result.text_block.word_count,
                "character_count": result.text_block.character_count
            }
            
            # Convert errors
            errors = []
            for error in result.errors:
                error_dict = {
                    "error_id": error.error_id,
                    "error_type": error.error_type.value,
                    "severity": error.severity.value,
                    "status": error.status.value,
                    "original_text": error.original_text,
                    "suggested_correction": error.suggested_correction,
                    "explanation": error.explanation,
                    "confidence_score": error.confidence_score,
                    "location": {
                        "page_number": error.location.page_number,
                        "bounding_box": error.location.bounding_box,
                        "paragraph_index": error.location.paragraph_index
                    },
                    "created_at": error.created_at.isoformat(),
                    "updated_at": error.updated_at.isoformat(),
                    "assigned_to": error.assigned_to,
                    "assigned_at": error.assigned_at.isoformat() if error.assigned_at else None,
                    "resolved_at": error.resolved_at.isoformat() if error.resolved_at else None,
                    "resolved_by": error.resolved_by,
                    "resolution_method": error.resolution_method.value if error.resolution_method else None,
                    "resolution_notes": error.resolution_notes,
                    "notes": error.notes,
                    "tags": error.tags,
                    "priority": error.priority,
                    "is_recurring": error.is_recurring
                }
                
                # Add type-specific fields if present
                if error.citation_style_expected:
                    error_dict["citation_style_expected"] = error.citation_style_expected
                if error.missing_elements:
                    error_dict["missing_elements"] = error.missing_elements
                if error.grammar_rule:
                    error_dict["grammar_rule"] = error.grammar_rule
                if error.plausibility_issue:
                    error_dict["plausibility_issue"] = error.plausibility_issue
                if error.requires_fact_check is not None:
                    error_dict["requires_fact_check"] = error.requires_fact_check
                
                errors.append(error_dict)
            
            result_dict = {
                "text_block": text_block,
                "errors": errors,
                "analysis_timestamp": result.analysis_timestamp.isoformat(),
                "processing_time_seconds": result.processing_time_seconds
            }
            analysis_results.append(result_dict)
        
        # Main report structure
        report_dict = {
            "document_name": report.document_name,
            "document_path": report.document_path,
            "analysis_timestamp": report.analysis_timestamp.isoformat(),
            "total_pages": report.total_pages,
            "total_text_blocks": report.total_text_blocks,
            "total_words": report.total_words,
            "analysis_results": analysis_results,
            "document_stats": {
                "total_errors": report.document_stats.total_errors,
                "errors_by_type": {k.value: v for k, v in report.document_stats.errors_by_type.items()},
                "errors_by_severity": {k.value: v for k, v in report.document_stats.errors_by_severity.items()},
                "errors_by_status": {k.value: v for k, v in report.document_stats.errors_by_status.items()},
                "average_confidence": report.document_stats.average_confidence,
                "most_problematic_pages": report.document_stats.most_problematic_pages
            },
            "progress_stats": {
                "total_errors": report.progress_stats.total_errors,
                "pending_errors": report.progress_stats.pending_errors,
                "in_progress_errors": report.progress_stats.in_progress_errors,
                "resolved_errors": report.progress_stats.resolved_errors,
                "dismissed_errors": report.progress_stats.dismissed_errors,
                "needs_review_errors": report.progress_stats.needs_review_errors,
                "completion_percentage": report.progress_stats.completion_percentage,
                "resolution_velocity": report.progress_stats.resolution_velocity,
                "average_resolution_time": report.progress_stats.average_resolution_time,
                "errors_by_assignee": report.progress_stats.errors_by_assignee,
                "bottleneck_error_types": [t.value for t in report.progress_stats.bottleneck_error_types]
            },
            "created_by": report.created_by,
            "last_modified": report.last_modified.isoformat(),
            "version": report.version
        }
        
        return report_dict
    
    @staticmethod
    def save_report_to_json(report: ThesisAnalysisReport, file_path: Union[str, Path]) -> None:
        """Save ThesisAnalysisReport to JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        report_dict = DataProcessor.export_report_to_json(report)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def validate_json_report(json_data: Dict[str, Any]) -> List[str]:
        """Validate JSON report structure and return list of issues."""
        issues = []
        
        # Check required fields
        required_fields = ["document_name", "analysis_results"]
        for field in required_fields:
            if field not in json_data:
                issues.append(f"Missing required field: {field}")
        
        # Check analysis results structure
        if "analysis_results" in json_data:
            analysis_results = json_data["analysis_results"]
            if not isinstance(analysis_results, list):
                issues.append("analysis_results must be a list")
            else:
                for i, result in enumerate(analysis_results):
                    if not isinstance(result, dict):
                        issues.append(f"analysis_results[{i}] must be a dictionary")
                        continue
                    
                    if "text_block" not in result:
                        issues.append(f"analysis_results[{i}] missing text_block")
                    
                    if "errors" not in result:
                        issues.append(f"analysis_results[{i}] missing errors")
                    elif not isinstance(result["errors"], list):
                        issues.append(f"analysis_results[{i}].errors must be a list")
                    else:
                        # Validate individual errors
                        for j, error in enumerate(result["errors"]):
                            if not isinstance(error, dict):
                                issues.append(f"analysis_results[{i}].errors[{j}] must be a dictionary")
                                continue
                            
                            error_required = ["error_type", "severity", "original_text", 
                                            "suggested_correction", "explanation"]
                            for field in error_required:
                                if field not in error:
                                    issues.append(f"analysis_results[{i}].errors[{j}] missing {field}")
        
        return issues
    
    @staticmethod
    def get_sample_error_for_testing() -> ManagedError:
        """Generate a sample error for testing purposes."""
        return ManagedError(
            error_id=f"test_{uuid.uuid4().hex[:8]}",
            error_type=ErrorType.CITATION_FORMAT,
            severity=Severity.HIGH,
            original_text="This is a sample error text [1].",
            suggested_correction="This is a sample error text [1].",
            explanation="Sample error for testing dashboard functionality.",
            location=Location(
                page_number=1,
                bounding_box=[100.0, 200.0, 400.0, 220.0],
                paragraph_index=0
            ),
            confidence_score=0.95,
            status=ErrorStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            citation_style_expected="IEEE",
            missing_elements=["proper formatting"]
        )
    
    @staticmethod
    def create_sample_report() -> ThesisAnalysisReport:
        """Create a sample report for testing purposes."""
        errors = [
            DataProcessor.get_sample_error_for_testing(),
            ManagedError(
                error_type=ErrorType.GRAMMAR,
                severity=Severity.MEDIUM,
                original_text="This sentence have a grammar error.",
                suggested_correction="This sentence has a grammar error.",
                explanation="Subject-verb agreement error.",
                location=Location(page_number=2, bounding_box=[50, 100, 300, 120], paragraph_index=1),
                confidence_score=0.88,
                status=ErrorStatus.IN_PROGRESS,
                assigned_to="reviewer@example.com"
            )
        ]
        
        text_block = TextBlock(
            content="Sample text content",
            page_number=1,
            bounding_box=[0, 0, 500, 700],
            block_index=0,
            word_count=20,
            character_count=100
        )
        
        analysis_result = AnalysisResult(
            text_block=text_block,
            errors=errors,
            analysis_timestamp=datetime.now(),
            processing_time_seconds=1.5
        )
        
        report = ThesisAnalysisReport(
            document_name="Sample Thesis.pdf",
            document_path="/sample/path/thesis.pdf",
            analysis_timestamp=datetime.now(),
            total_pages=25,
            total_text_blocks=150,
            total_words=8000,
            analysis_results=[analysis_result],
            document_stats=DocumentStats(
                total_pages=25, total_text_blocks=150, total_words=8000,
                total_errors=0, errors_by_type={}, errors_by_severity={}, 
                errors_by_status={}, average_confidence=0.0, most_problematic_pages=[]
            ),
            progress_stats=ProgressStats(
                total_errors=0, pending_errors=0, in_progress_errors=0,
                resolved_errors=0, dismissed_errors=0, needs_review_errors=0,
                completion_percentage=0.0, resolution_velocity=0.0,
                average_resolution_time=0.0, errors_by_assignee={}, bottleneck_error_types=[]
            ),
            created_by="test_user"
        )
        
        report.update_stats()
        return report