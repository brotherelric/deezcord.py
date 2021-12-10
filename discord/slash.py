"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz
Copyright (c) 2021-present 404kuso

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



from .mixins import Hashable
from .utils import All, MISSING
from .errors import Forbidden, InvalidArgument
from .enums import ApplicationCommandType, OptionType, ChannelType
from .user import User
from .member import Member
from .channel import TextChannel

import inspect
import asyncio
from typing import TYPE_CHECKING, ClassVar, Coroutine, List, Callable, Any, Tuple, Union, Dict, overload, TypeVar


if TYPE_CHECKING:
    from .state import ConnectionState
    from .types.interactions import (
        ApplicationCommandPermissions as ApplicationCommandPermissionsPayload,
        Interaction as InteractionPayload,
        ApplicationCommandOption as SlashOptionPayload,
        ApplicationCommandInteractionData as ApplicationCommandPayload,
    )
    C = TypeVar("C", bound="ApplicationCommand")

__all__ = (
    'SlashPermission',
    'SlashOption',
    'SlashCommand',
    'SubSlashCommand',
    'MessageCommand',
    'UserCommand',
)


def class_to_type(type):
    """
    Turns a python class. 
    This allows the SlashOption type to be a class
    

    >>> SlashOption(str, ...)
    >>> SlashOption(int, ...)
    >>> SlashOption([ChannelType.text, ChannelType.voice])
    """
    if isinstance(type, OptionType):
        return type
    if type is str:
        return OptionType.string
    if type is int:
        return OptionType.integer
    if type is bool:
        return OptionType.boolean
    if type in [Member, User]:
        return OptionType.member
    if type is TextChannel:
        return OptionType.channel
    # if type is Mentionable:
    #     return OptionType.mentionable
    if type is float:
        return OptionType.float
    if isinstance(type, list) and all(isinstance(x, ChannelType) for x in type):
        c = OptionType.channel
        c.__types__ = type  # set channel types for option
        return c
    if isinstance(type, (range)):
        if isinstance(type.start, float) or isinstance(type.stop, float):
            c = OptionType.float
            c.__range__ = (float(range.start), float(range.stop))
            return C
        c = OptionType.integer
        c.__range__ = (range.start, range.stop)
        return c

class SlashOption:

    __slots__: Tuple[str, ...] = (
        'type',
        'name',
        'description',
        'required',
        'choices',
        'channel_types',
        'min_value',
        'max_value',
        'options',
        'autocomplete'
    )

    def __init__(
        self, 
        type: OptionType, 
        name: str,
        description: str=MISSING, 
        required: bool=True, 
        choices: Union[List[Dict[str, Union[int, float, str]]], List[Tuple[str, Union[int, float, str]]], List[str]] = None, 
        autocomplete: bool=None, 
        channel_types: List[ChannelType]=None, 
        min_value: Union[int, float]=None, 
        max_value: Union[int, float]=None, 
        options: List[SlashOption]=None
    ):
        self.type = class_to_type(type)
        self.name = name
        self.description = description or '\u200b'
        self.required = required
        self.autocomplete = autocomplete
        self.channel_types = channel_types
        self.min_value = min_value
        self.max_value = max_value
        self.options = options
        self.choices: List[Dict[str, Union[int, float, str]]]
        if choices is not None and all(isinstance(c, tuple) for c in choices):
            self.choices = [{'name': c[0], 'value': c[1]} for c in choices]
        elif choices is not None and all(isinstance(c, str) for c in choices):
            self.choices = [{'name': c, 'value': c} for c in choices]
        else:
            self.choices = choices

        if hasattr(self.type, '__types__'):
            self.channel_types = self.type.__types__
        if hasattr(self.type, '__range__'):
            self.min_value, self.max_value = self.type.__range__

    def __eq__(self, o: Union[SlashOption, SlashOptionPayload]):
        if isinstance(o, dict):
            return (
                o['type'] == self.type.value
                and o['name'] == self.name
                and o['description'] == self.description
                and o.get('required', False) == self.required
                and o.get('choices') == self.choices
                and o.get('min_value') == self.min_value
                and o.get('max_value') == self.max_value
                and len(o.get('channel_types', [])) == len(self.channel_types or [])
                    and set(o.get('channel_types', [])) == set(self.channel_types or [])
            )

    def to_dict(self):
        payload = {
            'type': self.type.value,
            'name': self.name,
            'description': self.description
        }
        if self.type not in [OptionType.subcommand, OptionType.subcommand_group]:
            payload['required'] = self.required
        if self.min_value is not None:
            payload['min_value'] = self.min_value
        if self.max_value is not None:
            payload['max_value'] = self.max_value
        if self.channel_types is not None:
            payload['channel_typese'] = [c.value for c in self.channel_types]
        if not self.autocomplete and self.choices is not None:
            payload['choices'] = self.choices
        if self.autocomplete is not None:
            payload['autocomplete'] = self.autocomplete
        if self.options is not None:
            payload['options'] = [op.to_dict() for op in self.options]
        return payload


