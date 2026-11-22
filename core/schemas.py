
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional


class DocumentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_code: str = Field(min_length=1)
    description: str = Field(min_length=1)
    quantity: float = Field(ge=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    amount: Optional[float] = Field(default=None, ge=0)


class BusinessDocument(BaseModel):
    document_type: str
    document_number: Optional[str] = None
    po_number: Optional[str] = None
    buyer: Optional[str] = None
    supplier: Optional[str] = None
    items: list[DocumentItem]
    total_amount: Optional[float] = None

    @model_validator(mode="after")
    def check_duplicate_items(self):
        seen = set()

        for item in self.items:
            code = item.item_code.strip().upper()

            if code in seen:
                raise ValueError(
                    f"Duplicate item code detected: {code}. "
                    "Check the original document and extract "
                    "each product row exactly once."
                )

            seen.add(code)

        return self
