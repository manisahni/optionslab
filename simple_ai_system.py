#!/usr/bin/env python3
"""
Simple AI System for OptionsLab
Provides AI strategy generation and analysis using Google Gemini
"""
import os
import json
import requests
from typing import Dict, List, Optional
import streamlit as st

class SimpleAISystem:
    """Simple AI system for options strategy generation and analysis"""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    def _load_api_key(self) -> Optional[str]:
        """Load API key from environment or Streamlit secrets"""
        # Try environment variable first
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            return api_key
        
        # Try Streamlit secrets
        try:
            if hasattr(st, 'secrets') and st.secrets:
                return st.secrets.get("GEMINI_API_KEY")
        except:
            pass
        
        return None
    
    def _save_api_key(self, api_key: str) -> bool:
        """Save API key to Streamlit secrets"""
        try:
            if hasattr(st, 'secrets'):
                st.secrets["GEMINI_API_KEY"] = api_key
                return True
        except:
            pass
        return False
    
    def is_configured(self) -> bool:
        """Check if AI system is properly configured"""
        return self.api_key is not None
    
    def generate_strategy(self, market_conditions: str, risk_tolerance: str, 
                         strategy_type: str) -> Dict:
        """Generate an options strategy using AI"""
        if not self.is_configured():
            return {"error": "AI system not configured. Please set your Gemini API key."}
        
        prompt = f"""
        Create an options trading strategy with the following requirements:
        
        Market Conditions: {market_conditions}
        Risk Tolerance: {risk_tolerance}
        Strategy Type: {strategy_type}
        
        Please provide:
        1. Strategy name and description
        2. Entry conditions
        3. Exit conditions
        4. Risk management rules
        5. Expected outcomes
        
        Format the response as a JSON object with these fields:
        - name: strategy name
        - description: detailed description
        - entry_conditions: list of entry criteria
        - exit_conditions: list of exit criteria
        - risk_management: risk management rules
        - expected_outcomes: expected results
        """
        
        try:
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and result["candidates"]:
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    # Try to parse as JSON, fallback to text
                    try:
                        return json.loads(content)
                    except:
                        return {
                            "name": f"AI Generated {strategy_type}",
                            "description": content,
                            "entry_conditions": ["AI generated"],
                            "exit_conditions": ["AI generated"],
                            "risk_management": "AI generated",
                            "expected_outcomes": "AI generated"
                        }
                else:
                    return {"error": "No response from AI model"}
            else:
                return {"error": f"API Error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def analyze_backtest(self, results: Dict) -> Dict:
        """Analyze backtest results using AI"""
        if not self.is_configured():
            return {"error": "AI system not configured. Please set your Gemini API key."}
        
        # Extract key metrics
        total_return = results.get("total_return", 0)
        sharpe_ratio = results.get("sharpe_ratio", 0)
        max_drawdown = results.get("max_drawdown", 0)
        win_rate = results.get("win_rate", 0)
        num_trades = results.get("num_trades", 0)
        
        prompt = f"""
        Analyze this options trading backtest performance:
        
        Performance Metrics:
        - Total Return: {total_return:.2%}
        - Sharpe Ratio: {sharpe_ratio:.2f}
        - Max Drawdown: {max_drawdown:.2%}
        - Win Rate: {win_rate:.2%}
        - Number of Trades: {num_trades}
        
        Please provide:
        1. Overall performance assessment
        2. Key strengths and weaknesses
        3. Risk analysis
        4. Recommendations for improvement
        5. Market conditions suitability
        
        Format as JSON with fields:
        - assessment: overall performance rating
        - strengths: list of positive aspects
        - weaknesses: list of areas for improvement
        - risk_analysis: risk assessment
        - recommendations: improvement suggestions
        - market_suitability: when this strategy works best
        """
        
        try:
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and result["candidates"]:
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    try:
                        return json.loads(content)
                    except:
                        return {
                            "assessment": "AI Analysis",
                            "strengths": ["AI generated analysis"],
                            "weaknesses": ["AI generated analysis"],
                            "risk_analysis": content,
                            "recommendations": ["AI generated"],
                            "market_suitability": "AI generated"
                        }
                else:
                    return {"error": "No response from AI model"}
            else:
                return {"error": f"API Error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def render_key_manager(self):
        """Render the API key management UI"""
        st.subheader("🔑 Gemini API Key Configuration")
        
        # Check if key is already set
        if self.is_configured():
            st.success("✅ API Key is configured")
            if st.button("🔑 Show API Key"):
                st.code(self.api_key[:10] + "..." + self.api_key[-4:])
            if st.button("🗑️ Clear API Key"):
                self.api_key = None
                st.rerun()
        else:
            st.warning("⚠️ API Key not configured")
            
            # API key input
            api_key = st.text_input(
                "Enter your Gemini API Key:",
                type="password",
                help="Get your API key from https://makersuite.google.com/app/apikey",
                key="gemini_api_key_input"
            )
            
            if st.button("💾 Save and Verify Key", key="save_api_key_btn"):
                if api_key:
                    # Test the key
                    test_result = self._test_api_key(api_key)
                    if test_result:
                        self.api_key = api_key
                        self._save_api_key(api_key)
                        st.success("✅ API Key saved and verified!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid API key. Please check and try again.")
                else:
                    st.error("❌ Please enter an API key")
    
    def _test_api_key(self, api_key: str) -> bool:
        """Test if the API key is valid"""
        try:
            response = requests.post(
                f"{self.base_url}?key={api_key}",
                json={
                    "contents": [{
                        "parts": [{"text": "Hello"}]
                    }]
                },
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

# Global instance
_ai_system = None

def get_ai_system() -> SimpleAISystem:
    """Get the global AI system instance"""
    global _ai_system
    if _ai_system is None:
        _ai_system = SimpleAISystem()
    return _ai_system 