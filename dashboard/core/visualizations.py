"""
Shared Plotly Visualizations for VeritaScribe Dashboard

These visualization functions work with both FastHTML and Panel implementations.
All functions return Plotly Figure objects that can be embedded in either framework.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta

from .models import ManagedError, ProgressStats, ErrorType, Severity, ErrorStatus


# Color schemes and styling
VERITASCRIBE_COLORS = {
    "primary": "#2E86AB",
    "secondary": "#A23B72", 
    "accent": "#F18F01",
    "success": "#C73E1D",
    "warning": "#FFD23F",
    "error": "#EE6C4D",
    "light_gray": "#F8F9FA",
    "dark_gray": "#343A40"
}

STATUS_COLORS = {
    ErrorStatus.PENDING: "#DC3545",
    ErrorStatus.IN_PROGRESS: "#FFC107", 
    ErrorStatus.RESOLVED: "#28A745",
    ErrorStatus.DISMISSED: "#6C757D",
    ErrorStatus.NEEDS_REVIEW: "#17A2B8"
}

SEVERITY_COLORS = {
    Severity.HIGH: "#DC3545",
    Severity.MEDIUM: "#FD7E14", 
    Severity.LOW: "#28A745"
}

ERROR_TYPE_COLORS = {
    ErrorType.CITATION_FORMAT: "#2E86AB",
    ErrorType.GRAMMAR: "#A23B72",
    ErrorType.CONTENT_PLAUSIBILITY: "#F18F01"
}


def create_error_summary_chart(errors: List[ManagedError]) -> go.Figure:
    """Create summary bar chart of errors by type and severity."""
    if not errors:
        fig = go.Figure()
        fig.add_annotation(
            text="No errors to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig
    
    # Count errors by type and severity
    data = []
    for error in errors:
        data.append({
            "error_type": error.error_type.value.replace("_", " ").title(),
            "severity": error.severity.value.title(),
            "status": error.status.value.replace("_", " ").title()
        })
    
    df = pd.DataFrame(data)
    
    # Create grouped bar chart
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Errors by Type", "Errors by Severity"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Errors by type
    type_counts = df["error_type"].value_counts()
    fig.add_trace(
        go.Bar(
            x=type_counts.index,
            y=type_counts.values,
            marker_color=[ERROR_TYPE_COLORS.get(ErrorType(t.lower().replace(" ", "_")), 
                                                VERITASCRIBE_COLORS["primary"]) 
                         for t in type_counts.index],
            name="By Type",
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Errors by severity  
    severity_counts = df["severity"].value_counts()
    fig.add_trace(
        go.Bar(
            x=severity_counts.index,
            y=severity_counts.values,
            marker_color=[SEVERITY_COLORS.get(Severity(s.lower()), 
                                             VERITASCRIBE_COLORS["accent"]) 
                         for s in severity_counts.index],
            name="By Severity",
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title="Error Summary Overview",
        height=400,
        template="plotly_white",
        font=dict(size=12)
    )
    
    return fig


def create_status_pie_chart(errors: List[ManagedError]) -> go.Figure:
    """Create pie chart showing error status distribution."""
    if not errors:
        return _create_empty_chart("No errors to display")
    
    status_counts = {}
    for error in errors:
        status = error.status.value.replace("_", " ").title()
        status_counts[status] = status_counts.get(status, 0) + 1
    
    fig = go.Figure(data=[go.Pie(
        labels=list(status_counts.keys()),
        values=list(status_counts.values()),
        marker_colors=[STATUS_COLORS.get(ErrorStatus(k.lower().replace(" ", "_")), 
                                        VERITASCRIBE_COLORS["primary"]) 
                      for k in status_counts.keys()],
        textinfo='label+percent+value',
        textposition='outside'
    )])
    
    fig.update_layout(
        title="Error Status Distribution",
        height=400,
        template="plotly_white",
        font=dict(size=12)
    )
    
    return fig


def create_page_heatmap(errors: List[ManagedError], total_pages: int) -> go.Figure:
    """Create heatmap showing error distribution across pages."""
    if not errors:
        return _create_empty_chart("No errors to display")
    
    # Count errors per page
    page_counts = {}
    for error in errors:
        page = error.location.page_number
        page_counts[page] = page_counts.get(page, 0) + 1
    
    # Create matrix for heatmap (arrange in grid)
    cols = min(10, total_pages)  # Max 10 columns
    rows = (total_pages + cols - 1) // cols
    
    z_data = []
    page_labels = []
    
    for row in range(rows):
        z_row = []
        label_row = []
        for col in range(cols):
            page_num = row * cols + col + 1
            if page_num <= total_pages:
                count = page_counts.get(page_num, 0)
                z_row.append(count)
                label_row.append(f"Page {page_num}<br>{count} errors")
            else:
                z_row.append(0)
                label_row.append("")
        z_data.append(z_row)
        page_labels.append(label_row)
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        text=page_labels,
        texttemplate="%{text}",
        textfont={"size": 10},
        colorscale="Reds",
        showscale=True,
        colorbar=dict(title="Error Count")
    ))
    
    fig.update_layout(
        title=f"Error Distribution Across {total_pages} Pages",
        height=max(300, rows * 50),
        template="plotly_white",
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False),
        font=dict(size=12)
    )
    
    return fig


def create_confidence_histogram(errors: List[ManagedError]) -> go.Figure:
    """Create histogram of confidence scores."""
    if not errors:
        return _create_empty_chart("No errors to display")
    
    confidence_scores = [error.confidence_score for error in errors]
    
    fig = go.Figure(data=[go.Histogram(
        x=confidence_scores,
        nbinsx=20,
        marker_color=VERITASCRIBE_COLORS["primary"],
        opacity=0.7
    )])
    
    # Add vertical lines for quartiles
    q25 = pd.Series(confidence_scores).quantile(0.25)
    q50 = pd.Series(confidence_scores).quantile(0.50)
    q75 = pd.Series(confidence_scores).quantile(0.75)
    
    for q, label, color in [(q25, "Q1", "orange"), (q50, "Median", "red"), (q75, "Q3", "orange")]:
        fig.add_vline(x=q, line_dash="dash", line_color=color, 
                     annotation_text=f"{label}: {q:.2f}")
    
    fig.update_layout(
        title="Confidence Score Distribution",
        xaxis_title="Confidence Score",
        yaxis_title="Number of Errors",
        height=400,
        template="plotly_white",
        font=dict(size=12)
    )
    
    return fig


def create_progress_timeline(stats: ProgressStats, days: int = 30) -> go.Figure:
    """Create timeline showing progress over time (simulated for now)."""
    # TODO: Replace with actual time-series data from database
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Simulate progress data
    cumulative_resolved = []
    daily_velocity = stats.resolution_velocity
    
    for i, date in enumerate(dates):
        resolved = min(i * daily_velocity, stats.resolved_errors)
        cumulative_resolved.append(resolved)
    
    fig = go.Figure()
    
    # Cumulative resolved line
    fig.add_trace(go.Scatter(
        x=dates,
        y=cumulative_resolved,
        mode='lines+markers',
        name='Cumulative Resolved',
        line=dict(color=VERITASCRIBE_COLORS["success"], width=3),
        marker=dict(size=4)
    ))
    
    # Target line
    fig.add_hline(
        y=stats.total_errors,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Target: {stats.total_errors} errors"
    )
    
    fig.update_layout(
        title="Error Resolution Progress",
        xaxis_title="Date",
        yaxis_title="Cumulative Resolved Errors",
        height=400,
        template="plotly_white",
        hovermode='x unified',
        font=dict(size=12)
    )
    
    return fig


def create_workload_distribution(stats: ProgressStats) -> go.Figure:
    """Create bar chart showing error distribution by assignee."""
    if not stats.errors_by_assignee:
        return _create_empty_chart("No assigned errors")
    
    assignees = list(stats.errors_by_assignee.keys())
    error_counts = list(stats.errors_by_assignee.values())
    
    fig = go.Figure(data=[go.Bar(
        x=assignees,
        y=error_counts,
        marker_color=VERITASCRIBE_COLORS["primary"],
        text=error_counts,
        textposition='outside'
    )])
    
    fig.update_layout(
        title="Workload Distribution by Assignee", 
        xaxis_title="Assignee",
        yaxis_title="Number of Assigned Errors",
        height=400,
        template="plotly_white",
        font=dict(size=12)
    )
    
    return fig


def create_error_trends_by_type(errors: List[ManagedError], days: int = 7) -> go.Figure:
    """Create line chart showing error trends by type over time."""
    if not errors:
        return _create_empty_chart("No errors to display")
    
    # Group errors by date and type
    df_data = []
    for error in errors:
        df_data.append({
            "date": error.created_at.date(),
            "error_type": error.error_type.value.replace("_", " ").title(),
            "status": error.status.value
        })
    
    df = pd.DataFrame(df_data)
    
    if df.empty:
        return _create_empty_chart("No error data available")
    
    # Create date range
    end_date = df["date"].max()
    start_date = end_date - timedelta(days=days-1)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    fig = go.Figure()
    
    # Add line for each error type
    for error_type in df["error_type"].unique():
        type_df = df[df["error_type"] == error_type]
        daily_counts = type_df.groupby("date").size().reindex(date_range, fill_value=0)
        
        fig.add_trace(go.Scatter(
            x=daily_counts.index,
            y=daily_counts.values,
            mode='lines+markers',
            name=error_type,
            line=dict(width=2),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        title=f"Error Trends by Type (Last {days} Days)",
        xaxis_title="Date",
        yaxis_title="New Errors",
        height=400,
        template="plotly_white",
        hovermode='x unified',
        font=dict(size=12)
    )
    
    return fig


def create_resolution_time_analysis(errors: List[ManagedError]) -> go.Figure:
    """Create box plot showing resolution time by error type."""
    resolved_errors = [e for e in errors if e.resolved_at and e.created_at]
    
    if not resolved_errors:
        return _create_empty_chart("No resolved errors to analyze")
    
    # Calculate resolution times in hours
    data = []
    for error in resolved_errors:
        resolution_time = (error.resolved_at - error.created_at).total_seconds() / 3600
        data.append({
            "error_type": error.error_type.value.replace("_", " ").title(),
            "resolution_time": resolution_time,
            "severity": error.severity.value.title()
        })
    
    df = pd.DataFrame(data)
    
    fig = go.Figure()
    
    for error_type in df["error_type"].unique():
        type_data = df[df["error_type"] == error_type]["resolution_time"]
        
        fig.add_trace(go.Box(
            y=type_data,
            name=error_type,
            boxmean='sd',  # Show standard deviation
            marker_color=ERROR_TYPE_COLORS.get(
                ErrorType(error_type.lower().replace(" ", "_")), 
                VERITASCRIBE_COLORS["primary"]
            )
        ))
    
    fig.update_layout(
        title="Resolution Time Analysis by Error Type",
        xaxis_title="Error Type",
        yaxis_title="Resolution Time (Hours)",
        height=400,
        template="plotly_white",
        font=dict(size=12)
    )
    
    return fig


def create_dashboard_overview(errors: List[ManagedError], stats: ProgressStats) -> go.Figure:
    """Create comprehensive dashboard overview with multiple metrics."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Status Distribution", 
            "Progress Overview",
            "Error Types", 
            "Severity Breakdown"
        ),
        specs=[
            [{"type": "pie"}, {"type": "indicator"}],
            [{"type": "bar"}, {"type": "bar"}]
        ]
    )
    
    # Status pie chart
    if errors:
        status_counts = {}
        for error in errors:
            status = error.status.value.replace("_", " ").title()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        fig.add_trace(go.Pie(
            labels=list(status_counts.keys()),
            values=list(status_counts.values()),
            name="Status"
        ), row=1, col=1)
    
    # Progress indicator
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=stats.completion_percentage,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Completion %"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': VERITASCRIBE_COLORS["success"]},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ), row=1, col=2)
    
    # Error types
    if errors:
        type_counts = {}
        for error in errors:
            error_type = error.error_type.value.replace("_", " ").title()
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
        
        fig.add_trace(go.Bar(
            x=list(type_counts.keys()),
            y=list(type_counts.values()),
            name="Types"
        ), row=2, col=1)
    
    # Severity breakdown
    if errors:
        severity_counts = {}
        for error in errors:
            severity = error.severity.value.title()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        fig.add_trace(go.Bar(
            x=list(severity_counts.keys()),
            y=list(severity_counts.values()),
            name="Severity"
        ), row=2, col=2)
    
    fig.update_layout(
        title="Dashboard Overview",
        height=600,
        template="plotly_white",
        showlegend=False,
        font=dict(size=10)
    )
    
    return fig


def _create_empty_chart(message: str) -> go.Figure:
    """Create empty chart with message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        height=400,
        template="plotly_white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    return fig


def get_plotly_config() -> dict:
    """Get standard Plotly configuration for all charts."""
    return {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': [
            'pan2d', 'lasso2d', 'select2d', 'autoScale2d'
        ],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'veritascribe_chart',
            'height': 500,
            'width': 700,
            'scale': 1
        }
    }


# Export functions for easy import
__all__ = [
    'create_error_summary_chart',
    'create_status_pie_chart', 
    'create_page_heatmap',
    'create_confidence_histogram',
    'create_progress_timeline',
    'create_workload_distribution',
    'create_error_trends_by_type',
    'create_resolution_time_analysis',
    'create_dashboard_overview',
    'get_plotly_config',
    'VERITASCRIBE_COLORS',
    'STATUS_COLORS',
    'SEVERITY_COLORS',
    'ERROR_TYPE_COLORS'
]