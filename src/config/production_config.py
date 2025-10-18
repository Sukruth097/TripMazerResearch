"""
Production-Grade Configuration and Error Handling for Travel Services
====================================================================

This module provides:
1. Centralized configuration management
2. Robust error handling and retry logic
3. Rate limiting and circuit breaker patterns
4. Comprehensive logging
5. Service health monitoring
"""

import os
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import logging
from functools import wraps
import json
from datetime import datetime, timedelta


class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3


@dataclass 
class ServiceConfig:
    """Configuration for individual services"""
    name: str
    api_key: str
    base_url: str
    timeout: int = 30
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)
    circuit_breaker_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Service-specific settings
    max_results: int = 50
    cache_ttl: int = 300  # 5 minutes
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError(f"API key is required for service {self.name}")


class TravelServiceConfig:
    """
    Centralized configuration manager for travel services
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.services: Dict[str, ServiceConfig] = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from file and environment variables"""
        
        # Default configurations
        default_configs = {
            'serp_api': {
                'name': 'serp_api',
                'api_key': os.getenv('SERP_API_KEY', ''),
                'base_url': 'https://serpapi.com/search',
                'timeout': 30,
                'max_results': 20,
                'rate_limit_config': {
                    'requests_per_minute': 100,
                    'requests_per_hour': 2500
                }
            },
            'perplexity': {
                'name': 'perplexity',
                'api_key': os.getenv('PERPLEXITY_API_KEY', ''),
                'base_url': 'https://api.perplexity.ai/chat/completions',
                'timeout': 45,
                'max_results': 10,
                'rate_limit_config': {
                    'requests_per_minute': 60,
                    'requests_per_hour': 1000
                }
            },
            'gemini': {
                'name': 'gemini',
                'api_key': os.getenv('GEMINI_API_KEY', ''),
                'base_url': 'https://generativelanguage.googleapis.com',
                'timeout': 30,
                'rate_limit_config': {
                    'requests_per_minute': 60,
                    'requests_per_hour': 1500
                }
            }
        }
        
        # Load from config file if provided
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    default_configs.update(file_config)
            except Exception as e:
                logging.warning(f"Failed to load config file {self.config_file}: {e}")
        
        # Create service configurations
        for service_name, config_data in default_configs.items():
            try:
                # Handle nested configurations
                retry_config = RetryConfig(**config_data.get('retry_config', {}))
                rate_limit_config = RateLimitConfig(**config_data.get('rate_limit_config', {}))
                circuit_breaker_config = CircuitBreakerConfig(**config_data.get('circuit_breaker_config', {}))
                
                service_config = ServiceConfig(
                    name=config_data['name'],
                    api_key=config_data['api_key'],
                    base_url=config_data['base_url'],
                    timeout=config_data.get('timeout', 30),
                    max_results=config_data.get('max_results', 50),
                    cache_ttl=config_data.get('cache_ttl', 300),
                    retry_config=retry_config,
                    rate_limit_config=rate_limit_config,
                    circuit_breaker_config=circuit_breaker_config
                )
                
                self.services[service_name] = service_config
                
            except Exception as e:
                logging.error(f"Failed to configure service {service_name}: {e}")
    
    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """Get configuration for a specific service"""
        return self.services.get(service_name)
    
    def validate_configuration(self) -> List[str]:
        """Validate all service configurations"""
        errors = []
        
        for service_name, config in self.services.items():
            if not config.api_key:
                errors.append(f"Missing API key for service: {service_name}")
            
            if not config.base_url:
                errors.append(f"Missing base URL for service: {service_name}")
        
        return errors


class ServiceError(Exception):
    """Base exception for service errors"""
    
    def __init__(self, message: str, service_name: str, error_code: Optional[str] = None):
        self.message = message
        self.service_name = service_name
        self.error_code = error_code
        super().__init__(self.message)


class RateLimitError(ServiceError):
    """Exception for rate limit exceeded"""
    pass


class CircuitBreakerError(ServiceError):
    """Exception for circuit breaker open"""
    pass


