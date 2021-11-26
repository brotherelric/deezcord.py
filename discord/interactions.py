# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple, Union, overload

from discord.types.interactions import InteractionData


from . import utils
from .http import Route
from .enums import try_enum, InteractionType, InteractionResponseType
from .errors import InteractionResponded, HTTPException, ClientException, InvalidArgument
from .channel import PartialMessageable, ChannelType

from .user import User
from .member import Member
from .flags import MessageFlags
from .message import Message, Attachment
from .object import Object
from .permissions import Permissions
from .webhook.async_ import async_context, Webhook, handle_message_parameters
from .components import ComponentStore, Component, Button, SelectMenu, SelectOption

__all__ = (
    'Interaction',
    'ResponseMessage',
    'ComponentInteraction',
    'ButtonInteraction',
    'SelectInteraction'
)

if TYPE_CHECKING:
    from .types.interactions import (
        Interaction as InteractionPayload,
    )
    from .guild import Guild
    from .state import ConnectionState
    from .file import File
    from .mentions import AllowedMentions
    from .embeds import Embed
    from .channel import VoiceChannel, StageChannel, TextChannel, CategoryChannel, StoreChannel, PartialMessageable
    from .threads import Thread

    InteractionChannel = Union[
        VoiceChannel, StageChannel, TextChannel, CategoryChannel, StoreChannel, Thread, PartialMessageable
    ]

MISSING: Any = utils.MISSING



class ResponseMessage(Message):

    __slots__ = Message.__slots__ + ('application_id', 'token',)

    def __init__(self, *, state: ConnectionState, channel, data, application_id, token):
        super().__init__(state=state, channel=channel, data=data)
        self.token: str = token
        self.application_id: int = int(application_id)

    async def edit(
        self, 
        content: Optional[str],
        *,
        embed: Embed = MISSING, 
        embeds: List[Embed]=MISSING, 
        attachments: List[Attachment] = MISSING, 
        file: File= MISSING, 
        files: List[File] = MISSING,
        suppress: bool = MISSING, 
        delete_after: float = None, 
        allowed_mentions: AllowedMentions = MISSING, 
        components: List[Component] = MISSING
    ):
        """|coro|

        Edits the message.

        The content must be able to be transformed into a string via ``str(content)``.

        Parameters
        -----------
        content: Optional[:class:`str`]
            The new content to replace the message with.
            Could be ``None`` to remove the content.
        embed: Optional[:class:`Embed`]
            The new embed to replace the original with.
            Could be ``None`` to remove the embed.
        embeds: List[:class:`Embed`]
            The new embeds to replace the original with. Must be a maximum of 10.
            To remove all embeds ``[]`` should be passed.
        attachments: List[:class:`Attachment`]
            A list of attachments to keep in the message. If ``[]`` is passed
            then all attachments are removed.
        file: :class:`File`
            The file to upload. If you want to replace the currently uploaded file with this parameter,
            you have to set ``attachments`` to ``[]``.
        files: List[:class:`File`]
            A list of files to send with the content. This cannot be mixed with the
            ``file`` parameter.
        suppress: :class:`bool`
            Whether to suppress embeds for the message. This removes
            all the embeds if set to ``True``. If set to ``False``
            this brings the embeds back if they were suppressed.
            Using this parameter requires :attr:`~.Permissions.manage_messages`.
        delete_after: :class:`float`
            If provided, the number of seconds to wait in the background
            before deleting the message we just edited. If the deletion fails,
            then it is silently ignored.
        allowed_mentions: :class:`~discord.AllowedMentions`
            Controls the mentions being processed in this message. If this is
            passed, then the object is merged with :attr:`~discord.Client.allowed_mentions`.
            The merging behaviour only overrides attributes that have been explicitly passed
            to the object, otherwise it uses the attributes set in :attr:`~discord.Client.allowed_mentions`.
            If no object is passed at all then the defaults given by :attr:`~discord.Client.allowed_mentions`
            are used instead.
        components: List[:class:`~discord.Component`]
            The new message components to replace the message with.
            To remove all components ``[]`` should be passed.
        

        Raises
        -------
        HTTPException
            Editing the message failed.
        Forbidden
            Tried to suppress a message without permissions or
            edited a message's content or embed that isn't yours.
        ~discord.InvalidArgument
            You specified both ``embed`` and ``embeds``
        """
        payload = {}
        if content is not MISSING:
            if content is not None:
                payload['content'] = str(content)
            else:
                payload['content'] = None

        if embed is not MISSING and embeds is not MISSING:
            raise InvalidArgument('cannot pass both embed and embeds parameter to edit()')

        if embed is not MISSING:
            if embed is None:
                payload['embeds'] = []
            else:
                payload['embeds'] = [embed.to_dict()]
        elif embeds is not MISSING:
            payload['embeds'] = [e.to_dict() for e in embeds]

        if suppress is not MISSING:
            flags = MessageFlags._from_value(self.flags.value)
            flags.suppress_embeds = suppress
            payload['flags'] = flags.value

        if allowed_mentions is MISSING:
            if self._state.allowed_mentions is not None and self.author.id == self._state.self_id:
                payload['allowed_mentions'] = self._state.allowed_mentions.to_dict()
        else:
            if allowed_mentions is not None:
                if self._state.allowed_mentions is not None:
                    payload['allowed_mentions'] = self._state.allowed_mentions.merge(allowed_mentions).to_dict()
                else:
                    payload['allowed_mentions'] = allowed_mentions.to_dict()

        if attachments is not MISSING:
            payload['attachments'] = [a.to_dict() for a in attachments]

        if components is not MISSING:
            if components:
                payload['components'] = ComponentStore(components).to_dict()
            else:
                payload['components'] = []

        if file or files:
            self._update(await self._state.http.request(
                Route('PATCH', f'/webhooks/{self.application_id}/{self.token}/messages/{self.id}'),
                files=files or [file], form=utils.get_form(files or [file], payload)
            ))
        else:
            self._update(await self._state.http.request(
                Route('PATCH', f'/webhooks/{self.application_id}/{self.token}/messages/{self.id}'),
                json=payload
            ))
        if delete_after is not None:
            await self.delete(delay=delete_after)
    async def delete(self):
        """Override for delete function that will throw an exception"""
        raise NotImplementedError()

