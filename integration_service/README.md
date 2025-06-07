# Integration Service

This Django app is responsible for handling all interactions with broker APIs and sending back responses.

## Environment Variables

The following environment variables are required for this app to function properly:

```
# Broker integration settings
BROKER_API_ENCRYPTION_SECRET=your_secret_key
```

You can set these variables in a `.env` file in the root directory of the project, or in your environment.

## Credential Lifecycle & Validation

### Registration Flow
1. **Register Broker** (`/register_broker/`) - Creates credentials with `pending_verification` status
2. **Get Login URL** - User gets Zerodha login URL and completes OAuth flow
3. **Set Session** (`/set_session/`) - Exchanges request token for access token
   - **Validates credentials** automatically by testing with Zerodha API
   - **Updates status** to `active` if successful, `pending_verification` if failed
4. **Ready for Trading** - Credentials with `active` status can be used for API calls

### Status Values
- `pending_verification` - Initial status, awaiting session setup or failed validation
- `active` - Validated through successful session creation

### Automatic Validation
When a user calls the `set_session` API with a request token, the system automatically:

1. **Exchanges tokens** with Zerodha using `generate_session()`
2. **Validates credentials** implicitly (if API call succeeds, credentials are valid)
3. **Updates status** based on result:
   - ✅ Success → `active` 
   - ❌ Failure → `pending_verification`
4. **Saves encrypted access token** for future use

This approach is **more reliable** than separate validation calls because it uses the actual authentication flow.

## API Endpoints

### Register Broker

- **URL**: `/integration/register_broker/`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "user_id": "123",
    "broker_name": "zerodha",
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "data": {
      "credential_id": 1,
      "broker_name": "zerodha",
      "is_default": true,
      "status": "pending_verification"
    }
  }
  ```

### Set Session (Zerodha Authentication)

- **URL**: `/integration/set_session/`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "request_token": "your_request_token",
    "user_id": "123"
  }
  ```
- **Response**:
  ```json
  {
    "avatar_url": "https://...",
    "email": "user@example.com",
    "user_id": "XYZ123",
    "user_name": "John Doe",
    "exchanges": ["NSE", "BSE"],
    "order_types": ["MARKET", "LIMIT"],
    "products": ["CNC", "MIS"]
  }
  ```

**Note**: This API validates credentials and updates status to `active` if successful.

### Get User Brokers

- **URL**: `/integration/get_user_brokers/`
- **Method**: GET
- **Query Parameters**: `user_id=123`
- **Response**:
  ```json
  {
    "status": "success",
    "data": [
      {
        "credential_id": 1,
        "broker_name": "zerodha",
        "is_default": true,
        "status": "active",
        "created_at": "2023-05-27T04:33:05-0500"
      }
    ],
    "meta": {
      "count": 1
    }
  }
  ```

### Set Default Broker

- **URL**: `/integration/set_default_broker/`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "user_id": "123",
    "credential_id": 1
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "data": {
      "credential_id": 1,
      "broker_name": "zerodha",
      "is_default": true
    }
  }
  ```

## Security Features

### Encryption
All sensitive credential fields are encrypted before storage:
- `api_key` - Broker API key
- `api_secret` - Broker API secret  
- `access_token` - Trading access token

### Validation
- **Set Session API**: Validates credentials during OAuth token exchange with Zerodha
- **Real Authentication Flow**: Uses actual `generate_session()` calls rather than test API calls
- **Automatic Status Updates**: Credentials marked as `active` when session creation succeeds

### Audit Trail
- `last_refreshed_at` - Timestamp of successful session creation
- `validation_error` - Error message if session creation fails
- `last_used_at` - Timestamp of last trading activity 