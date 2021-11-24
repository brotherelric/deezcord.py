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

from typing import Any, ClassVar, Dict, List, Optional, TYPE_CHECKING, Tuple, Type, TypeVar, Union
from string import ascii_letters
from random import choice

from .enums import get_enum, ComponentType, ButtonStyle
from .utils import get_slots, MISSING
from .partial_emoji import PartialEmoji, _EmojiTag

if TYPE_CHECKING:
    from .types.components import (
        Component as ComponentPayload,
        ButtonComponent as ButtonComponentPayload,
        SelectMenu as SelectMenuPayload,
        SelectOption as SelectOptionPayload,
        ActionRow as ActionRowPayload,
    )
    from .emoji import Emoji


__all__ = (
    'Component',
    'ActionRow',
    'Button',
    'LinkButton',
    'SelectMenu',
    'SelectOption',
)

C = TypeVar('C', bound='Component')


class Component:
    """Represents a Discord Bot UI Kit Component.

    Currently, the only components supported by Discord are:

    - :class:`ActionRow`
    - :class:`Button`
    - :class:`SelectMenu`

    This class is abstract and cannot be instantiated.

    .. versionadded:: 2.0

    Attributes
    ------------
    type: :class:`ComponentType`
        The type of component.
    """

    __slots__: Tuple[str, ...] = ('type',)

    __repr_info__: ClassVar[Tuple[str, ...]]
    type: ComponentType

    def __repr__(self) -> str:
        attrs = ' '.join(f'{key}={getattr(self, key)!r}' for key in self.__repr_info__)
        return f'<{self.__class__.__name__} {attrs}>'

    @classmethod
    def _raw_construct(cls: Type[C], **kwargs) -> C:
        self: C = cls.__new__(cls)
        for slot in get_slots(cls):
            try:
                value = kwargs[slot]
            except KeyError:
                pass
            else:
                setattr(self, slot, value)
        return self

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


class ActionRow(Component):
    """Represents a Discord Bot UI Kit Action Row.

    This is a component that holds up to 5 children components in a row.

    This inherits from :class:`Component`.

    .. versionadded:: 2.0

    Attributes
    ------------
    type: :class:`ComponentType`
        The type of component.
    children: List[:class:`Component`]
        The children components that this holds, if any.
    """

    __slots__: Tuple[str, ...] = ('children',)

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(self, data: ComponentPayload):
        self.type: ComponentType = get_enum(ComponentType, data['type'])
        self.children: List[Component] = [_component_factory(d) for d in data.get('components', [])]

    def to_dict(self) -> ActionRowPayload:
        return {
            'type': int(self.type),
            'components': [child.to_dict() for child in self.children],
        }  # type: ignore

