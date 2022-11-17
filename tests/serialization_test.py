import os
import shutil
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from schemas.graph import WorkGraph
from schemas.schedule import Schedule
from schemas.serializable import S
from tests.models.serialization import TestSimpleSerialization, TestAutoJSONSerializable, TestJSONSerializable, \
    TestStrSerializable

STORAGE = './tmp_storage'  # Test files tmp storage


def stored_file(name):
    return os.path.join(STORAGE, name)


@pytest.yield_fixture(scope='module', autouse=True)
def setup_storage(request):
    if not os.path.exists(STORAGE):
        os.mkdir(STORAGE)
    yield
    shutil.rmtree(STORAGE)


@pytest.yield_fixture(scope='class')
def setup_core_resources(request):
    array_sample = [-100, 200.2, 'True', False]
    test_sample = TestSimpleSerialization()
    test_sample.key = '1,2,3'
    test_sample.value = [1, 2, 3]
    auto_json = TestAutoJSONSerializable(1,
                                         .5,
                                         array_sample,
                                         {str(i): i for i in array_sample},
                                         False,
                                         None,
                                         np.array(array_sample),
                                         pd.DataFrame({str(i): array_sample for i in array_sample}),
                                         test_sample,
                                         test_sample, None)
    auto_json.neighbor_info = auto_json
    manual_json = TestJSONSerializable(1, 'test', 100, '100', True)
    manual_str = TestStrSerializable(1, 'test', [True, 'test2', {'a': 1, 'b': 2}])
    return {
        'auto_json': auto_json,
        'manual_json': manual_json,
        'manual_str': manual_str
    }


@pytest.fixture(scope='class')
def setup_inherited_resources(request, setup_scheduling_inner_params, setup_schedule):
    schedule, _ = setup_schedule
    work_graph, contractor_list, _ = setup_scheduling_inner_params
    return {
        'work_graph': work_graph,
        'contractor_list': contractor_list,
        'schedule': schedule
    }


def perform_generalized_serializable_test(resource: S, name: str = None, verbose: bool = True) -> S:
    name = name or str(uuid4())
    resource.dump(STORAGE, name)
    new_resource = type(resource).load(STORAGE, name)
    if verbose:
        for k, v in new_resource.__dict__.items():
            print(f'---\n{k}:\n{v}', end='\n\n')
    return new_resource


class TestSerializationCore:
    def test_auto_json(self, setup_core_resources):
        perform_generalized_serializable_test(setup_core_resources['auto_json'], 'test_auto_json')

    def test_manual_json(self, setup_core_resources):
        perform_generalized_serializable_test(setup_core_resources['manual_json'], 'test_manual_json')

    def test_manual_str(self, setup_core_resources):
        perform_generalized_serializable_test(setup_core_resources['manual_str'], 'test_manual_str')


class TestInheritedSerializable:
    def test_schedule(self, setup_inherited_resources):
        new_schedule: Schedule = perform_generalized_serializable_test(setup_inherited_resources['schedule'],
                                                                       'test_schedule')

        full_df = new_schedule.full_schedule_df
        pure_df = new_schedule.pure_schedule_df
        s_works = list(new_schedule.works)
        swd = new_schedule.to_schedule_work_dict
        exec_time = new_schedule.execution_time

        assert full_df.shape[0] >= pure_df.shape[0]
        assert full_df.shape[1] > pure_df.shape[1]
        assert len(s_works) == full_df.shape[0]
        assert len(s_works) == len(swd)
        # assert isinstance(exec_time, Time)

    def test_work_graph(self, setup_inherited_resources):
        new_work_graph: WorkGraph = perform_generalized_serializable_test(setup_inherited_resources['work_graph'],
                                                                          'test_work_graph')

        vertex_count = new_work_graph.vertex_count
        start_node = new_work_graph.start
        finish_node = new_work_graph.finish
        nodes_dict = new_work_graph.dict_nodes
        nodes_list = new_work_graph.nodes
        adjacency_matrix = new_work_graph.adj_matrix

        assert vertex_count > 0
        assert not start_node.parents
        assert not finish_node.children
        assert len(nodes_dict) == len(nodes_list)
        assert adjacency_matrix.shape == (len(nodes_list), len(nodes_list))

