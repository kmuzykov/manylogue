from enum import Enum

class ChatMode(str, Enum):
    # agents reply only when addressed (not yet implemented)
    mentions = "mentions"
    # agents are invoked in a round-robin manner and have a chance to react or skip
    round_robin = "round_robin"