class ServiceTimeoutError(ServiceError):
    """Exception for service timeout"""
    pass


def retry_with_exponential_backoff(config: RetryConfig):
    """
    Decorator for implementing exponential backoff retry logic
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                        
                except Exception as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logging.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    
                    if asyncio.iscoroutinefunction(func):
                        await asyncio.sleep(delay)
                    else:
                        time.sleep(delay)
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, use the same logic without async/await
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                        
                except Exception as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        break
                    
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logging.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_limit
        self.last_update = time.time()
        self.lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None
    
    async def acquire(self) -> bool:
        """Acquire a token, return True if successful"""
        if self.lock:
            async with self.lock:
                return self._acquire_token()
        else:
            return self._acquire_token()
    
    def _acquire_token(self) -> bool:
        """Internal token acquisition logic"""
        now = time.time()
        time_passed = now - self.last_update
        
        # Add tokens based on time passed
        tokens_to_add = time_passed * (self.config.requests_per_minute / 60.0)
        self.tokens = min(self.config.burst_limit, self.tokens + tokens_to_add)
        self.last_update = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.half_open_attempts = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        now = time.time()
        
        if self.state == "closed":
            return True
        elif self.state == "open":
            if (now - self.last_failure_time) >= self.config.recovery_timeout:
                self.state = "half_open"
                self.half_open_attempts = 0
                return True
            return False
        elif self.state == "half_open":
            return self.half_open_attempts < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful execution"""
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "half_open":
            self.state = "open"
        elif self.failure_count >= self.config.failure_threshold:
            self.state = "open"


class ServiceHealthMonitor:
    """Monitor service health and availability"""
    
    def __init__(self):
        self.service_status: Dict[str, ServiceStatus] = {}
        self.last_check: Dict[str, datetime] = {}
        self.error_counts: Dict[str, int] = {}
        
    def update_service_status(self, service_name: str, status: ServiceStatus):
        """Update service status"""
        self.service_status[service_name] = status
        self.last_check[service_name] = datetime.now()
        
        if status == ServiceStatus.HEALTHY:
            self.error_counts[service_name] = 0
        else:
            self.error_counts[service_name] = self.error_counts.get(service_name, 0) + 1
    
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get current service status"""
        return self.service_status.get(service_name, ServiceStatus.UNKNOWN)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        healthy_services = sum(1 for status in self.service_status.values() 
                             if status == ServiceStatus.HEALTHY)
        total_services = len(self.service_status)
        
        return {
            "overall_health": "healthy" if healthy_services == total_services else "degraded",
            "healthy_services": healthy_services,
            "total_services": total_services,
            "service_details": {
                name: {
                    "status": status.value,
                    "last_check": self.last_check.get(name),
                    "error_count": self.error_counts.get(name, 0)
                }
                for name, status in self.service_status.items()
            }
        }


# Global configuration instance
travel_config = TravelServiceConfig()

# Global health monitor
health_monitor = ServiceHealthMonitor()


def configure_service_logging():
    """Configure logging for travel services"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('travel_services.log'),
            logging.StreamHandler()
        ]
    )
    
    # Set specific log levels for different components
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


# Example usage:
"""
# Initialize configuration
config = TravelServiceConfig('config/travel_services.json')

# Validate configuration
errors = config.validate_configuration()
if errors:
    print("Configuration errors:", errors)

# Get service configuration
serp_config = config.get_service_config('serp_api')

# Use retry decorator
@retry_with_exponential_backoff(serp_config.retry_config)
def api_call():
    # Your API call here
    pass

# Use rate limiter
rate_limiter = RateLimiter(serp_config.rate_limit_config)
if await rate_limiter.acquire():
    # Make API call
    pass

# Use circuit breaker
circuit_breaker = CircuitBreaker(serp_config.circuit_breaker_config)
if circuit_breaker.can_execute():
    try:
        # Make API call
        circuit_breaker.record_success()
    except Exception:
        circuit_breaker.record_failure()
        raise
"""