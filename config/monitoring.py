"""
Monitoring configuration for the application.
"""
import logging
from datetime import datetime
from django.conf import settings
from django.db import connection
from django.db.backends.utils import CursorWrapper
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache

logger = logging.getLogger(__name__)

class QueryCountDebugMiddleware(MiddlewareMixin):
    """
    This middleware will log the number of queries run
    and the total time taken for each request.
    """
    def process_response(self, request, response):
        if settings.DEBUG:
            total_time = 0
            queries = connection.queries
            for query in queries:
                query_time = query.get('time')
                if query_time is None:
                    query_time = query.get('duration', 0) / 1000
                total_time += float(query_time)
            
            logger.debug(
                "[SQL] %s queries run, total %s seconds",
                len(queries),
                total_time
            )
        return response

class RequestResponseLogMiddleware(MiddlewareMixin):
    """
    Logs request and response details for API monitoring.
    """
    def process_request(self, request):
        # Skip logging for admin and static files
        if request.path.startswith(('/admin/', '/static/', '/media/')):
            return None

        # Squelch the noise for the auth polling endpoint
        if request.path.endswith('/auth/profile/'):
            return None
            
        request.start_time = datetime.now()
        
        # Log request details
        logger.info(
            "[REQUEST] %s %s | User: %s | Data: %s | Params: %s",
            request.method,
            request.get_full_path(),
            getattr(request, 'user', 'Anonymous'),
            dict(request.POST) if request.method == 'POST' else {},
            dict(request.GET)
        )
        return None

    def process_response(self, request, response):
        # Skip logging for admin and static files
        if request.path.startswith(('/admin/', '/static/', '/media/')):
            return response

        # Reduce noise: verify-auth endpoint often returns 401, which is expected behavior
        if request.path.endswith('/auth/profile/') and response.status_code == 401:
            return response

            
        # Calculate request duration
        duration = 0
        if hasattr(request, 'start_time'):
            duration = (datetime.now() - request.start_time).total_seconds()
        
        # Log response details
        logger.info(
            "[RESPONSE] %s %s | Status: %s | Duration: %.2fs | User: %s",
            request.method,
            request.get_full_path(),
            response.status_code,
            duration,
            getattr(request, 'user', 'Anonymous')
        )
        
        # Add performance headers
        response['X-Request-Duration'] = f"{duration:.2f}"
        
        return response

def setup_api_metrics():
    """
    Set up API metrics collection.
    """
    try:
        from prometheus_client import start_http_server, Counter, Histogram
        
        # Define metrics
        REQUEST_COUNT = Counter(
            'http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        REQUEST_LATENCY = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency in seconds',
            ['method', 'endpoint']
        )
        
        # Start metrics server
        start_http_server(8001)
        logger.info("Started Prometheus metrics server on port 8001")
        
        return {
            'request_count': REQUEST_COUNT,
            'request_latency': REQUEST_LATENCY
        }
    except ImportError:
        logger.warning("Prometheus client not installed. Metrics collection disabled.")
        return None
