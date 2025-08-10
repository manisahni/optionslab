"""
API Key Management and Connection Validation Module

This module provides secure storage, validation, and management of API keys
for the 0DTE trading application.
"""

import os
import json
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv, set_key
import openai
from datetime import datetime

logger = logging.getLogger(__name__)

class APIManager:
    """Manages API keys and connections for the trading application"""
    
    def __init__(self, env_path: str = ".env"):
        """
        Initialize API Manager
        
        Args:
            env_path: Path to .env file
        """
        self.env_path = Path(env_path)
        self.load_environment()
        
    def load_environment(self):
        """Load environment variables from .env file"""
        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.info(f"Loaded environment from {self.env_path}")
        else:
            logger.warning(f"No .env file found at {self.env_path}")
    
    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Retrieve an API key from environment
        
        Args:
            key_name: Name of the API key (e.g., 'OPENAI_API_KEY')
            
        Returns:
            API key value or None if not found
        """
        key = os.getenv(key_name)
        if not key:
            logger.warning(f"API key '{key_name}' not found in environment")
        return key
    
    def set_api_key(self, key_name: str, key_value: str) -> bool:
        """
        Save an API key to .env file
        
        Args:
            key_name: Name of the API key
            key_value: Value of the API key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create .env file if it doesn't exist
            if not self.env_path.exists():
                self.env_path.touch()
                logger.info(f"Created new .env file at {self.env_path}")
            
            # Set the key
            set_key(str(self.env_path), key_name, key_value)
            logger.info(f"Successfully saved {key_name}")
            
            # Reload environment
            self.load_environment()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save API key: {e}")
            return False
    
    def validate_openai_connection(self) -> Tuple[bool, str]:
        """
        Test OpenAI API connection
        
        Returns:
            Tuple of (success, message)
        """
        api_key = self.get_api_key("OPENAI_API_KEY")
        
        if not api_key:
            return False, "OpenAI API key not found. Please set OPENAI_API_KEY in .env file"
        
        try:
            # Initialize the OpenAI client with v1.0+ API
            from openai import OpenAI
            
            client = OpenAI(api_key=api_key)
            
            # Try a simple API call
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            return True, "OpenAI API connection successful"
            
        except Exception as e:
            error_msg = str(e)
            if "Invalid" in error_msg or "Incorrect" in error_msg:
                return False, "Invalid OpenAI API key"
            elif "rate_limit" in error_msg.lower():
                return False, "OpenAI API rate limit exceeded"
            else:
                return False, f"OpenAI API connection failed: {error_msg}"
    
    def validate_ib_connection(self) -> Tuple[bool, str]:
        """
        Test Interactive Brokers connection
        
        Returns:
            Tuple of (success, message)
        """
        try:
            from ib_insync import IB
            
            # Get connection parameters
            host = os.getenv("IB_GATEWAY_HOST", "localhost")
            port = int(os.getenv("IB_GATEWAY_PORT", "4002"))
            client_id = int(os.getenv("IB_CLIENT_ID", "1"))
            
            # Try to connect
            ib = IB()
            ib.connect(host, port, clientId=client_id, timeout=10)
            
            if ib.isConnected():
                # Get account info to verify connection
                account_values = ib.accountValues()
                ib.disconnect()
                return True, f"IB Gateway connection successful (Connected to {host}:{port})"
            else:
                return False, "Failed to connect to IB Gateway"
                
        except ImportError:
            return False, "ib_insync not installed. Run: pip install ib_insync"
        except ConnectionRefusedError:
            return False, f"IB Gateway not running on {host}:{port}. Please start TWS or IB Gateway"
        except Exception as e:
            return False, f"IB connection failed: {str(e)}"
    
    def validate_all_connections(self) -> Dict[str, Tuple[bool, str]]:
        """
        Validate all API connections
        
        Returns:
            Dictionary of connection results
        """
        results = {}
        
        # Test OpenAI
        results['openai'] = self.validate_openai_connection()
        
        # Test IB (optional)
        if os.getenv("IB_GATEWAY_HOST") or os.getenv("IB_GATEWAY_PORT"):
            results['interactive_brokers'] = self.validate_ib_connection()
        else:
            results['interactive_brokers'] = (None, "IB connection not configured")
        
        return results
    
    def get_connection_status(self) -> str:
        """
        Get formatted connection status report
        
        Returns:
            Formatted status string
        """
        results = self.validate_all_connections()
        
        status = "API Connection Status\n"
        status += "=" * 50 + "\n\n"
        
        for api, (success, message) in results.items():
            if success is None:
                icon = "⚪"  # Not configured
            elif success:
                icon = "✅"  # Connected
            else:
                icon = "❌"  # Failed
                
            status += f"{icon} {api.replace('_', ' ').title()}: {message}\n"
        
        status += "\n" + "=" * 50 + "\n"
        status += f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return status
    
    def mask_api_key(self, key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display
        
        Args:
            key: API key to mask
            visible_chars: Number of characters to show at start and end
            
        Returns:
            Masked key
        """
        if not key or len(key) <= visible_chars * 2:
            return "*" * 8
        
        return f"{key[:visible_chars]}...{key[-visible_chars:]}"
    
    def list_configured_apis(self) -> Dict[str, str]:
        """
        List all configured API keys (masked)
        
        Returns:
            Dictionary of API names and masked keys
        """
        apis = {
            "OPENAI_API_KEY": self.get_api_key("OPENAI_API_KEY"),
            "IB_GATEWAY_HOST": os.getenv("IB_GATEWAY_HOST"),
            "IB_GATEWAY_PORT": os.getenv("IB_GATEWAY_PORT"),
        }
        
        configured = {}
        for name, value in apis.items():
            if value:
                if "KEY" in name:
                    configured[name] = self.mask_api_key(value)
                else:
                    configured[name] = value
        
        return configured