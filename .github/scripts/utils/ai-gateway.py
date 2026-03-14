from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar

import httpx
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, ValidationError

from toolkit.cloudflare.exceptions import CloudflareAuthError
from toolkit.config import Settings
from toolkit.errors import StructuredOutputError
from toolkit.utils.markdown import encode_data_url

SchemaT = TypeVar("SchemaT", bound=BaseModel)


_shared_loop: asyncio.AbstractEventLoop | None = None


def _cleanup_wrapper(coro: Any) -> Any:
    return await coro


def _run_sync(coro: Any) -> Any:
    """Run async code synchronously in a shared event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        global _shared_loop
        if _shared_loop is None or _shared_loop.is_closed():
            _shared_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_shared_loop)
        return _shared_loop.run_until_complete(_cleanup_wrapper(coro))
    raise RuntimeError("Synchronous WorkerAI methods cannot be called from an active event loop.")


def _schema_instruction(schema: type[BaseModel]) -> str:
    """Return JSON schema instruction for the model."""
    return (
        "Return valid JSON only. Do not wrap the response in markdown fences. "
        f"The JSON must satisfy this schema: {json.dumps(schema.model_json_schema(), sort_keys=True)}"
    )


def _extract_json_payload(raw_text: str) -> str:
    """Extract JSON from raw text, removing markdown fences if present."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


def _message_text(content: Any) -> str:
    """Extract text from message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    return str(content)


class AIAdapter(Protocol):
    """Protocol for AI adapters."""

    def generate_text(self, prompt: str, *, model: str | None = None, system_prompt: str | None = None) -> str: ...

    def generate_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> SchemaT: ...

    def generate_vision_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        image_paths: list[Path],
        context_text: str | None = None,
        model: str | None = None,
    ) -> SchemaT: ...


class OpenAIGatewayAdapter:
    """
    Adapter for OpenAI models via AI Gateway's OpenAI-compatible endpoint.
    
    Uses the new OpenAI-compatible endpoint in AI Gateway:
    https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/compat/chat/completions
    
    Models should be specified in {provider}/{model} format:
    - openai/gpt-5-mini
    - google-ai-studio/gemini-2.5-flash
    - anthropic/claude-sonnet-4-5
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # OpenAI-compatible endpoint for AI Gateway (NEW in June 2025)
        self.base_url = (
            f"https://gateway.ai.cloudflare.com/v1/"
            f"{settings.cloudflare_account_id}/{settings.cloudflare_ai_gateway_name}/compat/chat/completions"
        )

    def _create_client(self) -> AsyncOpenAI:
        """Create OpenAI client configured for AI Gateway."""
        return AsyncOpenAI(
            api_key=self.settings.cloudflare_api_token,
            base_url=self.base_url,
            default_headers={
                "cf-aig-authorization": f"Bearer {self.settings.cloudflare_api_token}",
            },
            timeout=120.0,
        )

    def _messages(self, prompt: str, system_prompt: str | None) -> list[dict[str, Any]]:
        """Build messages array."""
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _chat(self, *, model: str, messages: list[dict[str, Any]]) -> str:
        """Make chat completion request."""
        client = self._create_client()
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
            )
            if not response.choices:
                return ""
            return _message_text(response.choices[0].message.content)
        finally:
            await client.close()

    def generate_text(self, prompt: str, *, model: str | None = None, system_prompt: str | None = None) -> str:
        """Generate text using the specified model."""
        chosen_model = model or self.settings.workers_ai_reasoning_model
        return _run_sync(self._chat(model=chosen_model, messages=self._messages(prompt, system_prompt)))

    def generate_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> SchemaT:
        """Generate structured response using OpenAI's structured outputs feature."""
        return _run_sync(
            self._generate_structured_response_async(
                prompt,
                schema,
                model=model or self.settings.workers_ai_structured_model,
                system_prompt=system_prompt,
            )
        )

    async def _generate_structured_response_async(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        model: str,
        system_prompt: str | None = None,
    ) -> SchemaT:
        """Generate structured response using OpenAI's response_format parameter."""
        client = self._create_client()
        try:
            # Use OpenAI's structured outputs feature (response_format with json_schema)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt or "Extract the structured information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "description": "Structured output matching the schema",
                        "strict": True,
                        "schema": schema.model_json_schema()
                    }
                }
            )
            
            if not response.choices:
                raise StructuredOutputError("No response from model")
            
            message = response.choices[0].message
            
            # If the model returned parsed content (OpenAI SDK structured outputs)
            if hasattr(message, 'parsed') and message.parsed is not None:
                return message.parsed
            
            # Fall back to manual validation if no parsed content
            raw_text = _message_text(message.content or "{}")
            try:
                return schema.model_validate_json(_extract_json_payload(raw_text))
            except (ValidationError, json.JSONDecodeError) as exc:
                raise StructuredOutputError("Failed to parse structured response") from exc
                
        finally:
            await client.close()

    def generate_vision_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        image_paths: list[Path],
        context_text: str | None = None,
        model: str | None = None,
    ) -> SchemaT:
        """Generate structured response with vision support."""
        return _run_sync(
            self._generate_vision_structured_response_async(
                prompt,
                schema,
                image_paths=image_paths,
                context_text=context_text,
                model=model or self.settings.workers_ai_vision_model,
            )
        )

    async def _generate_vision_structured_response_async(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        image_paths: list[Path],
        context_text: str | None,
        model: str,
    ) -> SchemaT:
        """Generate structured response with images using OpenAI's vision API."""
        client = self._create_client()
        try:
            # Build content array with text and images
            content: list[dict[str, Any]] = [
                {
                    "type": "text",
                    "text": prompt,
                }
            ]
            
            # Add images (convert to data URLs)
            for image_path in image_paths:
                with open(image_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}
                })
            
            # Use OpenAI's structured outputs feature
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "description": "Structured output matching the schema",
                        "strict": True,
                        "schema": schema.model_json_schema()
                    }
                }
            )
            
            if not response.choices:
                raise StructuredOutputError("No response from vision model")
            
            message = response.choices[0].message
            
            # If the model returned parsed content
            if hasattr(message, 'parsed') and message.parsed is not None:
                return message.parsed
            
            # Fall back to manual validation
            raw_text = _message_text(message.content or "{}")
            try:
                return schema.model_validate_json(_extract_json_payload(raw_text))
            except (ValidationError, json.JSONDecodeError) as exc:
                raise StructuredOutputError("Failed to parse vision structured response") from exc
                
        finally:
            await client.close()


