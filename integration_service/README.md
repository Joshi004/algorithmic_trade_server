# Integration Service

This Django app is responsible for handling all interactions with broker APIs and sending back responses.

## Environment Variables

The following environment variables are required for this app to function properly:

```
# Broker integration settings
BROKER_ENCRYPTION_SECRET=your_secret_key
```

You can set these variables in a `.env` file in the root directory of the project, or in your environment.

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
      "status": "active"
    }
  }
  ```

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