class BaseButton(Component):
    __slots__: Tuple[str, ...] = (
        'style',
        'custom_id',    # Button
        'url',          # LinkButton
        
        'label',
        'disabled',
        'emoji',
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__
    
    def __init__(self, style, custom_id=None, url=None, disabled=False, label=None, emoji=None):
        self.type = ComponentType.button
        self.style: ButtonStyle = get_enum(ButtonStyle, style)
        self.custom_id: Optional[str] = ''.join([choice(ascii_letters) for _ in range(20)]) if custom_id is MISSING else custom_id
        self.url: Optional[str] = url

        self.label: str = "\u200b" if label is None else  label
        self.disabled: str = disabled
        self.emoji: Optional[PartialEmoji] = None
        if emoji is not None:
            try:
                self.emoji: Optional[PartialEmoji] = PartialEmoji.from_dict(emoji)
            except KeyError:
                self.emoji = None

    def to_dict(self) -> ButtonComponentPayload:
        payload = {
            'type': 2,
            'style': int(self.style),
            'label': self.label,
            'disabled': self.disabled,
        }
        if self.custom_id:
            payload['custom_id'] = self.custom_id

        if self.url:
            payload['url'] = self.url

        if self.emoji:
            payload['emoji'] = self.emoji.to_dict()

        return payload  # type: ignore
    
    @classmethod
    def from_dict(cls, data: ButtonComponentPayload):
        if data['style'] == ButtonStyle.link:
            return LinkButton.from_dict(data)
        return Button.from_dict(data)

class Button(BaseButton):
    def __init__(self, label=MISSING, style=ButtonStyle.gray, custom_id=MISSING, emoji=None, disabled=False):
        super().__init__(style=style, label=label, custom_id=custom_id, disabled=disabled, emoji=emoji)
    @classmethod
    def from_dict(cls, data):
        return cls(
            label=data.get("label"), 
            emoji=data.get("emoji"), 
            custom_id=data.get("custom_id"),
            style=get_enum(ButtonStyle, data.get("style")),
            disabled=data.get("disabled")
        )
class LinkButton(BaseButton):
    def __init__(self, url, label=MISSING, emoji=None, disabled=False):
        super().__init__(style=ButtonStyle.url, url=url, label=label, emoji=emoji, disabled=disabled)
    @classmethod
    def from_dict(cls, data):
        return cls(
            url=data.get("url"),
            label=data.get("label"),
            emoji=data.get("emoji"),
            disabled=data.get("disabledö")
        )

class SelectMenu(Component):
    __slots__: Tuple[str, ...] = (
        'options',
        'custom_id',
        'placeholder',
        'min_values',
        'max_values',
        'disabled',
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(self, options: List[SelectOption], 
        custom_id:str=MISSING, min_values=None, max_values=None,
        placeholder:Optional[str]=None, disabled=False
    ):
        self.type = ComponentType.select
        self.custom_id = ''.join([choice(ascii_letters) for _ in range(20)]) if custom_id is MISSING else custom_id 
        self.placeholder = placeholder
        self.min_values = min_values or 1
        self.max_values = max_values or min_values
        self.disabled = disabled or False
        self.options = options

    def to_dict(self) -> SelectMenuPayload:
        payload: SelectMenuPayload = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'min_values': self.min_values,
            'max_values': self.max_values,
            'options': [op.to_dict() for op in self.options],
            'disabled': self.disabled,
        }

        if self.placeholder:
            payload['placeholder'] = self.placeholder

        return payload
    @classmethod
    def from_dict(cls, data: SelectMenuPayload):
        return cls(
            options=[SelectOption.from_dict(op) for op in data.get("optioins", [])],
            custom_id=data.get("custom_id"),
            placeholder=data.get("placeholder"),
            min_values=data.get("min_values", 1),
            max_values=data.get("max_values", 1),
            disabled=data.get("disabled", False)
        )


class SelectOption:
    __slots__: Tuple[str, ...] = (
        'label',
        'value',
        'description',
        'emoji',
        'default',
    )

    def __init__(
        self, label: str, value: str = MISSING, description: Optional[str] = None, 
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None, default: bool = False,
    ) -> None:
        self.label = label
        self.value = label if value is MISSING else value
        self.description = description

        if emoji is not None:
            if isinstance(emoji, str):
                emoji = PartialEmoji.from_str(emoji)
            elif isinstance(emoji, _EmojiTag):
                emoji = emoji._to_partial()
            else:
                raise TypeError(f'expected emoji to be str, Emoji, or PartialEmoji not {emoji.__class__}')

        self.emoji = emoji
        self.default = default

    def __repr__(self) -> str:
        return (
            f'<SelectOption label={self.label!r} value={self.value!r} description={self.description!r} '
            f'emoji={self.emoji!r} default={self.default!r}>'
        )

    def __str__(self) -> str:
        if self.emoji:
            base = f'{self.emoji} {self.label}'
        else:
            base = self.label

        if self.description:
            return f'{base}\n{self.description}'
        return base

    @classmethod
    def from_dict(cls, data: SelectOptionPayload) -> SelectOption:
        try:
            emoji = PartialEmoji.from_dict(data['emoji'])
        except KeyError:
            emoji = None

        return cls(
            label=data['label'],
            value=data['value'],
            description=data.get('description'),
            emoji=emoji,
            default=data.get('default', False),
        )

    def to_dict(self) -> SelectOptionPayload:
        payload: SelectOptionPayload = {
            'label': self.label,
            'value': self.value,
            'default': self.default,
        }

        if self.emoji:
            payload['emoji'] = self.emoji.to_dict()  # type: ignore

        if self.description:
            payload['description'] = self.description

        return payload


def _component_factory(data: ComponentPayload) -> Component:
    component_type = data['type']
    if component_type == 1:
        return ActionRow(data)
    elif component_type == 2:
        return BaseButton.from_dict(data)  # type: ignore
    elif component_type == 3:
        return SelectMenu.from_dict(data)  # type: ignore
    else:
        as_enum = get_enum(ComponentType, component_type)
        return Component._raw_construct(type=as_enum)
