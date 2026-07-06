import json
import logging
from collections.abc import Callable, Sequence
from typing import cast

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, SettingSource, SystemMessage, TextBlock, ToolUseBlock, query, UserMessage, ToolResultBlock

from manylogue.messages.adapter_response import AdapterIntermediateResponse, AdapterIntermediateResponseType, AdapterFinalResponse
from manylogue.adapters.base_adapter import BaseAdapter
from manylogue.messages import Message

CLAUDE_DEFAULT_MODEL = "claude-opus-4-8[1m]"

# todo: expose via settings/params
CLAUDE_MAX_TURNS = 100
CLAUDE_PERMISSION_MODE = "bypassPermissions"
CLAUDE_SETTING_SOURCES: list[SettingSource] = ["user", "project", "local"]

logger = logging.getLogger(__name__)


class ClaudeAdapter(BaseAdapter):
    _model: str

    def __init__(self, working_dir: str, model: str = CLAUDE_DEFAULT_MODEL) -> None:
        super().__init__(working_dir)
        self._model = model

    async def get_response(self,
                           agent_name: str,
                           system_prompt: str,
                           roster: Sequence[str],
                           full_history: Sequence[Message],
                           new_messages: Sequence[Message],
                           on_intermediate_response: Callable[[
                               AdapterIntermediateResponse], None]
                           ) -> AdapterFinalResponse | None:

        options = ClaudeAgentOptions(
            system_prompt={"type": "preset",
                           "preset": "claude_code",
                           # don't overrite general Claude Code (CLI|Desktop) prompt
                           "append": system_prompt
                           },
            model=self._model,
            max_turns=CLAUDE_MAX_TURNS,
            permission_mode=CLAUDE_PERMISSION_MODE,
            resume=self.get_session_id(),
            cwd=self._working_dir,
            setting_sources=CLAUDE_SETTING_SOURCES
        )

        new_messages_combined_prompt = self._combine_new_messages(
            agent_name, roster, new_messages)

        try:

            # tool_use_id -> formatted call
            pending_tools: dict[str, str] = {}

            async for msg in query(prompt=new_messages_combined_prompt, options=options):
                match msg:
                    case AssistantMessage(content=blocks):
                        for block in blocks:
                            match block:
                                case TextBlock(text=text):
                                    on_intermediate_response(AdapterIntermediateResponse(
                                        type=AdapterIntermediateResponseType.narration, body=text))
                                case ToolUseBlock(id=tool_id, name=name, input=args):
                                    # only saving here as we're missing the 2nd part with result and size
                                    # once we get that we'll fire the complete intermediate response
                                    pending_tools[tool_id] = _format_call(
                                        name, args)

                                case _:
                                    # ignoring ThinkingBlock and etc for now.
                                    pass

                    case ResultMessage(session_id=sid, result=result):
                        self._update_session_id(sid)

                        if result is not None:
                            return AdapterFinalResponse(body=result)

                    case UserMessage(content=blocks):
                        for block in blocks:
                            # this is where we complete the earlier saved pending_tool
                            if isinstance(block, ToolResultBlock):
                                call = pending_tools.pop(
                                    block.tool_use_id, "tool")
                                on_intermediate_response(AdapterIntermediateResponse(
                                    type=AdapterIntermediateResponseType.tool,
                                    body=f"{call} -> {_result_size(block.content, block.is_error)}"))

                    case SystemMessage():
                        pass  # session lifecycle — spammy and not interesting atm.

                    case _:
                        logger.debug("Unhandled msg type %s",
                                     type(msg).__name__)

        except Exception:
            logger.exception("ClaudeAdapter call failed")

        return None

# todo: move helper methods somewhere nicer


def _format_call(name: str, args: object) -> str:
    if isinstance(args, dict):
        args_dict = cast(dict[str, object], args)
        for key in ("command", "file_path", "path", "pattern", "query", "url"):
            if key in args_dict:
                return f"{name}: {_truncate(str(args_dict[key]))}"
        return f"{name}: {_truncate(json.dumps(args_dict, ensure_ascii=False, default=str))}"
    return f"{name}: {_truncate(str(args))}"


def _result_size(content: object, is_error: bool | None) -> str:
    text = content if isinstance(content, str) else _stringify_blocks(content)
    n_lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return f"{'error' if is_error else 'ok'}, {n_lines} lines, {len(text.encode('utf-8'))} bytes"


def _stringify_blocks(content: object) -> str:
    if isinstance(content, list):
        parts: list[str] = []
        for block in cast(list[object], content):
            if isinstance(block, dict):
                block_dict = cast(dict[str, object], block)
                parts.append(str(block_dict.get("text", "")))
            else:
                parts.append(str(getattr(block, "text", block)))
        return "\n".join(parts)
    return str(content)


def _truncate(value: str, max_chars: int = 200) -> str:
    return value if len(value) <= max_chars else value[:max_chars - 3] + "..."
