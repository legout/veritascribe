"""Rate limiting implementation for LLM API calls using token bucket algorithm."""

import time
import asyncio
import logging
from typing import Dict, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from threading import Lock
import functools

logger = logging.getLogger(__name__)


@dataclass
class RateLimitStats:
    """Statistics for rate limiter usage."""
    total_requests: int = 0
    requests_allowed: int = 0
    requests_queued: int = 0
    requests_rejected: int = 0
    total_wait_time: float = 0.0
    max_wait_time: float = 0.0
    current_tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (allowed + queued) / total."""
        if self.total_requests == 0:
            return 1.0
        return (self.requests_allowed + self.requests_queued) / self.total_requests
    
    @property
    def average_wait_time(self) -> float:
        """Calculate average wait time for queued requests."""
        if self.requests_queued == 0:
            return 0.0
        return self.total_wait_time / self.requests_queued


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(
        self,
        requests_per_minute: float,
        burst_capacity: Optional[int] = None,
        queue_timeout: float = 300.0,
        backoff_multiplier: float = 1.5
    ):
        """
        Initialize token bucket rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            burst_capacity: Maximum burst capacity (defaults to 2x rpm)
            queue_timeout: Maximum time to wait in queue (seconds)
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.requests_per_minute = requests_per_minute
        self.tokens_per_second = requests_per_minute / 60.0
        self.burst_capacity = burst_capacity or int(requests_per_minute * 2)
        self.queue_timeout = queue_timeout
        self.backoff_multiplier = backoff_multiplier
        
        # Current token count (starts at burst capacity)
        self.tokens = float(self.burst_capacity)
        self.last_refill = time.time()
        self.lock = Lock()
        
        # Statistics
        self.stats = RateLimitStats()
        
        logger.info(f"Rate limiter initialized: {requests_per_minute} RPM, "
                   f"burst capacity: {self.burst_capacity}, "
                   f"queue timeout: {queue_timeout}s")
    
    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        new_tokens = elapsed * self.tokens_per_second
        self.tokens = min(self.burst_capacity, self.tokens + new_tokens)
        self.last_refill = now
        
        # Update stats
        self.stats.current_tokens = self.tokens
        self.stats.last_refill = now
    
    def _wait_time_for_tokens(self, tokens_needed: int = 1) -> float:
        """Calculate how long to wait for required tokens."""
        if self.tokens >= tokens_needed:
            return 0.0
        
        tokens_deficit = tokens_needed - self.tokens
        return tokens_deficit / self.tokens_per_second
    
    def can_proceed(self, tokens_needed: int = 1) -> bool:
        """Check if request can proceed immediately."""
        with self.lock:
            self._refill_tokens()
            return self.tokens >= tokens_needed
    
    def acquire(self, tokens_needed: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens, blocking until available or timeout.
        
        Args:
            tokens_needed: Number of tokens required
            timeout: Maximum time to wait (uses queue_timeout if None)
            
        Returns:
            True if tokens acquired, False if timeout
        """
        timeout = timeout or self.queue_timeout
        start_time = time.time()
        
        self.stats.total_requests += 1
        
        with self.lock:
            self._refill_tokens()
            
            # If tokens available, proceed immediately
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                self.stats.requests_allowed += 1
                self.stats.current_tokens = self.tokens
                return True
        
        # Need to wait - check if within timeout
        wait_time = self._wait_time_for_tokens(tokens_needed)
        if wait_time > timeout:
            self.stats.requests_rejected += 1
            logger.warning(f"Request rejected: would need {wait_time:.1f}s wait "
                          f"(timeout: {timeout:.1f}s)")
            return False
        
        # Queue the request
        self.stats.requests_queued += 1
        logger.debug(f"Queuing request for {wait_time:.1f}s")
        
        # Wait with exponential backoff
        backoff = 0.1  # Start with 100ms
        while time.time() - start_time < timeout:
            time.sleep(min(backoff, wait_time))
            backoff *= self.backoff_multiplier
            
            with self.lock:
                self._refill_tokens()
                if self.tokens >= tokens_needed:
                    self.tokens -= tokens_needed
                    actual_wait = time.time() - start_time
                    self.stats.total_wait_time += actual_wait
                    self.stats.max_wait_time = max(self.stats.max_wait_time, actual_wait)
                    self.stats.current_tokens = self.tokens
                    logger.debug(f"Request proceeded after {actual_wait:.1f}s wait")
                    return True
            
            # Recalculate wait time
            wait_time = self._wait_time_for_tokens(tokens_needed)
            if wait_time > (timeout - (time.time() - start_time)):
                break
        
        # Timeout
        self.stats.requests_rejected += 1
        actual_wait = time.time() - start_time
        logger.warning(f"Request timeout after {actual_wait:.1f}s")
        return False
    
    async def acquire_async(self, tokens_needed: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Async version of acquire method.
        
        Args:
            tokens_needed: Number of tokens required
            timeout: Maximum time to wait
            
        Returns:
            True if tokens acquired, False if timeout
        """
        timeout = timeout or self.queue_timeout
        start_time = time.time()
        
        self.stats.total_requests += 1
        
        # Check immediate availability
        if self.can_proceed(tokens_needed):
            with self.lock:
                self.tokens -= tokens_needed
                self.stats.requests_allowed += 1
                self.stats.current_tokens = self.tokens
                return True
        
        # Need to wait
        wait_time = self._wait_time_for_tokens(tokens_needed)
        if wait_time > timeout:
            self.stats.requests_rejected += 1
            return False
        
        self.stats.requests_queued += 1
        
        # Async wait with backoff
        backoff = 0.1
        while time.time() - start_time < timeout:
            await asyncio.sleep(min(backoff, wait_time))
            backoff *= self.backoff_multiplier
            
            if self.can_proceed(tokens_needed):
                with self.lock:
                    self.tokens -= tokens_needed
                    actual_wait = time.time() - start_time
                    self.stats.total_wait_time += actual_wait
                    self.stats.max_wait_time = max(self.stats.max_wait_time, actual_wait)
                    self.stats.current_tokens = self.tokens
                    return True
            
            wait_time = self._wait_time_for_tokens(tokens_needed)
            if wait_time > (timeout - (time.time() - start_time)):
                break
        
        self.stats.requests_rejected += 1
        return False
    
    def get_stats(self) -> RateLimitStats:
        """Get current rate limiter statistics."""
        with self.lock:
            self._refill_tokens()
            stats_copy = RateLimitStats(
                total_requests=self.stats.total_requests,
                requests_allowed=self.stats.requests_allowed,
                requests_queued=self.stats.requests_queued,
                requests_rejected=self.stats.requests_rejected,
                total_wait_time=self.stats.total_wait_time,
                max_wait_time=self.stats.max_wait_time,
                current_tokens=self.tokens,
                last_refill=self.last_refill
            )
            return stats_copy
    
    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self.lock:
            self.stats = RateLimitStats()
            self.stats.current_tokens = self.tokens
            self.stats.last_refill = self.last_refill


class ProviderRateLimiter:
    """Rate limiter manager for different LLM providers."""
    
    # Default rate limits for different providers (requests per minute)
    DEFAULT_LIMITS = {
        "openai": 3500,      # OpenAI Tier 1 default
        "openrouter": 60,    # Conservative default for mixed models
        "anthropic": 1000,   # Claude API default
        "custom": 100        # Conservative default for custom endpoints
    }
    
    def __init__(self):
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}
        self.global_stats = {"total_requests": 0, "total_wait_time": 0}
    
    def get_limiter(
        self,
        provider: str,
        requests_per_minute: Optional[float] = None,
        **kwargs
    ) -> TokenBucketRateLimiter:
        """
        Get or create rate limiter for provider.
        
        Args:
            provider: LLM provider name
            requests_per_minute: Custom RPM limit
            **kwargs: Additional rate limiter config
            
        Returns:
            TokenBucketRateLimiter instance
        """
        if provider not in self.limiters:
            rpm = requests_per_minute or self.DEFAULT_LIMITS.get(provider, 60)
            self.limiters[provider] = TokenBucketRateLimiter(
                requests_per_minute=rpm,
                **kwargs
            )
            logger.info(f"Created rate limiter for {provider}: {rpm} RPM")
        
        return self.limiters[provider]
    
    def rate_limited_call(
        self,
        provider: str,
        func: Callable,
        *args,
        tokens_needed: int = 1,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Execute function call with rate limiting.
        
        Args:
            provider: LLM provider name
            func: Function to call
            *args: Function arguments
            tokens_needed: Number of tokens needed
            timeout: Custom timeout
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RuntimeError: If rate limit exceeded
        """
        limiter = self.get_limiter(provider)
        
        if not limiter.acquire(tokens_needed, timeout):
            raise RuntimeError(f"Rate limit exceeded for {provider} "
                             f"(requested {tokens_needed} tokens)")
        
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Update global stats
            self.global_stats["total_requests"] += 1
            self.global_stats["total_wait_time"] += duration
            
            logger.debug(f"Rate-limited call to {provider} completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Rate-limited call to {provider} failed: {e}")
            raise
    
    async def rate_limited_call_async(
        self,
        provider: str,
        func: Callable,
        *args,
        tokens_needed: int = 1,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """Async version of rate_limited_call."""
        limiter = self.get_limiter(provider)
        
        if not await limiter.acquire_async(tokens_needed, timeout):
            raise RuntimeError(f"Rate limit exceeded for {provider}")
        
        try:
            start_time = time.time()
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            self.global_stats["total_requests"] += 1
            self.global_stats["total_wait_time"] += duration
            
            return result
        except Exception as e:
            logger.error(f"Async rate-limited call to {provider} failed: {e}")
            raise
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all providers."""
        stats = {"providers": {}, "global": self.global_stats.copy()}
        
        for provider, limiter in self.limiters.items():
            provider_stats = limiter.get_stats()
            stats["providers"][provider] = {
                "requests_per_minute": limiter.requests_per_minute,
                "burst_capacity": limiter.burst_capacity,
                "current_tokens": provider_stats.current_tokens,
                "total_requests": provider_stats.total_requests,
                "success_rate": provider_stats.success_rate,
                "average_wait_time": provider_stats.average_wait_time,
                "max_wait_time": provider_stats.max_wait_time
            }
        
        return stats
    
    def log_stats(self) -> None:
        """Log current rate limiting statistics."""
        stats = self.get_all_stats()
        
        logger.info("Rate Limiting Statistics:")
        logger.info(f"Global: {stats['global']['total_requests']} total requests")
        
        for provider, provider_stats in stats["providers"].items():
            logger.info(f"{provider}: {provider_stats['total_requests']} requests, "
                       f"{provider_stats['success_rate']:.1%} success rate, "
                       f"{provider_stats['current_tokens']:.1f} tokens available")


def rate_limit_decorator(provider: str, tokens_needed: int = 1):
    """
    Decorator to add rate limiting to functions.
    
    Args:
        provider: LLM provider name
        tokens_needed: Number of tokens needed
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get rate limiter from global instance
            from .config import get_rate_limiter
            limiter = get_rate_limiter()
            return limiter.rate_limited_call(
                provider, func, *args, tokens_needed=tokens_needed, **kwargs
            )
        return wrapper
    return decorator