class WorkersAIAdapter:
    """
    Adapter for Workers AI models using the direct API.
    
    For Workers AI models like @cf/openai/gpt-oss-20b, use the direct API:
    https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions
    
    This adapter uses the OpenAI-compatible endpoint for Workers AI models.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # Workers AI direct API with OpenAI-compatible endpoint
        self.base_url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{settings.cloudflare_account_id}/ai/v1/chat/completions"
        )

    def _create_client(self) -> httpx.AsyncClient:
        """Create HTTP client for Workers AI API."""
        return httpx.AsyncClient(
            timeout=120.0,
            headers={
                "Authorization": f"Bearer {self.settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
        )

    async def _chat(self, *, model: str, messages: list[dict[str, Any]]) -> str:
        """Make chat completion request to Workers AI."""
        async with self._create_client() as client:
            response = await client.post(
                self.base_url,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0,
                }
            )
            if response.status_code in (401, 403):
                raise CloudflareAuthError("Workers AI request was rejected.")
            response.raise_for_status()
            data = response.json()
            
            # Extract text from Workers AI response
            return self._extract_text(data)

    def _extract_text(self, data: dict[str, Any]) -> str:
        """Extract text from Workers AI API response."""
        result = data.get("result", data)
        
        # Handle different response formats
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if "response" in result and isinstance(result["response"], str):
                return result["response"]
            if "text" in result and isinstance(result["text"], str):
                return result["text"]
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                message = choice.get("message", {})
                return _message_text(message.get("content", ""))
        
        # Fallback: return as JSON
        return json.dumps(result)

    def generate_text(self, prompt: str, *, model: str | None = None, system_prompt: str | None = None) -> str:
        """Generate text using Workers AI model."""
        chosen_model = model or self.settings.workers_ai_reasoning_model
        return _run_sync(self._chat(
            model=chosen_model,
            messages=self._messages(prompt, system_prompt)
        ))

    def _messages(self, prompt: str, system_prompt: str | None) -> list[dict[str, Any]]:
        """Build messages array."""
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def generate_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> SchemaT:
        """Generate structured response using Workers AI's JSON mode."""
        return _run_sync(
            self._generate_structured_response_async(
                prompt,
                schema,
                model=model or self.settings.workers_ai_structured_model,
                system_prompt=system_prompt,
            )
        )

    async def _generate_structured_response_async(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        model: str,
        system_prompt: str | None = None,
    ) -> SchemaT:
        """Generate structured response using Workers AI's JSON mode."""
        full_prompt = f"{prompt}\n\n{_schema_instruction(schema)}"
        
        async with self._create_client() as client:
            response = await client.post(
                self.base_url,
                json={
                    "model": model,
                    "messages": [
                        *([{"role": "system", "content": system_prompt}] if system_prompt else []),
                        {"role": "user", "content": full_prompt},
                    ],
                    "temperature": 0,
                }
            )
            if response.status_code in (401, 403):
                raise CloudflareAuthError("Workers AI request was rejected.")
            response.raise_for_status()
            data = response.json()
            raw = self._extract_text(data)
            
            try:
                return schema.model_validate_json(_extract_json_payload(raw))
            except (ValidationError, json.JSONDecodeError) as exc:
                raise StructuredOutputError("Workers AI returned invalid structured output") from exc

    def generate_vision_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        image_paths: list[Path],
        context_text: str | None = None,
        model: str | None = None,
    ) -> SchemaT:
        """Generate structured response with vision support."""
        return _run_sync(
            self._generate_vision_structured_response_async(
                prompt,
                schema,
                image_paths=image_paths,
                context_text=context_text,
                model=model or self.settings.workers_ai_vision_model,
            )
        )

    async def _generate_vision_structured_response_async(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        image_paths: list[Path],
        context_text: str | None,
        model: str,
    ) -> SchemaT:
        """Generate structured response with images using Workers AI vision."""
        # Workers AI vision models support images in messages
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"{prompt}\n\nContext:\n{context_text or 'None'}\n\n"
                    f"{_schema_instruction(schema)}"
                ),
            }
        ]
        
        # Add images
        for image_path in image_paths:
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}
            })
        
        async with self._create_client() as client:
            response = await client.post(
                self.base_url,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": content}],
                    "temperature": 0,
                }
            )
            if response.status_code in (401, 403):
                raise CloudflareAuthError("Workers AI vision request was rejected.")
            response.raise_for_status()
            data = response.json()
            raw = self._extract_text(data)
            
            try:
                return schema.model_validate_json(_extract_json_payload(raw))
            except (ValidationError, json.JSONDecodeError) as exc:
                raise StructuredOutputError("Workers AI vision response could not be validated") from exc


