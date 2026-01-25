import numpy as np
import sys, os
import collections
import math
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)
from cap.core import find_optimal_cuts_dp

# 1. Fixed random seed globally? No, we use seed per trial now.

def run_fuzz_tests(seeds=None, num_trials=100):
    # If seeds not provided, generate range
    if seeds is None:
        seeds = list(range(12345, 12345 + num_trials))
    
    print(f"Starting STRICT fuzz tests with {len(seeds)} trials/seeds...")
    failures = []
    fallback_count = 0
    total_time = 0.0
    
    for seed in seeds:
        # 1. Deterministic RNG per trial
        rng = np.random.default_rng(seed)
        
        # 3. Sample parameters
        target_height = int(rng.choice([800, 1000, 1200]))
        window_frac = rng.uniform(0.05, 0.15)
        max_window = int(target_height * window_frac)
        
        smoothing_radius = int(rng.choice([0, 3, 5, 10, 15]))
        band_size = 200
        gap_cap = 0.05
        
        # Determine Regime deterministically from seed
        is_gap_regime = (seed % 2 == 1)
        regime_name = "Gap" if is_gap_regime else "Bridge"
        
        # Path Generation
        cuts_ground_truth = [0]
        current_row = 0
        k = int(rng.choice([2, 3, 4]))
        
        basins_metadata = [] # (start, end, center, depth, width)
        
        # Inject Basins along valid path
        for i in range(k):
             prev_center = cuts_ground_truth[-1]
             valid_step_found = False
             
             # Basin params (pre-sample width as it affects snapping)
             if is_gap_regime:
                 valley_depth = 0.0 
                 valley_width = rng.integers(15, 60)
             else:
                 valley_depth = rng.uniform(gap_cap + 0.01, 0.40)
                 valley_width = rng.integers(8, 60)
                 
             for attempt in range(100):
                 step = target_height + rng.integers(-max_window, max_window + 1)
                 raw_center = prev_center + step
                 
                 # Snap logic
                 center = raw_center
                 start_b = center - valley_width // 2
                 end_b = center + valley_width // 2
                 
                 band_idx_start = start_b // band_size
                 band_idx_end = end_b // band_size
                 
                 if band_idx_start != band_idx_end:
                     # Shift to band center
                     center = int((band_idx_start + 0.5) * band_size)
                 
                 # Check validity of SNAPPED distance
                 dist = center - prev_center
                 if abs(dist - target_height) <= max_window:
                     valid_step_found = True
                     current_row = center
                     cuts_ground_truth.append(current_row)
                     # Recalculate bounds for final center
                     start_b = center - valley_width // 2
                     end_b = center + valley_width // 2
                     break
             
             if not valid_step_found:
                 raise RuntimeError(f"Could not generate valid snapped path for seed {seed} at step {i}")
             
             basins_metadata.append({
                 'start': start_b, 'end': end_b, 
                 'center': center, 'depth': valley_depth, 'width': valley_width,
                 'ideal_idx': i
             })

        # Define H
        # Force tail large enough to prevent merging with previous step (T-M + tail > T+M => tail > 2M)
        tail = rng.integers(2 * max_window + 20, target_height + max_window + 1)
        H = cuts_ground_truth[-1] + tail
        
        # Build Ink Final
        # Baseline with deterministic noise (Step 6)
        baseline = 0.80
        noise = 1e-4 * np.sin(np.arange(H))
        ink = np.full(H, baseline, dtype=float) + noise
        
        # Paint basins
        for b in basins_metadata:
            s, e = b['start'], b['end']
            d = b['depth']
            # Clip
            s = max(0, s); e = min(H, e)
            if s < e:
                ink[s:e] = d
        
        # 7. Run Solver
        try:
            t0 = time.time()
            results = find_optimal_cuts_dp(ink, target_height, 
                                      window_frac=window_frac,
                                      smoothing_radius=smoothing_radius,
                                      band_size=band_size,
                                      gap_cap=gap_cap,
                                      return_debug_info=True)
            duration = time.time() - t0
            total_time += duration
            cuts, debug_info = results
            if debug_info.get("fallback"):
                fallback_count += 1
        except Exception as e:
            failures.append({
                "seed": seed, 
                "replay_line": f"REPLAY: seed={seed}, regime={regime_name}, ERROR", 
                "error": str(e),
                "full_detail": {"exception": str(e)}
            })
            continue

        # 8. Assertions
        try:
            fallback = debug_info.get("fallback", False)
            fallback_reason = debug_info.get("fallback_reason", None)
            
            # Basic Strict Invariants
            assert len(cuts) >= 2
            assert cuts[0] == 0
            assert cuts[-1] == H
            assert all(cuts[i] < cuts[i+1] for i in range(len(cuts)-1))
            
            if fallback:
                # Valid fallback trial
                valid_reasons = ["no_internal_candidates", "no_valid_path_to_end"]
                assert fallback_reason in valid_reasons, f"Unknown fallback reason: {fallback_reason}"
                # Log usage but don't fail strict coverage tests
                pass 
            else:
                # DP Success - Strict Coverage Verification
                internal_cuts = cuts[1:-1]
                assert len(internal_cuts) == k, \
                    f"Expected {k} internal cuts, got {len(internal_cuts)}. Cuts: {cuts}"

                tol = 10 # 10px tolerance
                
                for i, b in enumerate(basins_metadata):
                    s, e = b['start'], b['end']
                    matches = [c for c in internal_cuts if (s - tol) <= c <= (e + tol)]
                    
                    if len(matches) == 0:
                        raise AssertionError(f"Basin {i} (Regime {regime_name}) missed! Basin [{s}, {e}], Cuts: {internal_cuts}")
                    if len(matches) > 1:
                        raise AssertionError(f"Basin {i} (Regime {regime_name}) double-hit! Basin [{s}, {e}], Matches: {matches}")
                        
                for c in internal_cuts:
                    in_any = False
                    for b in basins_metadata:
                        if (b['start'] - tol) <= c <= (b['end'] + tol):
                            in_any = True
                            break
                    if not in_any:
                        raise AssertionError(f"Cut {c} is not in any basin! Basins: {[(b['start'], b['end']) for b in basins_metadata]}")

        except AssertionError as e:
            # Compact repro with Replay Line
            params_str = f"T={target_height}, W={window_frac:.2f}, R={smoothing_radius}, Band={band_size}, GapCap={gap_cap}"
            basins_compact = [(int(b['center']), int(b['start']), int(b['end']), f"{b['depth']:.3f}") for b in basins_metadata]
            
            repro_line = f"REPLAY: seed={seed}, regime={regime_name}, params='{params_str}', basins={str(basins_compact)}"
            
            repro = {
                "seed": seed,
                "replay_line": repro_line,
                "error": str(e),
                "full_detail": {
                   "regime": regime_name,
                   "status": "FALLBACK" if debug_info.get("fallback") else "SUCCESS",
                   "cuts": [int(c) for c in cuts],
                   "debug": {
                      "costs": debug_info.get("chosen_path_costs", [])
                   }
                }
            }
            failures.append(repro)
            
    # Schema Verification Test
    test_debug_schema()

    if len(failures) == 0:
        print("ALL STRICT FUZZ TESTS PASSED!")
    else:
        print(f"{len(failures)} FAILURES FOUND:")
        for f in failures[:5]:
            print("\n" + f["replay_line"])
            print(f"  Error: {f['error']}")
            # print(f"  Details: {f['full_detail']}")
        sys.exit(1)
        
    return {
        "num_trials": len(seeds),
        "failures": len(failures),
        "fallback_count": fallback_count,
        "total_time": total_time
    }


def test_debug_schema():
    print("Verifying Debug Schema...")
    ink = np.full(1000, 0.8)
    cuts, debug = find_optimal_cuts_dp(ink, 500, return_debug_info=True)
    
    required = ["bridge_debug", "chosen_path_costs", "fallback", "fallback_reason"]
    for r in required:
        assert r in debug, f"Missing debug key: {r}"
    
    assert isinstance(debug["fallback"], bool)
    print("Debug Schema Verified.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        seeds = [int(sys.argv[2])]
        run_fuzz_tests(seeds=seeds)
    else:
        run_fuzz_tests()
