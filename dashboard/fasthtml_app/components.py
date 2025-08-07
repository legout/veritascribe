"""
HTML Components for FastHTML Dashboard

Reusable components for building the VeritaScribe dashboard interface.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fasthtml.common import *
from typing import List, Optional
import plotly.graph_objects as go
from core.models import ManagedError, ErrorStatus, ErrorType, Severity


def create_nav_bar():
    """Create navigation bar."""
    return Nav(
        Div(
            A(
                I(cls="fas fa-graduation-cap"), 
                " VeritaScribe Dashboard",
                href="/",
                style="text-decoration: none; color: white; font-weight: bold; font-size: 1.2em;"
            ),
            Div(
                A(
                    I(cls="fas fa-home"), 
                    " Dashboard",
                    href="/",
                    cls="nav-link"
                ),
                A(
                    I(cls="fas fa-upload"), 
                    " Import",
                    href="/import", 
                    cls="nav-link"
                ),
                A(
                    I(cls="fas fa-download"), 
                    " Export",
                    href="/export",
                    cls="nav-link"
                ),
                style="display: flex; gap: 20px;"
            ),
            style="display: flex; justify-content: space-between; align-items: center;"
        ),
        style="""
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            padding: 15px 20px;
            color: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        """
    )


def create_page_header(title: str, subtitle: Optional[str] = None):
    """Create page header with title and optional subtitle."""
    elements = [H1(title, style="margin: 0; color: var(--dark-gray);")]
    
    if subtitle:
        elements.append(P(subtitle, style="margin: 10px 0 0 0; color: #666;"))
    
    return Div(
        *elements,
        style="margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid var(--light-gray);"
    )


def create_filter_sidebar(document_path: str):
    """Create filtering sidebar."""
    return Div(
        H4("Filter Errors", style="margin-top: 0; color: var(--dark-gray);"),
        
        Form(
            # Status filter
            Div(
                Label("Status:", cls="form-label"),
                Select(
                    Option("All Statuses", value="all", selected=True),
                    Option("Pending", value="pending"),
                    Option("In Progress", value="in_progress"),
                    Option("Resolved", value="resolved"), 
                    Option("Dismissed", value="dismissed"),
                    Option("Needs Review", value="needs_review"),
                    name="status",
                    cls="form-control",
                    hx_change="true"
                ),
                cls="form-group"
            ),
            
            # Error type filter
            Div(
                Label("Error Type:", cls="form-label"),
                Select(
                    Option("All Types", value="all", selected=True),
                    Option("Citation Format", value="citation_format"),
                    Option("Grammar", value="grammar"),
                    Option("Content Plausibility", value="content_plausibility"),
                    name="error_type",
                    cls="form-control",
                    hx_change="true"
                ),
                cls="form-group"
            ),
            
            # Severity filter
            Div(
                Label("Severity:", cls="form-label"),
                Select(
                    Option("All Severities", value="all", selected=True),
                    Option("High", value="high"),
                    Option("Medium", value="medium"),
                    Option("Low", value="low"),
                    name="severity", 
                    cls="form-control",
                    hx_change="true"
                ),
                cls="form-group"
            ),
            
            # Search box
            Div(
                Label("Search Text:", cls="form-label"),
                Input(
                    type="text",
                    name="search",
                    placeholder="Search in error text...",
                    cls="form-control",
                    hx_change="true",
                    hx_trigger="keyup changed delay:500ms"
                ),
                cls="form-group"
            ),
            
            # This form will trigger updates to the error table
            hx_post=f"/filter-errors/{document_path}",
            hx_target="#error-table-container",
            hx_trigger="change from:select, keyup from:input delay:500ms"
        ),
        
        # Bulk actions section
        Div(
            H5("Bulk Actions", style="color: var(--dark-gray); margin-top: 30px;"),
            
            Select(
                Option("Select Action...", value="", selected=True),
                Option("Mark as Resolved", value="mark_resolved"),
                Option("Mark as Dismissed", value="mark_dismissed"),
                Option("Assign to Me", value="assign_to_me"),
                name="bulk_action",
                cls="form-control",
                style="margin-bottom: 10px;"
            ),
            
            Button(
                "Apply to Selected",
                type="button",
                cls="btn btn-warning",
                style="width: 100%;",
                hx_post="/bulk-update",
                hx_include="[name='selected_errors[]'], [name='bulk_action']",
                hx_target="#bulk-result",
                hx_confirm="Are you sure you want to apply this action to selected errors?"
            ),
            
            Div(id="bulk-result", style="margin-top: 10px;")
        ),
        
        cls="sidebar"
    )


def create_error_table(errors: List[ManagedError], document_path: str):
    """Create interactive error table with checkboxes."""
    if not errors:
        return Div(
            P("No errors match the current filters.", 
              style="text-align: center; color: gray; padding: 40px;"),
            cls="card"
        )
    
    # Table header
    header = Tr(
        Th(
            Input(
                type="checkbox", 
                id="select-all",
                onchange="toggleAllErrorSelection(this)"
            ),
            style="width: 40px;"
        ),
        Th("Status", style="width: 120px;"),
        Th("Type", style="width: 140px;"),
        Th("Severity", style="width: 80px;"),
        Th("Page", style="width: 60px;"),
        Th("Text", style="width: 300px;"),
        Th("Suggestion", style="width: 300px;"),
        Th("Confidence", style="width: 90px;"),
        Th("Actions", style="width: 120px;")
    )
    
    # Table rows
    rows = []
    for error in errors:
        rows.append(create_error_row(error))
    
    return Div(
        # Table controls
        Div(
            Span(f"Showing {len(errors)} errors", style="color: #666;"),
            style="margin-bottom: 15px;"
        ),
        
        # Error table
        Table(
            Thead(header),
            Tbody(*rows),
            cls="error-table"
        ),
        
        # JavaScript for table interactions
        Script("""
        function toggleAllErrorSelection(checkbox) {
            const errorCheckboxes = document.querySelectorAll('input[name="selected_errors[]"]');
            errorCheckboxes.forEach(cb => cb.checked = checkbox.checked);
        }
        
        function updateErrorStatus(errorId, newStatus) {
            htmx.ajax('GET', `/update-error/${errorId}?status=${newStatus}`, {
                target: `#status-${errorId}`,
                swap: 'outerHTML'
            });
        }
        """)
    )


def create_error_row(error: ManagedError):
    """Create a single error table row."""
    return Tr(
        # Checkbox
        Td(
            Input(
                type="checkbox",
                name="selected_errors[]",
                value=error.error_id
            )
        ),
        
        # Status with dropdown
        Td(
            Select(
                Option("Pending", value="pending", 
                      selected=(error.status == ErrorStatus.PENDING)),
                Option("In Progress", value="in_progress",
                      selected=(error.status == ErrorStatus.IN_PROGRESS)),
                Option("Resolved", value="resolved",
                      selected=(error.status == ErrorStatus.RESOLVED)),
                Option("Dismissed", value="dismissed", 
                      selected=(error.status == ErrorStatus.DISMISSED)),
                Option("Needs Review", value="needs_review",
                      selected=(error.status == ErrorStatus.NEEDS_REVIEW)),
                hx_get=f"/update-error/{error.error_id}",
                hx_target=f"#status-{error.error_id}",
                hx_include="this",
                cls="form-control"
            ),
            id=f"status-{error.error_id}"
        ),
        
        # Error type
        Td(error.error_type.value.replace("_", " ").title()),
        
        # Severity with styling
        Td(
            Span(
                error.severity.value.title(),
                cls=f"severity-{error.severity.value}"
            )
        ),
        
        # Page number
        Td(str(error.location.page_number)),
        
        # Original text (truncated)
        Td(
            Span(
                error.original_text[:100] + ("..." if len(error.original_text) > 100 else ""),
                title=error.original_text,  # Full text on hover
                style="cursor: help;"
            )
        ),
        
        # Suggested correction (truncated)
        Td(
            Span(
                error.suggested_correction[:100] + ("..." if len(error.suggested_correction) > 100 else ""),
                title=error.suggested_correction,
                style="cursor: help;"
            )
        ),
        
        # Confidence score
        Td(
            Span(
                f"{error.confidence_score:.2f}",
                style=f"color: {'green' if error.confidence_score > 0.8 else 'orange' if error.confidence_score > 0.6 else 'red'}; font-weight: bold;"
            )
        ),
        
        # Actions
        Td(
            Button(
                I(cls="fas fa-info"),
                title="View Details",
                cls="btn btn-sm",
                style="background: var(--primary-color); color: white; margin-right: 5px;",
                hx_get=f"/error-details/{error.error_id}",
                hx_target="#error-modal",
                hx_trigger="click"
            ),
            Button(
                I(cls="fas fa-check"),
                title="Mark Resolved",
                cls="btn btn-sm btn-success",
                onclick=f"updateErrorStatus('{error.error_id}', 'resolved')"
            )
        )
    )


def create_status_badge(status: ErrorStatus):
    """Create status badge component."""
    status_classes = {
        ErrorStatus.PENDING: "status-pending",
        ErrorStatus.IN_PROGRESS: "status-in-progress", 
        ErrorStatus.RESOLVED: "status-resolved",
        ErrorStatus.DISMISSED: "status-dismissed",
        ErrorStatus.NEEDS_REVIEW: "status-needs-review"
    }
    
    return Span(
        status.value.replace("_", " ").title(),
        cls=f"status-badge {status_classes.get(status, '')}"
    )


def create_chart_container(chart_id: str, figure: go.Figure, title: str):
    """Create container for Plotly chart."""
    # Convert figure to JSON for embedding
    fig_json = figure.to_json()
    
    return Div(
        H4(title, style="margin-bottom: 15px; color: var(--dark-gray);"),
        Div(
            id=chart_id,
            style="height: 400px; width: 100%;"
        ),
        Script(f"""
            var figure = {fig_json};
            var config = {{
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d', 'autoScale2d'],
                toImageButtonOptions: {{
                    format: 'png',
                    filename: '{chart_id}',
                    height: 400,
                    width: 700,
                    scale: 1
                }}
            }};
            Plotly.newPlot('{chart_id}', figure.data, figure.layout, config);
        """),
        style="margin-bottom: 30px;"
    )


def create_document_selector(documents: List[dict], current_doc: Optional[str] = None):
    """Create document selector dropdown."""
    if not documents:
        return Div("No documents available", style="color: gray;")
    
    options = []
    for doc in documents:
        is_selected = current_doc == doc["document_path"]
        completion = doc.get("completion_percentage", 0)
        
        options.append(
            Option(
                f"{doc['document_name']} ({completion:.1f}% complete)",
                value=doc["document_path"],
                selected=is_selected
            )
        )
    
    return Div(
        Label("Select Document:", cls="form-label"),
        Select(
            *options,
            name="document",
            cls="form-control",
            hx_get="/switch-document",
            hx_target="#dashboard-content",
            hx_include="this"
        ),
        cls="form-group"
    )


def create_loading_spinner():
    """Create loading spinner component."""
    return Div(
        I(cls="fas fa-spinner fa-spin", style="font-size: 2em; color: var(--primary-color);"),
        P("Loading...", style="margin-top: 10px; color: #666;"),
        style="text-align: center; padding: 40px;"
    )


def create_error_details_modal(error: ManagedError):
    """Create detailed error view modal."""
    return Div(
        Div(
            # Modal header
            Div(
                H3("Error Details"),
                Button(
                    I(cls="fas fa-times"),
                    onclick="closeModal()",
                    style="background: none; border: none; font-size: 1.5em; cursor: pointer;"
                ),
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"
            ),
            
            # Error information
            Div(
                Div(
                    Strong("Error Type: "),
                    error.error_type.value.replace("_", " ").title(),
                    cls="form-group"
                ),
                Div(
                    Strong("Severity: "),
                    Span(error.severity.value.title(), cls=f"severity-{error.severity.value}"),
                    cls="form-group"
                ),
                Div(
                    Strong("Confidence Score: "),
                    f"{error.confidence_score:.2f}",
                    cls="form-group"
                ),
                Div(
                    Strong("Page: "),
                    str(error.location.page_number),
                    cls="form-group"
                ),
                Div(
                    Strong("Original Text: "),
                    P(error.original_text, style="background: #f8f9fa; padding: 10px; border-radius: 4px;"),
                    cls="form-group"
                ),
                Div(
                    Strong("Suggested Correction: "),
                    P(error.suggested_correction, style="background: #e8f5e8; padding: 10px; border-radius: 4px;"),
                    cls="form-group"
                ),
                Div(
                    Strong("Explanation: "),
                    P(error.explanation, style="background: #f0f8ff; padding: 10px; border-radius: 4px;"),
                    cls="form-group"
                ),
                
                # Notes section
                Div(
                    Strong("Notes: "),
                    Textarea(
                        error.notes or "",
                        name="notes",
                        rows="3",
                        cls="form-control",
                        placeholder="Add your notes here..."
                    ),
                    cls="form-group"
                ),
                
                # Action buttons
                Div(
                    Button("Mark as Resolved", cls="btn btn-success", 
                          onclick=f"updateErrorStatus('{error.error_id}', 'resolved')"),
                    Button("Dismiss", cls="btn btn-secondary",
                          onclick=f"updateErrorStatus('{error.error_id}', 'dismissed')"),
                    Button("Close", onclick="closeModal()", cls="btn"),
                    style="display: flex; gap: 10px; margin-top: 20px;"
                )
            ),
            
            style="background: white; padding: 30px; border-radius: 8px; max-width: 800px; max-height: 80vh; overflow-y: auto;"
        ),
        
        # Modal backdrop
        style="""
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); display: flex; align-items: center;
            justify-content: center; z-index: 1000;
        """,
        id="error-modal",
        onclick="event.target === this && closeModal()"
    )