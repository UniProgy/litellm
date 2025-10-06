import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from litellm._logging import verbose_proxy_logger
from litellm.proxy.utils import hash_token


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        client_ip = self._get_client_ip(request)
        api_key_hash = self._extract_and_hash_api_key(request)
        request_size_mb = self._get_request_size(request)
        method = request.method
        path = request.url.path
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        status_code = response.status_code
        
        log_message = (
            f"[REQUEST] IP: {client_ip} | "
            f"API Key: {api_key_hash} | "
            f"Size: {request_size_mb:.2f} MB | "
            f"Method: {method} | "
            f"Path: {path} | "
            f"Status: {status_code} | "
            f"Duration: {duration:.2f}s"
        )
        
        verbose_proxy_logger.info(log_message)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        elif request.client is not None:
            return request.client.host
        else:
            return "unknown"
    
    def _extract_and_hash_api_key(self, request: Request) -> str:
        x_auth_header = request.headers.get("x-authorization")
        
        if not x_auth_header:
            return "none"
        
        api_key = x_auth_header.strip()
        
        if api_key.lower().startswith("bearer "):
            api_key = api_key[7:]
        
        if not api_key:
            return "none"
        
        try:
            hashed = hash_token(api_key)
            return hashed[:10]
        except Exception:
            return "invalid"
    
    def _get_request_size(self, request: Request) -> float:
        content_length = request.headers.get("content-length")
        if content_length:
            size_bytes = int(content_length)
        else:
            size_bytes = 0
        
        size_mb = size_bytes / (1024 * 1024)
        return size_mb

