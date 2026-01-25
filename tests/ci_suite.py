import numpy as np
import time
import sys, os
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)
src_dir = os.path.join(script_dir, "..", "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

from fuzz_test import run_fuzz_tests, test_debug_schema
from cap.core import find_optimal_cuts_dp

# Regression Thresholds
THRESHOLD_FALLBACK_RATE = 0.15  # Max 15% fallback allowed on seed set 0-99
THRESHOLD_MEAN_RUNTIME = 0.5   # Max 0.5s mean runtime per trial

def run_acceptance_tests_subprocess():
    print("Running Acceptance Tests (Corpus Golden Check)...")
    acceptance_script = os.path.join(script_dir, "acceptance_test.py")
    res = subprocess.run([sys.executable, acceptance_script], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
        print("ACCEPTANCE TESTS FAILED")
        sys.exit(1)
    print("Acceptance Tests Passed.")

def run_boundary_tests():
    print("Running Boundary/Degenerate Tests...")
    failures = []
    
    cases = [
        {"name": "H just above target", "H": 1050, "T": 1000, "W": 0.1},
        {"name": "H below target", "H": 500, "T": 1000, "W": 0.1},
        {"name": "Zero Smoothing", "H": 2000, "T": 1000, "R": 0},
        {"name": "Huge Smoothing", "H": 2000, "T": 1000, "R": 100},
        {"name": "Band > H", "H": 2000, "T": 1000, "B": 5000}, # 1 band
        {"name": "MinGap > Injected", "H": 2000, "T": 1000, "GapCap": 0.05, "MinGap": 500}, # No gap candidates
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
            print(f"  Passed: {c['name']}")
        except Exception as e:
            failures.append(f"Case '{c['name']}' EXCEPTION: {e}")

    if failures:
        print(f"{len(failures)} BOUNDARY FAILURES:")
        for f in failures: print("  " + f)
        sys.exit(1)
    print("All Boundary Tests Passed.")

def run_stress_benchmark():
    print("Running Stress Benchmark...")
    H = 20000
    target = 1000
    ink = np.full(H, 1.0) # Dense profile to force bridge candidates
    
    start_time = time.time()
    cuts = find_optimal_cuts_dp(ink, target, band_size=50, window_frac=0.1)
    duration = time.time() - start_time
    
    print(f"  H={H}, T={target}. Empirically benchmarked: {duration:.4f}s")
    
    if duration > 5.0:
        print(f"STRESS FAIL: Time {duration}s > 5.0s budget")
        sys.exit(1)
    print("Stress Benchmark Passed.")

if __name__ == "__main__":
    print("=== CI SUITE START ===")
    
    # 1. Fuzz & Regression Stats
    fuzz_results = run_fuzz_tests(seeds=list(range(100)))
    
    fb_rate = fuzz_results["fallback_count"] / fuzz_results["num_trials"]
    mean_time = fuzz_results["total_time"] / fuzz_results["num_trials"]
    
    print(f"\nREGRESSION STATS (Seeds 0-99):")
    print(f"  Fallback Rate: {fb_rate:.2%} (Threshold: {THRESHOLD_FALLBACK_RATE:.2%})")
    print(f"  Mean Runtime:  {mean_time:.4f}s (Threshold: {THRESHOLD_MEAN_RUNTIME:.4f}s)")
    
    if fb_rate > THRESHOLD_FALLBACK_RATE:
        print("ERROR: Fallback rate regression detected!")
        sys.exit(1)
    if mean_time > THRESHOLD_MEAN_RUNTIME:
        print("ERROR: Mean runtime regression detected!")
        sys.exit(1)
        
    # 2. Boundary
    run_boundary_tests()
    
    # 3. Acceptance (Corpus)
    run_acceptance_tests_subprocess()
    
    # 4. Stress
    run_stress_benchmark()
    
    print("\n=== CI SUITE SUCCESS ===")

