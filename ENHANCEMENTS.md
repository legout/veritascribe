# VeritaScribe Enhancement Plan

## 1. Introduction

This document outlines a strategic plan for enhancing the VeritaScribe application. The project is currently in an excellent state, with a robust architecture that closely follows the initial project plan. Recent updates have added significant new capabilities, including **multi-provider LLM support** (OpenAI, OpenRouter, Anthropic) and **robust JSON parsing** to handle malformed API responses.

The following enhancements are designed to build on this strong foundation to:
-   **Add High-Impact Features:** Introduce new capabilities that will significantly improve the value and user experience.
-   **Improve Robustness & Quality:** Address potential shortcomings and strengthen the codebase to ensure reliability and maintainability.
-   **Align with Advanced Goals:** Implement the advanced features envisioned in the original project plan.

---

## 2. High-Impact Feature Enhancements

### 2.1. Annotated PDF Output

-   **Goal:** Generate a copy of the analyzed PDF with errors highlighted and explained directly on the page, providing highly contextual and actionable feedback.
-   **Current Status:** Not implemented. Reports are currently generated as separate text, JSON, and image files.
-   **Relevance:** Still a high-impact, user-facing feature that would greatly improve the usability of the tool.

#### Implementation Plan

1.  **New Function in `report_generator.py`:**
    *   Create a new method: `generate_annotated_pdf(self, report: ThesisAnalysisReport, original_pdf_path: str, output_path: str)`.

2.  **Implementation Logic:**
    *   Open the `original_pdf_path` using `fitz.open()`.
    *   Iterate through each `AnalysisResult` in `report.analysis_results`.
    *   For each `BaseError` within an `AnalysisResult`:
        *   Use `error.location.page_number` to get the correct `fitz.Page` object.
        *   Use `error.location.bounding_box` to define a `fitz.Rect`.
        *   **Highlight Error:** Add a highlight annotation using `page.add_highlight_annot(rect)`. The color can be conditional on `error.severity` (e.g., red for high, yellow for medium).
        *   **Add Comment:** Add a "Sticky Note" or "Text" annotation next to the highlight using `page.add_text_annot()` or `page.add_stamp_annot()`. The annotation's text content should include the `error_type`, `explanation`, and `suggested_correction`.
    *   Save the modified document to the `output_path` using `doc.save()`.

3.  **CLI Integration (`main.py`):**
    *   Add a new option to the `analyze` command: `--annotate-pdf: bool = typer.Option(False, "--annotate", help="Generate an annotated PDF with highlighted errors.")`.
    *   If this flag is set, call the new `generate_annotated_pdf` function.

### 2.2. DSPy Prompt Optimization (`teleprompt`)

-   **Goal:** Leverage `dspy.teleprompt` to automatically generate few-shot examples and optimize prompts, improving the accuracy and reliability of the LLM analysis.
-   **Current Status:** Not implemented. The system currently uses static prompts within `dspy.ChainOfThought`.
-   **Relevance:** Still highly relevant. This is a key DSPy feature that would improve the core analysis quality.

#### Implementation Plan

1.  **Create a "Gold Standard" Dataset:**
    *   Create a new file: `src/veritascribe/training_data.py`.
    *   Define a small list (5-10 examples) of `dspy.Example` objects for each analysis module (`LinguisticAnalyzer`, `ContentValidator`).
    *   Each example should contain a representative `text_chunk` and the ideal, validated JSON output for the `grammar_errors` or `content_errors` field.

2.  **Implement a Compilation Script:**
    *   Create a new script, e.g., `scripts/compile_modules.py`.
    *   This script will:
        *   Load the training data.
        *   Initialize the DSPy modules.
        *   Define a simple validation metric, e.g., `lambda gold, pred, trace: dspy.evaluate.metrics.answer_exact_match(gold, pred)`.
        *   Use `dspy.teleprompt.BootstrapFewShot(metric=...)` to create a teleprompter.
        *   Compile each analysis module using `teleprompter.compile(module, trainset=...)`.
        *   Save the compiled modules to disk, e.g., `compiled_linguistic_analyzer.json`.

3.  **Update Module Loading:**
    *   In `llm_modules.py`, modify the `AnalysisOrchestrator` to load the compiled modules using `module.load()` if they exist. This avoids re-compiling on every run.

### 2.3. Cost and Token Usage Monitoring

-   **Goal:** Track and report the token usage and estimated cost associated with each analysis run.
-   **Current Status:** Not implemented.
-   **Relevance:** Still highly relevant. The addition of multiple LLM providers makes this feature even more important for managing costs.

