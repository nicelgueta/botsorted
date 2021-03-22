from pydantic import BaseModel,validator  # pylint: disable=no-name-in-module
from ..config import config

class Interval(BaseModel):
    value: str
    @validator('value')
    def valid_interval(cls, v):
        if v not in config['validIntervals'].keys():
            raise ValueError(
            f"{v} not a valid interval. Must be one of: {list(config['validIntervals'].keys())}"
            )
        return v
