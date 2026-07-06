import json
import logging
from collections.abc import Callable, Sequence, Sized
from typing import Any

from openai_codex import AsyncCodex, CodexConfig
from openai_codex.generated.v2_all import (
    AgentMessageDeltaNotification,
    AgentMessageThreadItem,
    CommandExecutionThreadItem,
    DynamicToolCallThreadItem,
    ErrorNotification,
    FileChangeThreadItem,
    ItemCompletedNotification,
    McpToolCallThreadItem,
    MessagePhase,
    ReasoningEffort,
    ReasoningSummary,
    ReasoningSummaryTextDeltaNotification,
    ReasoningSummaryValue,
    WebSearchThreadItem,
)

from manylogue.messages.adapter_response import AdapterFinalResponse, AdapterIntermediateResponse, AdapterIntermediateResponseType
from manylogue.adapters.base_adapter import BaseAdapter
from manylogue.messages import Message

CODEX_DEFAULT_MODEL = "gpt-5.5"

logger = logging.getLogger(__name__)


class CodexAdapter(BaseAdapter):
    _model: str

    def __init__(self, working_dir: str, model: str = CODEX_DEFAULT_MODEL) -> None:
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

        combined_prompt = self._combine_new_messages(
            agent_name, roster, new_messages)
        session_id = self.get_session_id()

        try:
            async with AsyncCodex(config=CodexConfig(cwd=self._working_dir)) as codex:
                if session_id:
                    try:
                        thread = await codex.thread_resume(
                            session_id, cwd=self._working_dir)
                        prompt = combined_prompt
                    except Exception:
                        logger.exception(
                            "Codex thread resume failed; starting a fresh thread")
                        self._update_session_id(None)
                        thread = await codex.thread_start(cwd=self._working_dir, model=self._model)
                        prompt = system_prompt + "\n\n" + combined_prompt
                else:
                    thread = await codex.thread_start(cwd=self._working_dir, model=self._model)
                    # First turn only; resumed Codex threads carry context in app-server state.
                    prompt = system_prompt + "\n\n" + combined_prompt

                # todo: make the reasoning summary a configurable value
                turn = await thread.turn(prompt, cwd=self._working_dir, model=self._model, summary=ReasoningSummary(root=ReasoningSummaryValue.concise), effort=ReasoningEffort.high)

                answer_parts: list[str] = []
                reasoning_parts: list[str] = []
                final_response: str | None = None

                async for n in turn.stream():
                    payload = n.payload

                    # reasoning deltas accumulate into the current section
                    if isinstance(payload, ReasoningSummaryTextDeltaNotification):
                        reasoning_parts.append(payload.delta)
                        continue

                    # ANY other event closes the reasoning section -> one narration block
                    if reasoning_parts:
                        section = "".join(reasoning_parts).strip()
                        reasoning_parts.clear()
                        if section:
                            on_intermediate_response(AdapterIntermediateResponse(
                                type=AdapterIntermediateResponseType.narration, body=section))

                    if isinstance(payload, AgentMessageDeltaNotification):
                        answer_parts.append(payload.delta)
                        continue

                    if isinstance(payload, ErrorNotification):
                        if payload.will_retry:
                            on_intermediate_response(AdapterIntermediateResponse(
                                type=AdapterIntermediateResponseType.narration,
                                body=f"Codex is retrying after an error: {payload.error.message}",
                            ))
                            continue
                        raise RuntimeError(payload.error.message)

                    if isinstance(payload, ItemCompletedNotification):
                        item = _thread_item_root(payload.item)

                        if isinstance(item, AgentMessageThreadItem):
                            if item.phase == MessagePhase.final_answer:
                                final_response = item.text
                            elif item.phase == MessagePhase.commentary:
                                on_intermediate_response(AdapterIntermediateResponse(
                                    type=AdapterIntermediateResponseType.narration,
                                    body=item.text,
                                ))
                            continue

                        tool_summary = _tool_summary(item)
                        if tool_summary is not None:
                            on_intermediate_response(AdapterIntermediateResponse(
                                type=AdapterIntermediateResponseType.tool,
                                body=tool_summary,
                            ))
                # todo: refactor to a cleaner way than duplicating this code from within the loop here
                if reasoning_parts:
                    section = "".join(reasoning_parts).strip()
                    reasoning_parts.clear()
                    if section:
                        on_intermediate_response(AdapterIntermediateResponse(
                            type=AdapterIntermediateResponseType.narration, body=section))

                self._update_session_id(thread.id)
                return AdapterFinalResponse(
                    body=final_response if final_response is not None else "".join(
                        answer_parts),
                )

        except Exception:
            logger.exception("CodexAdapter call failed")
            return None

# todo: move helper methods

def _thread_item_root(item: object) -> object:
    return getattr(item, "root", item)


def _tool_summary(item: object) -> str | None:
    if isinstance(item, CommandExecutionThreadItem):
        exit_code = "" if item.exit_code is None else f", exit {item.exit_code}"
        return f"command: {_truncate(item.command)} -> {item.status.value}{exit_code}; {_output_size(item.aggregated_output)}"

    if isinstance(item, McpToolCallThreadItem):
        call = f"{item.server}.{item.tool}({_safe_json(item.arguments)})"
        if item.error is not None:
            result = f"error: {_truncate(item.error.message)}"
        elif item.result is not None:
            result = f"result: {_plural(_mcp_content_count(item.result), 'content item')}"
        else:
            result = "result: none"
        return f"mcp tool: {call} -> {item.status.value}; {result}"

    if isinstance(item, FileChangeThreadItem):
        paths = _paths_summary(change.path for change in item.changes)
        return f"file change: {item.status.value}; {paths}"

    if isinstance(item, DynamicToolCallThreadItem):
        tool = item.tool if item.namespace is None else f"{item.namespace}.{item.tool}"
        return f"tool: {tool}({_safe_json(item.arguments)}) -> {item.status.value}"

    if isinstance(item, WebSearchThreadItem):
        return f"web search: {_truncate(item.query)}"

    return None


def _output_size(output: str | None) -> str:
    if not output:
        return "output: none"
    return f"output: {_plural(_line_count(output), 'line')}, {_plural(len(output.encode('utf-8')), 'byte')}"


def _mcp_content_count(result: Any) -> int:
    content: object = getattr(result, "content", None)
    if isinstance(content, Sized) and not isinstance(content, (str, bytes)):
        return len(content)
    return 0


def _paths_summary(paths: Any) -> str:
    path_list = [str(path) for path in paths]
    if not path_list:
        return "no paths"
    shown = ", ".join(_truncate(path, 120) for path in path_list[:5])
    remaining = len(path_list) - 5
    return shown if remaining <= 0 else f"{shown}, +{remaining} more"


def _safe_json(value: Any) -> str:
    try:
        return _truncate(json.dumps(value, ensure_ascii=False, default=str))
    except TypeError:
        return _truncate(str(value))


def _line_count(text: str) -> int:
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _truncate(value: str, max_chars: int = 500) -> str:
    return value if len(value) <= max_chars else value[:max_chars - 3] + "..."