class Interaction:
    __slots__: Tuple[str, ...] = (
        '_state', 
        'deferred', 
        'responded', 
        '_deferred_hidden',
    
        'application_id',
        'token',
        'id',
        'type',
        'version',
        'data',
        'channel_id',
        'guild_id',
        'author',
        'message',
    )

    def __init__(self, state: ConnectionState, data: InteractionPayload) -> None:
        self._state = state
        
        self.deferred: bool = False
        self.responded: bool = False
        self._deferred_hidden: bool = False
 
        self.id: int = int(data["id"])
        """id of the interaction"""
        self.application_id: int = data["application_id"]
        """id of the application this interaction is for"""
        self.type: int = data["type"]
        """The type of interaction. See :class:`~InteractionType` for more information"""
        self.data: InteractionData = data["data"]
        """The passed data of the interaction"""
        self.channel_id: Optional[int] = utils._get_as_snowflake(data, "channel_id")
        """id of channel where the interaction was created"""
        self.guild_id: Optional[int] = utils._get_as_snowflake(data, "guild_id")
        """id of guild where the interaction was created"""
        self.author: Optional[Union[Member, User]] = None
        """The user who created the interaction"""
        self.token: str = data["token"]
        """a continuation token for responding to the interaction"""
        self.version: int = data["version"]
        """read-only property, always ``1``"""
        self.message: Optional[Message] = None
        """for components, the message they were attached to"""

        if data.get("member"):
            self.author = Member(data=data["member"], guild=self.guild, state=self._state)
        else:
            self.author = User(data=data["user"], guild=self.guild, state=self._state)

        if data.get("message"):
            self.message = Message(data=data["message"], channel=self.channel, state=self._state)
        
    @property
    def created_at(self):
        """The interaction's creation time in UTC"""
        return utils.snowflake_time(self.id)
    
    @property
    def guild(self) -> Optional[Guild]:
        """The guild where the interaction was created"""
        return self.guild_id and self._state._get_guild(self.guild_id)
    @property
    def channel(self) -> InteractionChannel:
        """The channel where the interaction was created"""
        return self._state.get_channel(self.channel_id) or self._state.get_channel(self.author.id)

    async def defer(self, *, hidden=False):
        """
        This will acknowledge the interaction. This will show the (*Bot* is thinking...) dialog
        .. note::
            
            This function should be used if the bot needs more than 15 seconds to respond
        
        Parameters
        ----------
        hidden: :class:`bool`, optional
            Whether the loading thing should be only visible to the user; default False.
        
        """
        if self.deferred:
            return

        payload = None
        if hidden is True:
            payload = {"flags": 64}
            self._deferred_hidden = True
        
        await self._state.http.respond_to(self.id, self.token, InteractionResponseType.deferred_channel_message, payload)
        self.deferred = True

    @overload
    async def respond(self, content: str = ..., tts: bool = ..., 
        embed: Embed = ..., file: File = ..., allowed_mentions: AllowedMentions = ..., 
        mention_author: bool = ..., components: List[Component] = ..., delete_after: float = ...,
        hidden: bool = ..., ninja_mode: bool = ...
    ): ...

    @overload
    async def respond(self, content: str = ..., tts: bool = ..., 
        embeds: List[Embed] = ..., file: File = ..., allowed_mentions: AllowedMentions = ..., 
        mention_author: bool = ..., components: List[Component] = ..., delete_after: float = ...,
        hidden: bool = ..., ninja_mode: bool = ...
    ): ...

    @overload
    async def respond(self, content: str = ..., tts: bool = ..., 
        embed: Embed = ..., files: List[File] = ..., allowed_mentions: AllowedMentions = ..., 
        mention_author: bool = ..., components: List[Component] = ..., delete_after: float = ...,
        hidden: bool = ..., ninja_mode: bool = ...
    ): ...

    @overload
    async def respond(self, content: str = ..., tts: bool = ..., 
        embeds: Embed = ..., files: List[File] = ..., allowed_mentions: AllowedMentions = ..., 
        mention_author: bool = ..., components: List[Component] = ..., delete_after: float = ...,
        hidden: bool = ..., ninja_mode: bool = ...
    ): ...


    async def respond(self, content=None, *, tts=False, embed=None, embeds=None, file=None, files=None,
        allowed_mentions=None, mention_author=None, components=None, delete_after=None, 
        hidden=False, ninja_mode=False
    ) -> ResponseMessage:
        """
        Responds to the interaction
        
        Parameters
        ----------
        content: :class:`str`, optional
            The raw message content
        tts: :class:`bool`
            Whether the message should be send with text-to-speech
        embed: :class:`discord.Embed`
            Embed rich content
        embeds: List[:class:`discord.Embed`]
            A list of embeds for the message
        file: :class:`discord.File`
            The file which will be attached to the message
        files: List[:class:`discord.File`]
            A list of files which will be attached to the message
        nonce: :class:`int`
            The nonce to use for sending this message
        allowed_mentions: :class:`discord.AllowedMentions`
            Controls the mentions being processed in this message
        mention_author: :class:`bool`
            Whether the author should be mentioned
        components: List[:class:`~Button` | :class:`~LinkButton` | :class:`~SelectMenu`]
            A list of message components to be included
        delete_after: :class:`float`
            After how many seconds the message should be deleted, only works for non-hiddend messages; default MISSING
        listener: :class:`Listener`
            A component-listener for this message
        hidden: :class:`bool`
            Whether the response should be visible only to the user 
        ninja_mode: :class:`bool`
            If true, the client will respond to the button interaction with almost nothing and returns nothing
        
        Returns
        -------
        :class:`~Message` | :class:`~EphemeralMessage`
            Returns the sent message
        """
        if ninja_mode is True or all(y in [None, False] for x, y in locals().items() if x not in ["self"]):
            try:
                await self._state.http.respond_to(self.id, self.token, InteractionResponseType.deferred_message_update)
                self.responded = True
                return
            except HTTPException as x:
                if "value must be one of (4, 5)" in str(x).lower():
                    # logging.error(str(x) + "\n" + "The 'ninja_mode' parameter is not supported for slash commands!")
                    ninja_mode = False
                else:
                    raise x

        if self.responded is True:
            return await self.send(content=content, tts=tts, embed=embed, embeds=embeds, 
                allowed_mentions=allowed_mentions, mention_author=mention_author, 
                components=components, hidden=hidden
            )

        payload = {"tts": tts}
        if content is not None:
            payload["content"] = str(content)
        if embed is not None or embeds is not None:
            payload["embed"] = embeds or [embed] 
        if allowed_mentions is not None:
            payload["alllowed_mentions"] = allowed_mentions.to_dict()
        if mention_author is not None:
            allowed_mentions = payload["allowed_mentions"] if "allowed_mentions" in payload else AllowedMentions().to_dict()
            allowed_mentions['replied_user'] = mention_author
            payload["allowed_mentions"] = allowed_mentions
        if components is not None:
            payload["components"] = ComponentStore(components).to_dict()

        
        hide_message = self._deferred_hidden or not self.deferred and hidden is True

        if hide_message:
            payload["flags"] = 64
        
        if self.deferred:
            route = Route("PATCH", f'/webhooks/{self.application_id}/{self.token}/messages/@original')
            if file is not None or files is not None:
                await self._state.http.request(route=route, files=files or [file], form=utils.get_form(files or [file], payload))
            else:
                await self._state.http.request(route, json=payload)    
        else:
            await self._state.http.respond_to(self.id, self.token, InteractionResponseType.channel_message, payload, files=files or [file] if file is not None else None)
        self.responded = True
        
        r = await self._state.http.request(Route("GET", f"/webhooks/{self.application_id}/{self.token}/messages/@original"))
        return ResponseMessage(state=self._state, channel=self.channel, data=r, application_id=self.application_id, token=self.token)
    async def send(self, content=None, *, tts=None, embed=None, embeds=None, file=None, files=None,
        allowed_mentions=None, mention_author=None, components=None, delete_after=None, hidden=False,
        force=False
    ) -> ResponseMessage:
        """
        Sends a message to the interaction using a webhook
        
        Parameters
        ----------
        content: :class:`str`, optional
            The raw message content
        tts: :class:`bool`, optional
            Whether the message should be send with text-to-speech
        embed: :class:`discord.Embed`, optional
            Embed rich content
        embeds: List[:class:`discord.Embed`], optional
            A list of embeds for the message
        file: :class:`discord.File`, optional
            The file which will be attached to the message
        files: List[:class:`discord.File`], optional
            A list of files which will be attached to the message
        nonce: :class:`int`, optional
            The nonce to use for sending this message
        allowed_mentions: :class:`discord.AllowedMentions`, optional
            Controls the mentions being processed in this message
        mention_author: :class:`bool`, optional
            Whether the author should be mentioned
        components: List[:class:`~Button` | :class:`~LinkButton` | :class:`~SelectMenu`]
            A list of message components to be included
        delete_after: :class:`float`, optional
            After how many seconds the message should be deleted, only works for non-hiddend messages; default MISSING
        listener: :class:`Listener`, optional
            A component-listener for this message
        hidden: :class:`bool`, optional
            Whether the response should be visible only to the user 
        ninja_mode: :class:`bool`, optional
            If true, the client will respond to the button interaction with almost nothing and returns nothing
        force: :class:`bool`, optional
            Whether sending the follow-up message should be forced.
            If ``False``, then a follow-up message will only be send if ``.responded`` is True; default False
        
        Returns
        -------
        :class:`~Message` | :class:`EphemeralMessage`
            Returns the sent message
        """
        if force is False and self.responded is False:
            return await self.respond(content=content, tts=tts, embed=embed, embeds=embeds, file=file, files=files, allowed_mentions=allowed_mentions, mention_author=mention_author, components=components, delete_after=delete_after, hidden=hidden)

        payload = {"tts": tts}
        if content is not None:
            payload["content"] = str(content)
        if embed is not None or embeds is not None:
            payload["embeds"] = embeds or [embed]
        if allowed_mentions is not None:
            payload["alllowed_mentions"] = allowed_mentions.to_dict()
        if mention_author is not None:
            allowed_mentions = payload["allowed_mentions"] if "allowed_mentions" in payload else AllowedMentions().to_dict()
            allowed_mentions['replied_user'] = mention_author
            payload["allowed_mentions"] = allowed_mentions
        if components is not None:
            payload["components"] = ComponentStore(components).to_dict()

        if hidden:
            payload["flags"] = 64

        route = Route("POST", f'/webhooks/{self.application_id}/{self.token}')
        if file is not None or files is not None:
            r = await self._state.http.request(route=route, files=files or [file], form=utils.get_form(files or [file], payload))
        else:
            r = await self._state.http.request(route, json=payload)

        msg = ResponseMessage(state=self._state, channel=self.channel, data=r, application_id=self.application_id, token=self.token)
        if delete_after is not None:
            await msg.delete(delay=delete_after)
        return msg
    
class ComponentInteraction(Interaction):
    def __init__(self, state: ConnectionState, data: InteractionPayload):
        super().__init__(state, data)
        self.component: Component = self.message.components.find(custom_id=self.data['custom_id'])
class ButtonInteraction(ComponentInteraction):
    component: Button
class SelectInteraction(ComponentInteraction):
    component: SelectMenu
    def __init__(self, state: ConnectionState, data: InteractionPayload):
        super().__init__(state, data)
        self.selected_values: List[str] = data['values']
        self.selected_options: List[SelectOption] = [
            self.component.options[i] for i, o in enumerate(self.components.options) 
                if o.value in self.selected_values
        ]