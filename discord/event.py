from __future__ import annotations
from datetime import datetime

from typing import TYPE_CHECKING, Any, Coroutine, Dict, Optional, List, Tuple, Union, overload


from . import utils
from .user import User
from .mixins import Hashable
from .enums import EntityType, EventStatus, PrivacyLevel
from .channel import StageChannel, VoiceChannel

if TYPE_CHECKING:
    from .types.event import (
        EntityMetadata,
        Event as EventPayload,
    )
    from .guild import Guild
    from .state import ConnectionState

MISSING = utils.MISSING


class ScheduledEvent(Hashable):

    __slots__: Tuple[str, ...] = (
        'guild',
        '_state',
        'id',

        'channel_id',
        'creator_id',
        'name',
        'description',
        'image',
        'scheduled_start_time',
        'scheduled_end_time',
        'privacy_level',
        'status',
        'entity_type',
        'entity_metadata',
        'sku_ids',
        'creator',
    )

    def __init__(self, *, guild: Guild, state: ConnectionState, data: EventPayload):
        self.guild: Guild = guild
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(data)
    
    @property
    def location(self) -> Union[str, VoiceChannel, StageChannel]:
        return self._entity_metadata.get('location', self._state.get_channel(self.channel_id))
    @property
    def channel(self) -> Union[VoiceChannel, StageChannel]:
        return self._state.get_channel(self.channel_id) if self.channel_id else None

    def _update(self, data: EventPayload):
        self.channel_id: Optional[int] = utils._get_as_snowflake(data, 'channel_id')
        self.creator_id: Optional[int] = utils._get_as_snowflake(data, 'creator_id')
        self.name: str = data['name']
        self.description: Optional[str] = data['description']
        self.image: Optional[str] = data['image']
        self.scheduled_start_time: datetime = datetime.fromisoformat(data['scheduled_start_time']).astimezone()
        self.scheduled_end_time: Optional[datetime] = datetime.fromisoformat(data['scheduled_end_time']).astimezone()
        self.privacy_level: PrivacyLevel = PrivacyLevel(data['privacy_level'])
        self.status: EventStatus = EventStatus(data['status'])
        self.entity_type: EntityType = EntityType(data['entity_type'])
        self.entity_metadata: EntityMetadata = data['entity_metadata']
        self.sku_ids: List[int] = [int(x) for x in data['sku_ids']]
        self.creator: Optional[User] = (
            User(state=self._state, data=data['creator']) 
                if 'creator' in data else None
        )
    
    async def delete(self, *, reason: Optional[str] = None):
        return await self._state.http.delete_event(self.guild.id, self.id, reason=reason)

    @overload
    async def edit(
        self,
        *, 
        reason: str = ...,
        location: Union[VoiceChannel, StageChannel, str] = ...,
        name: str = ...,
        description: str = ...,
        scheduled_start_time: str = ...,
        scheduled_end_time: str = ...,
        privacy_level: str = ...,
        status: EventStatus = ...
    ) -> ScheduledEvent:
        ...
    async def edit(self, *, reason: Optional[str]=None, **options: Dict[str, Any]):
        fields: Dict[str, Any] = {}
        if 'location' in options:
            location = options.pop('location')
            if isinstance(location, StageChannel):
                fields['channel_id'] = location.id
                fields['entity_metadata'] = {}
                fields['entity_type'] = EntityType.stage_instance
            elif isinstance(location, VoiceChannel):
                fields['channel_id'] = location.id
                fields['entity_metadata'] = {}
                fields['entity_type'] = EntityType.voice.value
            elif isinstance(location, str):
                fields['channel_id'] = None
                fields['entity_metadata'] = {'location': location}
                fields['entity_type'] = EntityType.external.value
        if 'scheduled_start_time' in options:
            fields['scheduled_start_time'] = options.pop('scheduled_start_time').astimezone().isoformat()
        if 'scheduled_end_time' in options:
            fields['scheduled_end_time'] = options.pop('scheduled_end_time').astimezone().isoformat()
        if 'name' in options:
            fields['name'] = options.pop('name')
        if 'description' in options:
            fields['description'] = options.pop('description')
        if 'privacy_level' in options:
            fields['privacy_level'] = options.pop('privacy_level')
        if 'status' in options:
            fields['status'] = options.pop('status').value
        data = await self._state.http.edit_event(self.guild.id, self.id, reason=reason, **fields)
        if data:
            return self.__class__(
                guild=self.guild, 
                state=self._state, 
                data=data
            )