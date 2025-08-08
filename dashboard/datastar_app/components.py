from fasthtml.common import *
from typing import List, Dict
from core.models import ManagedError, ErrorStatus

# datastar attribute helpers
try:
    from datastar_py import attribute_generator as data  # type: ignore
except Exception:  # pragma: no cover
    # Minimal no-op fallback to keep server rendering functional without datastar_py installed
    class _DataShim:
        @staticmethod
        def on(event: str, action: str) -> dict:
            return {}
    data = _DataShim()


def page_layout(title, *content):
    # Refactored layout:
    # - Navbar tabs drive datastar actions that show/hide content areas and trigger GETs to load them
    # - Sidebar (filters) placed in a left column
    # - Main content area hosts several named content regions which datastar updates
    return (
        Title(title),
        # Minimal styles to keep content areas hidden unless active
        Style(
            """
            .content-area { display: none; }
            .content-area.active { display: block; }
            """
        ),
        Header(
            Nav(
                Div("VeritaScribe", cls="navbar-start text-xl font-bold px-4"),
                Div(
                    A(
                        "Dashboard",
                        href="#",
                        id="nav-dashboard",
                        cls="btn btn-ghost btn-active mx-1",
                        data_on_click="@show('#dashboard-content');@hide('#errors-content,#analytics-content,#import-content');@removeClass('#nav-errors,#nav-analytics,#nav-import', 'btn-active');@addClass('#nav-dashboard', 'btn-active')"
                    ),
                    A(
                        "Errors",
                        href="#",
                        id="nav-errors",
                        cls="btn btn-ghost mx-1",
                        data_on_click="@show('#errors-content');@hide('#dashboard-content,#analytics-content,#import-content');@removeClass('#nav-dashboard,#nav-analytics,#nav-import', 'btn-active');@addClass('#nav-errors', 'btn-active');@get('/dashboard/errors', '#errors-full-table-container')"
                    ),
                    A(
                        "Analytics",
                        href="#",
                        id="nav-analytics",
                        cls="btn btn-ghost mx-1",
                        data_on_click="@show('#analytics-content');@hide('#dashboard-content,#errors-content,#import-content');@removeClass('#nav-dashboard,#nav-errors,#nav-import', 'btn-active');@addClass('#nav-analytics', 'btn-active');@get('/dashboard/stats', '#analytics-stats-container')"
                    ),
                    A(
                        "Import",
                        href="#",
                        id="nav-import",
                        cls="btn btn-ghost mx-1",
                        data_on_click="@show('#import-content');@hide('#dashboard-content,#errors-content,#analytics-content');@removeClass('#nav-dashboard,#nav-errors,#nav-analytics', 'btn-active');@addClass('#nav-import', 'btn-active');@get('/dashboard/import_form', '#import-form-container')"
                    ),
                    cls="flex-none px-4"
                ),
                cls="navbar bg-base-200 shadow-md"
            )
        ),
        Main(
            # Page wrapper + content container
            Div(
                # Page body: sidebar + main content container
                Div(
                    # Sidebar column (filters)
                    Div(
                        *content,
                        cls="w-full lg:w-80 p-4 sticky top-6 self-start"
                    ),
                    # Main display column with named content areas
                    Div(
                        # Dashboard content (shown by default)
                        Div(
                            Div(id="dashboard-stats-container", cls="mb-4"),
                            Div(id="dashboard-errors-container"),
                            id="dashboard-content",
                            cls="content-area active w-full",
                            data_on_ready="@get('/dashboard/stats', '#dashboard-stats-container');@get('/dashboard/errors', '#dashboard-errors-container')"
                        ),
                        # Errors full view
                        Div(
                            Div("Loading errors...", id="errors-full-table-container"),
                            id="errors-content",
                            cls="content-area w-full",
                        ),
                        # Analytics view
                        Div(
                            Div("Loading analytics...", id="analytics-stats-container"),
                            id="analytics-content",
                            cls="content-area w-full",
                        ),
                        # Import/upload view
                        Div(
                            Div("Loading import form...", id="import-form-container"),
                            id="import-content",
                            cls="content-area w-full",
                        ),
                        cls="flex-1 p-4 space-y-4"
                    ),
                    cls="flex flex-col lg:flex-row gap-6 items-start min-h-[60vh] max-w-6xl mx-auto w-full py-6 px-4"
                ),
                cls="min-h-screen bg-base-200"
            ),
            # Hidden global containers which can also receive datastar updates when needed
            Div(id="stats-cards-container", cls="hidden"),
            Div(id="errors-table-container", cls="hidden"),
            Div(id="import-form-container", cls="hidden"),
            # Scripts and styles (loaded once)
            Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
            Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@5"),
            Script(type="module", src="https://cdn.jsdelivr.net/npm/datastar@0.1.0/bundles/datastar.js", defer=True),
        )
    )


