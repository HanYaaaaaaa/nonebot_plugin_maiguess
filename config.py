from pydantic import BaseModel
from .guess import *


class Config(BaseModel):
    guesspath: str
    picpath: str
