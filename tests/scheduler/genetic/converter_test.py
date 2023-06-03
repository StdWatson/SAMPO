from fixtures import *
from sampo.scheduler.heft.base import HEFTScheduler
from sampo.utilities.validation import validate_schedule


def test_convert_schedule_to_chromosome(setup_toolbox, setup_wg, setup_contractors):
    tb, _ = setup_toolbox

    schedule = \
        HEFTScheduler().schedule(setup_wg, setup_contractors, validate=True)

    chromosome = tb.schedule_to_chromosome(schedule=schedule)
    assert tb.validate(chromosome)


def test_convert_chromosome_to_schedule(setup_toolbox, setup_contractors, setup_wg):
    tb, _ = setup_toolbox

    chromosome = tb.generate_chromosome()
    schedule, _, _, _ = tb.chromosome_to_schedule(chromosome)
    schedule = Schedule.from_scheduled_works(schedule.values(), setup_wg)

    validate_schedule(schedule, setup_wg, setup_contractors)
