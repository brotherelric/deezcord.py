from typing import TypedDict, Literal, Optional, List

from .user import PartialUser

PrivacyLevel = Literal[2]
EntityType = Literal[1, 2, 3]
EventStatus = Literal[1, 2, 3, 4]

class EntityMetadata(TypedDict, total=False):
    location: Optional[str]
class Event(TypedDict):
    id: str
    guild_id: str
    channel_id: Optional[str]
    creator_id: Optional[str] # not available for events before October 25th, 2021
    name: str
    description: Optional[str]
    image: Optional[str]
    scheduled_start_time: str
    scheduled_end_time: Optional[str]
    privacy_level: PrivacyLevel
    status: EventStatus
    entity_type: EntityType
    entity_id: str
    entity_metadata: Optional[EntityMetadata]
    sku_ids: List[str]
    creator: Optional[PartialUser]
    user_count: Optional[int]