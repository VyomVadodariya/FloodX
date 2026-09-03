"""
bedrock_alerts.py — Generative AI Emergency Alert Generation
=============================================================

Integrates with AWS Bedrock (Claude 3 Haiku / Sonnet) to generate 
context-aware, multilingual emergency alerts based on the deterministic
risk engine output.

Safety constraint: The LLM NEVER calculates the risk score. It only translates
the deterministic risk payload into actionable human instructions.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class BedrockAlertGenerator:
    """Singleton generator for Bedrock-based emergency alerts."""
    
    _client = None

    @classmethod
    def _get_client(cls):
        """Lazy-load AWS Bedrock runtime client."""
        if cls._client is None and BOTO3_AVAILABLE:
            try:
                cls._client = boto3.client(
                    service_name='bedrock-runtime',
                    region_name='us-east-1' # Configure as needed
                )
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {e}")
        return cls._client

    @classmethod
    def generate_alert(
        cls, 
        risk_prediction: dict[str, Any], 
        routing_info: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate an emergency alert using Claude 3 via AWS Bedrock."""
        
        # Guardrail: Only generate alerts for HIGH or CRITICAL risk
        risk_label = risk_prediction.get("risk_label", "UNKNOWN")
        if risk_label not in ("HIGH", "CRITICAL"):
            return {
                "status": "skipped",
                "message": f"Alert generation skipped for risk level: {risk_label}"
            }
            
        client = cls._get_client()
        if not client:
            logger.warning("AWS Bedrock not available. Returning fallback alert.")
            return cls._fallback_alert(risk_prediction, routing_info)
            
        prompt = cls._build_prompt(risk_prediction, routing_info)
        
        try:
            # Bedrock Converse API format for Anthropic Claude 3
            response = client.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 512,
                    "system": (
                        "You are an emergency response communication AI. Your job is to translate "
                        "deterministic flood risk telemetry into clear, actionable public alerts. "
                        "CRITICAL RULES: "
                        "1) DO NOT calculate or estimate numerical risk scores. "
                        "2) Only use the data provided in the payload. Do not hallucinate external conditions. "
                        "3) You must output ONLY a valid JSON object matching the exact schema requested, "
                        "without any markdown formatting or prefix text."
                    ),
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                })
            )
            
            response_body = json.loads(response.get('body').read())
            raw_text = response_body.get('content', [{}])[0].get('text', '{}')
            
            # Clean possible markdown wrapping if the LLM disobeyed
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "").strip()
                
            alert_payload = json.loads(raw_text)
            return {
                "status": "success",
                "alert": alert_payload
            }
            
        except (ClientError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to generate Bedrock alert: {e}")
            return cls._fallback_alert(risk_prediction, routing_info)
            
    @classmethod
    def _build_prompt(cls, risk_prediction: dict, routing_info: dict | None) -> str:
        """Construct the prompt containing the telemetry payload."""
        
        # Serialize the telemetry
        telemetry_json = json.dumps(risk_prediction, indent=2)
        route_text = ""
        
        if routing_info and routing_info.get("status") == "success":
            dest = routing_info.get("destination", "a safe zone")
            time = routing_info.get("travel_time", 0)
            route_text = f"\nEvacuation Route found: Proceed to {dest}. Est. travel time: {time} mins."
        else:
            route_text = "\nEvacuation Route: NO SAFE ROUTE FOUND. Shelter in place on high ground."
            
        prompt = f"""
Here is the latest telemetry from the deterministic risk engine:
<telemetry>
{telemetry_json}
</telemetry>
<routing>
{route_text}
</routing>

Based ONLY on this data, generate an emergency alert.
Output EXACTLY this JSON structure, and nothing else:
{{
  "alert_title": "Short descriptive title (e.g., FLASH FLOOD WARNING)",
  "severity": "HIGH or CRITICAL",
  "recommended_action": "1 sentence technical summary for officials",
  "civilian_message": "2-3 sentences clear, calm instruction for the public. Must include evacuation instructions if provided."
}}
"""
        return prompt

    @classmethod
    def _fallback_alert(cls, risk_prediction: dict, routing_info: dict | None) -> dict:
        """Deterministic fallback if Bedrock is unreachable or fails."""
        label = risk_prediction.get("risk_label", "CRITICAL")
        loc = risk_prediction.get("name", "your area")
        
        route_msg = "Move to higher ground immediately."
        if routing_info and routing_info.get("status") == "success":
            route_msg = f"Evacuate to {routing_info.get('destination')}."
            
        return {
            "status": "fallback",
            "alert": {
                "alert_title": f"AUTOMATED {label} FLOOD WARNING",
                "severity": label,
                "recommended_action": risk_prediction.get("recommended_action", "EVACUATE"),
                "civilian_message": f"Flood risk is {label} in {loc}. {route_msg} {risk_prediction.get('explanation', '')}"
            }
        }