def stats_cards(counts: Dict[str, int]):
    # daisyUI stats block wrapped in a subtle card to improve contrast on a light background
    return Div(
        Div(
            Div(
                Div("Total Errors", cls="stat-title"),
                Div(str(counts.get("total", 0)), cls="stat-value"),
                cls="stat"
            ),
            Div(
                Div("Pending", cls="stat-title"),
                Div(str(counts.get("pending", 0)), cls="stat-value text-warning"),
                cls="stat"
            ),
            Div(
                Div("Resolved", cls="stat-title"),
                Div(str(counts.get("completed", 0)), cls="stat-value text-success"),
                cls="stat"
            ),
            cls="stats stats-vertical lg:stats-horizontal"
        ),
        cls="card bg-base-100 p-4 shadow",
        id="stats"
    )


def filter_sidebar():
    # Form posts as form-data; server uses it to update filter_criteria
    # Adjusted spacing and background to behave as a left-hand sidebar
    return Form(
        Fieldset(
            Legend("Filters", cls="text-lg font-semibold"),
            Div(
                Label("Status", cls="label"),
                Select(
                    Option("All", value=""),
                    # Use model enum values to match server parsing
                    Option("Pending", value=ErrorStatus.PENDING.value),
                    Option("Resolved", value=ErrorStatus.RESOLVED.value),
                    name="status", cls="select select-bordered w-full bg-base-100"
                ),
                cls="form-control"
            ),
            Div(
                Label("Error Type", cls="label"),
                Select(
                    Option("All", value=""),
                    # more types from models (dynamic in future)
                    name="error_type", cls="select select-bordered w-full bg-base-100"
                ),
                cls="form-control"
            ),
            Div(
                Label("Severity", cls="label"),
                Select(
                    Option("All", value=""),
                    Option("High", value="high"),
                    Option("Medium", value="medium"),
                    Option("Low", value="low"),
                    name="severity", cls="select select-bordered w-full bg-base-100"
                ),
                cls="form-control"
            ),
            Div(
                Label("Search", cls="label"),
                Input(name="q", placeholder="Search...", cls="input input-bordered w-full bg-base-100"),
                cls="form-control"
            ),
            cls="space-y-4"
        ),
        data_on_change="@post('/dashboard/filter', {contentType: 'form'})",
        id="filters",
        cls="card bg-base-200 shadow p-4 w-full lg:w-80"
    )


def status_badge(status: str):
    color = {"Pending": "badge-warning", "Resolved": "badge-success", "Dismissed": "badge-neutral"}.get(status, "badge-ghost")
    return Span(status, cls=f"badge {color} badge-outline")


def error_row(e: ManagedError):
    return Tr(
        Td(e.error_id),
        Td(e.error_type.value.replace("_", " ").title()),
        Td(e.severity.value.title()),
        Td(e.explanation[:80] + "..." if getattr(e, "explanation", None) else ""),
        Td(status_badge(e.status.value.replace("_", " ").title())),
        Td(
            Div(
                Select(
                    Option("Pending", value=ErrorStatus.PENDING.value, selected=(e.status == ErrorStatus.PENDING)),
                    Option("Resolved", value=ErrorStatus.RESOLVED.value, selected=(e.status == ErrorStatus.RESOLVED)),
                    Option("Dismissed", value=ErrorStatus.DISMISSED.value, selected=(e.status == ErrorStatus.DISMISSED)),
                    name="status", cls="select select-sm select-bordered"
                ),
                Button(
                    "Update", cls="btn btn-sm btn-primary",
                    data_on_click=f"@post('/errors/{e.error_id}/status', {{contentType: 'form', selector: '#row-{e.error_id}'}})"
                ),
                cls="flex gap-2"
            ),
            id=f"row-{e.error_id}"
        )
    )


def error_table(errors: List[ManagedError]):
    return Div(
        Div("Errors", cls="text-xl font-semibold"),
        Div(
            Table(
                Thead(Tr(Th("ID"), Th("Type"), Th("Severity"), Th("Explanation"), Th("Status"), Th("Actions"))),
                Tbody(*(error_row(e) for e in errors)),
                cls="table table-zebra"
            ),
            cls="overflow-x-auto"
        ),
        id="error-table",
        cls="card bg-base-100 shadow p-4"
    )


def upload_form():
    return Form(
        Div(
            Input(type="file", name="file", accept=".json", required=True, cls="file-input file-input-bordered w-full bg-base-100"),
            Button(
                "Upload", cls="btn btn-primary",
                data_on_click="@post('/upload', {contentType: 'form', selector: '#upload-form'})"
            ),
            cls="flex gap-4 items-center"
        ),
        id="upload-form",
        cls="card bg-base-100 shadow p-4 w-full"
    )