class WorkerAIAgent:
    """Agent that can use tools and generate structured responses."""

    def __init__(self, adapter: OpenAIGatewayAdapter, settings: Settings) -> None:
        self.adapter = adapter
        self.settings = settings

    async def _run_async(
        self,
        prompt: str,
        *,
        schema: type[SchemaT],
        tools: list[Callable[..., Any]] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        image_paths: list[Path] | None = None,
        max_iterations: int = 10,
    ) -> SchemaT:
        """Run agent with tool calling and structured outputs."""
        from openai import pydantic_function_tool
        
        # Build initial messages
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Support vision/images
        if image_paths:
            import base64
            content_array: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            for path in image_paths:
                with open(path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                content_array.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}
                })
            messages.append({"role": "user", "content": content_array})
        else:
            messages.append({"role": "user", "content": prompt})
        
        chosen_model = model or self.settings.workers_ai_reasoning_model
        
        tool_map = {t.__name__: t for t in tools} if tools else {}
        
        def _callable_to_tool(func: Callable[..., Any]) -> dict[str, Any]:
            """Convert callable to OpenAI tool definition."""
            import inspect
            from pydantic import create_model
            
            sig = inspect.signature(func)
            fields: dict[str, Any] = {}
            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
                default = param.default if param.default != inspect.Parameter.empty else ...
                fields[name] = (annotation, default)
            
            model = create_model(func.__name__, **fields)  # type: ignore
            return pydantic_function_tool(model, name=func.__name__, description=func.__doc__ or "")
        
        formatted_tools = [_callable_to_tool(t) for t in tools] if tools else None
        
        client = self.adapter._create_client()
        
        try:
            for _ in range(max_iterations):
                kwargs: dict[str, Any] = {
                    "model": chosen_model,
                    "messages": messages,
                }
                if formatted_tools:
                    kwargs["tools"] = formatted_tools

                response = await client.chat.completions.create(**kwargs)
                message = response.choices[0].message

                if message.tool_calls:
                    message_dict = message.model_dump(exclude_unset=True)
                    if getattr(message, "content", None) is None:
                        message_dict["content"] = ""
                    messages.append(message_dict)

                    for tool_call in message.tool_calls:
                        func_name = tool_call.function.name
                        try:
                            func_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            func_args = {}

                        if func_name in tool_map:
                            try:
                                # Execute the tool
                                if asyncio.iscoroutinefunction(tool_map[func_name]):
                                    result = await tool_map[func_name](**func_args)
                                else:
                                    result = tool_map[func_name](**func_args)
                                result_str = json.dumps(result) if not isinstance(result, str) else result
                            except Exception as e:
                                result_str = f"Error executing tool: {e}"
                        else:
                            result_str = f"Error: Tool {func_name} not found"

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_str,
                        })
                    continue

                # Try to parse as structured output
                try:
                    raw_text = _message_text(message.content or "{}")
                    return schema.model_validate_json(_extract_json_payload(raw_text))
                except ValidationError:
                    # Basic self-correction/repair attempt
                    repair_prompt = (
                        "Repair the following output into valid JSON that strictly matches the schema.\n\n"
                        f"Schema: {json.dumps(schema.model_json_schema(), sort_keys=True)}\n\n"
                        f"Original output:\n{message.content}"
                    )
                    messages.append({"role": "user", "content": repair_prompt})
                    continue

            raise StructuredOutputError(f"Agent exceeded maximum iterations ({max_iterations}) without producing a final response.")
        finally:
            await client.close()

    def run(
        self,
        prompt: str,
        *,
        schema: type[SchemaT],
        tools: list[Callable[..., Any]] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        image_paths: list[Path] | None = None,
        max_iterations: int = 10,
    ) -> SchemaT:
        """Run agent synchronously."""
        return _run_sync(
            self._run_async(
                prompt=prompt,
                schema=schema,
                tools=tools,
                model=model,
                system_prompt=system_prompt,
                image_paths=image_paths,
                max_iterations=max_iterations,
            )
        )


