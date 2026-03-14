import os
import json
from typing import Optional

import boto3
from botocore.config import Config

CLAUDE_SONNET_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
CLAUDE_HAIKU_MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

_bedrock_client = None


def get_bedrock_client():
    """Get or create the Bedrock runtime client."""
    global _bedrock_client
    if _bedrock_client is None:
        region = os.getenv("AWS_REGION", "us-east-1")
        profile = os.getenv("AWS_PROFILE")

        config = Config(
            region_name=region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )

        session_kwargs = {}
        if profile:
            session_kwargs["profile_name"] = profile

        session = boto3.Session(**session_kwargs)
        _bedrock_client = session.client("bedrock-runtime", config=config)

    return _bedrock_client


def get_boto_session():
    """Get a configured boto3 session for Strands agents."""
    profile = os.getenv("AWS_PROFILE")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    session_kwargs = {"region_name": region}
    if profile:
        session_kwargs["profile_name"] = profile
    
    return boto3.Session(**session_kwargs)


async def invoke_claude(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "haiku",
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> Optional[str]:
    """
    Invoke Claude model via Bedrock.
    
    Args:
        prompt: The user message/prompt
        system_prompt: Optional system instructions
        model: "haiku" or "sonnet"
        max_tokens: Maximum response tokens
        temperature: Sampling temperature
        
    Returns:
        Model response text or None if failed
    """
    model_id = CLAUDE_HAIKU_MODEL_ID if model == "haiku" else CLAUDE_SONNET_MODEL_ID

    messages = [{"role": "user", "content": prompt}]

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }

    if system_prompt:
        body["system"] = system_prompt

    try:
        client = get_bedrock_client()
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [])

        if content and len(content) > 0:
            return content[0].get("text", "")

        return None

    except Exception as e:
        print(f"Bedrock invocation failed: {e}")
        return None


async def invoke_haiku(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> Optional[str]:
    """Convenience wrapper for Claude 3.5 Haiku."""
    return await invoke_claude(
        prompt=prompt,
        system_prompt=system_prompt,
        model="haiku",
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def invoke_sonnet(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.4,
) -> Optional[str]:
    """Convenience wrapper for Claude 4 Sonnet."""
    return await invoke_claude(
        prompt=prompt,
        system_prompt=system_prompt,
        model="sonnet",
        max_tokens=max_tokens,
        temperature=temperature,
    )
