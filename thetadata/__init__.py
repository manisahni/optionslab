"""
ThetaData Python Client Library

A comprehensive Python client for ThetaData Terminal API that provides both
synchronous and asynchronous interfaces to real-time and historical market data.

Connects to locally running ThetaData Terminal for seamless data access.

Quick Start:
    >>> from thetadata import ThetaDataTerminalClient
    >>> 
    >>> # Synchronous usage
    >>> client = ThetaDataTerminalClient()
    >>> expirations = client.list_option_expirations_sync("AAPL")
    >>> strikes = client.list_option_strikes_sync("AAPL", "20250117")
    >>> 
    >>> # Asynchronous usage
    >>> async def get_data():
    >>>     async with ThetaDataTerminalClient() as client:
    >>>         expirations = await client.list_option_expirations("AAPL")
    >>>         quote = await client.get_option_quote_snapshot("AAPL", "20250117", 200.0, "C")
"""

from .client import ThetaDataTerminalClient, ThetaDataClient
from .rest import ThetaDataRESTClient, RESTClient
from .stream import StreamClient
from .models import (
    Contract,
    Quote, 
    Trade,
    OHLC,
    Greeks,
    StreamMessage,
    PaginatedResponse,
    SubscriptionRequest,
    ErrorResponse,
    OptionRight,
    SecurityType,
    StreamMessageType,
)from .exceptions import (
    ThetaDataError,
    AuthenticationError,
    RateLimitError,
    ConnectionError,
    ResponseError,
    ValidationError,
    StreamError,
)

# Version info
__version__ = "0.1.0"
__author__ = "ThetaData Python Client"
__description__ = "Python client library for ThetaData Terminal API"

# Main exports - use the most specific names
__all__ = [
    # Main client classes
    "ThetaDataTerminalClient",  # Primary class - connects to local Terminal
    "ThetaDataRESTClient",      # REST-only client
    "StreamClient",             # WebSocket-only client
    
    # Backwards compatibility aliases
    "ThetaDataClient",          # Alias for ThetaDataTerminalClient
    "RESTClient",               # Alias for ThetaDataRESTClient
    
    # Data models
    "Contract",
    "Quote",
    "Trade", 
    "OHLC",
    "Greeks",
    "StreamMessage",
    "PaginatedResponse",
    "SubscriptionRequest",
    "ErrorResponse",
    
    # Enums
    "OptionRight",
    "SecurityType", 
    "StreamMessageType",
    
    # Exceptions
    "ThetaDataError",
    "AuthenticationError",
    "RateLimitError",
    "ConnectionError",
    "ResponseError",
    "ValidationError",
    "StreamError",
    
    # Package metadata
    "__version__",
    "__author__",
    "__description__",
]

# Configure logging
import logging

# Set up a null handler to prevent "No handler" warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Helpful constants for users
TERMINAL_DEFAULT_HOST = "localhost"
TERMINAL_DEFAULT_PORT = 25510

# Common option rights for convenience
CALL = "C"
PUT = "P"
