import pathlib
import cProfile
import pstats
import time
import platform

import pytest

from ...generate import default_generate

TEST_PATH = pathlib.Path("/media/raghuram/dmerk_test_disk/TEST_DATA/PERFORMANCE")


# # To clear page cache, run the following as root,
# # echo 3 > /proc/sys/vm/drop_caches
# # Ref: https://unix.stackexchange.com/a/87909/420985
# # Ref: https://en.wikipedia.org/wiki/Page_cache
# data = {
#     "/home/raghuram/Workspace/bin/Python-3.11.2/python": {
#         "FirstRun": 88.4159324169159,
#         "SecondRun": 18.878408670425415,
#     },
#     "/usr/bin/python3.10": {
#         "FirstRun": 86.97550201416016,
#         "SecondRun": 18.898996591567993,
#     },
#     "/home/raghuram/Workspace/bin/pypy3.10-v7.3.12-linux64/bin/pypy": {
#         "FirstRun": 118.44942545890808,
#         "SecondRun": 45.53729796409607,
#     },
# }
@pytest.mark.slow
@pytest.mark.test_performance
def test_performance_time(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    start = time.time()
    default_generate(TEST_PATH)
    end = time.time()
    time_taken = end - start
    print(f"Time Taken = {time_taken}s")
    # TODO: don't hardcode the time thresholds
    if platform.python_implementation() == "PyPy":
        assert time_taken < 120  # PyPy slow to startup I guess...
    else:
        assert time_taken < 90


@pytest.mark.slow
@pytest.mark.profile
def test_performance_profile(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    filename = "dmerk/test/generate/test_performance_profile.prof"
    stats = cProfile.runctx(
        "default_generate(TEST_PATH)", globals(), locals(), filename
    )
    p = pstats.Stats(filename)
    print(p.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(30))
    print(p.sort_stats(pstats.SortKey.TIME).print_stats(10))


def test_performance_memory(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print("TODO")
