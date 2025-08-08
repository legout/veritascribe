from fasthtml.common import *
from typing import AsyncIterator, Optional, Dict, Any
from starlette.responses import StreamingResponse
import json
import tempfile
import os
from core.error_manager import ErrorManager
from core.data_processor import DataProcessor
from core.models import FilterCriteria, ErrorStatus, ErrorType, Severity
from .stores import app_state, project_signals


# # Try to import datastar-py SSE helper; provide a minimal fallback if missing
# try:
from datastar_py import ServerSentEventGenerator as SSE  # type: ignore
# except Exception:  # pragma: no cover
#     class SSE:  # Fallback SSE generator
#         @staticmethod
#         def patch_elements(html: str) -> str:
#             # Minimal SSE format: the datastar client can interpret payloads as needed
#             return f"data: {json.dumps({'patch': {'elements': html}})}\n\n"

#         @staticmethod
#         def patch_signals(signals: Dict[str, Any]) -> str:
#             return f"data: {json.dumps({'patch': {'signals': signals}})}\n\n"


app, rt = fast_app()
error_manager = ErrorManager()

# Load initial data on startup
dp = DataProcessor()
initial_report = dp.load_and_convert_report("demo_thesis.pdf")
error_manager.import_analysis_report(initial_report)
app_state.selected_document = initial_report.document_path
app_state.errors = error_manager.get_errors(app_state.selected_document)


def sse_response(events: AsyncIterator[bytes]) -> StreamingResponse:
    # Generic SSE response helper for FastHTML (Starlette ASGI)
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(events, media_type="text/event-stream", headers=headers)


async def stream_patch(elements_html: Optional[str] = None, signals: Optional[Dict[str, Any]] = None) -> AsyncIterator[bytes]:
    if elements_html:
        yield SSE.patch_elements(elements_html).encode()
    if signals is not None:
        yield SSE.patch_signals(signals).encode()


@rt("/")
def get_home():
    # Initial shell; regions lazy-load via datastar actions on-load
    from .components import page_layout, filter_sidebar, stats_cards, error_table
    counts = {
        "total": len(app_state.errors),
        "pending": sum(getattr(e, "status", None) == ErrorStatus.PENDING for e in app_state.errors),
        "completed": sum(getattr(e, "status", None) == ErrorStatus.RESOLVED for e in app_state.errors),
    }
    return page_layout(
        "VeritaScribe Dashboard",
        filter_sidebar(),
        stats_cards(counts),
        error_table(app_state.errors),
    )


@rt("/dashboard/stats")
def get_stats():
    from .components import stats_cards
    counts = {
        "total": len(app_state.errors),
        "pending": sum(getattr(e, "status", None) == ErrorStatus.PENDING for e in app_state.errors),
        "completed": sum(getattr(e, "status", None) == ErrorStatus.RESOLVED for e in app_state.errors),
    }
    html = str(stats_cards(counts))  # FastTags stringify to HTML

    async def gen():
        async for chunk in stream_patch(elements_html=html, signals=project_signals()):
            yield chunk

    return sse_response(gen())


@rt("/dashboard/errors")
def get_errors():
    from .components import error_table
    html = str(error_table(app_state.errors))

    async def gen():
        async for chunk in stream_patch(elements_html=html):
            yield chunk

    return sse_response(gen())


@rt("/dashboard/import_form")
def get_import_form():
    from .components import upload_form
    html = str(upload_form())

    async def gen():
        async for chunk in stream_patch(elements_html=html):
            yield chunk

    return sse_response(gen())


@rt("/dashboard/filter")
def post_filter(status: str = "", error_type: str = "", severity: str = "", q: str = ""):
    # Build FilterCriteria and query errors via ErrorManager
    fc = FilterCriteria()

    # Normalize "all" sentinel values and map to enums if provided
    if status and status.lower() not in ("all", "all statuses"):
        try:
            fc.status = [ErrorStatus(status)]
        except Exception:
            pass

    if error_type and error_type.lower() not in ("all", "all types"):
        try:
            fc.error_type = [ErrorType(error_type)]
        except Exception:
            pass

    if severity and severity.lower() not in ("all", "all severities"):
        try:
            fc.severity = [Severity(severity)]
        except Exception:
            pass

    if q and q.strip():
        fc.search_text = q.strip()

    app_state.filter_criteria = fc
    app_state.errors = error_manager.get_errors(app_state.selected_document, fc)

    from .components import error_table
    html = str(error_table(app_state.errors))

    async def gen():
        async for chunk in stream_patch(elements_html=html, signals=project_signals()):
            yield chunk

    return sse_response(gen())


@rt("/errors/{error_id}/status")
def post_error_status(error_id: str, status: str):
    # Update in DB
    try:
        new_status = ErrorStatus(status)
    except Exception:
        new_status = None

    if new_status is not None:
        error_manager.update_error(error_id, {"status": new_status})
        # Update in-memory state to remain consistent
        for e in app_state.errors:
            if getattr(e, "error_id", None) == error_id:
                e.status = new_status
                break

    from .components import error_row
    target = next((e for e in app_state.errors if getattr(e, "error_id", None) == error_id), None)
    row_html = str(error_row(target)) if target else ""

    async def gen():
        async for chunk in stream_patch(elements_html=row_html, signals=project_signals()):
            yield chunk

    return sse_response(gen())


@rt("/errors/bulk")
def post_bulk(action: str):
    # Apply action to selected errors from signals (if needed, read_signals could be parsed from request)
    updates: Dict[str, Any] = {}

    if action == "mark_resolved":
        updates["status"] = ErrorStatus.RESOLVED
    elif action == "mark_dismissed":
        updates["status"] = ErrorStatus.DISMISSED
    elif action == "assign_to_me":
        updates["assigned_to"] = "web_user"
        updates["status"] = ErrorStatus.IN_PROGRESS

    if updates and app_state.selected_errors:
        error_manager.bulk_update_errors(app_state.selected_errors, updates)

    app_state.errors = error_manager.get_errors(app_state.selected_document, app_state.filter_criteria)

    from .components import error_table
    html = str(error_table(app_state.errors))

    async def gen():
        async for chunk in stream_patch(elements_html=html, signals=project_signals()):
            yield chunk

    return sse_response(gen())


@rt("/upload")
async def post_upload(file: UploadFile):
    dp = DataProcessor()
    # Persist uploaded file temporarily for DataProcessor
    data = await file.read()
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False) as tf:
        tf.write(data)
        temp_path = tf.name

    try:
        report = dp.load_and_convert_report(temp_path)
        # Persist and reload via ErrorManager
        error_manager.import_analysis_report(report)
        app_state.selected_document = report.document_path
        app_state.errors = error_manager.get_errors(app_state.selected_document, app_state.filter_criteria)

        from .components import stats_cards, error_table
        msg = Div("Upload successful", cls="alert alert-success")
        counts = {
            "total": len(app_state.errors),
            "pending": sum(getattr(e, "status", None) == ErrorStatus.PENDING for e in app_state.errors),
            "completed": sum(getattr(e, "status", None) == ErrorStatus.RESOLVED for e in app_state.errors),
        }
        html = str(Div(msg, stats_cards(counts), error_table(app_state.errors)))
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

    async def gen():
        async for chunk in stream_patch(elements_html=html, signals=project_signals()):
            yield chunk

    return sse_response(gen())


if __name__ == "__main__":
    serve()