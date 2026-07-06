import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Form, Path as PathParam, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.sse import EventSourceResponse, ServerSentEvent

from manylogue import config
from manylogue.chat import ChatRoom, HUMAN_NAME
from manylogue.util import render_message_fragment, resolve_existing_dir, templates
from manylogue.agents import AgentDefinition, AddAgentParticipantsRequest
from manylogue.messages import MessageDraft, MessageKind

# Layered: process env > <home>/.manylogue/.env > ./.env — before any config vars are read.
config.load_env()

# Logging — root at INFO so third-party DEBUG stays quiet; our manylogue.* loggers stay verbose.
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s %(levelname)s: %(message)s",
)
# Keep OUR code logging verbose; third-party libs stay at INFO to avoid DEBUG clutter
logging.getLogger("manylogue").setLevel(
    os.environ.get("MANYLOGUE_LOG_LEVEL", "DEBUG").upper())

logger = logging.getLogger(__name__)

BASE = Path(__file__).parent

# Chat id regex — mirrors the storage-side check; rejects path traversal.
CHAT_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"

# In-memory registry of live chat rooms, keyed by chat id.
chats: dict[str, ChatRoom] = {}

# --- Setup FastAPI ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Prime the cached home: resolves + seeds <home>/.manylogue once, at startup rather than
    # on the first request (so first-run seeding errors surface at boot).
    config.home()
    yield
    for chat in chats.values():
        await chat.stop()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/")
async def home(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"chats": ChatRoom.list_chats(config.home())})


@app.post("/chats")
async def create_chat(request: Request,
                      chat_name: str = Form(""),
                      chat_project_dir: str = Form("")) -> Response:

    # Validate before creating anything. On failure, re-render the home form with an
    # inline error and the user's input preserved — never a 500. resolve_existing_dir
    # rejects files and empty input, and expands ~ so "~/project" is a valid entry.
    project_dir = resolve_existing_dir(chat_project_dir)
    if project_dir is None:
        return templates.TemplateResponse(
            request=request, name="index.html",
            context={
                "chats": ChatRoom.list_chats(config.home()),
                "error": "That project directory doesn't exist. Enter an absolute path (or ~/path) to a folder.",
                "prefill": {"chat_name": chat_name, "chat_project_dir": chat_project_dir},
            },
            status_code=422,
        )

    room = _activate(ChatRoom.create(
        config.home(), project_dir, chat_name.strip() or "untitled"))
    return RedirectResponse(url=f"/chat/{room.chat_id}", status_code=303)


@app.get("/chats-list")
async def chats_list(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request, name="_chats-list.html",
        context={"chats": ChatRoom.list_chats(config.home())})


@app.get("/chat/{chat_id}")
async def chat(request: Request,
               chat_id: str = PathParam(pattern=CHAT_ID_PATTERN)) -> Response:

    current_chat = get_open_chat(chat_id)
    if current_chat is None:
        return Response(status_code=404)

    agent_definitions = AgentDefinition.load_all(config.home())

    context = {
        "chat_id": current_chat.chat_id,
        "chat_name": current_chat.name,
        "participants": current_chat.get_participants_view(),
        "available_agents": agent_definitions,
        "default_project_path": current_chat.default_project_dir,
    }
    return templates.TemplateResponse(request=request, name="chat.html", context=context)


@app.post("/chat/{chat_id}")
async def chat_post_message(chat_text_msg: str = Form(),
                            chat_id: str = PathParam(pattern=CHAT_ID_PATTERN)) -> Response:

    current_chat = get_open_chat(chat_id)
    if current_chat is None:
        return Response(status_code=404)

    human_message = MessageDraft(
        kind=MessageKind.message, author=HUMAN_NAME, body=chat_text_msg)
    await current_chat.append(human_message)

    return Response(status_code=204)


@app.get("/chat/{chat_id}/stream", response_class=EventSourceResponse)
async def chat_stream(request: Request, since: str | None = None,
                      chat_id: str = PathParam(pattern=CHAT_ID_PATTERN)):
    current_chat = get_open_chat(chat_id)
    if current_chat is None:
        return

    # Last-Event-ID wins on reconnect
    cursor = request.headers.get("last-event-id") or since

    agent_stream_queue = current_chat.subscribe_to_agent_stream()
    commited_messages_task = asyncio.create_task(
        current_chat.process_existing_messages_or_wait_for_new(cursor))
    agent_stream_events_task = asyncio.create_task(agent_stream_queue.get())

    try:
        while True:
            done, _ = await asyncio.wait(
                {commited_messages_task, agent_stream_events_task}, return_when=asyncio.FIRST_COMPLETED)

            if commited_messages_task in done:
                for m in commited_messages_task.result():
                    yield ServerSentEvent(raw_data=render_message_fragment(m), id=m.id)
                    cursor = m.id
                commited_messages_task = asyncio.create_task(
                    current_chat.process_existing_messages_or_wait_for_new(cursor))

            if agent_stream_events_task in done:
                event = agent_stream_events_task.result()
                data: dict[str, str] = {"author": event.author}
                if event.response is not None:
                    data["type"] = event.response.type.value
                    data["body"] = event.response.body
                if event.outcome is not None:
                    data["outcome"] = event.outcome.value
                yield ServerSentEvent(event=event.type.value, data=data)

                agent_stream_events_task = asyncio.create_task(
                    agent_stream_queue.get())
    except asyncio.CancelledError:
        # Server shutdown (timeout_graceful_shutdown) or client teardown cancels the
        # stream mid-await. End it quietly — otherwise every open tab turns Ctrl+C
        # into an "Exception in ASGI application" traceback.
        pass
    finally:
        commited_messages_task.cancel()
        agent_stream_events_task.cancel()
        current_chat.unsubscribe_from_agent_stream(agent_stream_queue)


@app.post("/chat/{chat_id}/participants")
async def chat_add_participant(body: AddAgentParticipantsRequest,
                               chat_id: str = PathParam(pattern=CHAT_ID_PATTERN)) -> Response:

    current_chat = get_open_chat(chat_id)
    if current_chat is None:
        return Response(status_code=404)

    for ref in body.participants:
        current_chat.add_participant_by_def(ref.name, ref.directory)

    # the client reloads to re-render the roster
    return Response(status_code=204)


def _activate(room: ChatRoom) -> ChatRoom:
    """Register in the live registry, and start the worker."""
    chats[room.chat_id] = room
    room.start()
    return room


def get_open_chat(chat_id: str) -> ChatRoom | None:
    if chat_id in chats:
        return chats[chat_id]
    room = ChatRoom.open(config.home(), chat_id)
    if room is None:
        return None
    return _activate(room)
