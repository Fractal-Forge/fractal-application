from fractal_core import EnhancedEncoder
from pydantic import BaseModel


class BaseModelEnhancedEncoder(EnhancedEncoder):
    def default(self, o):
        if isinstance(o, BaseModel):
            return o.dict()
        return super(BaseModelEnhancedEncoder, self).default(o)
