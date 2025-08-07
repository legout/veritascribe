"""
FastHTML Dashboard Application

Main application entry point for the VeritaScribe error management dashboard.
Uses FastHTML with HTMX for dynamic interactions and Plotly for visualizations.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

# Add parent directories to path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fasthtml.common import *
from fasthtml.components import *
import plotly.graph_objects as go

from core.error_manager import ErrorManager
from core.data_processor import DataProcessor
from core.visualizations import (
    create_error_summary_chart, create_status_pie_chart, 
    create_page_heatmap, create_dashboard_overview,
    get_plotly_config
)
from core.models import FilterCriteria, ErrorStatus, ErrorType, Severity

from fasthtml_app.components import (
    create_nav_bar, create_error_table, create_filter_sidebar,
    create_chart_container, create_status_badge, create_page_header
)


# Global error manager instance
error_manager = ErrorManager()

# FastHTML app setup
css = Style("""
:root {
    --primary-color: #2E86AB;
    --secondary-color: #A23B72;
    --accent-color: #F18F01;
    --success-color: #28A745;
    --warning-color: #FFC107;
    --error-color: #DC3545;
    --light-gray: #F8F9FA;
    --dark-gray: #343A40;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 0;
    background-color: var(--light-gray);
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 20px;
    margin-top: 20px;
}

.sidebar {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    height: fit-content;
}

.main-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.stat-card {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    padding: 20px;
    border-radius: 8px;
    text-align: center;
}

.stat-value {
    font-size: 2em;
    font-weight: bold;
    margin-bottom: 5px;
}

.stat-label {
    font-size: 0.9em;
    opacity: 0.9;
}

.error-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

.error-table th,
.error-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.error-table th {
    background-color: var(--light-gray);
    font-weight: 600;
}

.error-table tr:hover {
    background-color: #f5f5f5;
}

.status-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: 500;
}

