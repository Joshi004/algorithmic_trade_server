# ATS Application - Standardized Logging Structure

## Overview

This document describes the comprehensive restructuring of logging across all ATS (Algorithmic Trading Server) services. The new logging system provides consistent, meaningful, and properly leveled logs across all components.

## Key Improvements

### 1. **Centralized Configuration**
- Single logging configuration in `ats_base/settings.py`
- Multiple log files with automatic rotation
- Service-specific loggers with standardized prefixes

### 2. **Standardized Log Levels**
- **DEBUG**: Parameter details, query building, internal operations
- **INFO**: Important business events, API completions, state changes
- **WARNING**: Recoverable issues, performance concerns, missing optional configs
- **ERROR**: Failures requiring attention, with full context and stack traces
- **CRITICAL**: System-threatening issues

### 3. **Business Decision Logging**
- Dedicated business.log file for critical business decisions
- Structured context logging for trade decisions, risk assessments, scanner results
- Session state change tracking

### 4. **Print Statement Elimination**
- All print statements replaced with proper logging
- Debug comments converted to appropriate log levels
- Legacy print debugging removed

## Log File Structure

```
logs/
├── application.log     # General INFO+ logs from all services
├── debug.log          # DEBUG+ logs (detailed technical information)
├── business.log       # Business decision logs (trades, sessions, risk)
└── error.log          # ERROR+ logs (failures and critical issues)
```

## Service Prefixes

Each service uses standardized prefixes for easy identification:

- **[TMU]** - Trade Management Unit
- **[SCAN]** - Scanning Service  
- **[INTG]** - Integration Service
- **[GATE]** - ATS Gateway
- **[INIT]** - Initiation Service

## Usage Patterns

### 1. **Creating Service Loggers**

```python
from ats_base.logging_utils import create_service_logger

# Create standardized logger
logger = create_service_logger('trade_management_unit', 'models')
```

### 2. **Standard Logging**

```python
# Debug level - technical details
logger.debug("Building trade sessions query", context={
    'user_id': user_id,
    'filters_applied': filters
})

# Info level - important events
logger.info("Trade session created successfully", context={
    'session_id': session.id,
    'user_id': user_id
})

# Warning level - concerning but not critical
logger.warning("Slow database operation detected", context={
    'execution_time_ms': 1500,
    'operation': 'session_query'
})

# Error level - failures with context
logger.error("Failed to create trade session", context={
    'user_id': user_id,
    'error': str(e)
})
```

### 3. **Business Decision Logging**

```python
from ats_base.logging_utils import log_scanner_result, log_session_state_change

# Scanner decisions
log_scanner_result(
    logger=logger,
    symbol="RELIANCE",
    eligible=True,
    algorithm="UDTS",
    metrics={
        'reward_risk_ratio': 2.5,
        'consensus_trend': 'UPTREND',
        'trading_pairs_count': 3
    }
)

# Session state changes
log_session_state_change(
    logger=logger,
    session_id="12345",
    old_state="started",
    new_state="paused",
    reason="User initiated pause"
)
```

### 4. **Performance Logging with Decorators**

```python
from ats_base.logging_utils import log_execution_time, log_database_operation

@log_execution_time(logger, "user_sessions_query")
@log_database_operation(logger, 'SELECT', 'trade_sessions')
def get_user_sessions(user_id):
    # Implementation
    pass
```

## Migration Summary

### Fixed Issues

1. **Excessive INFO Logging**
   - Moved parameter logging from INFO to DEBUG level
   - Reduced noise in production logs
   - Preserved detailed information for debugging

2. **Print Statement Removal**
   - `scanning_service/lib/Algorithms/ScannerAlgos/UDTS/UDTSScanner.py`: Replaced debug prints
   - `trade_management_unit/lib/Indicators/MACD/RealTimeMACD.py`: Removed DB update prints
   - Multiple singleton and chart files: Cleaned up debug prints

