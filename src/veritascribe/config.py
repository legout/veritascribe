"""Configuration management for VeritaScribe using Pydantic Settings."""

import os
from typing import Optional, Dict, Any, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import dspy


class VeritaScribeSettings(BaseSettings):
    """Main configuration settings for VeritaScribe."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Provider Configuration
    llm_provider: Literal["openai", "openrouter", "anthropic", "custom"] = Field(
        default="openai", 
        description="LLM provider to use (openai, openrouter, anthropic, custom)"
    )
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_base_url: Optional[str] = Field(None, description="Custom OpenAI base URL for compatible APIs")
    
    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = Field(None, description="OpenRouter API key")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter API base URL")
    
    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key for Claude models")
    
    # Model Configuration
    default_model: str = Field(default="gpt-4", description="Default LLM model to use")
    max_tokens: int = Field(default=2000, description="Maximum tokens per LLM request")
    temperature: float = Field(default=0.1, description="LLM temperature for consistency")
    
    # Analysis Configuration
    grammar_analysis_enabled: bool = Field(default=True, description="Enable grammar analysis")
    content_analysis_enabled: bool = Field(default=True, description="Enable content plausibility analysis")
    citation_analysis_enabled: bool = Field(default=True, description="Enable citation analysis")
    
    # Error Severity Thresholds
    high_severity_threshold: float = Field(default=0.8, description="Threshold for high severity errors")
    medium_severity_threshold: float = Field(default=0.5, description="Threshold for medium severity errors")
    
    # Processing Configuration
    max_text_block_size: int = Field(default=2000, description="Maximum characters per text block for analysis")
    min_text_block_size: int = Field(default=50, description="Minimum characters for text block analysis")
    parallel_processing: bool = Field(default=True, description="Enable parallel LLM processing")
    max_concurrent_requests: int = Field(default=5, description="Maximum concurrent LLM requests")
    
    # Output Configuration
    output_directory: str = Field(default="./analysis_output", description="Default output directory")
    generate_visualizations: bool = Field(default=True, description="Generate error visualization charts")
    save_detailed_reports: bool = Field(default=True, description="Save detailed text reports")
    
    # Retry Configuration
    max_retries: int = Field(default=3, description="Maximum retries for failed LLM requests")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    @field_validator('llm_provider')
    @classmethod
    def validate_provider(cls, v):
        """Validate LLM provider selection."""
        valid_providers = ["openai", "openrouter", "anthropic", "custom"]
        if v not in valid_providers:
            raise ValueError(f"Invalid LLM provider '{v}'. Must be one of: {valid_providers}")
        return v
    
    def get_api_key(self) -> str:
        """Get the appropriate API key based on provider."""
        if self.llm_provider == "openai" or self.llm_provider == "custom":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required for provider 'openai' or 'custom'")
            return self.openai_api_key
        elif self.llm_provider == "openrouter":
            if not self.openrouter_api_key:
                raise ValueError("OpenRouter API key is required for provider 'openrouter'")
            return self.openrouter_api_key
        elif self.llm_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for provider 'anthropic'")
            return self.anthropic_api_key
        else:
            raise ValueError(f"Unknown provider: {self.llm_provider}")
    
    def get_base_url(self) -> Optional[str]:
        """Get the appropriate base URL based on provider."""
        if self.llm_provider == "openai":
            return self.openai_base_url  # None for standard OpenAI
        elif self.llm_provider == "openrouter":
            return self.openrouter_base_url
        elif self.llm_provider == "custom":
            return self.openai_base_url  # Required for custom endpoints
        elif self.llm_provider == "anthropic":
            return None  # Anthropic uses its own client
        else:
            return None
    
    def get_provider_display_name(self) -> str:
        """Get human-readable provider name."""
        provider_names = {
            "openai": "OpenAI",
            "openrouter": "OpenRouter",
            "anthropic": "Anthropic Claude",
            "custom": "Custom OpenAI-Compatible"
        }
        return provider_names.get(self.llm_provider, self.llm_provider.title())
    
    def format_model_name(self, model_name: Optional[str] = None) -> str:
        """Format model name with provider-specific prefix if needed."""
        model = model_name or self.default_model
        provider = self.llm_provider
        
        if provider == "openrouter":
            # OpenRouter requires 'openrouter/' prefix for LiteLLM
            if not model.startswith("openrouter/"):
                return f"openrouter/{model}"
        elif provider == "anthropic":
            # Anthropic models may need 'anthropic/' prefix depending on DSPy version
            if not model.startswith("anthropic/") and not model.startswith("claude-"):
                return f"anthropic/{model}"
        
        return model
    
    def get_provider_specific_max_tokens(self) -> int:
        """Get provider-specific max token limits optimized for each provider."""
        provider_token_limits = {
            "openai": min(self.max_tokens, 4000),  # OpenAI models generally handle larger contexts well
            "openrouter": min(self.max_tokens, 3000),  # More conservative for free/cheaper models
            "anthropic": min(self.max_tokens, 4000),  # Claude handles large contexts well
            "custom": min(self.max_tokens, 2000)  # Conservative for unknown endpoints
        }
        
        # For specific known problematic models, use even lower limits
        formatted_model = self.format_model_name()
        if "free" in formatted_model.lower() or "air" in formatted_model.lower():
            # Free models often have quality issues with large contexts
            return min(provider_token_limits.get(self.llm_provider, self.max_tokens), 2000)
        
        return provider_token_limits.get(self.llm_provider, self.max_tokens)


# Provider-specific model configurations
PROVIDER_MODELS = {
    "openai": {
        "default": "gpt-4",
        "models": [
            "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ],
        "recommended": {
            "quality": "gpt-4",
            "speed": "gpt-4o-mini", 
            "cost": "gpt-3.5-turbo"
        },
        "pricing": {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004}
        }
    },
    "openrouter": {
        "default": "anthropic/claude-3.5-sonnet",
        "models": [
            # Anthropic models
            "anthropic/claude-3.5-sonnet", "anthropic/claude-3-haiku", "anthropic/claude-3-opus",
            # OpenAI models  
            "openai/gpt-4", "openai/gpt-4-turbo", "openai/gpt-3.5-turbo",
            # Open source models
            "meta-llama/llama-3.1-70b-instruct", "meta-llama/llama-3.1-8b-instruct",
            "mistralai/mistral-7b-instruct", "google/gemini-pro",
            # Free models
            "z-ai/glm-4.5-air:free", "microsoft/phi-3-mini-128k-instruct:free"
        ],
        "recommended": {
            "quality": "anthropic/claude-3-opus",
            "speed": "anthropic/claude-3-haiku", 
            "cost": "z-ai/glm-4.5-air:free"
        },
        "pricing": {
            # Anthropic models via OpenRouter (per 1K tokens)
            "anthropic/claude-3.5-sonnet": {"prompt": 0.003, "completion": 0.015},
            "anthropic/claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
            "anthropic/claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            # OpenAI models via OpenRouter
            "openai/gpt-4": {"prompt": 0.03, "completion": 0.06},
            "openai/gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "openai/gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            # Open source models (approximate)
            "meta-llama/llama-3.1-70b-instruct": {"prompt": 0.0009, "completion": 0.0009},
            "meta-llama/llama-3.1-8b-instruct": {"prompt": 0.0002, "completion": 0.0002},
            "mistralai/mistral-7b-instruct": {"prompt": 0.0002, "completion": 0.0002},
            "google/gemini-pro": {"prompt": 0.0005, "completion": 0.0015},
            # Free models
            "z-ai/glm-4.5-air:free": {"prompt": 0.0, "completion": 0.0},
            "microsoft/phi-3-mini-128k-instruct:free": {"prompt": 0.0, "completion": 0.0}
        }
    },
    "anthropic": {
        "default": "claude-3-5-sonnet-20241022",
        "models": [
            "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"
        ],
        "recommended": {
            "quality": "claude-3-opus-20240229",
            "speed": "claude-3-5-haiku-20241022",
            "cost": "claude-3-haiku-20240307"
        },
        "pricing": {
            # Anthropic direct pricing (per 1K tokens)
            "claude-3-5-sonnet-20241022": {"prompt": 0.003, "completion": 0.015},
            "claude-3-5-haiku-20241022": {"prompt": 0.00025, "completion": 0.00125},
            "claude-3-opus-20240229": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet-20240229": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku-20240307": {"prompt": 0.00025, "completion": 0.00125}
        }
    },
    "custom": {
        "default": "llama3.1:8b",
        "models": [],  # User-defined
        "recommended": {
            "quality": "User-configured",
            "speed": "User-configured",
            "cost": "User-configured"
        },
        "pricing": {
            # Default pricing for custom models (often free local models)
            "default": {"prompt": 0.0, "completion": 0.0}
        }
    }
}


class DSPyConfig:
    """Configuration manager for DSPy LLM backend with multi-provider support."""
    
    def __init__(self, settings: VeritaScribeSettings):
        self.settings = settings
        self._lm: Optional[dspy.LM] = None
    
    def initialize_llm(self) -> dspy.LM:
        """Initialize and configure DSPy LLM backend based on provider."""
        if self._lm is None:
            try:
                # Get API key and validate provider
                api_key = self.settings.get_api_key()
                base_url = self.settings.get_base_url()
                provider = self.settings.llm_provider
                
                # Initialize based on provider
                if provider == "anthropic":
                    self._lm = self._initialize_anthropic(api_key)
                else:
                    # OpenAI, OpenRouter, or custom OpenAI-compatible
                    self._lm = self._initialize_openai_compatible(api_key, base_url, provider)
                
                # Configure DSPy to use this LLM
                dspy.configure(lm=self._lm)
                
                provider_name = self.settings.get_provider_display_name()
                formatted_model = self.settings.format_model_name()
                print(f"Initialized DSPy with {provider_name} - Model: {formatted_model}")
                return self._lm
                
            except Exception as e:
                provider_name = self.settings.get_provider_display_name()
                raise RuntimeError(f"Failed to initialize {provider_name} LLM: {e}")
        
        return self._lm
    
    def _initialize_anthropic(self, api_key: str) -> dspy.LM:
        """Initialize Anthropic Claude model."""
        formatted_model = self.settings.format_model_name()
        max_tokens = self.settings.get_provider_specific_max_tokens()
        return dspy.LM(
            model=formatted_model,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=self.settings.temperature
        )
    
    def _initialize_openai_compatible(self, api_key: str, base_url: Optional[str], provider: str) -> dspy.LM:
        """Initialize OpenAI-compatible model (OpenAI, OpenRouter, or custom)."""
        # Format model name with provider-specific prefix if needed
        formatted_model = self.settings.format_model_name()
        
        # Prepare initialization parameters with provider-specific token limits
        max_tokens = self.settings.get_provider_specific_max_tokens()
        init_params = {
            "model": formatted_model,
            "api_key": api_key,
            "max_tokens": max_tokens,
            "temperature": self.settings.temperature
        }
        
        # Add base URL if specified
        if base_url:
            init_params["base_url"] = base_url
            
            # Validate base URL for custom providers
            if provider == "custom" and not base_url:
                raise ValueError("Custom provider requires OPENAI_BASE_URL to be set")
        
        return dspy.LM(**init_params)
    
    def get_llm(self) -> dspy.LM:
        """Get the configured LLM instance."""
        if self._lm is None:
            return self.initialize_llm()
        return self._lm
    
    def validate_model(self) -> bool:
        """Validate that the configured model is supported by the provider."""
        provider = self.settings.llm_provider
        model = self.settings.default_model
        
        if provider in PROVIDER_MODELS:
            provider_config = PROVIDER_MODELS[provider]
            if provider_config["models"] and model not in provider_config["models"]:
                supported_models = ", ".join(provider_config["models"][:5])  # Show first 5
                more_count = len(provider_config["models"]) - 5
                if more_count > 0:
                    supported_models += f" (and {more_count} more)"
                
                print(f"Warning: Model '{model}' not in known {provider} models.")
                print(f"Supported models include: {supported_models}")
                print(f"Recommended models: {provider_config['recommended']}")
                return False
        
        return True
    
    def get_recommended_models(self) -> Dict[str, str]:
        """Get recommended models for the current provider."""
        provider = self.settings.llm_provider
        if provider in PROVIDER_MODELS:
            return PROVIDER_MODELS[provider]["recommended"]
        return {}
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get comprehensive provider information."""
        provider = self.settings.llm_provider
        provider_config = PROVIDER_MODELS.get(provider, {})
        
        return {
            "provider": provider,
            "provider_name": self.settings.get_provider_display_name(),
            "current_model": self.settings.default_model,
            "formatted_model": self.settings.format_model_name(),
            "default_model": provider_config.get("default", "Unknown"),
            "supported_models": provider_config.get("models", []),
            "recommended_models": provider_config.get("recommended", {}),
            "api_key_configured": bool(self._get_api_key_status()),
            "base_url": self.settings.get_base_url()
        }
    
    def _get_api_key_status(self) -> bool:
        """Check if the appropriate API key is configured."""
        try:
            self.settings.get_api_key()
            return True
        except ValueError:
            return False


def load_settings() -> VeritaScribeSettings:
    """Load configuration settings from environment and .env file."""
    try:
        settings = VeritaScribeSettings()
        return settings
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")


def setup_output_directory(output_dir: str) -> str:
    """Create output directory if it doesn't exist."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


# Global configuration instance
_settings: Optional[VeritaScribeSettings] = None
_dspy_config: Optional[DSPyConfig] = None


def get_settings() -> VeritaScribeSettings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def get_dspy_config() -> DSPyConfig:
    """Get global DSPy configuration instance."""
    global _dspy_config
    if _dspy_config is None:
        settings = get_settings()
        _dspy_config = DSPyConfig(settings)
    return _dspy_config


def initialize_system() -> tuple[VeritaScribeSettings, DSPyConfig]:
    """Initialize the complete VeritaScribe system configuration."""
    settings = get_settings()
    dspy_config = get_dspy_config()
    
    # Initialize LLM
    dspy_config.initialize_llm()
    
    # Setup output directory
    setup_output_directory(settings.output_directory)
    
    print("VeritaScribe system initialized successfully")
    return settings, dspy_config