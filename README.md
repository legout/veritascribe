# VeritaScribe

**AI-Powered Bachelor Thesis Review Tool**

VeritaScribe is an intelligent document analysis system that automatically reviews PDF thesis documents for quality issues including grammar errors, content plausibility problems, and citation format inconsistencies. Built with DSPy for LLM orchestration, Pydantic for structured data modeling, and PyMuPDF for PDF processing.

## ✨ Features

- **Multi-Provider LLM Support**: Works with OpenAI, OpenRouter, Anthropic Claude, and custom endpoints.
- **Multi-Language Analysis**: Supports English and German with language-specific grammar and context.
- **Comprehensive Analysis**: Grammar checking, content validation, and citation format verification.
- **DSPy Prompt Optimization**: Includes tools to fine-tune analysis prompts for higher accuracy.
- **Smart PDF Processing**: Extracts text while preserving layout context and location information.
- **Structured Reporting**: Generates detailed reports with error locations, severities, and suggestions.
- **Visual Analytics & Annotated PDFs**: Creates charts, visualizations, and annotated PDFs to highlight error patterns.
- **Flexible Configuration**: Customizable analysis parameters and provider selection.
- **CLI Interface**: Easy-to-use command-line interface with multiple analysis modes.
- **Cost Optimization**: Choose from 100+ models across providers for optimal cost/performance.

## 🚀 Quick Start

### Prerequisites

- Python 3.13 or higher
- API key for your chosen LLM provider:
  - **OpenAI**: [Get API key](https://platform.openai.com/api-keys)
  - **OpenRouter**: [Get API key](https://openrouter.ai/keys) (access to 100+ models)
  - **Anthropic**: [Get API key](https://console.anthropic.com/) (for Claude models)
  - **Custom**: Any OpenAI-compatible endpoint (local models, Azure, etc.)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd VeritaScribe
   ```

2. **Install dependencies using uv**:
   ```bash
   uv sync
   ```

3. **Configure your LLM provider**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and configure your preferred provider
   # See "LLM Providers" section below for examples
   ```

### Basic Usage

1. **Try the demo** (creates and analyzes a sample document):
   ```bash
   uv run python -m veritascribe demo
   ```

2. **Analyze your thesis**:
   ```bash
   uv run python -m veritascribe analyze your_thesis.pdf
   ```

3. **Generate an annotated PDF** with highlighted errors:
   ```bash
   uv run python -m veritascribe analyze your_thesis.pdf --annotate
   ```

##  CLI Commands

### `analyze` - Full Document Analysis
Performs comprehensive analysis of a thesis document.

```bash
uv run python -m veritascribe analyze [OPTIONS] PDF_PATH
```

**Options:**
- `--output, -o`: Output directory for reports (default: `./analysis_output`)
- `--citation-style, -c`: Expected citation style (default: `APA`)
- `--quick, -q`: Quick analysis mode (first 10 blocks only)
- `--no-viz`: Skip generating visualization charts
- `--annotate`: Generate an annotated PDF with highlighted errors
- `--verbose, -v`: Enable verbose logging

**Example:**
```bash
uv run python -m veritascribe analyze thesis.pdf --output ./results --annotate
```

### `quick` - Fast Analysis
Analyzes a subset of the document for quick feedback.

```bash
uv run python -m veritascribe quick [OPTIONS] PDF_PATH
```

**Options:**
- `--blocks, -b`: Number of text blocks to analyze (default: 5)

### `demo` - Create Sample Document
Creates and analyzes a demo thesis document.

```bash
uv run python -m veritascribe demo
```

### `config` - View Configuration
Displays current configuration settings.

```bash
uv run python -m veritascribe config
```

### `providers` - List Available Providers
Shows all supported LLM providers, models, and configuration examples.

```bash
uv run python -m veritascribe providers
```

### `optimize-prompts` - DSPy Prompt Optimization
Fine-tunes the analysis prompts using a few-shot learning dataset.

```bash
uv run python -m veritascribe optimize-prompts
```

### `test` - Run System Tests
Verifies that all components are working correctly.

```bash
uv run python -m veritascribe test
```

## 🌐 LLM Providers

VeritaScribe supports multiple LLM providers, giving you flexibility in model choice, cost optimization, and feature access.

### Available Providers

#### 1. OpenAI (Default)
- **Models**: GPT-4, GPT-4 Turbo, GPT-4o, GPT-3.5 Turbo
- **Best for**: High quality, reliability
- **Setup**:
  ```bash
  LLM_PROVIDER=openai
  OPENAI_API_KEY=sk-your-key-here
  DEFAULT_MODEL=gpt-4
  ```

#### 2. OpenRouter
- **Models**: 100+ models including Claude, Llama, Mistral, Gemini
- **Best for**: Cost optimization, model variety
- **Setup**:
  ```bash
  LLM_PROVIDER=openrouter
  OPENROUTER_API_KEY=sk-or-your-key-here
  DEFAULT_MODEL=anthropic/claude-3.5-sonnet
  ```

#### 3. Anthropic Claude
- **Models**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **Best for**: Advanced reasoning, long context
- **Setup**:
  ```bash
  LLM_PROVIDER=anthropic
  ANTHROPIC_API_KEY=sk-ant-your-key-here
  DEFAULT_MODEL=claude-3-5-sonnet-20241022
  ```

#### 4. Custom Endpoints
- **Models**: Any OpenAI-compatible API (Ollama, Azure, local models)
- **Best for**: Privacy, local deployment, custom setups
- **Examples**:
  ```bash
  # Local Ollama
  LLM_PROVIDER=custom
  OPENAI_API_KEY=ollama
  OPENAI_BASE_URL=http://localhost:11434/v1
  DEFAULT_MODEL=llama3.1:8b
  
  # Azure OpenAI
  LLM_PROVIDER=custom
  OPENAI_API_KEY=your-azure-key
  OPENAI_BASE_URL=https://your-resource.openai.azure.com/
  DEFAULT_MODEL=gpt-4
  ```

### Provider Comparison

| Provider | Cost | Speed | Quality | Models | Privacy |
|----------|------|-------|---------|--------|---------|
| OpenAI | High | Fast | Excellent | 6+ | Cloud |
| OpenRouter | Variable | Variable | Excellent | 100+ | Cloud |
| Anthropic | Medium | Fast | Excellent | 5+ | Cloud |
| Custom | Variable | Variable | Variable | Unlimited | Configurable |

## 🔧 Configuration

VeritaScribe uses environment variables for configuration. Copy `.env.example` to `.env` and customize.

## 📄 Understanding the Output

VeritaScribe generates several types of output:

### 1. Analysis Report (`*_report.md`)
A comprehensive Markdown report containing:
- Document summary and statistics
- Detailed error listings with locations
- Severity breakdown and recommendations

### 2. JSON Data Export (`*_data.json`)
Structured data in JSON format for programmatic access:
- All detected errors with metadata
- Text block information
- Analysis statistics

### 3. Visualizations (`*_visualizations/`)
Charts and graphs showing:
- Error distribution by type
- Error density per page
- Severity breakdown

### 4. Annotated PDF (`*_annotated.pdf`)
An optional PDF output with errors highlighted and comments added directly to the document.

### 5. Cost and Token Usage
The console output and Markdown report include details on token usage and the estimated cost of the analysis.

## Troubleshooting

Run into issues? Check the [Troubleshooting Guide](docs/troubleshooting.qmd) for help.

## 🏛️ Architecture

VeritaScribe follows a modular pipeline architecture. Learn more in the [Architecture Guide](docs/architecture.qmd).
