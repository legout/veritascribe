# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeritaScribe is an AI-powered bachelor thesis review tool built to automatically analyze PDF documents for quality issues. The system uses DSPy for LLM orchestration, Pydantic for structured data modeling, and PyMuPDF for PDF processing.

## Development Commands

**Package Management:**
- Install dependencies: `uv sync`
- Add new dependency: `uv add <package>`
- Run Python scripts: `uv run python <script>`

**Testing:**
- No test framework currently configured
- Test entry point: `uv run python -c "from veritascribe import hello; print(hello())"`

## Architecture

The project follows a modular pipeline architecture as outlined in ProjectPlan.md:

**Core Components (planned):**
- `config.py` - Central configuration using pydantic-settings
- `data_models.py` - Pydantic models for structured data (BaseError, TextBlock, AnalysisResult, ThesisAnalysisReport)
- `pdf_processor.py` - PDF text extraction with PyMuPDF, preserving layout context
- `llm_modules.py` - DSPy signatures and modules for analysis tasks
- `pipeline.py` - Main orchestration workflow
- `report_generator.py` - Report generation and visualization
- `main.py` - CLI entry point using Typer

**Data Flow:**
1. PDF → TextBlocks (with bounding box coordinates)
2. TextBlocks → LLM analysis modules (grammar, content, citations)
3. Analysis results → Structured errors with location hints
4. Aggregation → Comprehensive thesis analysis report
5. Report generation → Text reports and visualizations

**Key Dependencies:**
- `dspy>=2.6.27` - LLM orchestration and structured outputs
- `pydantic>=2.11.7` - Data validation and settings management
- `pymupdf>=1.26.3` - PDF processing with layout preservation
- `typer>=0.16.0` - CLI framework
- `matplotlib>=3.10.5` - Visualization
- `openai>=1.98.0` - LLM API access

## Development Notes

- Project uses Python 3.13+ requirement
- Build system: Hatchling
- Package structure: `src/veritascribe/` layout
- No existing test suite - implement pytest when adding tests
- Configuration should use environment variables for API keys
- Focus on defensive security - this is an analysis tool, not for malicious use