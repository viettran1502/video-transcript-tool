"""
Shared Whisper Model Manager — singleton with background loading.

All extractors share a single Whisper model instance, loaded in a background
thread so that constructors return instantly.

Usage:
    from whisper_manager import preload_model, require_model
    preload_model('small')          # fire-and-forget (non-blocking)
    model = require_model('small')  # blocks until ready
"""

import threading
import logging
from concurrent.futures import ThreadPoolExecutor, Future

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=1)
_model_name: str | None = None
_model_future: Future | None = None
_model = None


def _load_model(name: str):
    """Load a Whisper model (runs in background thread)."""
    import whisper
    logger.info(f"Loading Whisper model: {name}")
    model = whisper.load_model(name)
    logger.info(f"Whisper model '{name}' loaded successfully!")
    return model


def preload_model(name: str) -> None:
    """Start loading *name* in the background (non-blocking, fire-and-forget)."""
    global _model_name, _model_future, _model

    with _lock:
        # Already loaded or loading the same model — nothing to do.
        if _model_name == name and (_model is not None or _model_future is not None):
            return

        _model_name = name
        _model = None
        _model_future = _executor.submit(_load_model, name)


def require_model(name: str):
    """Return the loaded model, blocking if the background load is still in progress.

    If no preload was started or a *different* model is requested, this will
    load synchronously.
    """
    global _model_name, _model_future, _model

    with _lock:
        # Fast path: already resolved.
        if _model is not None and _model_name == name:
            return _model

        # A preload is in progress for the right model — wait on it.
        if _model_future is not None and _model_name == name:
            future = _model_future
        else:
            # Either no preload, or different model requested — load now.
            _model_name = name
            _model_future = _executor.submit(_load_model, name)
            future = _model_future

    # Wait outside the lock so other threads aren't blocked.
    try:
        result = future.result()
    except Exception as e:
        logger.error(f"Failed to load Whisper model '{name}': {e}")
        with _lock:
            _model_future = None
        return None

    with _lock:
        _model = result
        _model_future = None
    return result
