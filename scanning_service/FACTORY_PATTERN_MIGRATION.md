# Scanner Factory Pattern Migration Guide

## Overview

The scanner factory has been refactored to use a more flexible pattern that separates object creation from configuration. This guide explains the changes and how to migrate existing code.

## What Changed

### ❌ Old Pattern (Deprecated)

```python
# Factory required all parameters upfront
scanner = factory.get_scanner(
    scanning_algo_name="udts",
    tracking_algo_name="udts_slto", 
    trade_freq="5minute",
    user_id="user_123",
    integration_provider=integration_provider,
    tmu_provider=tmu_provider,
    trade_session_id="session_456"
)

# Scanner was ready to use immediately
scanner.fetch_instrument_tokens_and_start_tracking("user_123", is_dummy=False)
```

### ✅ New Pattern (Recommended)

```python
# Factory only needs algorithm name
scanner = factory.get_scanner("udts")

# Configure separately with required parameters
scanner.configure(
    trade_freq="5minute",
    user_id="user_123", 
    trade_session_id="session_456"
)

# Now ready to use
scanner.fetch_instrument_tokens_and_start_tracking("user_123", is_dummy=False)
```

## Benefits of New Pattern

### 🎯 **Flexible Factory Interface**
- Factory signature doesn't change when adding new scanner types
- Each scanner can accept different configuration parameters
- No unused parameters passed to scanners

### 🚀 **Lazy Dependency Loading**
- Dependencies imported only when `configure()` is called
- Faster factory instantiation
- Better memory usage

### 🔧 **Easy Extension**
```python
# Adding a new scanner doesn't require factory changes
class VolumeScanner(BaseScannerInterface):
    def configure(self, trade_freq, volume_threshold, **kwargs):
        # Only imports what it needs
        from volume_service import VolumeAnalyzer
        self.analyzer = VolumeAnalyzer(volume_threshold)
```

### 🧪 **Better Testing**
```python
# Easy to test with custom configuration
scanner = factory.get_scanner("udts")
scanner.configure(
    trade_freq="5minute",
    integration_provider=mock_provider  # Easy to inject mocks
)
```

## Migration Steps

### 1. Update Factory Usage

**Before:**
```python
scanner = factory.get_scanner(
    scanning_algo_name="udts",
    tracking_algo_name="udts_slto",
    trade_freq="5minute", 
    user_id=user_id,
    trade_session_id=trade_session_id
)
```

**After:**
```python
scanner = factory.get_scanner("udts")
scanner.configure(
    trade_freq="5minute",
    user_id=user_id,
    trade_session_id=trade_session_id
)
```

### 2. Update Scanner Implementations

**Before:**
```python
class MyScanner(BaseScannerInterface):
    def __init__(self, trade_freq, user_id, trade_session_id):
        super().__init__(trade_freq, user_id, trade_session_id)
        self.provider = SomeProvider(user_id)
```

**After:**
```python
class MyScanner(BaseScannerInterface):
    def __init__(self):
        super().__init__()
        self.provider = None
    
    def configure(self, trade_freq, user_id=None, trade_session_id=None, **kwargs):
        super().configure(trade_freq, user_id, trade_session_id, **kwargs)
        from some_service import SomeProvider
        self.provider = SomeProvider(user_id)
```

### 3. Add Configuration Checks

```python
def scan_method(self):
    self._ensure_configured()  # Ensure scanner is ready
    # ... scanning logic
```

## Error Handling

### Configuration Validation

```python
try:
    scanner = factory.get_scanner("udts")
    scanner.configure(trade_freq="5minute", user_id="user_123")
    scanner.start_scanning()
except RuntimeError as e:
    print(f"Scanner not configured: {e}")
```

### Dependency Import Errors

```python
def configure(self, **kwargs):
    try:
        from external_service import ExternalProvider
        self.provider = ExternalProvider()
    except ImportError:
        raise RuntimeError("External service not available")
```

## Common Patterns

### 1. Scanner with Custom Dependencies

```python
class MLScanner(BaseScannerInterface):
    def configure(self, trade_freq, model_path, threshold=0.8, **kwargs):
        super().configure(trade_freq, **kwargs)
        
        # Import ML dependencies only when needed
        from ml_service import ModelPredictor
        self.predictor = ModelPredictor(model_path)
        self.threshold = threshold

# Usage:
scanner = factory.get_scanner("ml_scanner")
scanner.configure(
    trade_freq="5minute",
    model_path="/models/trend_predictor.pkl",
    threshold=0.9
)
```

