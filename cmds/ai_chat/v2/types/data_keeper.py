from typing import Optional, TypedDict
from typing_extensions import NotRequired


class ProviderData(TypedDict):
    api_key: Optional[str]
    base_url: str
    models: NotRequired[list]