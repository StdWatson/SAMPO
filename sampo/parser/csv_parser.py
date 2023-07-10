import pickle
from itertools import chain
from random import Random

import pandas as pd
from pandas import DataFrame

from sampo.schemas.time_estimator import DefaultWorkEstimator, WorkTimeEstimator
from sampo.parser.contractor_type import ContractorType
from sampo.parser.general_build import add_graph_info, topsort_graph_df, build_work_graph, preprocess_graph_df
from sampo.schemas.contractor import Contractor, get_contractor_for_resources_schedule
from sampo.schemas.graph import WorkGraph
from sampo.utilities.task_name import NameMapper


class CSVParser:

    @staticmethod
    def parse(graph_info_file: str | None = None,
              contractor_types: list[int] = [ContractorType.Average.command_capacity()],
              unique_work_names_mapper: NameMapper | None = None,
              work_resource_estimator: WorkTimeEstimator = DefaultWorkEstimator()) \
            -> tuple[WorkGraph, list[Contractor]]:
        """
        Gets a WorkGraph either from file or as a synthetic data
        :param work_resource_estimator:
        :param use_task_resource_generation:
        :param unique_work_names_mapper:
        :param graph_info_file: Path to file, specified if generate_input == False.
        .pickle, if generate_resources=False, otherwise, works_info.csv or DataFrame
        :param rand: a random object to manage random processes
        :param generate_input: Whether to generate graph as synthetic data or not
        :param graph_mode: Mode of synthetic graph data. 'general', 'parallel' or 'sequence'
        :param synthetic_graph_vertices_lower_bound: Lower boundary of graph nodes count for synthetic data
        :param contractor_types: Types of contractor
        :return: WorkGraph, Contractors and Agents
        """

        graph_df = pd.read_csv(graph_info_file, sep=';', header=0) if isinstance(graph_info_file, str) else graph_info_file
        works_info = preprocess_graph_df(graph_df)

        works_info['activity_name_original'] = works_info.activity_name
        if unique_work_names_mapper:
            works_info.activity_name = works_info.activity_name.apply(lambda name: unique_work_names_mapper[name])

        resources = [work_resource_estimator.find_work_resources(w[0], float(w[1]))
                     for w in works_info.loc[:, ['activity_name', 'volume']].to_numpy()]

        contractor_name = 'Подрядчик'

        contractor_list = [get_contractor_for_resources_schedule(resources,
                                                                 contractor_capacity=contractor_types[i],
                                                                 contractor_id=str(i),
                                                                 contractor_name=contractor_name + ' ' + str(i + 1))
                           for i in range(len(contractor_types))]

        unique_res = list(set(chain(*[r.keys() for r in resources])))
        works_info.loc[:, unique_res] = DataFrame(resources).fillna(0)

        works_resources = add_graph_info(works_info)
        works_resources = topsort_graph_df(works_resources)
        work_graph = build_work_graph(works_resources, unique_res)

        return work_graph, contractor_list
