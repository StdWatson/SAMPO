from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Zone:
    name: str
    status: int


@dataclass
class ZoneReq:
    name: str
    require_status: int


@dataclass
class ZoneConfiguration:
    time_costs: np.ndarray

    def change_cost(self, from_status: int, to_status: int):
        return self.time_costs[from_status, to_status]


class ZoneStatuses(ABC):
    @abstractmethod
    def statuses_available(self) -> int:
        """
        :return: number of statuses available
        """
        ...

    @abstractmethod
    def match_status(self, target: int, to_compare: int) -> bool:
        """
        :param target: statues that should match
        :param to_compare: status that should be matched
        :return: does target match to_compare
        """
        ...


class DefaultZoneStatuses(ZoneStatuses):
    """
    Statuses: 0 - not stated, 1 - opened, 2 - closed
    """

    def statuses_available(self) -> int:
        return 3

    def match_status(self, target: int, to_compare: int) -> bool:
        return target == 0 or target == to_compare
