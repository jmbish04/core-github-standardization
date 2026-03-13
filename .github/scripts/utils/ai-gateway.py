import os
import requests
from typing import List, Dict, Any, Optional, Union

class AIGateway:
    """
    A type-safe utility for interacting with Cloudflare AI Gateway,
    specifically optimized for Universal Routing via OpenAI-compatible endpoints.
    """
    def __init__(self, account_id: str, gateway_id: str, ai_gateway_token: str) -> None:
        self.account_id = account_id
        self.gateway_id = gateway_id or 'github-actions'
        self.ai_gateway_token = ai_gateway_token
        # Base URL for the gateway
        self.base_url = f"https://gateway.ai.cloudflare.com/v1/{account_id}/{self.gateway_id}"

    def _format_model_id(self, model_id: str) -> str:
        """
        Safely normalizes AI model IDs to ensure canonical provider prefixes.
        Handles complex paths like '@cf/openai/gpt-oss-120b' safely without
        incorrectly triggering keyword fallback rules.
        """
        if not model_id:
            return model_id

        model_id_lower = model_id.lower()
        
        # Step 1: Evaluate explicit provider prefixes.
        # We use split('/', 1) to isolate the root prefix while preserving
        # any nested slashes in the actual model name.
        if "/" in model_id:
            # Split original string to preserve the exact casing of the model name
            parts = model_id.split("/", 1)
            prefix = parts[0].lower()
            remainder = parts[1]
            
            # Cloudflare Workers AI
            # We explicitly prepend '@cf/' back onto the remainder to preserve the full Cloudflare model path
            if prefix == '@cf':
                return f"workers-ai/@cf/{remainder}"
            elif prefix == 'workers-ai':
                return f"workers-ai/{remainder}"
                
            # Google AI Studio
            elif prefix in ['gemini', 'google-ai-studio']:
                return f"google-ai-studio/{remainder}"
                
            # OpenAI
            elif prefix in ['gpt', 'openai']:
                return f"openai/{remainder}"
                
            # Anthropic
            elif prefix in ['claude', 'anthropic']:
                return f"anthropic/{remainder}"
        
        # Step 2: Fallback keyword matching for unprefixed models.
        # (e.g., "gpt-4o" -> "openai/gpt-4o")
        # Because we evaluate the explicit prefixes in Step 1, a Cloudflare model
        # like "@cf/openai/gpt-oss" will never erroneously hit these checks.
        if "gpt" in model_id_lower or "o1" in model_id_lower or "o3" in model_id_lower:
            return f"openai/{model_id}"
        elif "claude" in model_id_lower:
            return f"anthropic/{model_id}"
        elif "gemini" in model_id_lower:
            return f"google-ai-studio/{model_id}"
            
        # Fallback: return as-is if no matching routing rules apply
        return model_id  

    def _format_model_name(self, model_id: str) -> str:
        """
        Automatically prepends the correct provider prefix for AI Gateway Universal Routing
        if it is not already present.
        """
        # _format_model_id now safely handles all mapping and prefixing logic.
        return self._format_model_id(model_id)

    def get_ai_gateway_base_url(self, model_id: str) -> str:
        """
        Returns the full provider-specific gateway URL for a model.
        Example: https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/openai/gpt-4o-mini
        """
        formatted_model = self._format_model_name(model_id)
        return f"{self.base_url}/{formatted_model}"

    def run_compat_chat_completions(self, model_id: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Executes a request against the Universal /compat/chat/completions endpoint.
        Handles models from Workers AI, OpenAI, Anthropic, and Google AI Studio natively.
        """
        url = f"{self.base_url}/compat/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.ai_gateway_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._format_model_name(model_id),
            "messages": messages,
            **kwargs
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() 
        return response.json()

    def run_compat_embeddings(self, model_id: str, input_text: Union[str, List[str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Executes a request against the Universal /compat/embeddings endpoint.
        """
        url = f"{self.base_url}/compat/embeddings"
        
        headers = {
            "Authorization": f"Bearer {self.ai_gateway_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._format_model_name(model_id),
            "input": input_text,
            **kwargs
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def generate_text(self, model_id: str, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """
        Convenience method for simple single-prompt text generation.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.run_compat_chat_completions(model_id, messages, **kwargs)

    def generate_structured_json(self, model_id: str, prompt: str, schema: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """
        Forces the model to return a structured JSON response.
        If a JSON schema dictionary is provided, it uses the strict `json_schema` format.
        Otherwise, it falls back to a generic `{"type": "json_object"}`.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "schema": schema
                }
            }
        else:
            response_format = {"type": "json_object"}
            
        return self.run_compat_chat_completions(
            model_id=model_id,
            messages=messages,
            response_format=response_format,
            **kwargs
        )

    def generate_embeddings(self, model_id: str, text: Union[str, List[str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Convenience method for generating embeddings for the provided text.
        Works seamlessly with Workers AI models (e.g., @cf/baai/bge-large-en-v1.5).
        """
        return self.run_compat_embeddings(model_id, text, **kwargs)


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "account_id")
    gateway_id = os.environ.get("CLOUDFLARE_GATEWAY_ID", "gateway_id")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "api_token")
    
    aig = AIGateway(account_id, gateway_id, api_token)
    
    # URL formatting test
    print("--- URL Routing Tests ---")
    print(aig.get_ai_gateway_base_url("gpt-4o-mini"))
    print(aig.get_ai_gateway_base_url("@cf/meta/llama-3.3-70b-instruct-fp8-fast"))
    print(aig.get_ai_gateway_base_url("claude-3-opus"))
    
    # 1. Text Generation (Workers AI)
    print("\n--- 1. Text Generation ---")
    try:
        text_resp = aig.generate_text(
            model_id="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            prompt="What is Cloudflare?"
        )
        print(text_resp["choices"][0]["message"]["content"][:100] + "...")
    except Exception as e:
        print(f"Text Error: {e}")

    # 2. Structured JSON Generation (OpenAI)
    print("\n--- 2. Structured JSON ---")
    try:
        user_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            },
            "required": ["name", "age"],
            "additionalProperties": False
        }
        json_resp = aig.generate_structured_json(
            model_id="gpt-4o-mini",
            prompt="Extract the following: John Doe is 35 years old.",
            schema=user_schema
        )
        print(json_resp["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"JSON Error: {e}")

    # 3. Text Embeddings (Workers AI)
    print("\n--- 3. Embeddings ---")
    try:
        embed_resp = aig.generate_embeddings(
            model_id="@cf/baai/bge-large-en-v1.5",
            text="Cloudflare AI Gateway is awesome."
        )
        print(f"Generated vector with {len(embed_resp['data'][0]['embedding'])} dimensions.")
    except Exception as e:
        print(f"Embeddings Error: {e}")
