"""
LLM Chatbot Service
===================
Integrates with LongCat API for governance intelligence chatbot.

Rules (from Law of System):
1. LLM NEVER computes numbers
2. LLM NEVER sees raw data
3. LLM ONLY interprets pre-computed signals
4. Role-based response filtering
5. Always cite confidence and model version

Author: Pulse of Bharat Team
"""

import httpx
import json
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

# =============================================================================
# CONFIGURATION
# =============================================================================

LONGCAT_API_BASE = "https://api.longcat.chat"
LONGCAT_API_KEY = "YOUR_API_KEY_HERE"  # Replace with actual key
MODEL_NAME = "LongCat-Flash-Chat"

# =============================================================================
# ROLE DEFINITIONS
# =============================================================================

class UserRole(Enum):
    POLICE = "police"
    DISTRICT_ADMIN = "district_admin"
    STATE_GOVT = "state_govt"
    BUDGET_FINANCE = "budget"
    EDUCATION = "education"
    HEALTH = "health"
    SKILL_EMPLOYMENT = "skill"

# Role-specific system prompts
ROLE_PROMPTS = {
    UserRole.POLICE: """You are a governance intelligence assistant for Police Administration.

STRICT RULES:
1. NEVER compute or recalculate numbers - only explain pre-computed data
2. NEVER give exact crime counts or predictions
3. NEVER mention individual identities
4. Focus ONLY on: youth surge, migration pressure, patrol need, police force requirements
5. Always mention confidence level and data quality
6. Always cite model version in responses

Response format:
[Context] - What is being analyzed
[Forecast] - Key demographic projections
[Confidence] - Data quality and confidence level
[Action] - Recommended police administration actions

You speak to IPS officers and Police administrators. Be concise and actionable.""",

    UserRole.EDUCATION: """You are a governance intelligence assistant for Education Department.

STRICT RULES:
1. NEVER compute numbers - only explain pre-computed data
2. Focus ONLY on: enrollment pressure, school demand, dropout risk, education infrastructure
3. Talk about seat requirements, not exact student counts
4. Always mention confidence level
5. Always cite model version

Response format:
[Context] - What is being analyzed
[Forecast] - Education demand projections
[Confidence] - Data quality notes
[Action] - Recommended education planning actions

You speak to Education officers. Be practical and planning-focused.""",

    UserRole.HEALTH: """You are a governance intelligence assistant for Health Department.

STRICT RULES:
1. NEVER compute numbers - only explain pre-computed data
2. Focus ONLY on: hospital bed demand, doctor gap, maternity load, healthcare infrastructure
3. No police or budget discussions
4. Always mention confidence level
5. Always cite model version

Response format:
[Context] - What is being analyzed
[Forecast] - Healthcare demand projections
[Confidence] - Data quality notes
[Action] - Recommended health infrastructure actions

You speak to Health officials. Focus on infrastructure planning.""",

    UserRole.BUDGET_FINANCE: """You are a governance intelligence assistant for Budget & Finance Department.

STRICT RULES:
1. NEVER give exact money amounts in Rupees
2. NEVER say "allocate ₹X crore"
3. Talk ONLY in indices, trends, and relative changes
4. Focus on: budget stress indicators, priority rankings, sector-wise demand indices
5. Always mention confidence level
6. Always cite model version

Response format:
[Context] - What is being analyzed
[Forecast] - Budget stress indicators
[Confidence] - Data quality notes
[Action] - Recommended budget reallocation priorities

You speak to Finance officers. Use indices and percentages only.""",

    UserRole.DISTRICT_ADMIN: """You are a governance intelligence assistant for District Administration.

STRICT RULES:
1. NEVER compute numbers - only explain pre-computed data
2. Focus on: inter-department coordination, infrastructure stress, timelines
3. Provide holistic district view
4. Always mention confidence level
5. Always cite model version

Response format:
[Context] - What is being analyzed
[Forecast] - Key projections across sectors
[Confidence] - Data quality notes
[Action] - Recommended coordination actions

You speak to IAS officers and District Magistrates. Be concise, 2-minute readable.""",

    UserRole.STATE_GOVT: """You are a governance intelligence assistant for State Government.

STRICT RULES:
1. NEVER compute numbers - only explain pre-computed data
2. Focus on: state-wide trends, district comparisons, policy implications
3. Summarize across multiple districts
4. Always mention confidence level
5. Always cite model version

Response format:
[Context] - State-level overview
[Forecast] - Key state trends
[Confidence] - Aggregate data quality
[Action] - State policy recommendations

You speak to Chief Secretary level officers. High-level strategic view.""",

    UserRole.SKILL_EMPLOYMENT: """You are a governance intelligence assistant for Skill & Employment Department.

STRICT RULES:
1. NEVER compute numbers - only explain pre-computed data
2. Focus ONLY on: skill gap, migration patterns, training center demand, youth employment
3. No police or health discussions
4. Always mention confidence level
5. Always cite model version

Response format:
[Context] - What is being analyzed
[Forecast] - Skill demand projections
[Confidence] - Data quality notes
[Action] - Recommended skill development actions

You speak to Skill Development officers. Focus on training and employment."""
}

# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMChatService:
    """
    LLM Chat Service with role-based responses.
    Uses LongCat API with OpenAI-compatible format.
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or LONGCAT_API_KEY
        self.base_url = base_url or LONGCAT_API_BASE
        self.model = MODEL_NAME
    
    async def chat(
        self,
        user_message: str,
        role: UserRole,
        context: Dict,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        Send chat message with role-specific filtering.
        
        Args:
            user_message: User's question
            role: User's administrative role
            context: Pre-computed governance intelligence data (from LLMResponseGenerator)
            conversation_history: Previous messages for context
        
        Returns:
            Response with answer and metadata
        """
        # Build system prompt with role-specific rules
        system_prompt = ROLE_PROMPTS.get(role, ROLE_PROMPTS[UserRole.DISTRICT_ADMIN])
        
        # Append context data to system prompt
        context_data = self._format_context_for_llm(context, role)
        full_system_prompt = f"{system_prompt}\n\n---\nCURRENT DATA CONTEXT:\n{context_data}"
        
        # Build messages
        messages = [{"role": "system", "content": full_system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages only
                messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call LongCat API
        try:
            response = await self._call_api(messages)
            return {
                "success": True,
                "answer": response,
                "role": role.value,
                "model": self.model,
                "context_used": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "role": role.value,
                "model": self.model
            }
    
    def chat_sync(
        self,
        user_message: str,
        role: UserRole,
        context: Dict,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """Synchronous version of chat for non-async contexts"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.chat(user_message, role, context, conversation_history)
        )
    
    async def _call_api(self, messages: List[Dict]) -> str:
        """Call LongCat API"""
        url = f"{self.base_url}/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _format_context_for_llm(self, context: Dict, role: UserRole) -> str:
        """Format context data for LLM consumption (never raw data)"""
        if not context:
            return "No specific context data available."
        
        lines = []
        
        # Basic info
        lines.append(f"District: {context.get('district', 'Not specified')}")
        lines.append(f"Data Quality: {context.get('data_quality', 'Unknown')}")
        lines.append(f"Model Version: {context.get('model_version', 'Unknown')}")
        lines.append(f"Confidence Note: {context.get('confidence_note', 'Not available')}")
        
        # Forecasts
        if "forecasts" in context:
            lines.append("\nFORECAST DATA:")
            for horizon, forecast in context["forecasts"].items():
                lines.append(f"  {horizon} Horizon:")
                lines.append(f"    - Year: {forecast.get('year', 'N/A')}")
                lines.append(f"    - Projected Population: {forecast.get('total_population', 'N/A'):,}")
                lines.append(f"    - Confidence: {forecast.get('confidence', 'N/A')}")
        
        # Role-specific policy insights
        if "policy_insights" in context:
            lines.append("\nPOLICY INSIGHTS (pre-computed):")
            for horizon, insights in context["policy_insights"].items():
                lines.append(f"  {horizon} Horizon:")
                for key, value in insights.items():
                    if key != "horizon":
                        display_key = key.replace("_", " ").title()
                        lines.append(f"    - {display_key}: {value}")
        
        return "\n".join(lines)
    
    def get_sample_questions(self, role: UserRole) -> List[str]:
        """Get sample questions for each role"""
        samples = {
            UserRole.POLICE: [
                "What is the projected youth population growth?",
                "Which areas need additional police personnel?",
                "What is the law and order stress level?",
                "How does migration affect policing needs?"
            ],
            UserRole.EDUCATION: [
                "How many additional school seats are needed?",
                "What is the dropout risk in this district?",
                "What is the education budget stress level?",
                "When should we plan for new schools?"
            ],
            UserRole.HEALTH: [
                "What is the hospital bed demand projection?",
                "How many additional doctors are needed?",
                "What is the maternity load trend?",
                "Which health facilities need expansion?"
            ],
            UserRole.BUDGET_FINANCE: [
                "What is the overall budget stress level?",
                "Which sectors need priority funding?",
                "What is the education budget index change?",
                "How should we reallocate resources?"
            ],
            UserRole.DISTRICT_ADMIN: [
                "What is the overall district projection?",
                "Which departments need coordination?",
                "What are the priority action items?",
                "What is the infrastructure stress timeline?"
            ],
            UserRole.STATE_GOVT: [
                "Compare this district with peers",
                "What is the state-wide trend?",
                "Which districts need intervention?",
                "What policy changes are recommended?"
            ],
            UserRole.SKILL_EMPLOYMENT: [
                "What is the skill training demand?",
                "How does migration affect skill availability?",
                "How many training centers are needed?",
                "What skills are in demand?"
            ]
        }
        return samples.get(role, samples[UserRole.DISTRICT_ADMIN])

# =============================================================================
# OFFLINE FALLBACK (When API not available)
# =============================================================================

class OfflineLLMService:
    """
    Offline fallback that generates structured responses without API.
    Uses the pre-computed data directly.
    """
    
    def generate_response(self, context: Dict, role: UserRole, question: str = None) -> str:
        """Generate offline response from context"""
        district = context.get("district", "Unknown District")
        quality = context.get("data_quality", "medium")
        
        # Build response based on role
        response_parts = []
        
        response_parts.append(f"**Context:**")
        response_parts.append(f"Analysis for {district} district.")
        response_parts.append(f"Role: {role.value.replace('_', ' ').title()}")
        response_parts.append("")
        
        response_parts.append(f"**Forecast:**")
        if "forecasts" in context:
            for horizon, forecast in context["forecasts"].items():
                pop = forecast.get("total_population", "N/A")
                if isinstance(pop, int):
                    pop = f"{pop:,}"
                response_parts.append(f"- {horizon}: Projected population {pop}")
        response_parts.append("")
        
        response_parts.append(f"**Policy Insights:**")
        if "policy_insights" in context:
            for horizon, insights in context["policy_insights"].items():
                response_parts.append(f"*{horizon} Horizon:*")
                for key, value in list(insights.items())[:5]:
                    if key != "horizon":
                        display_key = key.replace("_", " ").title()
                        response_parts.append(f"  - {display_key}: {value}")
        response_parts.append("")
        
        response_parts.append(f"**Confidence:**")
        response_parts.append(f"Data quality: {quality}. {context.get('confidence_note', '')}")
        response_parts.append("")
        
        response_parts.append(f"**Recommended Action:**")
        if "policy_insights" in context and "5Y" in context["policy_insights"]:
            priorities = context["policy_insights"]["5Y"].get("priority_sectors", [])
            if priorities:
                response_parts.append(f"Focus on: {', '.join(priorities)}")
        response_parts.append("")
        
        response_parts.append(f"*Source: {context.get('model_version', 'DEMOG_COHORT_v1.0')}*")
        
        return "\n".join(response_parts)

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'LLMChatService',
    'OfflineLLMService',
    'UserRole',
    'ROLE_PROMPTS'
]
