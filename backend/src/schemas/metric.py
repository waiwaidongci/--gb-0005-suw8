from pydantic import BaseModel,Field
class MetricInput(BaseModel):
    key: str=Field(pattern=r"^[a-z][a-z0-9_]{1,39}$")
    name: str=Field(min_length=2,max_length=80)
    expression: str=Field(min_length=1,max_length=200)
    unit: str=Field(default="元",max_length=16)
    description: str=Field(min_length=8,max_length=600)
