from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class ImportJobBaseSchema(BaseModel):
    
    entity_type: Literal["lead", "contact", "product", "order"] = Field(..., example="lead")
    import_type: Literal["create", "update", "upsert"] = Field("create", example="create")
    unique_field: Optional[str] = Field(None, example="email")
    assign_group_ids: Optional[List[int]] = Field(None, example=[1,2])
    assign_tag_ids: Optional[List[int]] = Field(None, example=[1,2])
    