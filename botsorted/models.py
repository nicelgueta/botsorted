from pydantic import BaseModel, validator  # pylint: disable=no-name-in-module


class Symbol(BaseModel):
    base: str
    quote: str

    def conc(self):
        return self.base + self.quote
