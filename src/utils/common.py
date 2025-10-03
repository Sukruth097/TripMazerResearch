"""
Common utilities and convenience functions for TripMazer
Includes easy-to-use perplexity search methods
"""

import asyncio
import sys
import os
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from services.perplexity_service import PerplexityService, PerplexitySearchResult
    from tools.search.perplexity_search_tool import PerplexitySearchTool
except ImportError:
    # Handle import errors gracefully
    PerplexityService = None
    PerplexitySearchTool = None

class TripMazerSearchUtils:
    """
    Convenient search utilities for TripMazer
    Provides easy-to-use methods for various search scenarios
    """
    
    def __init__(self):
        """Initialize search utilities"""
        if PerplexityService:
            self.perplexity_service = PerplexityService()
            self.search_tool = PerplexitySearchTool(self.perplexity_service)
        else:
            self.perplexity_service = None
            self.search_tool = None
    
    async def perplexity_search(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "general",
        format_output: str = "list"
    ) -> Any:
        """
        Reusable perplexity search method
        
        Args:
            query: Search query string
            max_results: Maximum number of results (default: 5)
            search_type: Type of search - general, travel, hotel, flight, restaurant, activities
            format_output: Output format - "list", "dict", "formatted", "urls"
            
        Returns:
            Search results in requested format
            
        Example:
            # Basic usage
            results = await search_utils.perplexity_search("latest AI developments 2024")
            
            # Travel-specific search
            hotels = await search_utils.perplexity_search(
                "best hotels in Paris", 
                search_type="hotel",
                format_output="formatted"
            )
        """
        if not self.perplexity_service:
            return self._mock_results(query, max_results, format_output)
        
        try:
            # Perform the search
            results = await self.perplexity_service.perplexity_search(
                query=query,
                max_results=max_results,
                search_type=search_type
            )
            
            # Format output based on requested format
            return self._format_output(results, format_output)
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            return self._mock_results(query, max_results, format_output)
    
    async def travel_search(
        self,
        destination: str,
        category: str = "general",
        max_results: int = 5,
        format_output: str = "formatted"
    ) -> Any:
        """
        Travel-specific search method
        
        Args:
            destination: Travel destination
            category: Search category - general, hotels, flights, restaurants, activities
            max_results: Maximum number of results
            format_output: Output format
            
        Returns:
            Travel search results
            
        Example:
            hotels = await search_utils.travel_search("Tokyo", "hotels")
            restaurants = await search_utils.travel_search("Paris", "restaurants", max_results=10)
        """
        if not self.perplexity_service:
            return f"Mock travel results for {destination} - {category}"
        
        try:
            results = await self.perplexity_service.travel_search(
                destination=destination,
                search_category=category,
                max_results=max_results
            )
            
            return self._format_output(results, format_output)
            
        except Exception as e:
            print(f"Travel search error: {str(e)}")
            return f"Error searching for {category} in {destination}: {str(e)}"
    
    async def multi_search(
        self,
        queries: List[str],
        max_results_per_query: int = 3,
        format_output: str = "dict"
    ) -> Dict[str, Any]:
        """
        Search multiple queries in parallel
        
        Args:
            queries: List of search queries
            max_results_per_query: Maximum results per query
            format_output: Output format for each query's results
            
        Returns:
            Dictionary mapping queries to their results
            
        Example:
            queries = [
                "best restaurants in Tokyo",
                "cheap flights to Japan",
                "top attractions in Kyoto"
            ]
            results = await search_utils.multi_search(queries)
        """
        if not self.perplexity_service:
            return {query: f"Mock results for: {query}" for query in queries}
        
        try:
            # Use the service's multi_search method
            results = await self.perplexity_service.multi_search(
                queries=queries,
                max_results_per_query=max_results_per_query
            )
            
            # Format each query's results
            formatted_results = {}
            for query, query_results in results.items():
                formatted_results[query] = self._format_output(query_results, format_output)
            
            return formatted_results
            
        except Exception as e:
            print(f"Multi-search error: {str(e)}")
            return {query: f"Error: {str(e)}" for query in queries}
    
    async def comprehensive_destination_search(
        self,
        destination: str,
        max_results_per_category: int = 3
    ) -> Dict[str, Any]:
        """
        Comprehensive search for a destination covering all categories
        
        Args:
            destination: Travel destination
            max_results_per_category: Maximum results per category
            
        Returns:
            Dictionary with results for all travel categories
            
        Example:
            all_info = await search_utils.comprehensive_destination_search("Barcelona")
            print(all_info["hotels"])
            print(all_info["restaurants"])
        """
        categories = ["general", "hotels", "flights", "restaurants", "activities"]
        
        if not self.search_tool:
            return {cat: f"Mock {cat} results for {destination}" for cat in categories}
        
        try:
            results = await self.search_tool.multi_category_travel_search(
                destination=destination,
                categories=categories,
                max_results_per_category=max_results_per_category
            )
            
            return results
            
        except Exception as e:
            print(f"Comprehensive search error: {str(e)}")
            return {cat: f"Error: {str(e)}" for cat in categories}
    
    def _format_output(self, results: List, format_type: str) -> Any:
        """Format search results based on requested format"""
        if not results:
            return [] if format_type == "list" else {}
        
        if format_type == "list":
            return results
        elif format_type == "dict":
            return [result.to_dict() if hasattr(result, 'to_dict') else result for result in results]
        elif format_type == "formatted":
            if hasattr(results[0], 'title'):
                return self.perplexity_service.format_results_for_agents(results)
            else:
                return str(results)
        elif format_type == "urls":
            return [getattr(result, 'url', '') for result in results if hasattr(result, 'url')]
        elif format_type == "titles":
            return [getattr(result, 'title', str(result)) for result in results]
        else:
            return results
    
    def _mock_results(self, query: str, max_results: int, format_type: str) -> Any:
        """Provide mock results when service is unavailable"""
        mock_data = [
            f"Mock result {i+1} for query: {query}"
            for i in range(min(max_results, 3))
        ]
        
        if format_type == "dict":
            return [{"title": item, "content": item, "url": ""} for item in mock_data]
        elif format_type == "formatted":
            return "\\n".join([f"{i+1}. {item}" for i, item in enumerate(mock_data)])
        else:
            return mock_data
    
    async def quick_travel_info(self, destination: str) -> str:
        """
        Quick method to get essential travel information for a destination
        
        Args:
            destination: Travel destination
            
        Returns:
            Formatted string with essential travel info
            
        Example:
            info = await search_utils.quick_travel_info("Rome")
            print(info)
        """
        try:
            # Search for general travel information
            results = await self.travel_search(
                destination=destination,
                category="general",
                max_results=3,
                format_output="formatted"
            )
            
            return f"Essential travel information for {destination}:\\n\\n{results}"
            
        except Exception as e:
            return f"Could not retrieve travel info for {destination}: {str(e)}"

