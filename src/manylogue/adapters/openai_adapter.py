import json
import logging
from collections.abc import Callable, Sequence

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from manylogue.messages.adapter_response import AdapterFinalResponse, AdapterIntermediateResponse
from manylogue.adapters.base_adapter import BaseAdapter
from manylogue.messages import Message


OPENAI_DEFAULT_URL = "http://localhost:11434/v1"
OPENAI_DEFAULT_MODEL = "llama3.2:1b"
OPENAI_DEFAULT_API_KEY = "ollama"

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    """Adapter for any OpenAI-compatible Chat Completions endpoint.

    Stateless: there is no server-side session, so every call resends the system
    prompt, the roster, and the entire visible history. The defaults point at a
    local Ollama server, but any /v1/chat/completions endpoint works.
    Conversation-only for now — no file or tool access.
    """

    _base_url: str
    _model: str
    _api_key: str
    _openai_client: AsyncOpenAI

    def __init__(self,
                 working_dir: str,
                 base_url: str = OPENAI_DEFAULT_URL,
                 model: str = OPENAI_DEFAULT_MODEL,
                 api_key: str = OPENAI_DEFAULT_API_KEY) -> None:

        super().__init__(working_dir)
        self._base_url = base_url
        self._model = model
        self._api_key = api_key
        self._openai_client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=self._api_key)

    async def get_response(self,
                           agent_name: str,
                           system_prompt: str,
                           roster: Sequence[str],
                           full_history: Sequence[Message],
                           new_messages: Sequence[Message],
                           on_intermediate_response: Callable[[
                               AdapterIntermediateResponse], None]
                           ) -> AdapterFinalResponse | None:

        try:
            messages: list[ChatCompletionMessageParam] = []

            # Stateless, so the system message is rebuilt every call and always carries
            # the current roster (no send-on-change caching like the stateful adapters).
            messages.append(
                {"role": "system", "content": f"{system_prompt}\n\n{self._roster_line(roster)}"})

            messages.extend([self._convert_message(agent_name, m)
                            for m in full_history])

            logger.debug("Sending to OpenAI Adapter: (%s):\n%s",
                         self._model,
                         json.dumps(messages, indent=2))

            response = await self._openai_client.chat.completions.create(
                model=self._model, messages=messages)
            answer = response.choices[0].message.content

            logger.info("OpenAI Adapter answer: (%s): %s", self._model, answer)

            if answer is not None:
                return AdapterFinalResponse(body=answer)

        except Exception:
            logger.exception("OpenAIAdapter call failed")

        return None

    def _convert_message(self, agent_name: str, message: Message) -> ChatCompletionMessageParam:
        if agent_name == message.author:
            return {"role": "assistant", "content": message.body}   # no prefix
        return {"role": "user", "content": f"[{message.author}]\n{message.body}"}
