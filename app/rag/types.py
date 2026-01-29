from typing import TypedDict, List, Any

class ChatTurn(TypedDict):
    user: str
    bot: str
    sources: List[Any]  # später: besser typisieren (Document)