class ApplicationCommand(Hashable):

    __slots__: Tuple[str, ...] = (
        '__aliases__',
        '__subcommands__',
        '__original_name__',
        
        '_state',
        'cog',      # for cog commands

        'type',
        'id',
        'callback',
        'name',
        'description',
        'options',
        'guild_ids',
        'default_permission',
        'guild_permissions',
        'permissions'
    )

    def __init__(
        self, 
        type, 
        callback, 
        name=MISSING,
        description=MISSING, 
        options=None, 
        guild_ids=None, 
        default_permission=True, 
        guild_permissions={}, 
        state=None
    ):
        self.__aliases__: List[str] = getattr(callback, '__aliases__', None)
        self.__subcommands__: Dict[str, Union[SubSlashCommand, Dict[str, SubSlashCommand]]] = {}
        self.__original_name__: str = name

        self._state: ConnectionState = state
        self.cog = None     # set later in cog commands

        self.type: ApplicationCommandType = type
        self.id: int = None     # set later

        self.callback: Callable[..., Coroutine[Any, Any, Any]] = callback
        self.name: str = name or self.callback.__name__
        self.description: str = description
        if description is MISSING:
            self.description = description or inspect.getdoc(self.callback) or '\u200b'
        if description is None:
            self.description = "\u200b"
        self.options: List[SlashOption] = options or []
        self.guild_ids: List[int] = guild_ids
        self.default_permission: bool = default_permission
        self.guild_permissions: Dict[int, SlashPermission] = guild_permissions
        self.permissions: SlashPermission = SlashPermission()
    async def __call__(self, *args, **kwargs):
        if self.cog is not None:
            return await self.callback(self.cog, *args, **kwargs)
        return await self.callback(*args, **kwargs)

    def to_dict(self) -> ApplicationCommandPayload:
        payload = {
            'type': self.type.value,
            'name': self.name,
            'description': self.description,
            'default_permission': self.default_permission,
        }
        if self.options:
            payload['options'] = [op.to_dict() for op in self.options]
        return payload


    def is_global(self) -> bool:
        return not (self.guild_ids and len(self.guild_ids) > 0)
    def has_aliases(self) -> bool:
        return self.__aliases__ and len(self.__aliases__) > 0

    async def edit(self, guild_id, **fields):
        ...
        return await self.update(guild_id=guild_id)
    async def update(self, *, guild_id=None):
        if self.is_global():
            await self._state.slash_http.edit_global_command(self.id, self.to_dict())
            return
        for guild in ([guild_id] if guild_id else self.guild_ids):
            await self._state.slash_http.edit_guild_command(
                self.id, 
                guild_id, 
                self.to_dict(), 
                self.guild_permissions[guild].to_dict()
            )

