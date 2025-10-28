from src.services.perplexity_service import PerplexityService
import os
from src.services.serp_api_service import SerpAPIService
from google import genai
from dotenv import load_dotenv

load_dotenv()


def get_perplexity_service():
    """
    Get initialized Perplexity service instance.
    
    Returns:
        PerplexityService: Configured Perplexity service
        
    Raises:
        ValueError: If PERPLEXITY_API_KEY is not set
    """
    # from src.services.perplexity_service import PerplexityService
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    return PerplexityService(api_key)


def get_serp_api_service():
    """
    Get initialized SERP API service instance.
    
    Returns:
        SerpAPIService: Configured SERP API service
        
    Raises:
        ValueError: If SERP_API_KEY is not set
    """
    # from src.services.serp_api_service import SerpAPIService
    
    api_key = os.getenv('SERP_API_KEY')
    if not api_key:
        raise ValueError("SERP_API_KEY environment variable is required")
    return SerpAPIService(api_key)


def get_gemini_client():
    """
    Get initialized Google Gemini client.
    
    Returns:
        genai.Client: Configured Gemini client
        
    Raises:
        ValueError: If GEMINI_API_KEY is not set
        ImportError: If google-genai package not available
    """    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    client = genai.Client(api_key=api_key)
    return client


