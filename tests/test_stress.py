
import numpy as np
import sys
import os
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
sys.path.append(src_dir)

from cap.core import find_optimal_cuts_dp

def test_boundary_cases():

    print("Running boundary tests...", end=" ")
    failures = []

    cases = [
        {"name": "H just above target", "H": 1050, "T": 1000, "W": 0.1},
        {"name": "H below target", "H": 500, "T": 1000, "W": 0.1},
        {"name": "Zero Smoothing", "H": 2000, "T": 1000, "R": 0},
        {"name": "Huge Smoothing", "H": 2000, "T": 1000, "R": 100},
        {"name": "Band > H", "H": 2000, "T": 1000, "B": 5000},
        {"name": "MinGap > Injected", "H": 2000, "T": 1000, "GapCap": 0.05, "MinGap": 500},
    ]

    for c in cases:
        try:
            H = c.get("H", 2000)
            target = c.get("T", 1000)
            win = c.get("W", 0.05)
            smooth = c.get("R", 5)
            band = c.get("B", 200)
            min_gap = c.get("MinGap", 12)

            ink = np.full(H, 0.8)
            cuts = find_optimal_cuts_dp(ink, target, window_frac=win,
                                        smoothing_radius=smooth, band_size=band, min_gap_rows=min_gap)

            if len(cuts) < 2 or cuts[0] != 0 or cuts[-1] != H:
                failures.append(f"Case '{c['name']}': Invalid result {cuts}")
        except Exception as e:
            failures.append(f"Case '{c['name']}' EXCEPTION: {e}")

    if failures:
        print(f"FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  {f}")
        raise AssertionError(f"{len(failures)} boundary test failures")

    print("PASS")





def test_fuzz_random_profiles():

    print("Running fuzz tests (50 trials)...", end=" ")

    np.random.seed(42)
    num_trials = 50
    failures = []

    for trial in range(num_trials):
        try:

            H = np.random.randint(1000, 10000)
            target = np.random.randint(500, 2000)
            window_frac = np.random.uniform(0.03, 0.2)


            ink = np.random.uniform(0.0, 1.0, H)


            cuts = find_optimal_cuts_dp(ink, target, window_frac=window_frac)


            assert len(cuts) >= 2, f"Trial {trial}: too few cuts"
            assert cuts[0] == 0, f"Trial {trial}: doesn't start at 0"
            assert cuts[-1] == H, f"Trial {trial}: doesn't end at H"
            assert all(cuts[i] < cuts[i+1] for i in range(len(cuts)-1)), \
                f"Trial {trial}: cuts not increasing"

        except Exception as e:
            failures.append(f"Trial {trial}: {str(e)}")

    if failures:
        print(f"FAIL ({len(failures)} failures)")
        for f in failures[:5]:
            print(f"  {f}")
        raise AssertionError(f"{len(failures)} fuzz test failures")

    print("PASS")





def test_stress_benchmark():

    print("Running stress benchmark (H=20000)...", end=" ")

    H = 20000
    target = 1000
    ink = np.full(H, 1.0)

    start_time = time.time()
    cuts = find_optimal_cuts_dp(ink, target, band_size=50, window_frac=0.1)
    duration = time.time() - start_time

    assert len(cuts) >= 2, "Invalid cuts"
    assert cuts[0] == 0 and cuts[-1] == H, "Invalid bounds"

    if duration > 5.0:
        print(f"FAIL (took {duration:.2f}s, expected <5s)")
        raise AssertionError(f"Stress test too slow: {duration:.2f}s")

    print(f"PASS ({duration:.2f}s)")





def run_stress_tests():

    print("=" * 70)
    print("Running Stress Tests")
    print("=" * 70)

    tests = [
        test_boundary_cases,
        test_fuzz_random_profiles,
        test_stress_benchmark,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"FAILED: {str(e)}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    else:
        print("\nALL STRESS TESTS PASSED!")

if __name__ == "__main__":
    run_stress_tests()