class ChatInputCommand(ApplicationCommand):

    __slots__ = ApplicationCommand.__slots__

    def __init__(
        self, 
        name: str=MISSING, 
        callback: Callable[..., Coroutine[Any, Any, Any]]=None,
        description: str=MISSING,
        options: List[SlashOption]=None,
        guild_ids: List[int]=None,
        default_permission: bool=True,
        guild_permissions: dict={},
        state: ConnectionState=None
    ):
        ApplicationCommand.__init__(
            self,
            type=ApplicationCommandType.chat_input, 
            callback=callback, 
            name=name, 
            description=description, 
            options=options, 
            guild_ids=guild_ids,
            guild_permissions=guild_permissions, 
            default_permission=default_permission, 
            state=state
        )
    def is_subcommand(self) -> bool:
        return hasattr(self, 'base')
class SlashCommand(ChatInputCommand):

    __slots__ = ChatInputCommand.__slots__

    def __getitem__(self, name) -> SubSlashCommand:
        return self.__subcommands__[name]
    def __setitem__(self, name, value):
        self.__subcommands__[name] = value
    def __delitem__(self, name):
        del self.__subcommands__[name]
    def __eq__(self, object: Union[ApplicationCommand, ApplicationCommandPayload]):
        if isinstance(object, dict):
            return (
                object['type'] == self.type.value
                and object['name'] == self.name
                and len(self.options) == len(object['options'])
                    and all(object['options'][i] == self.options[i] for i, _ in enumerate(self.options))
            )
        if isinstance(object, ApplicationCommand):
            ...
        return False
    
    def to_dict(self) -> ApplicationCommandPayload:
        payload = super().to_dict()
        
        # this will replace the options with the subcommands converted to a dict
        if self.has_subcommands():
            payload['options'] = [
                self.__subcommands__[sub].to_dict() 
                    if not isinstance(self.__subcommands__[sub], dict) else
                (
                    SlashOption(OptionType.subcommand_group, name=sub,
                        options=[
                            self.__subcommands__[sub][x].to_option() for x in self.__subcommands__[sub]
                        ]).to_dict()
                )
                    for sub in self.__subcommands__
            ]
        
        return payload

    def add_subcommand(self, command):
        command.base = self
        if command.group_name:
            if self.__subcommands__.get(command.group_name) is None:
                self.__subcommands__[command.group_name] = {}
            self.__subcommands__[command.group_name][command.name] = command
        else:
            self.__subcommands__[command.name] = command
    
    def has_subcommands(self):
        return self.__subcommands__ and len(self.__subcommands__) > 0

    @property
    def subcommands(self):
        return self.__subcommands__
class _TempBase:
    __slots__ = ('name',)
    def __init__(self, name):
        self.name: str = name
class SubSlashCommand(ChatInputCommand):
    
    __slots__ = ChatInputCommand.__slots__ + (
        'base',
        'group_name',
        'base_names'
    )
    
    def __init__(
        self, 
        base: SlashCommand,
        base_names: Union[List[str], str]=MISSING,
        callback: Callable[..., Coroutine[Any, Any, Any]]=None,
        name: str=MISSING,
        description: str=MISSING,
        options: List[SlashOption] = None,
        guild_ids: List[int] = None,
        default_permission: bool = True,
        guild_permissions: dict = {},
        state: ConnectionState = None
    ):
        self.base = base or _TempBase(base_names[0])
        self.group_name = base_names[1] if len(base_names) > 1 else None
        ChatInputCommand.__init__(self,
            name=name, 
            callback=callback, 
            description=description, 
            options=options, 
            guild_ids=guild_ids, 
            default_permission=default_permission, 
            guild_permissions=guild_permissions, 
            state=state
        )

    def to_option(self) -> SlashOption:
        return SlashOption(OptionType.subcommand, self.name, self.description, False)

    @property
    def base_name(self):
        return self.base.name


class ContextCommand(ApplicationCommand):
    __slots__: Tuple[str, ...] = (
        '__aliases__',
        '__original_name__',
        
        '_state',
        'id',
        'callback',
        'name',
        'guild_ids',
        'default_permission',
        'guild_permissions'
    )
    def __init__(self, type, name, callback=None, guild_ids=None, default_permission=True, guild_permissions={}, state=None):
        ApplicationCommand.__init__(self,
            type=type, 
            callback=callback, 
            name=name,
            guild_ids=guild_ids, 
            default_permission=default_permission,
            guild_permissions=guild_permissions,
            state=state
        )
    def to_dict(self) -> ApplicationCommandPayload:
        return {
            'type': self.type.value,
            'name': self.name,
            'default_permission': self.default_permission
        }
      
