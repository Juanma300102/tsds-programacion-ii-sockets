from enum import Enum
import json


class MessageTypeEnum(Enum):
    CLIENT_TO_CLIENT = 1
    CLIENT_TO_SERVER = 2
    SERVER_TO_CLIENT = 3
    CLIENT_LIST_UPDATE = 4


class Message:
    message_type: MessageTypeEnum
    message: str
    destination: str | None

    def __init__(
        self, type: MessageTypeEnum, message: str, destination: str | None = None
    ) -> None:
        self.message_type = type
        self.message = message
        self.destination = destination
        self.validate()

    def validate(self):
        if not self.message_type in MessageTypeEnum:
            raise ValueError("The received message type isn't valid")
        if (
            self.message_type == MessageTypeEnum.CLIENT_TO_CLIENT
            and not self.destination
        ):
            raise ValueError("A destination needed for CLIENT TO CLIENT communication")

    def dump(self) -> bytes:
        repr_ = {
            "message_type": self.message_type.value,
            "message": self.message,
            "destination": self.destination,
        }
        return json.dumps(repr_).encode("utf-8")