### 2. Scanner with External APIs

```python
class NewsScanner(BaseScannerInterface):
    def configure(self, trade_freq, api_key, sentiment_threshold=-0.1, **kwargs):
        super().configure(trade_freq, **kwargs)
        
        from news_service import NewsAPI
        self.news_api = NewsAPI(api_key)
        self.sentiment_threshold = sentiment_threshold

# Usage:
scanner = factory.get_scanner("news_scanner")
scanner.configure(
    trade_freq="5minute",
    api_key="your-api-key",
    sentiment_threshold=-0.2
)
```

### 3. Scanner with Multiple Data Sources

```python
class HybridScanner(BaseScannerInterface):
    def configure(self, trade_freq, enable_news=True, enable_social=False, **kwargs):
        super().configure(trade_freq, **kwargs)
        
        # Conditional imports based on configuration
        if enable_news:
            from news_service import NewsProvider
            self.news_provider = NewsProvider()
            
        if enable_social:
            from social_service import SocialProvider  
            self.social_provider = SocialProvider()

# Usage:
scanner = factory.get_scanner("hybrid_scanner")
scanner.configure(
    trade_freq="5minute",
    enable_news=True,
    enable_social=True
)
```

## Testing Examples

### Unit Testing Scanners

```python
def test_udts_scanner_configuration():
    factory = ScannerAlgoFactory()
    scanner = factory.get_scanner("udts")
    
    # Test unconfigured state
    assert not scanner.is_configured()
    
    # Test configuration
    scanner.configure(trade_freq="5minute", user_id="test_user")
    assert scanner.is_configured()
    assert scanner.trade_frequency == "5minute"

def test_scanner_with_mocks():
    scanner = factory.get_scanner("udts")
    
    # Mock providers
    mock_integration = Mock()
    mock_tmu = Mock()
    
    scanner.configure(
        trade_freq="5minute",
        integration_provider=mock_integration,
        tmu_provider=mock_tmu
    )
    
    # Test scanner uses mocked providers
    scanner.fetch_instruments_from_db()
    mock_tmu.fetch_instruments.assert_called_once()
```

### Integration Testing

```python
def test_full_scanner_lifecycle():
    # Create and configure scanner
    scanner = factory.get_scanner("udts")
    scanner.configure(
        trade_freq="5minute",
        user_id="integration_test_user",
        trade_session_id="test_session"
    )
    
    # Verify configuration
    assert scanner.is_configured()
    
    # Test scanning (would use test data)
    scanner.fetch_instrument_tokens_and_start_tracking("test_user", is_dummy=True)
    
    # Cleanup
    scanner.stop_scanning()
```

## Backward Compatibility

⚠️ **Breaking Changes**: The old factory signature is no longer supported. 

**Migration Timeline**:
1. ✅ All scanners updated to new pattern
2. ✅ Consumer updated to use new pattern  
3. ✅ Tests updated to new pattern
4. ❌ Old factory signature removed

## Best Practices

### 1. Always Check Configuration
```python
def start_scanning(self):
    self._ensure_configured()
    # ... scanning logic
```

### 2. Validate Configuration Parameters
```python
def configure(self, trade_freq, **kwargs):
    if trade_freq not in SUPPORTED_FREQUENCIES:
        raise ValueError(f"Unsupported frequency: {trade_freq}")
    super().configure(trade_freq, **kwargs)
```

### 3. Handle Import Errors Gracefully
```python
def configure(self, **kwargs):
    try:
        from optional_service import OptionalProvider
        self.optional_provider = OptionalProvider()
    except ImportError:
        log("Optional service not available, using fallback", level="warning")
        self.optional_provider = None
```

### 4. Document Configuration Parameters
```python
def configure(self, trade_freq: str, user_id: str = None, 
              custom_threshold: float = 0.8, **kwargs):
    """
    Configure the scanner.
    
    Args:
        trade_freq: Trading frequency (required)
        user_id: User identifier (optional)
        custom_threshold: Custom analysis threshold (default: 0.8)
        **kwargs: Additional configuration parameters
    """
```

This new pattern provides much better flexibility and maintainability for the scanner system! 🚀 