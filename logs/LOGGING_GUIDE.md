# ATS Application - Logging Architecture Guide

## Overview

This document provides a comprehensive guide to the logging architecture of the Algorithmic Trading Server (ATS) application. The ATS uses a sophisticated multi-file logging system designed for different analytical purposes and operational monitoring.

---

## Log Files Structure

### 📁 Current Log Files

| File Name | Size (Current) | Purpose | Retention |
|-----------|----------------|---------|-----------|
| `application.log` | ~1.9MB | General application flow and INFO+ events | 5 backups @ 10MB each |
| `debug.log` | ~1.6MB | Comprehensive technical debugging information | 5 backups @ 10MB each |
| `business.log` | ~1.7KB | Critical business decisions and trade logic | 5 backups @ 10MB each |
| `error.log` | ~888KB | Error tracking and failure analysis | 10 backups @ 10MB each |

---

## Log Distribution Matrix

### 🔄 Intentional Log Duplication Strategy

The ATS logging system uses **intentional duplication** across multiple files for different analytical purposes:

| Log Level | debug.log | application.log | business.log | error.log | Console |
|-----------|-----------|-----------------|--------------|-----------|---------|
| **DEBUG** |     ✅    |         ❌       |       ❌     |     ❌     |   ❌    |
| **INFO**  |     ✅    |         ✅       |       ✅*    |     ❌     |   ✅    | 
| **WARNING** |   ✅    |         ✅       |       ❌     |     ❌     |   ✅    |
| **ERROR** |     ✅    |         ✅       |       ❌     |     ✅     |   ✅    |
| **CRITICAL** |  ✅    |         ✅       |       ❌     |     ✅     |   ✅    |

*\*business.log only receives INFO+ logs from business-specific loggers*

---

## File-Specific Details

### 🔧 debug.log
**Purpose**: Comprehensive technical debugging and development support

**Content Includes:**
- All log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Detailed technical information with process/thread IDs
- Function names and line numbers
- Parameter values and execution flow
- Database query building and execution details
- API request/response debugging

**Format**: `{timestamp} | {level:8} | {logger_name:20} | {process}:{thread} | {function}:{line} | {message}`

**Example Entry:**
```
2025-06-20 10:53:11 | DEBUG | trade_management_unit.models | 2533:281472594407840 | debug:64 | [TMU] Building active trade sessions query | user_id=None | scanning_algo_id=1
```

**Sources:**
- All service loggers (ats_gateway, trade_management_unit, scanning_service, integration_service, initiation_service)
- Django framework logs
- Third-party library logs

---

### 📊 application.log
**Purpose**: General application monitoring and operational overview

**Content Includes:**
- INFO, WARNING, ERROR, CRITICAL levels
- Application startup/shutdown events
- API endpoint access logs
- Service-to-service communication
- Authentication and authorization events
- General operational status

**Format**: `{timestamp} | {level:8} | {logger_name:15} | {message}`

**Example Entry:**
```
2025-06-20 10:49:23 | INFO | ats_gateway.middleware.jwt_auth_middleware | JWT Middleware processing request | Path: /integration/get_quotes/
```

**Sources:**
- All service loggers
- Django server logs (daphne)
- Root logger
- Django request/response logs

---

### 💼 business.log
**Purpose**: Critical business decision tracking and trade analytics

**Content Includes:**
- Trade session lifecycle events
- Scanner algorithm results and decisions
- Risk management assessments
- Portfolio and position management
- Trading frequency and execution decisions
- Business rule validations

**Format**: `{timestamp} | {level:8} | [BUSINESS] | {logger_name:15} | {message}`

**Example Entry:**
```
2025-06-20 10:50:12 | INFO | [BUSINESS] | trade_management_unit.trade_session_lib | [TMU] User trade sessions query completed | sessions_found=4 | user_id=c64706ca-0975-4726-b9e6-ab90dab0deb7
```

**Sources:**
- `business.trade_session` logger
- `business.scanner` logger  
- `business.trade_execution` logger
- `business.risk_management` logger
- Trade Management Unit business operations
- Scanning Service business logic
- Initiation Service business decisions

---

### ⚠️ error.log
**Purpose**: Error tracking, failure analysis, and incident response

**Content Includes:**
- ERROR and CRITICAL level messages only
- Exception details with stack traces
- System failures and recovery attempts
- API errors and invalid requests
- Database connection issues
- External service integration failures

**Format**: `{timestamp} | {level:8} | {logger_name:20} | {process}:{thread} | {function}:{line} | {message}`

