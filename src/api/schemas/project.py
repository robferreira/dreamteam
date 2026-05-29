from typing import Any

from pydantic import BaseModel, EmailStr, Field


class ProjectMetadataSchema(BaseModel):
    system_name: str = Field(..., min_length=2, max_length=256)
    system_description: str = Field(..., min_length=10)
    owner_name: str = Field(..., min_length=2)
    owner_email: EmailStr
    area: str = Field(..., min_length=2)
    organization: str | None = None
    stack_hint: str | None = None
    additional_context: dict[str, Any] | None = None

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "system_name": self.system_name,
            "system_description": self.system_description,
            "owner_name": self.owner_name,
            "owner_email": str(self.owner_email),
            "area": self.area,
            "organization": self.organization,
            "stack_hint": self.stack_hint,
            "additional_context": self.additional_context or {},
        }


class ProjectResponse(BaseModel):
    id: str
    slug: str
    system_name: str
    system_description: str
    owner_name: str
    owner_email: str
    area: str
    organization: str | None = None
    stack_hint: str | None = None
    stack_resolved: str | None = None
    root_path: str
    files: list[str] = Field(default_factory=list)
    created_at: str | None = None
