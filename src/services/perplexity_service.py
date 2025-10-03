import os
import requests
from typing import Dict, Any, Optional, Union, Iterator
import structlog

logger = structlog.get_logger('PerplexityService')

class PerplexityService:
    """
    Simplified service for interacting with Perplexity AI API using HTTP requests
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Perplexity service
        
        Args:
            api_key: Perplexity API key
        """
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.logger = logger
        
        if not self.api_key:
            self.logger.warning("Perplexity API key not found")
            raise ValueError("Perplexity API key is required")
        
        self.logger.info("Perplexity service initialized successfully")
    
    def search(
        self,
        query: str,
        system_prompt: str = "You are a helpful assistant that provides accurate, up-to-date information with citations when possible.",
        temperature: float = 0.1,
        model: str = "sonar-pro"
    ) -> Dict[str, Any]:
        """
        Perform search using Perplexity AI Search
        
        Args:
            query: Search query string
            system_prompt: System prompt to guide the model's behavior
            temperature: Temperature for response generation
            model: Model to use for search
            
        Returns:
            Dict containing search results
        """
        try:
            # For sonar models, combine system prompt with user query since they don't support system messages
            combined_content = f"{system_prompt}\n\nUser Query: {query}"
            
            payload = {
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": combined_content}
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Search successful for query: {query}")
                return result['choices'][0]['message']['content']
            else:
                self.logger.error(f"Search failed: {response.status_code} - {response.text}")
                return {"error": f"API request failed: {response.status_code}"}
                
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return {"error": str(e)}

    
    def check_connection(self) -> str:
        """
        Check if connection to Perplexity API is working
        
        Returns:
            str: "Connection successful" if connection is successful, "Connection failed" otherwise
        """
        try:
            # Test with a simple chat completion request
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                self.logger.info("Perplexity API connection successful")
                return "Connection is successful"
        except Exception as e:
            self.logger.error(f"Connection check failed: {str(e)}")
            return "Connection check failed"