class MessageCommand(ContextCommand):

    __slots__ = ContextCommand.__slots__

    def __init__(self, name, callback=None, guild_ids=None, default_permission=True, guild_permissions={}, state=None):
        ContextCommand.__init__(self,
            ApplicationCommandType.message, 
            name=name,
            callback=callback, 
            guild_ids=guild_ids, 
            default_permission=default_permission, 
            guild_permissions=default_permission, 
            state=state
        )
class UserCommand(ContextCommand):

    __slots__ = ContextCommand.__slots__

    def __init__(self, name, callback=None, guild_ids=None, default_permission=True, guild_permissions={}, state=None):
        ContextCommand.__init__(self,
            ApplicationCommandType.user, 
            name=name,
            callback=callback, 
            guild_ids=guild_ids, 
            default_permission=default_permission, 
            guild_permissions=default_permission, 
            state=state
        )


class CommandStore:
    __slots__: Tuple[str, ...] = (
        'api', 
        '_state', 
        '_cache', 
        '_raw_cache', 
        '_on_sync',
    )
    
    def __init__(self, state, commands = []) -> None:
        self.api = APITools(state)
        self._state: ConnectionState = state
        self._cache: dict = {}
        self._raw_cache: Dict[int, ApplicationCommand] = {}    # dict with commands saved with their id
        # setup cache
        self.clear()
        # loads the commands into the cache
        self.load(commands)

        async def on_sync():
            ...
        self._on_sync: Callable[[], Coroutine[Any, Any, Any]] = on_sync
    def __repr__(self):
        return f"<{self.__class__.__name__}{self._cache}>"
    def __getitem__(self, index) -> Dict[str, Union[ ApplicationCommand, Dict[str, Union[ ApplicationCommand, Dict[str, Union[ ApplicationCommand, dict ]] ]] ]]:
        """
        Special keys
        -------------
        Shortcut for subkeying
        ```py
        x:y:z -> [x][y][z]
        ```
        - - -
        Shortcut for filtering
        ```py
        !x!y -> {key: ... for key in dict if key not in ['x', 'y']}
        ```
        
        Note that this will return a copy of the original dict, if we want to acces objects from the original dict, we can use a simple workaround:
        ```py
        for key in self["!illegal_key"]:
            self[key] # this will grant you acces to the object from the original dict
        ```
        """
        # subkeying or whatever this is called
        if ":" in index:
            keys = index.split(":")
            cur = self._cache[keys.pop(0)]
            while True:
                if len(keys) == 0:
                    return cur
                if cur is None or not isinstance(cur, dict):
                    raise KeyError(f"No key with name '{keys[-1]}'")
                cur = cur.get(keys.pop(0))
        # filtering
        elif "!" in index:
            black_keys = index.split("!")
            return {key: self._cache[key] for key in self._cache if key not in black_keys}
        else:
            return self._cache[index]
    def __setitem__(self, index, value):
        """
        Special keys
        -------------
        Shortcut for setting subkeys
        ```py
        x:y:z = ... -> [x][y][z] = ...
        ```
        - - -
        Shortcut for filtered setting
        ```py
        !x!y = ... -> for key in self:
                          if key not in ["x", "y"]:
                              self[key] = ...
        ```
        
        Sets everything to the value except the "illegal keys"
        """
        # subkeying? or whatever you would call that
        if ":" in index:
            keys = index.split(":")
            cur = self._cache[keys.pop(0)]
            while True:
                if len(keys) == 0:
                    cur = value
                    break
                if cur is None or not isinstance(cur, dict):
                    raise KeyError(f"No key with name '{keys[-1]}'")
                cur = cur.get(keys.pop(0))
        # set everything to value except
        if "!" in index:
            black_keys = index.split("!")
            for x in self:
                if x not in black_keys:
                    self[x] = value
        else:
            self._cache[index] = value
    def __delitem__(self, index):
        if ":" in index:
            keys = index.split(":")
            cur = self._cache[keys.pop(0)]
            while True:
                if len(keys) == 0:
                    del cur
                    break
                if cur is None or not isinstance(cur, dict):
                    raise KeyError(f"No key with name '{keys[-1]}'")
                cur = cur.get(keys.pop(0))
        else:
            del self._cache[index]
    def __iter__(self):
        return iter(self._cache)
    def __contains__(self, command: ApplicationCommand):
        type_key = str(command.type)
        if command.is_global():
            if command.is_subcommand():
                if self["globals"].get(type_key) is None:
                    return False
                if self["globals"][type_key].get(command.base_name) is None:
                    return False
                if len(command.base_names) > 1:
                    if self["globals"][type_key][command.base_name].subcommands.get(command.group_name) is None:
                        return False
                    if self["globals"][type_key][command.base_name][command.group_name].get(command.name) is None:
                        return False
                    return True
                return self["globals"][type_key][command.base_name].subcommands.get(command.name) is not None
            if self["globals"].get(type_key) is None:
                return False
            return self["globals"][type_key].get(command.name) is not None
        
        # check for every guild_id
        for g in command.guild_ids:
            guild = str(g)
            if self.get(guild) is None:
                return False
            if self[guild].get(type_key) is None:
                return False
            if command.is_subcommand():
                if self[guild][type_key].get(command.base_names[0]) is None:
                    return False
                # if more than one base
                if len(command.base_names) > 1:
                    if self[guild][type_key][command.base_names[0]].subcommands.get(command.base_names[1]) is None:
                        return False
                    if self[guild][type_key][command.base_names[0]][command.base_names[1]].get(command.name) is None:
                        return False
                # one base only
                else:
                    if self[guild][type_key][command.base_names[0]].subcommands.get(command.name) is not None:
                        return False
            else:
                if self[guild][type_key].get(command.name) is None:
                    return False 
        return True
    def __eq__(self, object):
        if isinstance(object, self.__class__):
            return len(object._cache) == len(self._cache) and object._cache == self._cache
        return False
    
    def add_command(self, command):
        return self.append(command)
    

    def on_sync(self, method):
        """Decorator for a method that should be called when the commands were synced
        
        Usage
        ------
        .. code-block::
            @Slash.commands.on_sync
            async def on_commands_sync():
                ...
        """
        if not asyncio.iscoroutinefunction(method):
            raise InvalidArgument("on_sync has to be async")
        self._on_sync = method
        

    # region overloading def load(self, cache)
    @overload
    def load(self, cache: List[ApplicationCommand]) -> ApplicationCommand:
        """Loads some commands into the cache
        
        Parameters
        -----------
        cache: List[:class:`command`]:
            The commands that should be loaded into this cache instance
        Returns
        --------
        :class:`CommandCache`:
            The own instance with the commands loaded into it
        """
        ...
    @overload
    def load(self, cache: Union[CommandStore, dict]) -> CommandStore:
        """Replaces the own raw cache with the passed cache
        
        Parameters
        -----------
        cache: :class:`CommandCacheList` | :class:`dict`:
            The raw cache which should be loaded into this cache instance
        Returns
        --------
        :class:`CommandCache`:
            The own instance with the cache loaded into it
        """
        ...
    # endregion
    def load(self, cache):
        # first overload, application commands
        if isinstance(cache, list):
            for x in cache:
                self._add(x)
            return self
        # second overloadd, raw cache
        self._cache = cache
        return self
    def clear(self):
        """Clears the cache and makes it empty"""
        self._cache = {
            "globals": {
                str(ApplicationCommandType.chat_input): {},
                str(ApplicationCommandType.user): {},
                str(ApplicationCommandType.message): {}
            }
        }
        return self
    def copy(self):
        return self.__class__(self._state).load(self._cache)
    def _add(self, command: ApplicationCommand):
        if command._state is None:
            command._state = self._state
        type_key = str(command.type)
        if command.is_global():
            if command.is_subcommand():
                base = self["globals"][type_key].get(command.base_names[0])
                if base is None:
                    base = SlashCommand(name=command.base_names[0], callback=None,
                        guild_permissions=command.guild_permissions, default_permission=command.default_permission
                    )
                base.add_subcommand(command)
                self["globals"][type_key][base.name] = base  
            else:
                self["globals"][type_key][command.name] = command
        else:
            for guild_id in command.guild_ids:
                guild = str(guild_id)
                if self.get(guild) is None:
                    self[guild] = {}
                if self[guild].get(type_key) is None:
                    self[guild][type_key] = {}
                if command.type is ApplicationCommandType.chat_input and command.is_subcommand():
                    # is subcommand
                    base = self[guild][type_key].get(command.base_name)
                    if base is None:
                        base = SlashCommand(callback=None, name=command.base_name,
                            guild_permissions=command.guild_permissions, default_permission=command.default_permission
                        )
                    base.add_subcommand(command)
                    self[guild][type_key][base.name] = base  
                else:
                    self[guild][type_key][command.name] = command
        return self
    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    def append(self, base: C, is_base=False) -> C:
        if base.has_aliases() and is_base is False:
            for a in base.__aliases__:
                cur = base.copy()
                cur.name = a
                self.append(cur, is_base=True)
        self._add(base)
        return base
    def remove(self, base: SlashCommand):
        """Removes a SlashCommand from the cache
        
        base: :class:`SlashCommand`
            The command that should be removeed
        """
        key_type = str(base.type)
        name = base.name if not base.is_subcommand() else base.base_names[0]
        if base.is_global():
            keys = ["global"]
        else:
            keys = [str(x) for x in base.guild_ids]
        for k in keys:
            if self[k].get(key_type) is None:
                return
            if self[k][key_type].get(name) is None:
                return
            if not base.is_subcommand():
                del self[k][key_type][name]
                return
            if len(base.base_names) > 1:
                del self[k][key_type][name][base.base_names[1]][base.name]
                return
            else:
                del self[k][key_type][name][base.name]
                return
    async def sync(self, delete_unused=False):
        """Updates the api with the commands in the cache
        
        delete_unused: :class:`bool`, optional
            Whether commands that are not included in this cache should be deleted; default False
        """
        http = self._state.slash_http
        self._raw_cache = {}
        

        for ct in self["globals"]:
            for base_name in self["globals"][ct]:
                base = self["globals"][ct][base_name]
                new_command = None # variable to store the new command data
                api_command = await self.api.get_global_command(base.name, base.type.value)
                print(api_command == base)
                if api_command is None:
                    new_command = await http.create_global_command(base.to_dict())
                else:
                    if api_command != base:
                        new_command = await http.edit_global_command(api_command["id"], base.to_dict())
                # directly set the id of the command so no extra request is needed
                base.id = new_command["id"] if new_command else api_command["id"]
                self._raw_cache[base.id] = base

        # self["!globals"] returns a copy of a filtered dict but since we will be only using the
        # copy's key and acces the original self dict, there won't be any problems
        # 
        # for each guild
        for guild in self["!globals"]:
            guild_object = self._state._get_guild(int(guild))
            # acces original dict with filtered keys
            for ct in self[guild]:
                for base_name in self[guild][ct]:
                    base = self[guild][ct][base_name]
                    new_command = None # variable to store the new command data
                    api_command = await self.api.get_guild_command(base.name, base.type, guild)
                    if api_command:
                        # get permissions for the command
                        api_permissions = await http.get_command_permissions(api_command["id"], guild)
                    global_command = await self.api.get_global_command(base.name, base.type)
                    # If no command in that guild or a global one was found
                    if api_command is None or global_command is not None:
                        # Check global commands
                        # allow both global and guild commands to exist
                        new_command = await http.create_guild_command(base.to_dict(), guild, base.permissions.to_dict())
                    elif api_command != base:
                        new_command = await http.edit_guild_command(api_command["id"], guild, base.to_dict(), base.permissions.to_dict())
                    elif api_permissions != base.permissions:
                        await http.update_command_permissions(guild, api_command["id"], base.permissions.to_dict())
                    base.id = new_command["id"] if new_command else api_command["id"]
                    self._raw_cache[base.id] = base
                    guild_object._add_channel

        if delete_unused is True:
            for global_command in await self.api.get_global_commands():
                key_type = str(ApplicationCommandType(global_command["type"]))
                # command of a type we didn't register
                if self["globals"].get(key_type) is None:
                    await http.delete_global_command(global_command["id"])
                    continue
                # command with a name we didn't register
                if self["globals"][key_type].get(global_command["name"]) is None:
                    await http.delete_global_command(global_command["id"])
                    continue
            for guild in [str(x.id) for x in self._state.guilds]:
                for guild_command in await self.api.get_guild_commands(guild):
                    # command in a guild we didn't register
                    if self.get(guild) is None:
                        await http.delete_guild_command(guild_command["id"], guild)
                        continue
                    key_type = str(ApplicationCommandType(guild_command["type"]))
                    # command of a type we didn't register
                    if self[guild].get(key_type) is None:
                        await http.delete_guild_command(guild_command["id"], guild)
                        continue
                    # command with a name we didn't register
                    if self[guild][key_type].get(guild_command["name"]) is None:
                        await http.delete_guild_command(guild_command["id"], guild)
                        continue
        
        self._state.dispatch('commands_synced')
        await self._on_sync()
    async def nuke(self, globals=True, guilds=All):
        """
        Deletes all commands registered in the api of this bot
        
        Parameters
        ----------
        globals: :class:`bool`, optional
            Whether all global commands should be deleted; default True
        guild: List[:class:`int`], optional
            The guild ids where commands should be deleted; default All
        
        Usage
        -----
        delete all commands
        >>> await commands.nuke()
        delete only global commands
        >>> await commands.nuke(guilds=None)
    
        delete only guild commands
        >>> await commands.nuke(globals=False)
    
        delete commands in specific guilds
        >>> await commands.nuke(globals=False, guilds=[814473329325899787])
        """
        if guilds is All:
            guilds = self._cache["!globals"]
        if guilds is None:
            guilds = []
        if globals is True:
            await self._state.slash_http.delete_global_commands()
        for id in guilds:
            self._state.slash_http.delete_guild_commands(id)
         
    def dispatch(self, type, interaction):
        self._state.dispatch('application_command', interaction)
        if type == ApplicationCommandType.chat_input.value:
            self._state.dispatch('slash_command', interaction, **interaction.options)
        if type == ApplicationCommandType.user.value:
            self._state.dispatch('user_command', interaction, interaction.target)
        if type == ApplicationCommandType.message.value:
            self._state.dispatch('message_command', interaction, interaction.target)
        if interaction.command:
            if type == ApplicationCommandType.chat_input.value:
                promise = interaction.command(interaction, **interaction.options)
            elif type in [ApplicationCommandType.message.value, ApplicationCommandType.user.value]:
                promise = interaction.command(interaction, interaction.target)
            else:
                promise = interaction.command(interaction)
            asyncio.create_task(
                promise, 
                name=f'discord-ui-slash-dispatch-{interaction.command.id}'
            )


    def get_interaction_command(self, data: InteractionPayload):
        command = self._raw_cache.get(data["data"]["id"])
        if command is None:
            return

        # is subcommand
        if data["data"].get("options") is not None and data["data"]["options"][0]["type"] in [OptionType.subcommand, OptionType.subcommand_group]:
            try:
                base_one = command[data["data"]["options"][0]["name"]]
            except KeyError:
                return
            # if command has only one base
            if data["data"]["options"][0]["type"] == OptionType.subcommand:
                # return the subcommand
                return base_one
            elif data["data"]["options"][0]["type"] == OptionType.subcommand_group:
                try:
                    return base_one[data["data"]["options"][0]["options"][0]["name"]]
                except KeyError:
                    return None
        return command
    def get_commands(self, *, all=True, guilds=[], **keys):
        guilds = [str(x) for x in guilds]
        commands = {}
        for x in self._cache:
            if x in keys or str(x) in guilds or all:
                commands[x] = self._cache.get(x)
        return commands
    def filter_commands(self, command_type) -> Dict[str, ApplicationCommand]:
        commands = {}
        for x in self._cache:
            # multiple types
            if isinstance(command_type, (list, tuple)):
                for ct in command_type:
                    if commands.get(x) is None:
                        commands[x] = {}
                    if commands[x].get(str(ct)) is None:
                        commands[x][str(ct)] = {}
                    if len(self._cache[x].get(str(ct), {})) > 0:
                        commands[x][str(ct)] = self._cache[x].get(str(ct), {})
            # single type
            elif self._cache[x].get(str(command_type)):
                commands[x] = self._cache[x].get(str(command_type))
        return commands

    @property
    def all(self) -> ApplicationCommand:
        """All commands"""
        return self._cache
    @property
    def globals(self) -> Dict[str, ApplicationCommand]:
        """All global commands"""
        return self["globals"]
    @property
    def chat_commands(self) -> Dict[str, SlashCommand]:
        """All chat commands (slash commands)"""
        return self.filter_commands(ApplicationCommandType.chat_input)
    @property
    def context_commands(self) -> Dict[str, ContextCommand]:
        """All context commands (message commands, user commands)"""
        return self.filter_commands((ApplicationCommandType.message, ApplicationCommandType.user))
    @property
    def subcommands(self) -> Dict[str, Union[SubSlashCommand, Dict[str, SubSlashCommand]]]:
        """All subcommands"""
        filter = [list(x.values()) for x in list(self.filter_commands(ApplicationCommandType.chat_input).values())]
        return [z for a in [y.subcommands for x in filter for y in x] for z in a]

    