#### Implementation Plan

1.  **Update `ThesisAnalysisReport` Data Model:**
    *   In `data_models.py`, add the following fields to `ThesisAnalysisReport`:
        *   `token_usage: Optional[Dict[str, int]] = None`
        *   `estimated_cost: Optional[float] = None`

2.  **Add Pricing Information to `config.py`:**
    *   Extend the `PROVIDER_MODELS` dictionary to include pricing information (e.g., `cost_per_prompt_token`, `cost_per_completion_token`) for each model.

3.  **Implement Calculation Logic in `pipeline.py`:**
    *   After an analysis run is complete, inspect the `dspy.settings.lm.history` object.
    *   Create a new private method in `ThesisAnalysisPipeline`, e.g., `_calculate_llm_usage(self) -> Tuple[Dict, float]`.
    *   This method will iterate through `dspy.settings.lm.history`, sum the `prompt_tokens` and `completion_tokens`, and calculate the total cost using the pricing information from the `config`.
    *   Clear the history (`dspy.settings.lm.history.clear()`) after calculation.

4.  **Integrate into Pipeline and Reports:**
    *   Call `_calculate_llm_usage` at the end of the `analyze_thesis` method and populate the new fields in the `ThesisAnalysisReport`.
    *   Update `report_generator.py` and the CLI summary in `main.py` to display the token usage and estimated cost.

---

## 3. Robustness and Quality Improvements

### 3.1. Implement LLM Request Retries

-   **Goal:** Make LLM API calls more resilient to transient network errors or rate limiting.
-   **Current Status:** `max_retries` and `retry_delay` are defined in `config.py` but are not used.
-   **Relevance:** Still highly relevant. The new `safe_json_parse` function handles malformed responses, but this does not address API-level failures.

#### Implementation Plan

1.  **Add Dependency:**
    *   Run `uv add backoff`.

2.  **Implement Retry Logic in `llm_modules.py`:**
    *   Modify the `forward` method in each analysis module (`LinguisticAnalyzer`, `ContentValidator`, `CitationChecker`).
    *   Apply a `@backoff.on_exception(...)` decorator to the `self.analyzer(...)` call.
    *   Configure the decorator to use `self.settings.max_retries` and `self.settings.retry_delay`.
    *   Catch specific, retry-able exceptions from the underlying LLM libraries (e.g., `openai.RateLimitError`, `openai.APIConnectionError`, `anthropic.APIConnectionError`).

### 3.2. Establish a Pytest Test Suite

-   **Goal:** Create a formal test suite to ensure code quality, prevent regressions, and enable confident refactoring.
-   **Current Status:** No formal test suite exists. The `veritascribe test` command is a simple smoke test.
-   **Relevance:** Still highly relevant and critical for long-term maintainability.

#### Implementation Plan

1.  **Add Dependency and Configure:**
    *   Run `uv add pytest`.
    *   Create a `tests/` directory in the project root.
    *   In `pyproject.toml`, add `[tool.pytest.ini_options]` and set `testpaths = ["tests"]`.

2.  **Write Unit Tests:**
    *   **`tests/test_pdf_processor.py`:** Test helper functions like `_clean_extracted_text` and `_is_header_footer_or_page_number`.
    *   **`tests/test_data_models.py`:** Test Pydantic model validation and calculated properties.
    *   **`tests/test_report_generator.py`:** Test the `_generate_recommendation` logic.
    *   **`tests/test_pipeline.py`:** Write an integration test that runs the `quick_analyze` pipeline on a test PDF.

3.  **Update `CLAUDE.md`:**
    *   Change the testing command from `veritascribe test` to `uv run pytest`.

### 3.3. Improve Bibliography Extraction

-   **Goal:** Make the bibliography extraction process more robust.
-   **Current Status:** The current implementation uses a simple regex search for section headers.
-   **Relevance:** Still relevant. A more robust implementation would improve the accuracy of citation analysis.

#### Implementation Plan

1.  **Enhance `extract_bibliography_section` in `pdf_processor.py`:**
    *   Modify the function to use `page.get_text("dict")` to get font and positional information.
    *   **Identify Start:** Find the "References" or "Bibliography" header.
    *   **Collect Content:** Iterate through text blocks on that page and subsequent pages.
    *   **Identify End:** The bibliography section likely ends when a new major header (e.g., "Appendix") with a larger font size is found.