import numpy as np
import sys, os

sys.path.append(os.path.join(os.getcwd(), "src"))
from cap.core import find_optimal_cuts_dp

def assert_invariants(cuts, H):
    assert isinstance(cuts, (list, tuple)), "cuts must be a list/tuple"
    assert len(cuts) >= 2, "must have at least [0, H]"
    assert cuts[0] == 0, f"cuts must start at 0, got {cuts[0]}"
    assert cuts[-1] == H, f"cuts must end at H, got {cuts[-1]}"
    assert all(cuts[i] < cuts[i+1] for i in range(len(cuts)-1)), "cuts must be strictly increasing"
    assert all((cuts[i+1] - cuts[i]) > 0 for i in range(len(cuts)-1)), "no empty segments"

def assert_strict_window(cuts, target_height, window_frac):
    max_window = int(target_height * window_frac)
    for i in range(len(cuts) - 2):  # exclude last segment
        h = cuts[i+1] - cuts[i]
        assert abs(h - target_height) <= max_window, (
            f"segment {i} height {h} violates strict window +/- {max_window}"
        )

def assert_cut_in_any_gap(cut, gap_intervals):
    # gap_intervals: list of (a,b) inclusive/exclusive conventions; keep consistent
    ok = any(a <= cut <= b for (a, b) in gap_intervals)
    assert ok, f"cut {cut} not inside any expected gap interval {gap_intervals}"

def test_standard_case_gap_alignment():
    print("Running test_standard_case_gap_alignment...")
    H = 3500
    target_height = 1000
    window_frac = 0.1

    # Deterministic baseline: mostly moderate ink
    ink = np.full(H, 0.30, dtype=float)

    # Inject clear gaps (wide enough to be robust under smoothing)
    gap1 = (940, 960)
    gap2 = (2040, 2060)
    gap3 = (3040, 3060)
    ink[gap1[0]:gap1[1]] = 0.0
    ink[gap2[0]:gap2[1]] = 0.0
    ink[gap3[0]:gap3[1]] = 0.0

    cuts = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac)
    assert_invariants(cuts, H)
    assert_strict_window(cuts, target_height, window_frac)

    # Verify early cuts fall inside the injected gaps
    expected_gaps = [gap1, gap2, gap3]
    for cut in cuts[1:-1]:
        if cut < H - target_height: 
            assert_cut_in_any_gap(cut, expected_gaps)
    print("PASS")

def test_dense_case_requires_bridge_like_candidates():
    print("Running test_dense_case_requires_bridge_like_candidates...")
    H = 3500
    target_height = 1000
    window_frac = 0.1

    # 1. Ensure NO Gap Candidates
    # Set ink > 0.05 everywhere. Gap threshold caps at 0.05.
    # So is_gap will be False everywhere.
    ink = np.full(H, 0.8, dtype=float)
    
    # 2. Inject "Bridge" Valleys
    # These are local minima (0.2) but still > 0.05, so NOT gaps.
    # The algorithm MUST use bridge candidates to find these.
    # We place them intentionally slightly off perfect multiples to verify tracking.
    bridge1_center = 980
    bridge2_center = 2020
    bridge3_center = 2950 # Slightly short segment
    
    # Make valleys wide enough (e.g. 20px) to be stable bridge candidates
    ink[bridge1_center-10:bridge1_center+10] = 0.2
    ink[bridge2_center-10:bridge2_center+10] = 0.2
    ink[bridge3_center-10:bridge3_center+10] = 0.2

    cuts = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac)
    assert_invariants(cuts, H)
    assert_strict_window(cuts, target_height, window_frac)

    # 3. Assert cuts matched the bridge valleys
    # We expect cuts roughly at [0, 980, 2020, 2950, 3500] (or similar logic)
    # The last segment 2950->3500 is 550px, which is allowed for last page.
    
    # 3. Assert cuts matched the bridge valleys strictly by position
    # We expect cuts roughly at [0, 980, 2020, 2950, 3500]
    
    # Verify strict positional order
    # cuts[0] is 0 checked by invariants
    
    assert abs(cuts[1] - bridge1_center) < 5, f"Expected 1st cut at {bridge1_center}, got {cuts[1]}"
    assert abs(cuts[2] - bridge2_center) < 5, f"Expected 2nd cut at {bridge2_center}, got {cuts[2]}"
    
    print("PASS")

