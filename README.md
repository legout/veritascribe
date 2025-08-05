# VeritaScribe

**AI-Powered Bachelor Thesis Review Tool**

VeritaScribe is an intelligent document analysis system that automatically reviews PDF thesis documents for quality issues including grammar errors, content plausibility problems, and citation format inconsistencies. Built with DSPy for LLM orchestration, Pydantic for structured data modeling, and PyMuPDF for PDF processing.

## ✨ Features

- **Multi-Provider LLM Support**: Works with OpenAI, OpenRouter, Anthropic Claude, and custom endpoints
- **Comprehensive Analysis**: Grammar checking, content validation, and citation format verification
- **Smart PDF Processing**: Extracts text while preserving layout context and location information
- **Structured Reporting**: Generates detailed reports with error locations, severities, and suggestions
- **Visual Analytics**: Creates charts and visualizations to highlight error patterns
- **Flexible Configuration**: Customizable analysis parameters and provider selection
- **CLI Interface**: Easy-to-use command-line interface with multiple analysis modes
- **Cost Optimization**: Choose from 100+ models across providers for optimal cost/performance

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

3. **Quick analysis** (analyzes first few text blocks):
   ```bash
   uv run python -m veritascribe quick your_thesis.pdf
   ```

## =� CLI Commands

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
- `--verbose, -v`: Enable verbose logging

**Example:**
```bash
uv run python -m veritascribe analyze thesis.pdf --output ./results --citation-style MLA
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

### Quick Setup Commands

```bash
# View available providers and models
uv run python -m veritascribe providers

# Check current configuration
uv run python -m veritascribe config

# Test your setup
uv run python -m veritascribe test
```

## 🔧 Configuration

VeritaScribe uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

### Required Configuration

Choose your LLM provider and set the appropriate API key:

```bash
# Provider selection (openai, openrouter, anthropic, custom)
LLM_PROVIDER=openai

# API Keys (set the one for your chosen provider)
OPENAI_API_KEY=your_openai_api_key_here           # For OpenAI or custom
OPENROUTER_API_KEY=sk-or-your_key_here           # For OpenRouter
ANTHROPIC_API_KEY=sk-ant-your_key_here           # For Anthropic Claude

# Custom endpoint (required for custom provider)
OPENAI_BASE_URL=https://your-endpoint.com/v1     # For custom endpoints
```

### Optional Configuration

```bash
# LLM Model Settings
DEFAULT_MODEL=gpt-4                    # LLM model to use
MAX_TOKENS=2000                        # Maximum tokens per request
TEMPERATURE=0.1                        # LLM temperature (0.0-1.0)

# Analysis Features
GRAMMAR_ANALYSIS_ENABLED=true          # Enable grammar checking
CONTENT_ANALYSIS_ENABLED=true         # Enable content validation
CITATION_ANALYSIS_ENABLED=true        # Enable citation format checking

# Error Severity Thresholds
HIGH_SEVERITY_THRESHOLD=0.8            # Threshold for high severity (0.0-1.0)
MEDIUM_SEVERITY_THRESHOLD=0.5          # Threshold for medium severity (0.0-1.0)

# Processing Settings
PARALLEL_PROCESSING=true               # Enable parallel LLM requests
MAX_CONCURRENT_REQUESTS=5              # Maximum simultaneous requests
MAX_TEXT_BLOCK_SIZE=2000              # Maximum characters per analysis block

# Output Settings
OUTPUT_DIRECTORY=./analysis_output     # Default output directory
GENERATE_VISUALIZATIONS=true           # Generate error charts
SAVE_DETAILED_REPORTS=true            # Save detailed text reports

# Retry Settings
MAX_RETRIES=3                         # Maximum retry attempts
RETRY_DELAY=1.0                       # Delay between retries (seconds)
```

## =� Understanding the Output

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

## <� Error Types

VeritaScribe detects three main categories of issues:

### Grammar Errors
- Spelling mistakes
- Grammatical inconsistencies
- Punctuation issues
- Style problems

### Content Plausibility
- Logical inconsistencies
- Factual accuracy concerns
- Argument structure issues
- Citation-content mismatches

### Citation Format
- Incorrect citation style
- Missing references
- Inconsistent formatting
- Bibliography issues

## =� Tips for Best Results

1. **Use High-Quality PDFs**: Text-based PDFs work better than scanned images
2. **Configure Citation Style**: Specify your expected citation style for accurate checking
3. **Review High-Priority Issues First**: Focus on high-severity errors for maximum impact
4. **Use Quick Mode for Drafts**: Get fast feedback during writing with `quick` command
5. **Monitor Token Usage**: Large documents may consume significant API tokens

## = Troubleshooting

### Common Issues

**"OpenAI API key is required"**
- Ensure your `.env` file contains a valid `OPENAI_API_KEY`
- Check that the `.env` file is in the project root directory

**"PDF file not found"**
- Verify the file path is correct
- Ensure the file has a `.pdf` extension

**"No text blocks extracted"**
- The PDF might be image-based (scanned). Try using OCR tools first
- Check if the PDF is password-protected or corrupted

**High API costs**
- Use `--quick` mode for large documents
- Adjust `MAX_TEXT_BLOCK_SIZE` to smaller values
- Set `PARALLEL_PROCESSING=false` to reduce concurrent requests

### Getting Help

1. **Run system tests**: `uv run python -m veritascribe test`
2. **Check configuration**: `uv run python -m veritascribe config`
3. **Enable verbose logging**: Add `--verbose` to commands
4. **Try the demo**: `uv run python -m veritascribe demo`

## <� Architecture

VeritaScribe follows a modular pipeline architecture:

```
PDF Input � Text Extraction � LLM Analysis � Error Aggregation � Report Generation
```

**Core Components:**
- `pdf_processor.py`: Text extraction with layout preservation
- `llm_modules.py`: DSPy-based analysis modules
- `data_models.py`: Pydantic models for structured data
- `pipeline.py`: Orchestration and workflow management
- `report_generator.py`: Output generation and visualization

## > Contributing

Contributions are welcome! This tool is designed for defensive security and academic quality assurance purposes only.

## =� License

[Add your license information here]

## = Related Projects

- [DSPy](https://github.com/stanfordnlp/dspy) - LLM programming framework
- [Pydantic](https://pydantic.dev/) - Data validation library
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing library