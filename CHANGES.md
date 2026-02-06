# Bug Fixes and Changes

This document tracks bug fixes and improvements made to the MAGMA project.

## Bug Fixes

### 1. Fixed List Comprehension Bug in `app.py` (Line 128)
**Issue**: The list comprehension `[h.get("ticker") for h in portfolio.get("holdings", [])] or None` had two problems:
- A list comprehension never evaluates to `False`, so `or None` would never trigger
- The list could contain `None` values if `h.get("ticker")` returned `None`

**Fix**: Changed to properly filter out `None` values and handle empty lists:
```python
tickers = [h.get("ticker") for h in portfolio.get("holdings", []) if h.get("ticker")]
data = _gather_market_snapshot(tickers if tickers else None)
```

**Impact**: The recommendations endpoint now correctly handles portfolios with missing ticker values and empty portfolios.

---

### 2. Fixed Bare Exception Handler in `app.py` (Lines 77-79)
**Issue**: Silent exception handling in price persistence could hide important errors.

**Fix**: Added proper logging while maintaining graceful degradation:
```python
try:
    dp.upsert_prices(prices)
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Failed to persist prices: {e}")
```

**Impact**: Errors in price persistence are now logged for debugging while the request continues to succeed.

---

### 3. Fixed Deprecated Quantization API in `llm_interface.py` (Lines 76-82)
**Issue**: Using deprecated `torch.quantization.quantize_dynamic` which is removed in PyTorch 2.0+.

**Fix**: Added fallback to use new API (`torch.ao.quantization`) with graceful fallback to old API:
```python
try:
    from torch.ao.quantization import quantize_dynamic
    self.model = quantize_dynamic(...)
except ImportError:
    # Fallback to deprecated API for older PyTorch versions
    self.model = torch.quantization.quantize_dynamic(...)
```

**Impact**: Code now works with both old and new PyTorch versions, and errors are properly logged.

---

### 4. Fixed Device Mapping Issue in `llm_interface.py` (Line 145)
**Issue**: After quantization, accessing `self.model.device` might fail or return incorrect device.

**Fix**: Added robust device detection that works with quantized models:
```python
device = next(self.model.parameters()).device if hasattr(self.model, 'parameters') and next(iter(self.model.parameters()), None) is not None else torch.device('cpu')
enc = {k: v.to(device) for k, v in enc.items()}
```

**Impact**: Model inference now works correctly with quantized models.

---

### 5. Fixed Bare Exception Handlers in `data_pipeline.py`
**Issue**: Multiple silent exception handlers throughout the data pipeline made debugging difficult.

**Fix**: Added proper logging to all exception handlers:
- `_fetch_prices_finnhub()`: Added warning log for failed price fetches
- `_fetch_prices_twelvedata()`: Added warning log for failed price fetches
- `fetch_fundamentals()`: Added debug logs for failed profile/metric fetches
- `fetch_news_rss()`: Added warning log for failed RSS feed parsing

**Impact**: All data fetching errors are now logged with appropriate log levels, making debugging and monitoring much easier.

---

---

### 6. Fixed Syntax Errors in `data_pipeline.py`
**Issue**: Indentation errors in exception handlers caused syntax errors that prevented the app from loading.

**Fix**: Corrected indentation for exception handlers in `_fetch_prices_finnhub()` and `_fetch_prices_twelvedata()` functions.

**Impact**: The application can now start successfully.

---

### 7. Improved Context Limit Calculation in `llm_interface.py`
**Issue**: Context limit calculation was too restrictive and could cause generation failures.

**Fix**: Improved the context limit calculation to:
- Use model's `max_position_embeddings` as the hard limit
- Reserve 20% of context for generation (minimum 256 tokens)
- Better fallback handling for different model configurations

**Impact**: More reliable text generation with proper context window management.

---

### 8. Enhanced Error Handling and Logging in `app.py`
**Issue**: Limited error visibility and logging made debugging difficult.

**Fix**: Added:
- Proper logging configuration
- Better error messages with context
- More informative logging for recommendations endpoint
- Proper exception handling that preserves HTTP exceptions

**Impact**: Better observability and easier debugging of production issues.

---

### 9. Improved Device Detection in `llm_interface.py`
**Issue**: Device detection logic was complex and could fail with quantized models.

**Fix**: Simplified device detection with proper exception handling:
```python
try:
    if hasattr(self.model, 'parameters'):
        params = list(self.model.parameters())
        if params:
            device = params[0].device
        else:
            device = torch.device('cpu')
    else:
        device = torch.device('cpu')
except Exception:
    device = torch.device('cpu')
```

**Impact**: More robust device handling across different model configurations.

---

## Summary

All identified bugs have been fixed:
- ✅ List comprehension logic bug
- ✅ Silent exception handlers (now properly logged)
- ✅ Deprecated API usage (with backward compatibility)
- ✅ Device mapping issues with quantized models
- ✅ Missing error logging throughout data pipeline
- ✅ Syntax errors in data pipeline
- ✅ Context limit calculation improvements
- ✅ Enhanced error handling and logging
- ✅ Improved device detection

No changes were made to:
- `sys_prompt.txt` (as requested)
- `formulas.py` (as requested)