3. **Inconsistent Prefixes**
   - Standardized all service prefixes: [TMU], [SCAN], [INTG], [GATE], [INIT]
   - Consistent message formatting across services

4. **Missing Business Logs**
   - Added scanner eligibility decision logging
   - Added trade session state change logging
   - Added risk assessment logging infrastructure

### Legacy Compatibility

- Existing `log()` functions in each service updated to use new infrastructure
- Backwards compatibility maintained for existing code
- Gradual migration path for custom logging implementations

## Configuration Details

### Django Settings Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} | {levelname:8} | {name:20} | {process:5d}:{thread:5d} | {funcName}:{lineno} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'business': {
            'format': '{asctime} | {levelname:8} | [BUSINESS] | {name:15} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'file_debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/debug.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_business': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/business.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'business',
        }
        # ... other handlers
    },
    'loggers': {
        'trade_management_unit': {
            'handlers': ['console', 'file_debug', 'file_info', 'file_business', 'file_error'],
            'level': 'DEBUG',
            'propagate': False,
        }
        # ... other service loggers
    }
}
```

## Best Practices

### 1. **Log Level Guidelines**

- **DEBUG**: Use for technical details that help with troubleshooting
- **INFO**: Use for normal business operations and significant events
- **WARNING**: Use for issues that don't stop operation but need attention
- **ERROR**: Use for failures that need immediate attention
- **CRITICAL**: Use for system-threatening issues

### 2. **Context Logging**

Always provide relevant context with structured data:

```python
# Good
logger.info("User authentication successful", context={
    'user_id': user.id,
    'login_method': 'jwt',
    'ip_address': request.META.get('REMOTE_ADDR')
})

# Avoid
logger.info(f"User {user.id} logged in")
```

### 3. **Error Logging**

Include full context and stack traces for errors:

```python
try:
    # operation
except Exception as e:
    logger.error("Operation failed", context={
        'operation': 'user_registration',
        'user_email': email,
        'error_type': type(e).__name__,
        'error': str(e)
    }, exc_info=True)  # Includes stack trace
```

### 4. **Business Decision Logging**

Use dedicated business logging functions for critical decisions:

```python
# Scanner decisions
log_scanner_result(logger, symbol, eligible, algorithm, metrics)

# Risk assessments  
log_risk_assessment(logger, symbol, risk_level, factors, passed)

# Trade decisions
log_trade_decision(logger, decision, symbol, reasoning, context)
```

## Monitoring and Alerting

### Log Monitoring Recommendations

1. **Error Rate Monitoring**: Alert on sudden increases in ERROR/CRITICAL logs
2. **Business Metrics**: Monitor scanner success rates, session state changes
3. **Performance Monitoring**: Alert on slow operation warnings
4. **Log Volume**: Monitor for unusual log volume spikes

### Key Metrics to Track

- Scanner eligibility rates by algorithm
- Trade session state change patterns
- Database operation performance
- API response times
- Authentication failure rates

## Future Enhancements

1. **Structured JSON Logging**: For better log parsing and analysis
2. **Distributed Tracing**: For cross-service operation tracking
3. **Log Sampling**: For high-frequency operations
4. **Real-time Dashboards**: For live monitoring of business metrics
5. **Automated Log Analysis**: For pattern detection and anomaly alerts

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `sys.path.append()` is added before importing logging_utils
2. **Log File Permissions**: Verify write permissions for logs/ directory
3. **Circular Imports**: Use late imports if needed in utility functions
4. **Legacy Print Statements**: Search codebase for remaining print() calls

### Debug Mode

To increase log verbosity for debugging:

```python
# In Django settings for development
LOGGING['loggers']['your_service']['level'] = 'DEBUG'
```

This standardized logging structure provides comprehensive visibility into application behavior while maintaining performance and readability. The structured approach enables better monitoring, debugging, and business intelligence gathering across the entire ATS platform. 