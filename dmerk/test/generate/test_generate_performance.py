import pathlib
import cProfile
import pstats

from ...generate import default_generate

TEST_PATH = pathlib.Path("/media/raghuram/dmerk_test_disk/TEST_DATA/PERFORMANCE/1M")

def test_performance_benchmark(request, benchmark):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    benchmark(default_generate, TEST_PATH)

def test_performance_profile(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    filename = "dmerk/test/generate/test_performance_profile.prof"
    stats = cProfile.runctx("default_generate(TEST_PATH)", globals(), locals(), filename)
    p = pstats.Stats(filename)
    p.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(30)
    p.sort_stats(pstats.SortKey.TIME).print_stats(10)

def test_performance_memory(request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print("TODO")
