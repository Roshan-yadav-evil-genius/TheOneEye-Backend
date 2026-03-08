from enum import Enum

class ConnectionStatus(Enum):
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    PENDING = "pending"


class FollowingStatus(Enum):
    NOT_FOLLOWING = "not_following"
    FOLLOWING = "following"