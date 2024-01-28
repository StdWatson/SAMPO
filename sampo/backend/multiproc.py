import math
from typing import Callable

import sampo.scheduler

from random import Random

import pathos.multiprocessing

from sampo.api.genetic_api import ChromosomeType, FitnessFunction
from sampo.backend import T, R
from sampo.backend.default import DefaultComputationalBackend
from sampo.scheduler.genetic.operators import Individual
from sampo.scheduler.genetic.utils import create_toolbox_using_cached_chromosomes, init_chromosomes_f
from sampo.scheduler.heft import HEFTScheduler, HEFTBetweenScheduler
from sampo.scheduler.heft.prioritization import prioritization
from sampo.scheduler.resource import AverageReqResourceOptimizer
from sampo.scheduler.resources_in_time import AverageBinarySearchResourceOptimizingScheduler
from sampo.scheduler.topological.base import RandomizedTopologicalScheduler
from sampo.schemas import WorkGraph, Contractor, LandscapeConfiguration, Time, WorkTimeEstimator, Schedule, GraphNode, \
    NoSufficientContractorError
from sampo.schemas.schedule_spec import ScheduleSpec
from sampo.schemas.time_estimator import DefaultWorkEstimator


def scheduler_info_initializer(wg: WorkGraph,
                               contractors: list[Contractor],
                               landscape: LandscapeConfiguration,
                               spec: ScheduleSpec,
                               selection_size: int,
                               mutate_order: float,
                               mutate_resources: float,
                               mutate_zones: float,
                               deadline: Time | None,
                               weights: list[int] | None,
                               init_chromosomes: dict[str, tuple[ChromosomeType, float, ScheduleSpec]],
                               assigned_parent_time: Time,
                               rand: Random | None = None,
                               work_estimator_recreate_params: tuple | None = None):
    global g_wg, g_contractors, g_landscape, g_spec, g_toolbox, g_work_estimator, g_deadline, g_rand, g_weights

    g_wg = wg
    g_contractors = contractors
    g_landscape = landscape
    g_spec = spec
    g_deadline = deadline
    g_weights = weights

    g_rand = rand or Random()
    assigned_parent_time = assigned_parent_time or Time(0)

    g_work_estimator = work_estimator_recreate_params[0](*work_estimator_recreate_params[1])

    if init_chromosomes is not None:
        g_toolbox = create_toolbox_using_cached_chromosomes(wg,
                                                            contractors,
                                                            selection_size,
                                                            mutate_order,
                                                            mutate_resources,
                                                            mutate_zones,
                                                            init_chromosomes,
                                                            rand,
                                                            spec,
                                                            g_work_estimator,
                                                            assigned_parent_time,
                                                            landscape)