def test_smoothing_prefers_wide_band_over_single_row():
    print("Running test_smoothing_prefers_wide_band_over_single_row...")
    H = 2000
    target_height = 1000
    window_frac = 0.1

    ink = np.full(H, 0.80, dtype=float)

    # Candidate A: Single-row dip at 950. 
    ink[950] = 0.0
    
    # Candidate B: Wide band at 1050.
    wide_band = (1035, 1065) 
    ink[wide_band[0]:wide_band[1]] = 0.15

    # 1. Test WITHOUT Smoothing
    cuts_raw = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac, smoothing_radius=0)
    assert_invariants(cuts_raw, H)
    assert_strict_window(cuts_raw, target_height, window_frac) # Strict check added
    
    cut_raw = cuts_raw[1]
    assert abs(cut_raw - 950) < 5, f"NO-SMOOTHING failed: got {cut_raw}"
    print("  [PASS] Radius=0 selected sharp dip.")

    # 2. Test WITH Smoothing
    cuts_smooth = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac, smoothing_radius=10)
    assert_invariants(cuts_smooth, H)
    assert_strict_window(cuts_smooth, target_height, window_frac) # Strict check added
    
    cut_smooth = cuts_smooth[1]
    assert wide_band[0] <= cut_smooth <= wide_band[1], f"SMOOTHING failed: got {cut_smooth}"
    print("  [PASS] Radius=10 selected wide band.")
    
    print("PASS")

def test_last_page_behavior():
    print("Running test_last_page_behavior...")
    # H = 2150, Target = 1000.
    # Expected: [0, 1000, 2150] is BAD (1150 > 1000 + window?) 
    # Wait, window=0.1*1000=100. Max=1100. 1150 is too big.
    # So it MUST do [0, 1000, 2000, 2150] or similar.
    # Last segment height 150.
    H = 2150
    target_height = 1000
    window_frac = 0.1
    max_window = 100
    
    ink = np.full(H, 0.3, dtype=float)
    # Give it wider perfect gaps so ink cost is 0 at these points
    # This ensures the 3-page solution (cost 0) beats the 2-page solution (cost > 0 due to height)
    ink[990:1010] = 0.0
    ink[1990:2010] = 0.0
    
    cuts = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac)
    assert_invariants(cuts, H)
    
    # Check internal segments
    # Should have roughly 2 cuts before H?
    # 0 -> 1000 (h=1000) OK
    # 1000 -> 2000 (h=1000) OK
    # 2000 -> 2150 (h=150) OK (Last Page)
    
    # Strict assertions on structure
    assert len(cuts) == 4, f"Expected [0, ~1000, ~2000, 2150], got {cuts}"
    assert 990 <= cuts[1] <= 1010, f"Expected first cut near 1000 gap, got {cuts[1]}"
    assert 1990 <= cuts[2] <= 2010, f"Expected second cut near 2000 gap, got {cuts[2]}"
    assert cuts[3] == 2150
    
    # Verify strict window for non-last
    assert_strict_window(cuts, target_height, window_frac)
    
    # Verify last segment is valid logic
    last_h = cuts[-1] - cuts[-2]
    # It should be short
    assert last_h <= target_height + max_window, "Last page exceeded max extension"
    # In this specific setup, we expect it to be small (~150)
    assert last_h < target_height * 0.5, f"Expected short tail, got {last_h}"
    
    print("PASS")

if __name__ == "__main__":
    test_standard_case_gap_alignment()
    test_dense_case_requires_bridge_like_candidates()
    test_smoothing_prefers_wide_band_over_single_row()
    test_last_page_behavior()
    print("ALL TESTS PASSED")
