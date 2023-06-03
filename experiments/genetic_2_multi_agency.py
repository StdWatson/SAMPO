from random import Random

from sampo.generator import SimpleSynthetic
from sampo.generator.pipeline.types import SyntheticGraphType
from sampo.scheduler.genetic.base import GeneticScheduler
from sampo.scheduler.multi_agency.block_generator import SyntheticBlockGraphType, generate_block_graph
from sampo.scheduler.multi_agency.multi_agency import Agent, Manager
from sampo.scheduler.utils.obstruction import OneInsertObstruction

r_seed = 231
p_rand = SimpleSynthetic(rand=r_seed)
rand = Random(r_seed)


def obstruction_getter(i: int):
    return OneInsertObstruction.from_static_graph(0.5, rand, p_rand.work_graph(SyntheticGraphType.Sequential, 10))



if __name__ == '__main__':
    schedulers = [GeneticScheduler(50, 50, 0.5, 0.5, 100),
                  GeneticScheduler(50, 100, 0.25, 0.5, 100),
                  GeneticScheduler(50, 100, 0.5, 0.75, 100),
                  GeneticScheduler(50, 100, 0.75, 0.75, 100),
                  GeneticScheduler(50, 50, 0.9, 0.9, 100)]

    contractors = [p_rand.contractor(10) for _ in range(len(schedulers))]

    agents = [Agent(f'Agent {i}', schedulers[i % len(schedulers)], [contractor])
              for i, contractor in enumerate(contractors)]
    manager = Manager(agents)

    bg = generate_block_graph(SyntheticBlockGraphType.Sequential, 10, [1, 1, 1], lambda x: (50, 100), 0.5,
                              rand, obstruction_getter, 2, [3, 4], [3, 4], logger=print)
    conjuncted = bg.to_work_graph()

    scheduled_blocks = manager.manage_blocks(bg, logger=print)

    print(f'Multi-agency res: {max(sblock.end_time for sblock in scheduled_blocks.values())}')

    best_genetic = GeneticScheduler(50, 50, 0.9, 0.9, 100)

    schedule = best_genetic.schedule(conjuncted, [contractors[4]])

    print(f'Genetic res: {schedule.execution_time}')
