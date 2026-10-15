from typing import Annotated, Any, Literal, Optional, Union
from pydantic import BaseModel, Field, TypeAdapter


class FillNulls(BaseModel):
    op: Literal["fill_nulls"]
    column: str
    strategy: Literal["mean", "median", "mode", "constant"]
    value: Any = None


class DropDuplicates(BaseModel):
    op: Literal["drop_duplicates"]
    columns: Optional[list[str]] = None
    keep: Literal["first", "last"] = "first"


class RenameColumn(BaseModel):
    op: Literal["rename_column"]
    column: str
    new_name: str


class DropNulls(BaseModel):
    op: Literal["drop_nulls"]
    columns: Optional[list[str]] = None  # None = all columns
    how: Literal["any", "all"] = "any"


class CastType(BaseModel):
    op: Literal["cast_type"]
    column: str
    to: Literal["int", "float", "str", "bool", "datetime"]


class TrimText(BaseModel):
    op: Literal["trim_text"]
    column: str


class ChangeCase(BaseModel):
    op: Literal["change_case"]
    column: str
    case: Literal["lower", "upper", "title"]


class FilterRows(BaseModel):
    """Keeps rows that match. Null cells never match a comparison."""
    op: Literal["filter_rows"]
    column: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte",
                      "contains", "is_null", "not_null"]
    value: Any = None


class SortRows(BaseModel):
    op: Literal["sort"]
    column: str
    ascending: bool = True  # nulls always last


class DropColumn(BaseModel):
    op: Literal["drop_column"]
    column: str


Operation = Annotated[
    Union[FillNulls, DropDuplicates, RenameColumn, DropNulls, CastType,
          TrimText, ChangeCase, FilterRows, SortRows, DropColumn],
    Field(discriminator="op"),
]
_adapter = TypeAdapter(Operation)


def parse_op(data: dict):
    return _adapter.validate_python(data)


class OpResult(BaseModel):
    op: str
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int
    cells_changed: int
    message: str