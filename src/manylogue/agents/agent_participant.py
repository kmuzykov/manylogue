"""Participant records — a chat seat as data.

The durable on-disk record (with its embedded agent state) and the wire shape
the UI sends to add seats to a room. The live behavior behind a seat lives in
Agent / MissingAgent.
"""

from pydantic import BaseModel, ConfigDict, Field


class AgentState(BaseModel):
    """The resumable part of a seat: message cursor + adapter session id."""
    model_config = ConfigDict(frozen=True)
    last_seen_message_id: str | None
    adapter_session_id: str | None


class PersistedParticipant(BaseModel):
    """Durable face of a chat participant: how to rebuild it (def_name), its resolved
    seat identity (name), its cwd, and its live cursor/session (state).

    One record per seat in participants.json. A live Agent derives this from itself
    (to_record); a MissingAgent round-trips the record it was loaded with verbatim, so a
    temporarily renamed/deleted def keeps its place and resumes from its saved cursor.
    """
    model_config = ConfigDict(frozen=True)
    def_name: str          # agent-def id == the toml file stem, used to reload the def
    name: str              # resolved (deduped) seat name == Agent.agent_name
    directory: str         # cwd for this seat
    state: AgentState = Field(
        default_factory=lambda: AgentState(
            last_seen_message_id=None, adapter_session_id=None))


class AgentParticipantRef(BaseModel):
    """One seat in an add-participants request: which definition, run where."""
    name: str          # agent-def id == the toml file stem
    directory: str     # cwd for this seat; today = chat default, later = per-agent override


class AddAgentParticipantsRequest(BaseModel):
    participants: list[AgentParticipantRef]
