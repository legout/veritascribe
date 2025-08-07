"""
Error Management System for VeritaScribe Dashboard

Provides persistent storage, filtering, bulk operations, and analytics
for error tracking and resolution workflow.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from contextlib import contextmanager

from .models import (
    ManagedError, ThesisAnalysisReport, FilterCriteria, 
    ErrorStatus, ErrorType, Severity, ResolutionMethod,
    ProgressStats
)


class ErrorManager:
    """Manages error storage, filtering, and workflow operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize error manager with SQLite database."""
        if db_path is None:
            db_path = Path("dashboard_errors.db")
        
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Errors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    error_id TEXT PRIMARY KEY,
                    document_name TEXT NOT NULL,
                    document_path TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    original_text TEXT NOT NULL,
                    suggested_correction TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    page_number INTEGER NOT NULL,
                    bounding_box TEXT NOT NULL,  -- JSON array
                    paragraph_index INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    assigned_to TEXT,
                    assigned_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolved_by TEXT,
                    resolution_method TEXT,
                    resolution_notes TEXT,
                    notes TEXT,
                    tags TEXT,  -- JSON array
                    priority INTEGER DEFAULT 0,
                    is_recurring BOOLEAN DEFAULT 0,
                    
                    -- Citation-specific fields
                    citation_style_expected TEXT,
                    missing_elements TEXT,  -- JSON array
                    
                    -- Grammar-specific fields
                    grammar_rule TEXT,
                    
                    -- Content-specific fields
                    plausibility_issue TEXT,
                    requires_fact_check BOOLEAN
                )
            """)
            
            # Documents table for metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_path TEXT PRIMARY KEY,
                    document_name TEXT NOT NULL,
                    total_pages INTEGER NOT NULL,
                    total_text_blocks INTEGER NOT NULL,
                    total_words INTEGER NOT NULL,
                    analysis_timestamp TIMESTAMP NOT NULL,
                    created_by TEXT,
                    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    version TEXT DEFAULT '1.0'
                )
            """)
            
            # User activity log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    action TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (error_id) REFERENCES errors (error_id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_document ON errors (document_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_status ON errors (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_type ON errors (error_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_severity ON errors (severity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_page ON errors (page_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_assigned ON errors (assigned_to)")
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def import_analysis_report(self, report: ThesisAnalysisReport) -> None:
        """Import a complete analysis report into the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert/update document metadata
            cursor.execute("""
                INSERT OR REPLACE INTO documents (
                    document_path, document_name, total_pages, total_text_blocks,
                    total_words, analysis_timestamp, created_by, last_modified, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.document_path, report.document_name, report.total_pages,
                report.total_text_blocks, report.total_words, report.analysis_timestamp,
                report.created_by, report.last_modified, report.version
            ))
            
            # Import all errors
            for result in report.analysis_results:
                for error in result.errors:
                    self._insert_error(cursor, error, report.document_name, report.document_path)
            
            conn.commit()
    
    def _insert_error(self, cursor: sqlite3.Cursor, error: ManagedError, 
                     document_name: str, document_path: str) -> None:
        """Insert a single error into the database."""
        cursor.execute("""
            INSERT OR REPLACE INTO errors (
                error_id, document_name, document_path, error_type, severity, status,
                original_text, suggested_correction, explanation, confidence_score,
                page_number, bounding_box, paragraph_index, created_at, updated_at,
                assigned_to, assigned_at, resolved_at, resolved_by, resolution_method,
                resolution_notes, notes, tags, priority, is_recurring,
                citation_style_expected, missing_elements, grammar_rule,
                plausibility_issue, requires_fact_check
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            error.error_id, document_name, document_path, error.error_type.value,
            error.severity.value, error.status.value, error.original_text,
            error.suggested_correction, error.explanation, error.confidence_score,
            error.location.page_number, json.dumps(error.location.bounding_box),
            error.location.paragraph_index, error.created_at, error.updated_at,
            error.assigned_to, error.assigned_at, error.resolved_at, error.resolved_by,
            error.resolution_method.value if error.resolution_method else None,
            error.resolution_notes, error.notes, json.dumps(error.tags),
            error.priority, error.is_recurring,
            error.citation_style_expected, 
            json.dumps(error.missing_elements) if error.missing_elements else None,
            error.grammar_rule, error.plausibility_issue, error.requires_fact_check
        ))
    
    def get_errors(self, document_path: Optional[str] = None, 
                   criteria: Optional[FilterCriteria] = None) -> List[ManagedError]:
        """Get errors with optional filtering."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM errors"
            params = []
            conditions = []
            
            if document_path:
                conditions.append("document_path = ?")
                params.append(document_path)
            
            if criteria:
                if criteria.status:
                    status_placeholders = ",".join("?" * len(criteria.status))
                    conditions.append(f"status IN ({status_placeholders})")
                    params.extend([s.value for s in criteria.status])
                
                if criteria.error_type:
                    type_placeholders = ",".join("?" * len(criteria.error_type))
                    conditions.append(f"error_type IN ({type_placeholders})")
                    params.extend([t.value for t in criteria.error_type])
                
                if criteria.severity:
                    sev_placeholders = ",".join("?" * len(criteria.severity))
                    conditions.append(f"severity IN ({sev_placeholders})")
                    params.extend([s.value for s in criteria.severity])
                
                if criteria.assigned_to:
                    assigned_placeholders = ",".join("?" * len(criteria.assigned_to))
                    conditions.append(f"assigned_to IN ({assigned_placeholders})")
                    params.extend(criteria.assigned_to)
                
                if criteria.page_range:
                    conditions.append("page_number BETWEEN ? AND ?")
                    params.extend(criteria.page_range)
                
                if criteria.confidence_range:
                    conditions.append("confidence_score BETWEEN ? AND ?")
                    params.extend(criteria.confidence_range)
                
                if criteria.search_text:
                    search_condition = """(
                        original_text LIKE ? OR 
                        suggested_correction LIKE ? OR 
                        explanation LIKE ? OR
                        notes LIKE ?
                    )"""
                    conditions.append(search_condition)
                    search_param = f"%{criteria.search_text}%"
                    params.extend([search_param] * 4)
                
                if criteria.has_assignment is not None:
                    if criteria.has_assignment:
                        conditions.append("assigned_to IS NOT NULL")
                    else:
                        conditions.append("assigned_to IS NULL")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_error(row) for row in rows]
    
    def _row_to_error(self, row: sqlite3.Row) -> ManagedError:
        """Convert database row to ManagedError object."""
        from .models import Location
        
        return ManagedError(
            error_id=row["error_id"],
            error_type=ErrorType(row["error_type"]),
            severity=Severity(row["severity"]),
            status=ErrorStatus(row["status"]),
            original_text=row["original_text"],
            suggested_correction=row["suggested_correction"],
            explanation=row["explanation"],
            confidence_score=row["confidence_score"],
            location=Location(
                page_number=row["page_number"],
                bounding_box=json.loads(row["bounding_box"]),
                paragraph_index=row["paragraph_index"]
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            assigned_to=row["assigned_to"],
            assigned_at=row["assigned_at"],
            resolved_at=row["resolved_at"],
            resolved_by=row["resolved_by"],
            resolution_method=ResolutionMethod(row["resolution_method"]) if row["resolution_method"] else None,
            resolution_notes=row["resolution_notes"],
            notes=row["notes"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            priority=row["priority"],
            is_recurring=bool(row["is_recurring"]),
            citation_style_expected=row["citation_style_expected"],
            missing_elements=json.loads(row["missing_elements"]) if row["missing_elements"] else None,
            grammar_rule=row["grammar_rule"],
            plausibility_issue=row["plausibility_issue"],
            requires_fact_check=bool(row["requires_fact_check"]) if row["requires_fact_check"] is not None else None
        )
    
    def update_error(self, error_id: str, updates: Dict[str, Any], user: str = "system") -> bool:
        """Update an error with change tracking."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current error for change logging
            cursor.execute("SELECT * FROM errors WHERE error_id = ?", (error_id,))
            current_row = cursor.fetchone()
            if not current_row:
                return False
            
            # Build update query
            update_fields = []
            params = []
            
            for field, value in updates.items():
                if field in ["status", "assigned_to", "resolved_by", "resolution_method"]:
                    # Log the change
                    old_value = current_row[field]
                    if old_value != value:
                        cursor.execute("""
                            INSERT INTO activity_log (error_id, user, action, old_value, new_value)
                            VALUES (?, ?, ?, ?, ?)
                        """, (error_id, user, f"update_{field}", str(old_value), str(value)))
                
                update_fields.append(f"{field} = ?")
                
                # Handle enum values
                if hasattr(value, 'value'):
                    params.append(value.value)
                elif isinstance(value, (list, dict)):
                    params.append(json.dumps(value))
                else:
                    params.append(value)
            
            # Always update timestamp
            update_fields.append("updated_at = ?")
            params.append(datetime.now())
            params.append(error_id)
            
            query = f"UPDATE errors SET {', '.join(update_fields)} WHERE error_id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            return cursor.rowcount > 0
    
    def bulk_update_errors(self, error_ids: List[str], updates: Dict[str, Any], 
                          user: str = "system") -> int:
        """Update multiple errors at once."""
        count = 0
        for error_id in error_ids:
            if self.update_error(error_id, updates, user):
                count += 1
        return count
    
    def assign_error(self, error_id: str, assigned_to: str, user: str = "system") -> bool:
        """Assign an error to a user."""
        updates = {
            "assigned_to": assigned_to,
            "assigned_at": datetime.now(),
            "status": ErrorStatus.IN_PROGRESS
        }
        return self.update_error(error_id, updates, user)
    
    def resolve_error(self, error_id: str, resolved_by: str, method: ResolutionMethod,
                     notes: str = "", user: str = "system") -> bool:
        """Mark an error as resolved."""
        updates = {
            "status": ErrorStatus.RESOLVED,
            "resolved_at": datetime.now(),
            "resolved_by": resolved_by,
            "resolution_method": method,
            "resolution_notes": notes
        }
        return self.update_error(error_id, updates, user)
    
    def get_progress_stats(self, document_path: Optional[str] = None) -> ProgressStats:
        """Calculate progress statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Base query
            base_query = "SELECT * FROM errors"
            params = []
            if document_path:
                base_query += " WHERE document_path = ?"
                params.append(document_path)
            
            # Get all errors
            cursor.execute(base_query, params)
            errors = cursor.fetchall()
            
            if not errors:
                return ProgressStats(
                    total_errors=0, pending_errors=0, in_progress_errors=0,
                    resolved_errors=0, dismissed_errors=0, needs_review_errors=0,
                    completion_percentage=100.0, resolution_velocity=0.0,
                    average_resolution_time=0.0, errors_by_assignee={},
                    bottleneck_error_types=[]
                )
            
            # Count by status
            status_counts = {status: 0 for status in ErrorStatus}
            assignee_counts = {}
            resolution_times = []
            
            for error in errors:
                status_counts[ErrorStatus(error["status"])] += 1
                
                if error["assigned_to"]:
                    assignee = error["assigned_to"]
                    assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
                
                if error["resolved_at"] and error["created_at"]:
                    resolution_time = (error["resolved_at"] - error["created_at"]).total_seconds() / 3600
                    resolution_times.append(resolution_time)
            
            # Calculate velocity (resolved in last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_resolved = [e for e in errors 
                             if e["resolved_at"] and e["resolved_at"] > week_ago]
            velocity = len(recent_resolved) / 7.0
            
            completion_percentage = (
                status_counts[ErrorStatus.RESOLVED] / len(errors) * 100
                if errors else 100.0
            )
            
            return ProgressStats(
                total_errors=len(errors),
                pending_errors=status_counts[ErrorStatus.PENDING],
                in_progress_errors=status_counts[ErrorStatus.IN_PROGRESS],
                resolved_errors=status_counts[ErrorStatus.RESOLVED],
                dismissed_errors=status_counts[ErrorStatus.DISMISSED],
                needs_review_errors=status_counts[ErrorStatus.NEEDS_REVIEW],
                completion_percentage=completion_percentage,
                resolution_velocity=velocity,
                average_resolution_time=sum(resolution_times) / len(resolution_times) if resolution_times else 0.0,
                errors_by_assignee=assignee_counts,
                bottleneck_error_types=[]  # TODO: Calculate based on resolution patterns
            )
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """Get list of all documents in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.*, COUNT(e.error_id) as total_errors,
                       SUM(CASE WHEN e.status = 'resolved' THEN 1 ELSE 0 END) as resolved_errors
                FROM documents d
                LEFT JOIN errors e ON d.document_path = e.document_path
                GROUP BY d.document_path
                ORDER BY d.last_modified DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "document_path": row["document_path"],
                    "document_name": row["document_name"],
                    "total_pages": row["total_pages"],
                    "total_words": row["total_words"],
                    "analysis_timestamp": row["analysis_timestamp"],
                    "last_modified": row["last_modified"],
                    "total_errors": row["total_errors"],
                    "resolved_errors": row["resolved_errors"],
                    "completion_percentage": (
                        row["resolved_errors"] / row["total_errors"] * 100
                        if row["total_errors"] > 0 else 100.0
                    )
                })
            
            return results
    
    def delete_document(self, document_path: str) -> bool:
        """Delete a document and all its errors."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete errors first (due to foreign key constraint)
            cursor.execute("DELETE FROM errors WHERE document_path = ?", (document_path,))
            
            # Delete document
            cursor.execute("DELETE FROM documents WHERE document_path = ?", (document_path,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def export_errors_to_json(self, criteria: Optional[FilterCriteria] = None, 
                             document_path: Optional[str] = None) -> Dict[str, Any]:
        """Export filtered errors to JSON format."""
        errors = self.get_errors(document_path, criteria)
        
        return {
            "export_timestamp": datetime.now().isoformat(),
            "total_errors": len(errors),
            "filters_applied": criteria.dict() if criteria else None,
            "document_path": document_path,
            "errors": [error.dict() for error in errors]
        }