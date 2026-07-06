import re
from pathlib import Path
import tomllib
from pydantic import BaseModel, ConfigDict


class AgentDefinition(BaseModel):
    """A reusable agent recipe from <home>/.manylogue/agents/<name>.toml: which adapter
    (brain) to run, which role file (soul) to load, and the model. Defined once, offered
    in the participant picker, and resolved into a live Agent when added to a chat.
    """
    model_config = ConfigDict(frozen=True)

    adapter: str
    name: str
    description: str
    role: str
    model: str

    @staticmethod
    def __load(agent_definition_file: Path) -> "AgentDefinition":

        with open(agent_definition_file, "rb") as f:
            raw_data = tomllib.load(f)

        raw_data["name"] = agent_definition_file.stem
        agent_def = AgentDefinition.model_validate(raw_data)
        return agent_def

    @staticmethod
    def load_all(workspace_root: Path) -> tuple["AgentDefinition", ...]:

        # todo: util to handle common paths and add ".manylogue"
        agent_definitions_dir = workspace_root / ".manylogue" / "agents"
        if not agent_definitions_dir.is_dir():
            return ()

        return tuple(
            AgentDefinition.__load(f)
            for f in sorted(agent_definitions_dir.glob("*.toml"))
        )

    @staticmethod
    def load_one(workspace_root: Path, agent_def_name: str) -> "AgentDefinition | None":

        # agent_def_name is client input — only a bare file stem is allowed (kills path
        # traversal), and a missing file resolves to None so callers degrade gracefully.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", agent_def_name):
            return None

        # todo: util to handle common paths and add ".manylogue"
        agent_file = workspace_root / ".manylogue" / "agents" / f"{agent_def_name}.toml"
        if not agent_file.is_file():
            return None
        return AgentDefinition.__load(agent_file)
