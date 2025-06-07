# Security Configuration Guide

This document explains all security-related environment variables used in the ATS (Algorithmic Trading System) and how to configure them properly.

## Overview

The ATS uses multiple encryption keys and secrets for different security purposes:
- **Django Secret Key**: Framework-level security for sessions, CSRF, etc.
- **JWT Tokens**: Authentication tokens for API access
- **Broker API Encryption**: Protects sensitive trading credentials

## Environment Variables

### 1. Django Framework Security

#### `DJANGO_SECRET_KEY`
- **Purpose**: Django framework security (sessions, CSRF, cookies)
- **Length**: 50+ characters recommended
- **Example**: `prod-django-secret-key-change-in-production-make-it-50-chars-long`
- **Used By**: Django framework automatically
- **Production**: MUST be changed from default value

```yaml
# docker-compose.yml
- DJANGO_SECRET_KEY=your-unique-50-character-secret-key-for-production
```

### 2. JWT Authentication

#### `JWT_LONG_LIVED_TOKEN_SECRET`
- **Purpose**: Signs Long Lived Tokens (24 hours) for refresh operations
- **Length**: 32+ characters recommended  
- **Example**: `jwt-llt-secret-key-32-chars-change-this`
- **Used By**: `ats_gateway/utils/jwt_utils.py`
- **Security**: Used for token refresh, not direct API access

#### `JWT_SHORT_LIVED_TOKEN_SECRET`
- **Purpose**: Signs Short Lived Tokens (15 minutes) for API access
- **Length**: 32+ characters recommended
- **Example**: `jwt-slt-secret-key-32-chars-change-this`  
- **Used By**: `ats_gateway/utils/jwt_utils.py`
- **Security**: Used for actual API authentication

```yaml
# docker-compose.yml
- JWT_LONG_LIVED_TOKEN_SECRET=your-secure-llt-signing-key-32-characters
- JWT_SHORT_LIVED_TOKEN_SECRET=your-secure-slt-signing-key-32-characters
```

### 3. Broker API Credentials Protection

#### `BROKER_API_ENCRYPTION_SECRET`
- **Purpose**: Encrypts/decrypts broker API secrets in database
- **Length**: 32+ characters recommended
- **Example**: `broker-encryption-key-32-chars-change-this-for-production`
- **Used By**: `integration_service/lib/broker/broker_service.py`
- **Security**: Protects trading API credentials (Zerodha, Upstox, etc.)
- **Fallback**: If not set, API secrets stored in plain text (development only)

```yaml
# docker-compose.yml  
- BROKER_API_ENCRYPTION_SECRET=your-strong-encryption-key-for-broker-apis
```

## Security Levels by Environment

### Development Environment
- Default fallback keys are acceptable
- Focus on functionality over security
- Encryption is optional but recommended

### Production Environment
- ALL keys MUST be changed from defaults
- Keys should be generated using secure random methods
- Broker encryption MUST be enabled
- Regular key rotation recommended

## Key Generation

### Generate Secure Keys

```bash
# For Django Secret Key (50 characters)
python -c "import secrets; print(secrets.token_urlsafe(50))"

# For JWT Keys (32 characters)  
python -c "import secrets; print(secrets.token_urlsafe(32))"

# For Broker Encryption (32 characters)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Example Production Configuration

```yaml
# docker-compose.yml - Production Example
environment:
  # Django Framework
  - DJANGO_SECRET_KEY=kJ8mN2pQ5rS7tU9vW1xY3zA6bC8dE0fG2hI4jK6lM8nO0pR2sT4uV6wX8yZ1aB3c
  
  # JWT Authentication  
  - JWT_LONG_LIVED_TOKEN_SECRET=aB3cD5eF7gH9iJ1kL3mN5oP7qR9sT1uV3wX5yZ7aB9cD
  - JWT_SHORT_LIVED_TOKEN_SECRET=cD5eF7gH9iJ1kL3mN5oP7qR9sT1uV3wX5yZ7aB9cD1eF
  
  # Broker API Protection
  - BROKER_API_ENCRYPTION_SECRET=eF7gH9iJ1kL3mN5oP7qR9sT1uV3wX5yZ7aB9cD1eF3gH
```

## Implementation Status

| Component | Environment Variable | Status | Default Fallback |
|-----------|---------------------|---------|------------------|
| Django Security | `DJANGO_SECRET_KEY` | ✅ Implemented | Development key |
| JWT Long Lived | `JWT_LONG_LIVED_TOKEN_SECRET` | ✅ Implemented | `ABCD1234` |
| JWT Short Lived | `JWT_SHORT_LIVED_TOKEN_SECRET` | ✅ Implemented | `9876ZYXW` |
| Broker Encryption | `BROKER_API_ENCRYPTION_SECRET` | ✅ Implemented | Plain text storage |

## Security Audit Checklist

### Before Production Deployment

- [ ] All environment variables set to unique, secure values
- [ ] No default/fallback keys used in production
- [ ] Broker API encryption enabled and tested
- [ ] JWT keys are different from each other
- [ ] Keys are at least 32 characters long
- [ ] Keys stored securely (not in code repository)

### Regular Security Maintenance

- [ ] Rotate keys every 6-12 months
- [ ] Monitor logs for encryption/decryption errors
- [ ] Verify broker credentials are encrypted in database
- [ ] Test JWT token generation and validation
- [ ] Review access logs for suspicious activity

## Troubleshooting

### Common Issues

1. **"BROKER_API_ENCRYPTION_SECRET environment variable is not set"**
   - Set the environment variable in docker-compose.yml
   - Restart the affected services

2. **JWT token validation failures**
   - Verify JWT secret keys match between services
   - Check token expiration times
   - Ensure keys haven't been changed without restart

3. **Broker credentials not encrypting**
   - Check BROKER_API_ENCRYPTION_SECRET is set
   - Verify logs for encryption success/failure messages
   - Test with a new broker registration

### Verification Commands

```bash
# Check if encryption is working
docker exec -it ats-django-app python manage.py shell -c "
from integration_service.lib.broker.broker_service import BrokerService;
service = BrokerService();
try:
    service._get_encryption_key();
    print('✅ Broker encryption configured')
except:
    print('❌ Broker encryption not configured')
"

# Verify JWT configuration
docker exec -it ats-django-app python manage.py shell -c "
from ats_gateway.utils.jwt_utils import LLT_SECRET_KEY, SLT_SECRET_KEY;
print('LLT Key configured:', 'ABCD1234' != LLT_SECRET_KEY);
print('SLT Key configured:', '9876ZYXW' != SLT_SECRET_KEY);
"
```

## Migration Notes

### From Hardcoded to Environment Variables

If upgrading from hardcoded keys:

1. Set environment variables in docker-compose.yml
2. Restart all services
3. Existing JWT tokens will become invalid (users need to re-login)
4. Existing broker credentials will need re-encryption if encryption is enabled

### Database Migration for Broker Encryption

When enabling broker encryption for the first time:

1. Existing plain text API secrets will remain as-is
2. New registrations will be encrypted
3. To encrypt existing credentials, run a data migration script (not included)

---

**Security Note**: Never commit actual production keys to version control. Use environment variables or secure secret management systems. 