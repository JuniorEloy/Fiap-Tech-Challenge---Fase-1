from pydantic import BaseModel, ConfigDict


class LogoutResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)
