import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client(http_options=types.HttpOptions(
    timeout=90000, retry_options=types.HttpRetryOptions(attempts=1)
))
MODEL = os.getenv("LAB_MODEL", "gemini-3.5-flash-lite")


@dataclass
class AgentResult:
    answer: str
    stop_reason: str
    steps: int
    prompt_tokens_per_step: list[int] = field(default_factory=list)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(self.prompt_tokens_per_step)


@dataclass
class Decision:
    approved: bool
    args: dict | None = None
    feedback: str = ""


Approver = Callable[[str, dict], Decision]


def call_llm(contents, config, retries: int = 5):
    for attempt in range(retries):
        try:
            return client.models.generate_content(model=MODEL, contents=contents, config=config)
        except errors.APIError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                wait = 2 ** attempt * 5
                print(f"  .. provider error {e.code}, retrying in {wait}s")
                time.sleep(wait)
            else:
                raise


def execute_tool(tools_map: dict[str, Callable], name: str, args: dict) -> str:
    if name not in tools_map:
        return f"ERROR: Unknown tool '{name}'. Available tools: {', '.join(tools_map)}."
    try:
        return str(tools_map[name](**args))
    except TypeError as error:
        return f"ERROR: Bad arguments for {name}: {error}"
    except Exception as error:
        return f"ERROR: {name} failed: {error}"


def run_agent(
    user_prompt: str,
    tools: list[Callable],
    system_instruction: str,
    max_steps: int = 8,
    requires_approval: frozenset[str] = frozenset(),
    approver: Approver | None = None,
    show_thoughts: bool = False,
    verbose: bool = True,
) -> AgentResult:
    tools_map = {fn.__name__: fn for fn in tools}
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        thinking_config=(types.ThinkingConfig(include_thoughts=True, thinking_level="high")
                         if show_thoughts else None),
    )
    messages = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]
    tokens: list[int] = []
    progress = []

    for step in range(1, max_steps + 1):
        try:
            response = call_llm(messages, config)
        except Exception as error:
            return AgentResult(f"STOPPED: provider error: {error}", "provider_error", step, tokens)

        usage = response.usage_metadata
        prompt_tokens = (usage.prompt_token_count or 0) if usage else 0
        tokens.append(prompt_tokens)
        if verbose:
            print(f"\n--- [Step {step}/{max_steps}] input tokens: {prompt_tokens:,} ---")
        if not response.candidates or not response.candidates[0].content:
            return AgentResult("STOPPED: provider returned no content.", "provider_error", step, tokens)
        content = response.candidates[0].content
        if verbose and content.parts:
            for part in content.parts:
                if part.thought and part.text:
                    print(f"  [Thought] {part.text.strip()[:300]}")

        calls = response.function_calls or []
        if not calls:
            return AgentResult(response.text or "", "done", step, tokens)

        messages.append(content)
        parts = []
        for call in calls:
            try:
                args = dict(call.args or {})
            except (TypeError, ValueError) as error:
                output = f"ERROR: Bad arguments for {call.name}: {error}"
            else:
                if verbose:
                    print(f"  -> [Tool Call] {call.name}({json.dumps(args)[:200]})")
                if call.name in requires_approval:
                    try:
                        decision = approver(call.name, args.copy()) if approver else Decision(
                            False, feedback="No approver configured"
                        )
                        if not decision.approved:
                            output = f"DENIED BY OPERATOR: {decision.feedback}. Adjust your plan."
                        else:
                            approved_args = decision.args if decision.args is not None else args
                            output = execute_tool(tools_map, call.name, approved_args)
                            if decision.args is not None:
                                output = f"OPERATOR EDITED ARGUMENTS: {json.dumps(approved_args)}\n{output}"
                    except Exception as error:
                        output = f"ERROR: Approval for {call.name} failed: {error}"
                else:
                    output = execute_tool(tools_map, call.name, args)

            progress.append(f"{call.name}: {output[:160]}")
            if verbose:
                print(f"  <- [Tool Output] {output[:160]}")
            parts.append(types.Part(function_response=types.FunctionResponse(
                id=call.id, name=call.name, response={"result": output}
            )))
        messages.append(types.Content(role="user", parts=parts))

    return AgentResult(
        f"STOPPED after {max_steps} steps without a final answer. Last results: {'; '.join(progress[-3:])}",
        "max_steps", max_steps, tokens,
    )