# Global instance for easy import and use
search_utils = TripMazerSearchUtils()

# Convenience functions for direct use
async def perplexity_search(query: str, max_results: int = 5, search_type: str = "general") -> List:
    """
    Direct convenience function for perplexity search
    
    Example:
        from src.utils.common import perplexity_search
        results = await perplexity_search("latest AI developments 2024", max_results=5)
        for result in results:
            print(f"{result.title}: {result.url}")
    """
    return await search_utils.perplexity_search(
        query=query,
        max_results=max_results,
        search_type=search_type,
        format_output="list"
    )

async def travel_search(destination: str, category: str = "general", max_results: int = 5) -> str:
    """
    Direct convenience function for travel search
    
    Example:
        from src.utils.common import travel_search
        hotels = await travel_search("Paris", "hotels")
        print(hotels)
    """
    return await search_utils.travel_search(
        destination=destination,
        category=category,
        max_results=max_results
    )

# Example usage function that can be run directly
async def example_usage():
    """
    Example usage of the search utilities
    """
    print("TripMazer Search Utils Examples")
    print("=" * 40)
    
    # Basic search
    print("\\n1. Basic Search:")
    results = await search_utils.perplexity_search(
        "latest AI developments 2024",
        max_results=3,
        format_output="titles"
    )
    print(results)
    
    # Travel search
    print("\\n2. Travel Search:")
    hotels = await search_utils.travel_search(
        "Tokyo",
        "hotels",
        max_results=3
    )
    print(hotels[:200] + "..." if len(str(hotels)) > 200 else hotels)
    
    # Multi search
    print("\\n3. Multi Search:")
    queries = ["best pizza in NYC", "top museums in Paris"]
    multi_results = await search_utils.multi_search(queries, max_results_per_query=2)
    for query, results in multi_results.items():
        print(f"{query}: {len(results) if isinstance(results, list) else 'String result'}")
    
    # Quick travel info
    print("\\n4. Quick Travel Info:")
    info = await search_utils.quick_travel_info("Barcelona")
    print(info[:200] + "..." if len(info) > 200 else info)

if __name__ == "__main__":
    # Run example if file is executed directly
    asyncio.run(example_usage())