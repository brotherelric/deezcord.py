from __future__ import annotations
from datetime import datetime

from typing import TYPE_CHECKING, Any, Coroutine, Dict, Optional, List, Tuple, Union, overload

from . import utils
from .user import User, PartialUser
from .member import Member
from .mixins import Hashable
from .enums import EntityType, EventStatus, PrivacyLevel
from .channel import StageChannel, VoiceChannel

if TYPE_CHECKING:
    from .types.event import (
        EntityMetadata,
        Event as EventPayload,
    )
    from .types.snowflake import Snowflake
    from .guild import Guild
    from .state import ConnectionState

MISSING = utils.MISSING

__all__ = (
    'ScheduledEvent',
)

class ScheduledEvent(Hashable):

    __slots__: Tuple[str, ...] = (
        'guild',
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
        '_state',
        '_subscribers'
    )

    def __init__(self, *, guild: Guild, state: ConnectionState, data: EventPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._subscribers: Dict[int, PartialUser] = {}
        self._update(guild, data)

    def _add_subscriber(self, user: PartialUser, /):
        self._subscribers[user.id] = user
    def _remove_subscriber(self, user: PartialUser, /):
        self._subscribers.pop(user.id, None)
    
    def get_subscriber(self, id: int) -> Optional[PartialUser]:
        return self._subscribers.get(id)

    @property
    def subscribers(self) -> List[PartialUser]:
        # TODO: autoset this on guild guild sync, but discord needs to implement something for this
        return self._subscribers.values()
    @property
    def location(self) -> Union[str, VoiceChannel, StageChannel]:
        return (
            self.entity_metadata and self.entity_metadata.get('location')
        ) or self._state.get_channel(self.channel_id)
    @property
    def channel(self) -> Union[VoiceChannel, StageChannel]:
        return self._state.get_channel(self.channel_id) if self.channel_id else None


    def _update(self, guild: Guild, data: EventPayload):
        self.guild: Guild = guild
        self.channel_id: Optional[int] = utils._get_as_snowflake(data, 'channel_id')
        self.creator_id: Optional[int] = utils._get_as_snowflake(data, 'creator_id')
        self.name: str = data['name']
        self.description: Optional[str] = data['description']
        self.image: Optional[str] = data['image']
        self.scheduled_start_time: datetime = datetime.fromisoformat(data['scheduled_start_time']).astimezone()
        self.scheduled_end_time: Optional[datetime] = utils.parse_time(data['scheduled_end_time'])
        self.privacy_level: PrivacyLevel = PrivacyLevel(data['privacy_level'])
        self.status: EventStatus = EventStatus(data['status'])
        self.entity_type: EntityType = EntityType(data['entity_type'])
        self.entity_metadata: EntityMetadata = data['entity_metadata']
        self.sku_ids: List[int] = [int(x) for x in data['sku_ids']]
        self.creator: Optional[Union[User, PartialUser]] = (
            'creator' in data and User(state=self._state, data=data['creator'])
        ) or self._state.get_user(self.creator_id) or PartialUser(state=self._state, id=self.creator_id)
    
    async def delete(self, *, reason: Optional[str] = None):
        return await self._state.http.delete_event(self.guild.id, self.id, reason=reason)

    # only available to user-bots
    # async def subscribe(self):
    #     return await self._state.http.subscribe_event(self.guild.id, self.id)
    # async def unsubscribe(self):
    #     return await self._state.http.unsubscribe_event(self.guild.id, self.id)

    async def fetch_subscribers(
        self, 
        *,
        limit: int=100,
        with_member: bool=True,
        before: Snowflake=None,
        after: Snowflake=None
    ):
        data = await self._state.http.get_event_subscribers(self.guild.id, self.id,
            limit=limit, with_member=with_member, before=before, after=after
        )
        if not with_member:
            return [User(state=self._state, data=d['user']) for d in data]
        return [
            # with_member returns {'user': ...}, {'member': ...}, we need to cnvert it to MemberWithUser
            Member(state=self._state, data=(c['member'] | {'user': c['user']}), guild=self.guild)
                for c in data
        ]

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