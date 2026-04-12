from pydantic import BaseModel, ConfigDict
import datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime.datetime
