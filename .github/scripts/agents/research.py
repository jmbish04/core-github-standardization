import os
import json
import requests
from pydantic import BaseModel
from litellm import completion
# 1. Define your exact structured output using Pydantic
class RepoAnalysis(BaseModel):
    is_relevant: bool
    ai_features_found: list[str]
    summary: str
    confidence_score: float
def main():
    account_id = os.environ["CF_ACCOUNT_ID"]
    gateway_id = os.environ["CF_GATEWAY_ID"]
    api_token = os.environ["CF_API_TOKEN"]
    query = os.environ["QUERY"]
    raw_model_name = os.environ.get("MODEL_NAME", "workers-ai/@cf/openai/gpt-oss-120b")
    # 2. Format the Cloudflare AI Gateway URL
    # Note: We use the /workers-ai/v1 endpoint to enable OpenAI compatibility
    api_base = f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/compat"
    # TRICK: Cloudflare Workers AI models start with @cf/...
    # LiteLLM needs 'openai/' prefix to use the OpenAI-compatible endpoint.
    # User passes 'workers-ai/@cf/openai/gpt-oss-120b' or similar.
    # We split by '@cf' to get the suffix and prepend 'openai/@cf'
    if "@cf" in raw_model_name:
        suffix = raw_model_name.split("@cf", 1)[1]
        litellm_model = f"openai/@cf{suffix}"
    else:
         # Fallback if no @cf found, just assume it's openai/
        litellm_model = f"openai/{raw_model_name}"
    print(f"Executing Deep Research analysis for: {query}")
    print(f"Using LiteLLM Model: {litellm_model}")
    # 3. Call the model using LiteLLM
    response = completion(
        # The 'openai/' prefix tells LiteLLM to treat this custom endpoint exactly like OpenAI
        model=litellm_model,
        api_base=api_base,
        api_key=api_token,
        messages=[
            {"role": "system", "content": "You are a code analyzer. Extract structured data from the provided repository description. You must strictly adhere to the requested JSON schema."},
            {"role": "user", "content": f"Analyze this repository based on the search query: '{query}'."}
        ],
        
        # 4. Enforce Structured Output
        # LiteLLM automatically converts this Pydantic class into JSON Schema for Cloudflare
        response_format=RepoAnalysis,
        
        # 5. Reasoning Tokens Configuration
        # Allocate 4096 tokens and force 'high' effort to simulate a "minimum" reasoning constraint
        max_tokens=4096,
        extra_body={
            "reasoning": {
                "effort": "high"
            }
        }
    )
    # 6. Extract and validate the response
    # The model returns a stringified JSON object matching our Pydantic schema
    raw_json_str = response.choices[0].message.content
    print("\n--- AI Analysis Result ---")
    print(raw_json_str)
    # 7. Post the verified data in a batch to your Cloudflare Worker API
    worker_url = os.environ.get("WORKER_API_URL")
    if worker_url:
        print(f"Posting data to Worker API: {worker_url}...")
        # We parse it just to ensure it's valid JSON before sending
        payload = json.loads(raw_json_str) 
        
        requests.post(
            worker_url, 
            json={"query": query, "results": payload}, 
            headers={"X-API-Key": os.environ.get("WORKER_API_KEY", "")}
        )
        print("Data successfully synced to Worker.")
if __name__ == "__main__":
    main()
