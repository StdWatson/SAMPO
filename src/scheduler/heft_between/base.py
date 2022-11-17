from typing import List, Optional, Dict, Any, Iterable

from utilities.time_estimator import WorkTimeEstimator
from metrics.resources_in_time.base import ResourceOptimizer
from scheduler.base import SchedulerType
from scheduler.heft.base import HEFTScheduler
from scheduler.heft.prioritization import prioritization
from scheduler.heft.time_computaion import calculate_working_time_cascade
from scheduler.resource.coordinate_descent import CoordinateDescentResourceOptimizer
from scheduler.utils.momentum_timeline import create_timeline, find_min_start_time, schedule
from scheduler.utils.multi_contractor import get_best_contractor_and_worker_borders
from schemas.contractor import Contractor, get_worker_contractor_pool, WorkerContractorPool
from schemas.graph import WorkGraph, GraphNode
from schemas.schedule import Schedule
from schemas.scheduled_work import ScheduledWork
from utilities.base_opt import dichotomy_int
from utilities.validation import validate_schedule


class HEFTBetweenScheduler(HEFTScheduler):

    def __init__(self,
                 scheduler_type: SchedulerType = SchedulerType.HEFTAddBetween,
                 resource_optimizer: ResourceOptimizer = CoordinateDescentResourceOptimizer(dichotomy_int),
                 work_estimator: Optional[WorkTimeEstimator or None] = None):
        super().__init__(scheduler_type, resource_optimizer, work_estimator)

    def schedule(self, wg: WorkGraph,
                 contractors: List[Contractor],
                 start: str,
                 validate: bool = False) \
            -> Schedule:
        agents = get_worker_contractor_pool(contractors)
        ordered_nodes = prioritization(wg, self.work_estimator)

        schedule = Schedule.from_scheduled_works(
            self.build_scheduler(ordered_nodes, agents, contractors, self.work_estimator),
            start, wg
        )

        if validate:
            validate_schedule(schedule, wg, contractors)

        return schedule

    def build_scheduler(self, ordered_nodes: List[GraphNode],
                        worker_pool: WorkerContractorPool, contractors: List[Contractor],
                        work_estimator: WorkTimeEstimator = None) \
            -> Iterable[ScheduledWork]:
        """
        Find optimal number of workers who ensure the nearest finish time.
        Finish time is combination of two dependencies: max finish time, max time of waiting of needed workers
        This is selected by iteration from minimum possible numbers of workers until then the finish time is decreasing
        :param contractors:
        :param work_estimator:
        :param ordered_nodes:
        :param worker_pool:
        :return:
        """
        # dict for writing parameters of completed_jobs
        node2swork: Dict[GraphNode, ScheduledWork] = {}
        # list for support the queue of workers
        timeline = create_timeline(ordered_nodes, contractors)
        # add to queue all available workers

        for index, node in enumerate(reversed(ordered_nodes)):  # the tasks with the highest rank will be done first
            work_unit = node.work_unit
            if node in node2swork:  # here
                continue

            inseparable_chain = node.get_inseparable_chain() if node.get_inseparable_chain() is not None else [node]

            min_count_worker_team, max_count_worker_team, contractor, workers \
                = get_best_contractor_and_worker_borders(worker_pool, contractors, work_unit.worker_reqs)

            best_worker_team = [worker.copy() for worker in workers]

            def get_finish_time(worker_team):
                return find_min_start_time(timeline[contractor.id], node, node2swork, inseparable_chain,
                                           best_worker_team, work_estimator)[0] \
                       + calculate_working_time_cascade(node, worker_team, work_estimator)

            self.resource_optimizer.optimize_resources(worker_pool, contractors, best_worker_team,
                                                       min_count_worker_team, max_count_worker_team, get_finish_time)

            # finish scheduling
            schedule(index, node, node2swork, inseparable_chain, timeline, best_worker_team, contractor, work_estimator)

        # parallelize_local_sequence(ordered_nodes, 0, len(ordered_nodes), node2swork)
        # recalc_schedule(reversed(ordered_nodes), node2swork, agents, work_estimator)

        return node2swork.values()