**Example Entry:**
```
2025-06-20 10:49:24 | ERROR | root | 2533:281472841871776 | get_quotes:43 | Error getting quotes: Invalid `api_key` or `access_token`.
```

**Sources:**
- All service loggers (ERROR+ only)
- Django framework errors
- Database operation failures
- Third-party API errors
- Authentication/authorization failures

---

## Service-Specific Log Sources

### 🚪 ATS Gateway (`ats_gateway`)
**Logs to**: debug.log, application.log, error.log, console

**Generates logs for:**
- JWT authentication middleware
- Request/response processing
- User authentication/registration
- CORS handling
- Internal service request routing

### 🏪 Trade Management Unit (`trade_management_unit`)
**Logs to**: debug.log, application.log, business.log, error.log, console

**Generates logs for:**
- Trade session lifecycle management
- Portfolio tracking and updates
- Risk management decisions
- Instrument data processing
- Algorithm execution (MACD, SLTO)
- Historical data processing

### 🔍 Scanning Service (`scanning_service`)
**Logs to**: debug.log, application.log, business.log, error.log, console

**Generates logs for:**
- Market scanning algorithms (UDTS)
- Redis stream processing
- Scanner queue management
- Instrument eligibility assessments
- Real-time market data analysis

### 🔗 Integration Service (`integration_service`)
**Logs to**: debug.log, application.log, error.log, console

**Generates logs for:**
- Broker API integrations (Kite Connect)
- Market data fetching
- Order placement and management
- Authentication with external services
- Quote and historical data retrieval

### 🚀 Initiation Service (`initiation_service`)
**Logs to**: debug.log, application.log, business.log, error.log, console

**Generates logs for:**
- Trade initiation decisions
- Signal processing and validation
- Entry point calculations
- Risk assessment before trade initiation

---

## Log Rotation Configuration

### 📋 Rotation Settings

| File | Max Size | Backup Count | Rotation Pattern |
|------|----------|--------------|------------------|
| debug.log | 10MB | 5 | debug.log.1, debug.log.2, ..., debug.log.5 |
| application.log | 10MB | 5 | application.log.1, application.log.2, ..., application.log.5 |
| business.log | 10MB | 5 | business.log.1, business.log.2, ..., business.log.5 |
| error.log | 10MB | 10 | error.log.1, error.log.2, ..., error.log.10 |

### 🔄 Rotation Behavior
- **Automatic**: Files rotate when they reach the size limit
- **Naming**: Newest backup is `.1`, oldest is `.{backupCount}`
- **Cleanup**: Old backups beyond the count limit are automatically deleted
- **No Downtime**: Rotation happens seamlessly without stopping the application

---

## Common Log Patterns

### 🔐 Authentication Flow
```
application.log & debug.log:
- JWT Middleware processing request
- Token extraction and validation
- User authentication success/failure
- Session management
```

### 📊 Business Operations
```
business.log:
- Trade session creation/termination
- Scanner algorithm results
- Risk assessment outcomes
- Portfolio updates
```

### ⚡ API Request Flow
```
debug.log: Detailed parameter validation
application.log: Request start/completion
error.log: Any failures or errors
```

### 🔍 Database Operations
```
debug.log: Query building, parameters, execution time
application.log: Operation completion status
error.log: Database connection or query failures
```

---

## Monitoring and Analysis Tips

### 📈 Performance Monitoring
- **debug.log**: Look for `execution_time_ms` entries
- **application.log**: Monitor API response patterns
- **error.log**: Track failure rates and types

### 🔍 Troubleshooting
1. **Start with error.log** for immediate issues
2. **Check application.log** for request flow context
3. **Use debug.log** for detailed technical investigation
4. **Review business.log** for trade-related issues

### 📊 Business Analytics
- **business.log**: Trade session success rates
- **business.log**: Scanner algorithm performance
- **business.log**: Risk management effectiveness

---

## Configuration Location

**File**: `algorithmic_trade_server/ats_base/settings.py`
**Section**: `LOGGING` dictionary (lines ~200-320)

To modify logging behavior, edit the handlers, loggers, and formatters in the Django settings file.

---

## Best Practices

### ✅ Do's
- Use appropriate log levels (DEBUG for development, INFO for business events)
- Include context information in log messages
- Use structured logging with key-value pairs
- Monitor log file sizes and rotation

### ❌ Don'ts
- Don't log sensitive information (passwords, API keys)
- Don't use DEBUG level in production for high-frequency operations
- Don't ignore ERROR level logs
- Don't disable log rotation

---

*Last Updated: June 20, 2025*
*Application Version: ATS v1.0* 