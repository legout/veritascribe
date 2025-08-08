# VeritaScribe Datastar Dashboard

This directory contains the `datastar`-powered rewrite of the VeritaScribe error management dashboard.

## Overview

This application provides a real-time, interactive interface for analyzing and managing VeritaScribe error reports. It is built with modern, Python-centric tools to ensure a clean, maintainable, and highly reactive user experience without the need for custom JavaScript.

## Technology Stack

-   **Backend Framework:** [`fasthtml`](https://github.com/AnswerDotAI/fasthtml)
-   **Reactivity:** [`datastar`](https://github.com/starfederation/datastar) and [`datastar-py`](https://github.com/starfederation/datastar-py)
-   **UI Components:** [`daisyUI`](https://daisyui.com/)
-   **Styling:** [`Tailwind CSS`](https://tailwindcss.com/) (via CDN)

## Project Structure

The application is organized into the following key files:

-   [`app.py`](dashboard/datastar_app/app.py): The main `fasthtml` application. It defines all URL routes, handles server-side logic, and streams updates to the client using Server-Sent Events (SSE).
-   [`stores.py`](dashboard/datastar_app/stores.py): Defines the server-side state management using a simple Python dataclass. The `app_state` object holds the application's state, which is projected to the UI via `datastar` signals.
-   [`components.py`](dashboard/datastar_app/components.py): Contains reusable functions that generate `daisyui`-styled HTML components. These functions are used by the routes in `app.py` to build the UI.
-   `static/`: This directory is reserved for any static assets, although this project currently relies on CDNs for all frontend dependencies.

## Running the Application

To run the dashboard, execute the main launch script from the root of the project:

```bash
python dashboard/launch_fasthtml.py
```

The application will be available at `http://localhost:8000`.