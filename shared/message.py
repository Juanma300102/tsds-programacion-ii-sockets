from enum import Enum
import json
import logging
from typing import Self

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure the logger
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class MessageTypeEnum(Enum):
    CLIENT_TO_CLIENT = 1
    CLIENT_TO_SERVER = 2
    SERVER_TO_CLIENT = 3
    CLIENT_LIST_UPDATE = 4
    DISCONNECT_NOTIFICATION = 5
    UPDATE_CLIENT_ALIAS = 6
    GENERATED_CLIENT_UUID = 7


class Message:
    message_type: MessageTypeEnum
    message: str
    destination: str | None
    from_: str | None

    def __init__(
        self,
        type: MessageTypeEnum,
        message: str,
        destination: str | None = None,
        from_: str | None = None,
    ) -> None:
        self.message_type = type
        self.message = message
        self.destination = destination
        self.from_ = from_
        self.validate()

    def validate(self):
        if not self.message_type in MessageTypeEnum:
            raise ValueError("The received message type isn't valid")
        if (
            self.message_type == MessageTypeEnum.CLIENT_TO_CLIENT
            and not self.destination
            and not self.from_
        ):
            raise ValueError(
                "Properties Destination and/or From needed for CLIENT TO CLIENT communication"
            )

    def dump(self) -> bytes:
        repr_ = {
            "message_type": self.message_type.value,
            "message": self.message,
            "destination": self.destination,
            "from": self.from_,
        }
        return json.dumps(repr_).encode("utf-8")

    @classmethod
    def decode(cls, data: bytes) -> Self:
        try:
            loaded = json.loads(data.decode("utf-8"))
            return Message(
                type=MessageTypeEnum(int(loaded["message_type"])),
                message=loaded["message"],
                destination=loaded["destination"],
                from_=loaded["from"],
            )
        except json.decoder.JSONDecodeError as err:
            raise err
        except ValueError as err:
            raise err