class WorkerAIClient:
    """Client for managing AI adapters."""

    def __init__(
        self,
        settings: Settings,
        *,
        openai_adapter: AIAdapter | None = None,
        workers_ai_adapter: AIAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.openai_adapter = openai_adapter or OpenAIGatewayAdapter(settings)
        self.workers_ai_adapter = workers_ai_adapter or WorkersAIAdapter(settings)

    def _select_adapter(self, requested: str | None, *, prefer_workers_ai: bool = False) -> tuple[str, AIAdapter]:
        """Select appropriate adapter based on model name."""
        adapter_name = requested or self.settings.workers_ai_adapter
        if adapter_name == "openai":
            return "openai", self.openai_adapter
        if adapter_name == "workers_ai":
            return "workers_ai", self.workers_ai_adapter
        if prefer_workers_ai:
            return "workers_ai", self.workers_ai_adapter
        return "openai", self.openai_adapter

    def agent(self) -> WorkerAIAgent:
        """Returns an agent configured with the OpenAI adapter."""
        if not isinstance(self.openai_adapter, OpenAIGatewayAdapter):
            raise RuntimeError("Agent wrapper requires OpenAIGatewayAdapter.")
        return WorkerAIAgent(adapter=self.openai_adapter, settings=self.settings)

    def generate_text(self, prompt: str, *, model: str | None = None, system_prompt: str | None = None, adapter: str | None = None) -> str:
        """Generate text using the specified adapter."""
        _, chosen = self._select_adapter(adapter)
        return chosen.generate_text(prompt, model=model, system_prompt=system_prompt)

    def generate_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        adapter: str | None = None,
    ) -> SchemaT:
        """Generate structured response using the specified adapter."""
        _, chosen = self._select_adapter(adapter)
        return chosen.generate_structured_response(prompt, schema, model=model, system_prompt=system_prompt)

    def generate_vision_structured_response(
        self,
        prompt: str,
        schema: type[SchemaT],
        *,
        image_paths: list[Path],
        context_text: str | None = None,
        model: str | None = None,
        adapter: str | None = None,
    ) -> SchemaT:
        """Generate structured response with vision using the specified adapter."""
        adapter_name, chosen = self._select_adapter(adapter)
        try:
            return chosen.generate_vision_structured_response(
                prompt,
                schema,
                image_paths=image_paths,
                context_text=context_text,
                model=model,
            )
        except StructuredOutputError:
            if adapter_name != "openai":
                raise
            return self.workers_ai_adapter.generate_vision_structured_response(
                prompt,
                schema,
                image_paths=image_paths,
                context_text=context_text,
                model=model,
            )
