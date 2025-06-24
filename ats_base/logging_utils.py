"""
Centralized Logging Utilities for ATS Application

This module provides standardized logging functions and utilities for consistent
logging across all services in the ATS application.
"""

import logging
import time
import functools
from typing import Any, Dict, Optional, Union
from datetime import datetime


class ServiceLogger:
    """
    Standardized logger wrapper for ATS services.
    Provides consistent logging methods with service-specific prefixes.
    """
    
    def __init__(self, service_name: str, module_name: str = None):
        """
        Initialize service logger.
        
        Args:
            service_name: Name of the service (e.g., 'trade_management_unit')
            module_name: Optional module name for more specific logging
        """
        self.service_name = service_name
        self.module_name = module_name
        
        # Create logger name
        if module_name:
            logger_name = f"{service_name}.{module_name}"
        else:
            logger_name = service_name
            
        self.logger = logging.getLogger(logger_name)
        self.business_logger = logging.getLogger(f"business.{service_name}")
        
        # Service prefixes for consistent formatting
        self.service_prefixes = {
            'trade_management_unit': 'TMU',
            'scanning_service': 'SCAN',
            'integration_service': 'INTG', 
            'ats_gateway': 'GATE',
            'initiation_service': 'INIT'
        }
        
        self.prefix = self.service_prefixes.get(service_name, service_name.upper())
    
    def _format_message(self, message: str, context: Dict[str, Any] = None) -> str:
        """Format message with service prefix and optional context."""
        formatted_msg = f"[{self.prefix}] {message}"
        
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            formatted_msg += f" | {context_str}"
            
        return formatted_msg
    
    def debug(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message, context), **kwargs)
    
    def info(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message, context), **kwargs)
    
    def warning(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message, context), **kwargs)
    
    def error(self, message: str, context: Dict[str, Any] = None, exc_info: bool = True, **kwargs):
        """Log error message with optional exception info."""
        kwargs['exc_info'] = exc_info
        self.logger.error(self._format_message(message, context), **kwargs)
    
    def critical(self, message: str, context: Dict[str, Any] = None, exc_info: bool = True, **kwargs):
        """Log critical message with optional exception info."""
        kwargs['exc_info'] = exc_info
        self.logger.critical(self._format_message(message, context), **kwargs)
    
    def business_info(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log business-specific information."""
        self.business_logger.info(self._format_message(message, context), **kwargs)
    
    def business_warning(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log business-specific warning."""
        self.business_logger.warning(self._format_message(message, context), **kwargs)
    
    def business_error(self, message: str, context: Dict[str, Any] = None, exc_info: bool = True, **kwargs):
        """Log business-specific error."""
        kwargs['exc_info'] = exc_info
        self.business_logger.error(self._format_message(message, context), **kwargs)


def log_execution_time(logger: ServiceLogger, operation_name: str = None):
    """
    Decorator to log execution time of functions.
    
    Args:
        logger: ServiceLogger instance
        operation_name: Optional name for the operation (defaults to function name)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or func.__name__
            
            logger.debug(f"Starting operation: {operation}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.debug(f"Operation completed: {operation}", 
                           context={'execution_time_ms': round(execution_time * 1000, 2)})
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Operation failed: {operation}", 
                           context={'execution_time_ms': round(execution_time * 1000, 2), 
                                   'error': str(e)})
                raise
        
        return wrapper
    return decorator


def log_database_operation(logger: ServiceLogger, operation_type: str, table_name: str = None):
    """
    Decorator to log database operations.
    
    Args:
        logger: ServiceLogger instance
        operation_type: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        table_name: Optional table name
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            context = {'operation': operation_type}
            if table_name:
                context['table'] = table_name
            
            logger.debug(f"Database operation started", context=context)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log different levels based on execution time
                if execution_time > 1.0:  # Slow queries
                    logger.warning(f"Slow database operation", 
                                 context={**context, 'execution_time_ms': round(execution_time * 1000, 2)})
                else:
                    logger.debug(f"Database operation completed", 
                               context={**context, 'execution_time_ms': round(execution_time * 1000, 2)})
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Database operation failed", 
                           context={**context, 'execution_time_ms': round(execution_time * 1000, 2), 
                                   'error': str(e)})
                raise
        
        return wrapper
    return decorator


def log_api_call(logger: ServiceLogger, endpoint: str = None, method: str = None):
    """
    Decorator to log API calls.
    
    Args:
        logger: ServiceLogger instance
        endpoint: Optional endpoint name
        method: Optional HTTP method
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            context = {}
            if endpoint:
                context['endpoint'] = endpoint
            if method:
                context['method'] = method
            
            logger.info(f"API call started", context=context)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"API call completed", 
                          context={**context, 'execution_time_ms': round(execution_time * 1000, 2)})
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"API call failed", 
                           context={**context, 'execution_time_ms': round(execution_time * 1000, 2), 
                                   'error': str(e)})
                raise
        
        return wrapper
    return decorator


def create_service_logger(service_name: str, module_name: str = None) -> ServiceLogger:
    """
    Factory function to create standardized service loggers.
    
    Args:
        service_name: Name of the service
        module_name: Optional module name
        
    Returns:
        ServiceLogger instance
    """
    return ServiceLogger(service_name, module_name)


# Business Decision Logging Helpers
def log_trade_decision(logger: ServiceLogger, decision: str, symbol: str, 
                      reasoning: str, context: Dict[str, Any] = None):
    """Log trade decision with context."""
    log_context = {
        'symbol': symbol,
        'decision': decision,
        'reasoning': reasoning
    }
    if context:
        log_context.update(context)
    
    logger.business_info(f"Trade decision made", context=log_context)


def log_risk_assessment(logger: ServiceLogger, symbol: str, risk_level: str, 
                       factors: Dict[str, Any], passed: bool):
    """Log risk assessment results."""
    log_context = {
        'symbol': symbol,
        'risk_level': risk_level,
        'assessment_passed': passed,
        **factors
    }
    
    if passed:
        logger.business_info(f"Risk assessment passed", context=log_context)
    else:
        logger.business_warning(f"Risk assessment failed", context=log_context)


def log_scanner_result(logger: ServiceLogger, symbol: str, eligible: bool, 
                      algorithm: str, metrics: Dict[str, Any]):
    """Log scanner eligibility results."""
    log_context = {
        'symbol': symbol,
        'algorithm': algorithm,
        'eligible': eligible,
        **metrics
    }
    
    logger.business_info(f"Scanner evaluation completed", context=log_context)


def log_session_state_change(logger: ServiceLogger, session_id: str, 
                            old_state: str, new_state: str, reason: str = None):
    """Log trade session state changes."""
    log_context = {
        'session_id': session_id,
        'old_state': old_state,
        'new_state': new_state
    }
    if reason:
        log_context['reason'] = reason
    
    logger.business_info(f"Session state changed", context=log_context) 