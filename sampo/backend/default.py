import sampo.scheduler

from random import Random
from typing import Callable

from sampo.api.genetic_api import FitnessFunction, ChromosomeType
from sampo.backend import ComputationalBackend, T, R, ComputationalContext
from sampo.scheduler.genetic.utils import init_chromosomes_f, create_toolbox_using_cached_chromosomes
from sampo.schemas import WorkGraph, Contractor, LandscapeConfiguration, WorkTimeEstimator, Schedule, GraphNode, Time
from sampo.schemas.schedule_spec import ScheduleSpec
from sampo.schemas.time_estimator import DefaultWorkEstimator


class DefaultComputationalContext(ComputationalContext):

    def map(self, action: Callable[[T], R], values: list[T]) -> list[R]:
        return [action(v) for v in values]


class DefaultComputationalBackend(ComputationalBackend):
    _actions = {}

    def new_context(self) -> ComputationalContext:
        return DefaultComputationalContext()

    def cache_scheduler_info(self,
                             wg: WorkGraph,
                             contractors: list[Contractor],
                             landscape: LandscapeConfiguration,
                             spec: ScheduleSpec,
                             rand: Random | None = None,
                             work_estimator: WorkTimeEstimator | None = None):
        self._wg = wg
        self._contractors = contractors
        self._landscape = landscape
        self._spec = spec
        self._rand = rand
        self._work_estimator = work_estimator

    def cache_genetic_info(self,
                           population_size: int,
                           mutate_order: float,
                           mutate_resources: float,
                           mutate_zones: float,
                           init_schedules: dict[str, tuple[Schedule, list[GraphNode] | None, ScheduleSpec, float]],
                           assigned_parent_time: Time):
        self._population_size = population_size
        self._mutate_order = mutate_order
        self._mutate_resources = mutate_resources
        self._mutate_zones = mutate_zones
        self._init_schedules = init_schedules
        self._assigned_parent_time = assigned_parent_time

    def compute_chromosomes(self,
                            fitness: FitnessFunction,
                            chromosomes: list[ChromosomeType]) -> list[float]:
        if self._toolbox is None:
            init_chromosomes = init_chromosomes_f(self._wg, self._contractors, self._init_schedules,
                                                  self._landscape)

            rand = self._rand or Random()
            work_estimator = self._work_estimator or DefaultWorkEstimator()
            assigned_parent_time = self._assigned_parent_time or Time(0)

            self._toolbox = create_toolbox_using_cached_chromosomes(self._wg,
                                                                    self._contractors,
                                                                    self._population_size,
                                                                    self._mutate_order,
                                                                    self._mutate_resources,
                                                                    self._mutate_zones,
                                                                    init_chromosomes,
                                                                    rand,
                                                                    self._spec,
                                                                    work_estimator,
                                                                    assigned_parent_time,
                                                                    self._landscape)

        return [fitness.evaluate(chromosome, self._toolbox.evaluate_chromosome) for chromosome in chromosomes]