class MultiprocessingComputationalBackend(DefaultComputationalBackend):

    def __init__(self, n_cpus: int):
        self._n_cpus = n_cpus
        self._init_chromosomes = None
        super().__init__()

    def map(self, action: Callable[[T], R], values: list[T]) -> list[R]:
        return self._pool.map(action, values)

    def _recreate_pool(self):
        self._pool = pathos.multiprocessing.Pool(self._n_cpus,
                                                 initializer=scheduler_info_initializer,
                                                 initargs=(self._wg,
                                                           self._contractors,
                                                           self._landscape,
                                                           self._spec,
                                                           self._selection_size,
                                                           self._mutate_order,
                                                           self._mutate_resources,
                                                           self._mutate_zones,
                                                           self._deadline,
                                                           self._weights,
                                                           self._init_chromosomes,
                                                           self._assigned_parent_time,
                                                           self._rand,
                                                           self._work_estimator.get_recreate_info()))

    def cache_scheduler_info(self,
                             wg: WorkGraph,
                             contractors: list[Contractor],
                             landscape: LandscapeConfiguration,
                             spec: ScheduleSpec,
                             rand: Random | None = None,
                             work_estimator: WorkTimeEstimator = DefaultWorkEstimator()):
        super().cache_scheduler_info(wg, contractors, landscape, spec, rand, work_estimator)
        self._recreate_pool()

    def cache_genetic_info(self,
                           selection_size: int,
                           mutate_order: float,
                           mutate_resources: float,
                           mutate_zones: float,
                           deadline: Time | None,
                           weights: list[int] | None,
                           init_schedules: dict[str, tuple[Schedule, list[GraphNode] | None, ScheduleSpec, float]],
                           assigned_parent_time: Time):
        super().cache_genetic_info(selection_size, mutate_order, mutate_resources,
                                   mutate_zones, deadline, init_schedules, assigned_parent_time)
        self._init_chromosomes = init_chromosomes_f(self._wg, self._contractors, init_schedules, self._landscape)
        self._recreate_pool()

    def compute_chromosomes(self, fitness: FitnessFunction, chromosomes: list[ChromosomeType]) -> list[float]:
        def mapper(chromosome):
            return fitness.evaluate(chromosome, g_toolbox.evaluate_chromosome)

        return self.map(mapper, chromosomes)

    def generate_first_population(self, size_population: int) -> list[Individual]:

        weights = g_weights or [2, 2, 1, 1, 1, 1]

        def mapper(key: str):
            def randomized_init() -> ChromosomeType:
                schedule = RandomizedTopologicalScheduler(g_work_estimator, int(g_rand.random() * 1000000)) \
                    .schedule(g_wg, g_contractors, landscape=g_landscape)
                return g_toolbox.schedule_to_chromosome(schedule, g_spec, g_landscape)

            def init_k_schedule(scheduler_class, k) -> tuple[Schedule | None, list[GraphNode] | None, ScheduleSpec | None]:
                try:
                    return scheduler_class(work_estimator=g_work_estimator,
                                           resource_optimizer=AverageReqResourceOptimizer(k)) \
                        .schedule(g_wg, g_contractors,
                                  g_spec,
                                  landscape=g_landscape), list(reversed(prioritization(g_wg, g_work_estimator))), g_spec
                except NoSufficientContractorError:
                    return None, None, None

            if g_deadline is None:
                def init_schedule(scheduler_class) -> tuple[Schedule | None, list[GraphNode] | None, ScheduleSpec | None]:
                    try:
                        return scheduler_class(work_estimator=g_work_estimator).schedule(g_wg, g_contractors,
                                                                                       landscape=g_landscape), \
                            list(reversed(prioritization(g_wg, g_work_estimator))), g_spec
                    except NoSufficientContractorError:
                        return None, None, None

            else:
                def init_schedule(scheduler_class) -> tuple[Schedule | None, list[GraphNode] | None, ScheduleSpec | None]:
                    try:
                        (schedule, _, _, _), modified_spec = AverageBinarySearchResourceOptimizingScheduler(
                            scheduler_class(work_estimator=g_work_estimator)
                        ).schedule_with_cache(g_wg, g_contractors, g_deadline, g_spec, landscape=g_landscape)
                        return schedule, list(reversed(prioritization(g_wg, g_work_estimator))), modified_spec
                    except NoSufficientContractorError:
                        return None, None, None

            def convert(schedule: Schedule, priority_list: list[GraphNode], spec: ScheduleSpec):
                return g_toolbox.schedule_to_chromosome(schedule, spec, priority_list)

            match key:
                case 'heft_end':
                    return convert(*init_schedule(HEFTScheduler))
                case 'heft_between':
                    return convert(*init_schedule(HEFTBetweenScheduler))
                case '12.5%':
                    return convert(*init_k_schedule(HEFTScheduler, 8))
                case '25%':
                    return convert(*init_k_schedule(HEFTScheduler, 4))
                case '75%':
                    return convert(*init_k_schedule(HEFTScheduler, 4 / 3))
                case '87.5%':
                    return convert(*init_k_schedule(HEFTScheduler, 8 / 7))
                case 'randomized':
                    return convert(*randomized_init())

        count_for_specified_types = (size_population // 3) // len(weights)
        count_for_specified_types = count_for_specified_types if count_for_specified_types > 0 else 1
        sum_counts_for_specified_types = count_for_specified_types * len(weights)
        counts = [count_for_specified_types * importance for importance in weights.values()]

        weights_multiplier = math.ceil(sum_counts_for_specified_types / sum(counts))
        counts = [count * weights_multiplier for count in counts]

        count_for_topological = size_population - sum_counts_for_specified_types
        count_for_topological = count_for_topological if count_for_topological > 0 else 1
        counts += [count_for_topological]

        chromosome_keys = ['heft_end', 'heft_between', '12.5%', '25%', '75%', '87.5%', 'randomized']
        chromosome_types = g_rand.sample(chromosome_keys, k=size_population, counts=counts)

        chromosomes = self._pool.map(mapper, chromosome_types)
        return [Individual(chromosome) for chromosome in chromosomes]