.status-pending { background-color: #ffeaa7; color: #2d3436; }
.status-in-progress { background-color: #fab1a0; color: #2d3436; }
.status-resolved { background-color: #00b894; color: white; }
.status-dismissed { background-color: #636e72; color: white; }
.status-needs-review { background-color: #74b9ff; color: white; }

.severity-high { color: var(--error-color); font-weight: bold; }
.severity-medium { color: var(--warning-color); font-weight: bold; }
.severity-low { color: var(--success-color); font-weight: bold; }

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    text-decoration: none;
    display: inline-block;
    transition: all 0.2s;
}

.btn-primary {
    background-color: var(--primary-color);
    color: white;
}

.btn-primary:hover {
    background-color: #1e5f7a;
    transform: translateY(-1px);
}

.btn-success {
    background-color: var(--success-color);
    color: white;
}

.btn-warning {
    background-color: var(--warning-color);
    color: white;
}

.form-group {
    margin-bottom: 15px;
}

.form-label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: var(--dark-gray);
}

.form-control {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    box-sizing: border-box;
}

.form-control:focus {
    border-color: var(--primary-color);
    outline: none;
    box-shadow: 0 0 0 2px rgba(46, 134, 171, 0.2);
}

.chart-container {
    height: 400px;
    margin: 20px 0;
}

@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr;
    }
    
    .stats-row {
        grid-template-columns: 1fr;
    }
}
""")

app, rt = fast_app(
    pico=False,
    hdrs=(
        Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"),
        Script(src="https://unpkg.com/htmx.org@1.9.10"),
        Script(src="https://cdn.plot.ly/plotly-latest.min.js"),
        css
    )
)


@rt("/")
def homepage():
    """Main dashboard page."""
    return Titled("VeritaScribe Dashboard",
        create_nav_bar(),
        Div(
            create_page_header("Dashboard Overview"),
            Div(id="dashboard-content",
                hx_get="/dashboard-content",
                hx_trigger="load"
            ),
            cls="container"
        )
    )


@rt("/dashboard-content")
def dashboard_content():
    """Load main dashboard content."""
    # Get document list
    documents = error_manager.get_document_list()
    
    if not documents:
        return Div(
            H2("Welcome to VeritaScribe Dashboard"),
            P("No documents have been imported yet."),
            Div(
                A("Import Document", href="/import", cls="btn btn-primary"),
                style="margin-top: 20px;"
            ),
            cls="card"
        )
    
    # Get errors for the most recent document
    latest_doc = documents[0]
    errors = error_manager.get_errors(document_path=latest_doc["document_path"])
    stats = error_manager.get_progress_stats(document_path=latest_doc["document_path"])
    
    return Div(
        # Statistics cards
        create_stats_cards(stats, latest_doc),
        
        # Dashboard grid
        Div(
            create_filter_sidebar(latest_doc['document_path']),
            Div(
                # Charts section
                Div(
                    H3("Visual Analytics"),
                    Div(id="charts-container",
                        hx_get=f"/charts/{latest_doc['document_path']}",
                        hx_trigger="load"
                    ),
                    cls="card"
                ),
                
                # Error management section
                Div(
                    H3("Error Management"),
                    Div(# Initially load without filters
                        create_error_table(errors, latest_doc['document_path']upd
                        id="error-table-container",
                        
                        
                    ),
                    cls="card"
                ),
                cls="main-content"
            ),
            cls="dashboard-grid"
        )
    )


@rt("/charts/{document_path:path}")
def get_charts(document_path: str):
    """Generate charts for a specific document."""
    errors = error_manager.get_errors(document_path=document_path)
    stats = error_manager.get_progress_stats(document_path=document_path)
    
    if not errors:
        return P("No errors found for visualization.", style="text-align: center; color: gray; padding: 40px;")
    
    # Get document info for page count
    documents = [doc for doc in error_manager.get_document_list() 
                if doc["document_path"] == document_path]
    total_pages = documents[0]["total_pages"] if documents else 10
    
    # Create charts
    summary_chart = create_error_summary_chart(errors)
    status_chart = create_status_pie_chart(errors)
    heatmap_chart = create_page_heatmap(errors, total_pages)
    
    charts_html = [
        create_chart_container("error-summary", summary_chart, "Error Summary"),
        create_chart_container("status-distribution", status_chart, "Status Distribution"),
        create_chart_container("page-heatmap", heatmap_chart, "Page Distribution")
    ]
    
    return Div(*charts_html)


@rt("/error-table/{document_path:path}")
def get_error_table(document_path: str):
    """Get error table without filters (initial load)."""
    # Get all errors without any filtering
    errors = error_manager.get_errors(document_path=document_path)
    return create_error_table(errors, document_path)


@rt("/filter-errors/{document_path:path}", methods=["POST"])
async def filter_errors(request, document_path: str):
    """Handle error filtering from sidebar."""
    try:
        # Get form data from request
        form = await request.form()
        
        # Extract filter values from form
        status = form.get("status", "all")
        error_type = form.get("error_type", "all")
        severity = form.get("severity", "all")
        search = form.get("search", "")
        
        # Build filter criteria only if filters are specified
        criteria = None
        
        # Only create criteria if we have actual filters (not "all" values)
        if (status and status not in ["all", "All Statuses"]) or \
           (error_type and error_type not in ["all", "All Types"]) or \
           (severity and severity not in ["all", "All Severities"]) or \
           (search and search.strip()):
            
            criteria = FilterCriteria()
            
            if status and status not in ["all", "All Statuses"]:
                try:
                    criteria.status = [ErrorStatus(status)]
                except ValueError:
                    pass  # Invalid status, ignore
            
            if error_type and error_type not in ["all", "All Types"]:
                try:
                    criteria.error_type = [ErrorType(error_type)]
                except ValueError:
                    pass  # Invalid error type, ignore
            
            if severity and severity not in ["all", "All Severities"]:
                try:
                    criteria.severity = [Severity(severity)]
                except ValueError:
                    pass  # Invalid severity, ignore
            
            if search and search.strip():
                criteria.search_text = search.strip()
        
        # Get filtered errors
        errors = error_manager.get_errors(document_path=document_path, criteria=criteria)
        
        return create_error_table(errors, document_path)
    except Exception as e:
        return Div(f"Filter error: {str(e)}", cls="error-message")


@rt("/update-error/{error_id}")
def update_error_status(error_id: str, status: str):
    """Update error status via HTMX."""
    try:
        new_status = ErrorStatus(status)
        success = error_manager.update_error(error_id, {"status": new_status}, "web_user")
        
        if success:
            # Return updated status badge
            return create_status_badge(new_status)
        else:
            return Span("Update failed", cls="error-message")
    except ValueError:
        return Span("Invalid status", cls="error-message")


@rt("/bulk-update", methods=["POST"])
def bulk_update_errors(selected_errors: list = [], bulk_action: str = ""):
    """Handle bulk updates to selected errors."""
    if not selected_errors or not bulk_action:
        return Div("No errors selected or action specified", cls="error-message")
    
    count = 0
    if bulk_action == "mark_resolved":
        count = error_manager.bulk_update_errors(
            selected_errors, 
            {"status": ErrorStatus.RESOLVED}, 
            "web_user"
        )
    elif bulk_action == "mark_dismissed":
        count = error_manager.bulk_update_errors(
            selected_errors,
            {"status": ErrorStatus.DISMISSED},
            "web_user"
        )
    elif bulk_action == "assign_to_me":
        count = error_manager.bulk_update_errors(
            selected_errors,
            {"assigned_to": "web_user", "status": ErrorStatus.IN_PROGRESS},
            "web_user"
        )
    
    return Div(f"Updated {count} errors successfully", 
              cls="success-message",
              hx_trigger="updated")


@rt("/import")
def import_page():
    """Document import page."""
    return Titled("Import Document",
        create_nav_bar(),
        Div(
            create_page_header("Import Analysis Report"),
            Div(
                H3("Upload VeritaScribe JSON Report"),
                Form(
                    Div(
                        Label("Select JSON file:", cls="form-label"),
                        Input(type="file", name="json_file", accept=".json", cls="form-control"),
                        cls="form-group"
                    ),
                    Div(
                        Button("Import Report", type="submit", cls="btn btn-primary"),
                        cls="form-group"
                    ),
                    hx_post="/upload",
                    hx_encoding="multipart/form-data",
                    hx_target="#import-result"
                ),
                Div(id="import-result"),
                cls="card"
            ),
            cls="container"
        )
    )


@rt("/upload", methods=["POST"])  
async def upload_file(request):
    """Handle file upload and import."""
    try:
        # Get the form data
        form = await request.form()
        json_file = form.get("json_file")
        
        if not json_file or not hasattr(json_file, 'filename') or json_file.filename == "":
            return Div("No file selected", cls="error-message")
        
        if not json_file.filename.endswith(".json"):
            return Div("Please select a JSON file", cls="error-message")
        
        # Save uploaded file temporarily
        import tempfile
        
        # Read the file content
        content = await json_file.read()
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        try:
            # Load and convert report
            report = DataProcessor.load_and_convert_report(temp_path)
            
            # Import into database
            error_manager.import_analysis_report(report)
            
            return Div(
                H4("Import Successful!", style="color: var(--success-color);"),
                P(f"Imported document: {report.document_name}"),
                P(f"Total errors: {len(report.get_all_errors())}"),
                A("View Dashboard", href="/", cls="btn btn-primary"),
                cls="success-message"
            )
            
        finally:
            # Clean up temp file
            temp_path.unlink()
        
    except Exception as e:
        return Div(f"Import failed: {str(e)}", cls="error-message")


def create_stats_cards(stats, document_info):
    """Create statistics cards for the dashboard."""
    return Div(
        Div(
            Div(str(stats.total_errors), cls="stat-value"),
            Div("Total Errors", cls="stat-label"),
            cls="stat-card"
        ),
        Div(
            Div(f"{stats.completion_percentage:.1f}%", cls="stat-value"),
            Div("Completed", cls="stat-label"),
            cls="stat-card"
        ),
        Div(
            Div(str(stats.pending_errors), cls="stat-value"),
            Div("Pending", cls="stat-label"),
            cls="stat-card"
        ),
        Div(
            Div(str(document_info["total_pages"]), cls="stat-value"),
            Div("Pages", cls="stat-label"),
            cls="stat-card"
        ),
        cls="stats-row"
    )


if __name__ == "__main__":
    # For development
    serve(host="localhost", port=8000, reload=True)