"""
Azure Functions Configuration Module
Handles environment variables, Key Vault integration, and Azure-specific settings.
"""

import os
import logging
from typing import Optional
from azure.identity import DefaultAzureCredential, EnvironmentCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)

class AzureConfig:
    """Azure configuration manager for Functions deployment."""
    
    def __init__(self):
        self.is_azure_environment = self._detect_azure_environment()
        self.key_vault_url = os.getenv("KEY_VAULT_URL")
        self.credential = None
        self.secret_client = None
        
        if self.is_azure_environment and self.key_vault_url:
            self._initialize_key_vault()
    
    def _detect_azure_environment(self) -> bool:
        """Detect if running in Azure Functions environment."""
        azure_indicators = [
            "WEBSITE_SITE_NAME",
            "FUNCTIONS_WORKER_RUNTIME", 
            "AZURE_CLIENT_ID"
        ]
        return any(os.getenv(indicator) for indicator in azure_indicators)
    
    def _initialize_key_vault(self):
        """Initialize Azure Key Vault client."""
        try:
            # Try different credential types
            if os.getenv("AZURE_CLIENT_ID"):
                # Use service principal authentication
                self.credential = EnvironmentCredential()
            else:
                # Use managed identity or default credential
                self.credential = DefaultAzureCredential()
            
            self.secret_client = SecretClient(
                vault_url=self.key_vault_url, 
                credential=self.credential
            )
            logger.info("Key Vault client initialized successfully")
            
        except Exception as e:
            logger.warning(f"Key Vault initialization failed: {e}. Using environment variables.")
            self.secret_client = None
    
    def get_secret(self, secret_name: str, fallback_env_var: str = None) -> Optional[str]:
        """
        Get secret from Key Vault or environment variable.
        
        Args:
            secret_name: Name of the secret in Key Vault
            fallback_env_var: Environment variable name as fallback
            
        Returns:
            Secret value or None if not found
        """
        # Try Key Vault first
        if self.secret_client:
            try:
                secret = self.secret_client.get_secret(secret_name)
                logger.info(f"Retrieved secret '{secret_name}' from Key Vault")
                return secret.value
            except Exception as e:
                logger.warning(f"Failed to get secret '{secret_name}' from Key Vault: {e}")
        
        # Fallback to environment variable
        env_var_name = fallback_env_var or secret_name.upper().replace("-", "_")
        value = os.getenv(env_var_name)
        
        if value:
            logger.info(f"Retrieved secret '{secret_name}' from environment variable '{env_var_name}'")
            return value
        
        logger.error(f"Secret '{secret_name}' not found in Key Vault or environment variables")
        return None
    
    def setup_api_keys(self):
        """Setup API keys from Key Vault or environment variables."""
        api_keys = {
            "PERPLEXITY_API_KEY": self.get_secret("perplexity-api-key", "PERPLEXITY_API_KEY"),
            "SERP_API_KEY": self.get_secret("serp-api-key", "SERP_API_KEY"), 
            "GEMINI_API_KEY": self.get_secret("gemini-api-key", "GEMINI_API_KEY")
        }
        
        # Set environment variables for the application
        for key, value in api_keys.items():
            if value:
                os.environ[key] = value
                logger.info(f"API key '{key}' configured successfully")
            else:
                logger.error(f"API key '{key}' not found - application may not work correctly")
        
        return api_keys

# Global configuration instance
azure_config = AzureConfig()

def initialize_azure_environment():
    """Initialize Azure environment on startup."""
    logger.info("Initializing Azure Functions environment...")
    logger.info(f"Azure environment detected: {azure_config.is_azure_environment}")
    logger.info(f"Key Vault URL: {azure_config.key_vault_url}")
    
    # Setup API keys
    api_keys = azure_config.setup_api_keys()
    
    # Log configuration status (without exposing actual keys)
    configured_keys = [key for key, value in api_keys.items() if value]
    missing_keys = [key for key, value in api_keys.items() if not value]
    
    logger.info(f"Configured API keys: {configured_keys}")
    if missing_keys:
        logger.warning(f"Missing API keys: {missing_keys}")
    
    return len(configured_keys) > 0

def get_environment_info():
    """Get environment information for debugging."""
    return {
        "is_azure": azure_config.is_azure_environment,
        "key_vault_available": azure_config.secret_client is not None,
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "function_app_name": os.getenv("WEBSITE_SITE_NAME", "local"),
        "python_version": os.getenv("PYTHON_VERSION", "unknown")
    }