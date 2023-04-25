import pathlib
import cProfile
import pstats
import time
import platform

import pytest

from ...generate import default_generate

TEST_PATH = pathlib.Path("/media/raghuram/dmerk_test_disk/TEST_DATA/PERFORMANCE")


def test_performance_time(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    start = time.time()
    default_generate(TEST_PATH, exclude=[])
    end = time.time()
    print(f"Time Taken = {end-start}s")
    # TODO: don't hardcode the time thresholds
    if platform.python_implementation() == "PyPy":
        assert end - start < 60  # PyPy slow to startup I guess...
    else:
        assert end - start < 20


@pytest.mark.slow
@pytest.mark.profile
def test_performance_profile(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    filename = "dmerk/test/generate/test_performance_profile.prof"
    stats = cProfile.runctx(
        "default_generate(TEST_PATH, exclude=[])", globals(), locals(), filename
    )
    p = pstats.Stats(filename)
    print(p.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(30))
    print(p.sort_stats(pstats.SortKey.TIME).print_stats(10))


def test_performance_memory(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print("TODO")
