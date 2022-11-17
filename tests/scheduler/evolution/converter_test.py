from scheduler.heft.base import HEFTScheduler
from utilities.validation import validate_schedule
from fixtures import *


def test_convert_schedule_to_chromosome(setup_toolbox, setup_wg, setup_contractors, setup_start_date):
    tb, _ = setup_toolbox

    schedule = \
        HEFTScheduler().schedule(setup_wg, setup_contractors, setup_start_date, validate=True)

    chromosome = tb.schedule_to_chromosome(schedule=schedule)
    assert tb.validate(chromosome)


def test_convert_chromosome_to_schedule(setup_toolbox, setup_contractors, setup_wg, setup_start_date):
    tb, _ = setup_toolbox

    chromosome = tb.n_per_product()
    schedule = Schedule.from_scheduled_works(tb.chromosome_to_schedule(chromosome).values(), setup_start_date, setup_wg)

    validate_schedule(schedule, setup_wg, setup_contractors)