class APITools():
    __slots__: Tuple[str, ...] = ('state',)
    def __init__(self, state) -> None:
        self._state: ConnectionState = state

    async def get_commands(self) -> List[dict]:
        return await self.get_global_commands() + await self.get_all_guild_commands()
    async def get_global_commands(self) -> List[dict]:
        return await self._state.slash_http.get_global_commands()
    async def get_global_command(self, name, typ) -> Union[dict, None]:
        for x in await self.get_global_commands():
            if x["name"] == name and x["type"] == typ:
                return x
    async def get_all_guild_commands(self):
        commands = []
        async for x in [x.id for x in self._state.guilds]:
            try:
                commands += await self._state.slash_http.get_guild_commands(x.id)
            except Forbidden:
                continue
        return commands
    async def get_guild_commands(self, guild_id: str) -> List[dict]:
        return await self._state.slash_http.get_guild_commands(guild_id)
    async def get_guild_command(self, name, typ, guild_id) -> Union[dict, None]:
        # returns all commands in a guild
        for x in await self.get_guild_commands(guild_id):
            if hasattr(typ, "value"):
                typ = typ.value
            if x["name"] == name and x["type"] == typ:
                return x

class SlashPermission:
    __slots__ = ('allowed', 'forbidden')
    def __init__(self, *, allowed: Dict[int, int]={}, forbidden: Dict[int, int]={}) -> None:
        """
        
        >>> SlashPermission(
            allowed={
                09090909: SlashPermission.user,
                012391039104: SlashPermission.user 
                909092049309: SlashPermission.role
            },
            forbidden={
                24294320923: SlashPermission.role
            }
        )
        """
        self.allowed = allowed
        self.forbidden = forbidden

    def to_dict(self) -> List[ApplicationCommandPermissionsPayload]:
        return [
            {'id': id, 'type': self.allowed[id], 'permission': True} for id in self.allowed
        ] + [
            {'id': id, 'type': self.forbidden[id], 'permission': False} for id in self.forbidden
        ]

    role: ClassVar[int] = 1
    user: ClassVar[int] = 2