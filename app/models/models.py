from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Shared Pydantic base model with camelCase JSON aliasing.

    All request/response models in this service inherit from this class.
    ``alias_generator`` auto-converts snake_case attribute names to
    camelCase in JSON serialization/deserialization, matching wire-format
    conventions (e.g. ``access_token`` in Python ↔ ``accessToken`` in JSON).

    ``populate_by_name=True`` allows construction with either snake_case
    or camelCase keys.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, extra="forbid", populate_by_name=True
    )
