from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
import typing

from dottygen.automata.states import State

@dataclass
class Action(ABC):
    """Interface for an action in the EFSM. An action can either be a send or a receive."""

    role: str
    label: str
    state_id: str
    succ_id: str
    payloads: typing.List[str]
    succ: State = field(init=False, compare=False)

    _ERR_MSG_TWO_REGEX: typing.ClassVar[str] = '(?P<role>.+)(?P<bla>[?])(?P<op>[#])\(\)'
    _ACTION_LABEL_REGEX: typing.ClassVar[str] = '(?P<role>.+)(?P<op>[!?])(?P<label>.+)\((?P<payloads>.*)\)'
    _ERR_MESSAGE_REGEX: typing.ClassVar[str] = '(?P<role>.+)(?P<op>[#])'
    _action_token_to_constructor: typing.ClassVar[typing.Dict[str, typing.Type['Action']]] = {}

    @classmethod
    def __init_subclass__(cls, *, action_token: str):
        """Register a type of action which uses the specified 'action_token' 
        in the transition label."""

        cls._action_token_to_constructor[action_token] = cls
        return super().__init_subclass__()

    @classmethod
    def parse(cls, action_label: str, src_state_id: str, dst_state_id: str) -> 'Action':
        """Parse the action specified by 'action_label' (in Scribble notation) into an
        Action instance, transitioning from 'src_state_id' to 'dst_state_id'."""

        matcher_error_2 = re.match(cls._ERR_MSG_TWO_REGEX, action_label)
        matcher = re.match(cls._ACTION_LABEL_REGEX, action_label)
        matcher_error = re.match(cls._ERR_MESSAGE_REGEX, action_label)
        if not matcher and not matcher_error and not matcher_error_2:
            raise ValueError(f'Invalid action: "{action_label}"')


        if matcher_error_2:
          components = matcher_error_2.groupdict()
        elif matcher_error:
            components = matcher_error.groupdict()
        else:
            components = matcher.groupdict()

        Constructor = Action._action_token_to_constructor.get(components['op'])
        if not Constructor:
            raise ValueError(f'Unsupported operation: "{components["op"]}"')

        payloads = [payload.strip() for payload in components['payloads'].split(',')
                    if payload.strip()] if matcher and not matcher_error_2 else []

        labels = components['label'] if matcher and not matcher_error_2 else []
        
        return Constructor(role=components['role'],
                           label=labels,
                           state_id=src_state_id,
                           succ_id=dst_state_id,
                           payloads=payloads)

    @abstractmethod
    def add_to_efsm(self, efsm: 'EfsmBuilder'):
        """Add this Action instance to the specified 'efsm'.
        
        To be implemented by concrete Action classes, as they customise 
        how the Action is added to the EFSM."""

        raise NotImplementedError('Action.add_to_efsm')


class SendAction(Action, action_token='!'):

    def add_to_efsm(self, efsm: 'EfsmBuilder'):
        efsm.add_action_to_send_state(self)


class ReceiveAction(Action, action_token='?'):

    def add_to_efsm(self, efsm: 'EfsmBuilder'):
        efsm.add_action_to_receive_state(self)

class ReceiveErrorAction(Action, action_token='#'):

    def add_to_efsm(self, efsm: 'EfsmBuilder'):
        efsm.add_action_to_receive_state(self, True)