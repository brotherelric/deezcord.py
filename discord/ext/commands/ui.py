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

from typing import TYPE_CHECKING, Any, List, Dict, Coroutine, Callable, Tuple, TypeVar
from ...utils import MISSING
from ...interactions import ApplicationCommandInteraction
from ...slash import CommandStore, MessageCommand, SlashOption, SlashPermission, SlashCommand, SubSlashCommand, UserCommand
if TYPE_CHECKING:
    from ..commands.bot import Bot
    from typing_extensions import Concatenate, ParamSpec, TypeGuard
    
    P = ParamSpec('P')

T = TypeVar('T')
Coro = Coroutine[Any, Any, T]
InteractionT = TypeVar('InteractionT', bound=ApplicationCommandInteraction)



class UI:
    __slots__: Tuple[str] = ('client','_temp_commands')
    def __init__(self, client):
        self.client: Bot = client
        self._temp_commands = CommandStore(self.client._connection)
        
        @self.client.listen()
        async def on_ready():
            self.client._connection._command_store.load(self._temp_commands)
            del self._temp_commands

    def add_command(self, command: T) -> T:
        if not self.client.is_ready():
            return self._temp_commands.add_command(command)
        return self.commands.add_command(command)
    @property
    def commands(self):
        return self.client._connection._command_store

    def command(
        self,
        name: str,
        description: str = MISSING,
        options: List[SlashOption] = None,
        guild_ids: List[int] = None,
        default_permission: bool = True,
        guild_permissions: Dict[int, SlashPermission] = {}
    ):
        def decorator(callback: Callable[Concatenate[InteractionT, P], Coro[T]]):
            return self.add_command(SlashCommand(
                name=name,
                callback=callback,
                description=description,
                options=options,
                guild_ids=guild_ids,
                default_permission=default_permission,
                guild_permissions=guild_permissions,
                state=self.client._connection
            ))
        return decorator

    def subcommand(
        self,
        base_names: List[str],
        name: str,
        description: str = MISSING,
        options: List[SlashOption] = None,
        guild_ids: List[int] = None,
        default_permission: bool = True,
        guild_permissions: Dict[int, SlashPermission] = {}
    ):
        def decorator(callback: Callable[Concatenate[InteractionT, P], Coro[T]]):
            return self.add_command(SubSlashCommand(
                base_names=base_names,
                name=name,
                callback=callback,
                description=description,
                options=options,
                guild_ids=guild_ids,
                default_permission=default_permission,
                guild_permissions=guild_permissions,
                state=self.client._connection
            ))
        return decorator

    def message_command(
        self,
        name: str,
        guild_ids: List[int] = None,
        default_permission: bool = True,
        guild_permissions: Dict[int, SlashPermission] = {}
    ):
        def decorator(callback: Callable[Concatenate[InteractionT, P], Coro[T]]):
            return self.add_command(MessageCommand(
                name=name,
                callback=callback,
                guild_ids=guild_ids,
                default_permission=default_permission,
                guild_permissions=guild_permissions,
                state=self.client._connection
            ))
        return decorator

    def message_command(
        self,
        name: str,
        guild_ids: List[int] = None,
        default_permission: bool = True,
        guild_permissions: Dict[int, SlashPermission] = {}
    ):
        def decorator(callback: Callable[Concatenate[InteractionT, P], Coro[T]]):
            return self.add_command(UserCommand(
                name=name,
                callback=callback,
                guild_ids=guild_ids,
                default_permission=default_permission,
                guild_permissions=guild_permissions,
                state=self.client._connection
            ))
        return decorator