from typing import Annotated, Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from jobtrail.config import get_settings

_settings = get_settings()

Timestamp = AwareDatetime
Limit = Annotated[int, Field(ge=1, le=_settings.max_page_limit)]
Offset = Annotated[int, Field(ge=0)]
YearMonth = Annotated[
    str,
    Field(
        pattern=r"^\d{4}-\d{2}(-\d{2})?$",
        description="YYYY-MM または YYYY-MM-DD",
    ),
]


class InputModel(BaseModel):
    """未知のフィールドは拒否する（Claude の項目名の誤りを早く知らせるため）。"""

    model_config = ConfigDict(extra="forbid")


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmptyInput(InputModel):
    pass


class PageInput(InputModel):
    limit: Limit = _settings.default_page_limit
    offset: Offset = 0


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorOutput(BaseModel):
    code: str
    message: str
    hint: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class PingOutput(OutputModel):
    status: str
    version: str
