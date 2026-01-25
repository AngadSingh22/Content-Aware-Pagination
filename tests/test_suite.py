
import numpy as np
import sys
import os
from PIL import Image
import json
import hashlib


script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
sys.path.append(src_dir)

from cap.core import find_optimal_cuts_dp, compute_ink_density, CutMode
from cap.io import save_pdf_from_crops, RenderMode


try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False





def assert_invariants(cuts, H):

    assert isinstance(cuts, (list, tuple)), "cuts must be a list/tuple"
    assert len(cuts) >= 2, "must have at least [0, H]"
    assert cuts[0] == 0, f"cuts must start at 0, got {cuts[0]}"
    assert cuts[-1] == H, f"cuts must end at H, got {cuts[-1]}"
    assert all(cuts[i] < cuts[i+1] for i in range(len(cuts)-1)), "cuts must be strictly increasing"
    assert all((cuts[i+1] - cuts[i]) > 0 for i in range(len(cuts)-1)), "no empty segments"

def assert_strict_window(cuts, target_height, window_frac):

    max_window = int(target_height * window_frac)
    for i in range(len(cuts) - 2):
        h = cuts[i+1] - cuts[i]
        assert abs(h - target_height) <= max_window, (
            f"segment {i} height {h} violates strict window +/- {max_window}"
        )

def assert_cut_in_any_gap(cut, gap_intervals):

    ok = any(a <= cut <= b for (a, b) in gap_intervals)
    assert ok, f"cut {cut} not inside any expected gap interval {gap_intervals}"





def test_standard_case_gap_alignment():

    print("  test_standard_case_gap_alignment...", end=" ")
    H = 3500
    target_height = 1000
    window_frac = 0.1

    ink = np.full(H, 0.30, dtype=float)


    gap1 = (940, 960)
    gap2 = (2040, 2060)
    gap3 = (3040, 3060)
    ink[gap1[0]:gap1[1]] = 0.0
    ink[gap2[0]:gap2[1]] = 0.0
    ink[gap3[0]:gap3[1]] = 0.0

    cuts = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac)
    assert_invariants(cuts, H)
    assert_strict_window(cuts, target_height, window_frac)


    expected_gaps = [gap1, gap2, gap3]
    for cut in cuts[1:-1]:
        if cut < H - target_height:
            assert_cut_in_any_gap(cut, expected_gaps)
    print("PASS")

def test_dense_case_requires_bridge_like_candidates():

    print("  test_dense_case_requires_bridge_like_candidates...", end=" ")
    H = 3500
    target_height = 1000
    window_frac = 0.1


    ink = np.full(H, 0.8, dtype=float)


    bridge1_center = 980
    bridge2_center = 2020
    bridge3_center = 2950

    ink[bridge1_center-10:bridge1_center+10] = 0.2
    ink[bridge2_center-10:bridge2_center+10] = 0.2
    ink[bridge3_center-10:bridge3_center+10] = 0.2

    cuts = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac)
    assert_invariants(cuts, H)
    assert_strict_window(cuts, target_height, window_frac)


    assert abs(cuts[1] - bridge1_center) < 5, f"Expected 1st cut at {bridge1_center}, got {cuts[1]}"
    assert abs(cuts[2] - bridge2_center) < 5, f"Expected 2nd cut at {bridge2_center}, got {cuts[2]}"

    print("PASS")

def test_smoothing_prefers_wide_band_over_single_row():

    print("  test_smoothing_prefers_wide_band_over_single_row...", end=" ")
    H = 2000
    target_height = 1000
    window_frac = 0.1

    ink = np.full(H, 0.80, dtype=float)


    ink[950] = 0.0


    wide_band = (1035, 1065)
    ink[wide_band[0]:wide_band[1]] = 0.15


    cuts_raw = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac, smoothing_radius=0)
    assert_invariants(cuts_raw, H)
    assert_strict_window(cuts_raw, target_height, window_frac)

    cut_raw = cuts_raw[1]
    assert abs(cut_raw - 950) < 5, f"NO-SMOOTHING failed: got {cut_raw}"


    cuts_smooth = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac, smoothing_radius=10)
    assert_invariants(cuts_smooth, H)
    assert_strict_window(cuts_smooth, target_height, window_frac)

    cut_smooth = cuts_smooth[1]
    assert wide_band[0] <= cut_smooth <= wide_band[1], f"SMOOTHING failed: got {cut_smooth}"

    print("PASS")

def test_last_page_behavior():

    print("  test_last_page_behavior...", end=" ")
    H = 2150
    target_height = 1000
    window_frac = 0.1
    max_window = 100

    ink = np.full(H, 0.3, dtype=float)

    ink[990:1010] = 0.0
    ink[1990:2010] = 0.0

    cuts = find_optimal_cuts_dp(ink, target_height, window_frac=window_frac)
    assert_invariants(cuts, H)


    assert len(cuts) == 4, f"Expected [0, ~1000, ~2000, 2150], got {cuts}"
    assert 990 <= cuts[1] <= 1010, f"Expected first cut near 1000 gap, got {cuts[1]}"
    assert 1990 <= cuts[2] <= 2010, f"Expected second cut near 2000 gap, got {cuts[2]}"
    assert cuts[3] == 2150


    assert_strict_window(cuts, target_height, window_frac)


    last_h = cuts[-1] - cuts[-2]
    assert last_h <= target_height + max_window, "Last page exceeded max extension"
    assert last_h < target_height * 0.5, f"Expected short tail, got {last_h}"

    print("PASS")





def test_random_configurations_with_engineered_basins():

    print("  test_random_configurations (20 trials)...", end=" ")

    np.random.seed(42)
    num_trials = 20
    failures = []

    for trial in range(num_trials):

        H = np.random.randint(2000, 5000)
        target_height = np.random.randint(800, 1500)
        window_frac = np.random.uniform(0.03, 0.15)
        smoothing_radius = np.random.choice([0, 5, 10, 15])
        snap_px = np.random.randint(20, 60)
        cut_mode = np.random.choice([CutMode.WHITESPACE, CutMode.FIXED_HEIGHT_SNAP])


        ink = np.random.uniform(0.3, 0.7, H)

        num_pages = max(2, H // target_height)
        safe_basins = []

        for page_idx in range(1, num_pages):
            ideal_cut = page_idx * target_height
            if ideal_cut >= H:
                break

            basin_start = max(0, ideal_cut - 30)
            basin_end = min(H, ideal_cut + 30)
            ink[basin_start:basin_end] = np.random.uniform(0.0, 0.05, basin_end - basin_start)
            safe_basins.append((basin_start, basin_end))

        try:
            cuts = find_optimal_cuts_dp(
                ink, target_height,
                window_frac=window_frac,
                smoothing_radius=smoothing_radius,
                cut_mode=cut_mode,
                snap_px=snap_px
            )


            assert cuts[0] == 0, f"Trial {trial}: cuts must start at 0"
            assert cuts[-1] == H, f"Trial {trial}: cuts must end at H"
            assert all(cuts[i] < cuts[i+1] for i in range(len(cuts)-1)), \
                f"Trial {trial}: cuts must be strictly increasing"


            max_window = int(target_height * window_frac)

            for cut_idx in range(1, len(cuts) - 1):
                cut = cuts[cut_idx]

                in_basin = any(start <= cut <= end for start, end in safe_basins)
                ideal_boundary = (cut // target_height) * target_height + target_height
                in_snap_neighborhood = abs(cut - ideal_boundary) <= snap_px
                prev_cut = cuts[cut_idx - 1]
                segment_height = cut - prev_cut
                within_window = abs(segment_height - target_height) <= max_window

                if not (in_basin or in_snap_neighborhood or within_window):
                    failures.append(
                        f"Trial {trial}: Cut at {cut} not in basin, snap neighborhood, or window. "
                        f"Mode: {cut_mode}, safe_basins: {safe_basins}"
                    )

        except Exception as e:
            failures.append(f"Trial {trial}: Exception {str(e)}")

    if failures:
        print(f"FAIL ({len(failures)} failures)")
        for f in failures[:3]:
            print(f"    {f}")
        raise AssertionError(f"{len(failures)} property test failures")

    print("PASS")

def test_whitespace_vs_fixed_height_snap_modes():

    print("  test_mode_comparison...", end=" ")

    np.random.seed(123)
    H = 3000
    target_height = 1000

    ink = np.random.uniform(0.2, 0.6, H)


    for i in range(1, 4):
        gap_center = i * 950
        if gap_center < H:
            ink[gap_center-10:gap_center+10] = 0.0


    cuts_ws = find_optimal_cuts_dp(ink, target_height, cut_mode=CutMode.WHITESPACE)
    cuts_fhs = find_optimal_cuts_dp(ink, target_height, cut_mode=CutMode.FIXED_HEIGHT_SNAP, snap_px=50)


    for cuts, mode in [(cuts_ws, "WHITESPACE"), (cuts_fhs, "FIXED_HEIGHT_SNAP")]:
        assert cuts[0] == 0, f"{mode}: must start at 0"
        assert cuts[-1] == H, f"{mode}: must end at H"
        assert len(cuts) >= 2, f"{mode}: must have at least 2 cuts"

    print("PASS")





def test_fixed_size_padding_produces_exact_dimensions():

    if not HAS_PYPDF2:
        print("  test_fixed_size_padding... SKIP (PyPDF2 not installed)")
        return

    print("  test_fixed_size_padding...", end=" ")

    width = 800
    height = 3500
    target_height = 1000
    dpi = 300


    img_array = np.ones((height, width, 3), dtype=np.uint8) * 255
    for i in range(10, height, 100):
        img_array[i:i+5, :] = 0

    ink_profile = compute_ink_density(img_array)
    cuts = find_optimal_cuts_dp(ink_profile, target_height, cut_mode=CutMode.WHITESPACE)

    crops = [img_array[cuts[i]:cuts[i+1], :] for i in range(len(cuts) - 1)]

    output_path = "tmp_rovodev_test_padding.pdf"
    try:
        save_pdf_from_crops(
            crops, output_path, dpi=dpi,
            render_mode=RenderMode.FIXED_SIZE_WITH_PADDING,
            target_height_px=target_height
        )

        reader = PdfReader(output_path)
        expected_width_pt = width * 72 / dpi
        expected_height_pt = target_height * 72 / dpi

        all_correct = True
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            actual_width_pt = float(page.mediabox.width)
            actual_height_pt = float(page.mediabox.height)

            width_match = abs(actual_width_pt - expected_width_pt) < 0.1


            if page_num == len(reader.pages) - 1:
                height_match = actual_height_pt <= expected_height_pt + 0.1
            else:
                height_match = abs(actual_height_pt - expected_height_pt) < 0.1

            if not (width_match and height_match):
                all_correct = False
                break

        assert all_correct, "Some pages have incorrect dimensions"
        print("PASS")

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

def test_variable_size_allows_different_heights():

    if not HAS_PYPDF2:
        print("  test_variable_size... SKIP (PyPDF2 not installed)")
        return

    print("  test_variable_size...", end=" ")

    width = 800
    height = 3000
    dpi = 300

    img_array = np.ones((height, width, 3), dtype=np.uint8) * 255
    for i in range(10, height, 80):
        img_array[i:i+3, :] = 0

    ink_profile = compute_ink_density(img_array)
    cuts = find_optimal_cuts_dp(ink_profile, 1000, cut_mode=CutMode.WHITESPACE)

    crops = [img_array[cuts[i]:cuts[i+1], :] for i in range(len(cuts) - 1)]

    output_path = "tmp_rovodev_test_variable.pdf"
    try:
        save_pdf_from_crops(crops, output_path, dpi=dpi, render_mode=RenderMode.VARIABLE_SIZE)

        reader = PdfReader(output_path)
        assert len(reader.pages) > 0, "PDF should have pages"
        print("PASS")

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)





def load_profile_from_image(path):

    img = Image.open(path).convert('L')
    arr = np.array(img, dtype=float) / 255.0
    ink_profile = np.mean(1.0 - arr, axis=1)
    return ink_profile

def test_acceptance_corpus():

    print("  test_acceptance_corpus...", end=" ")

    DATASET_DIR = "G:/test_dataset"
    GOLDEN_FILE = os.path.join(script_dir, "golden_cuts.json")

    if not os.path.exists(DATASET_DIR):
        print("SKIP (dataset not found at G:/test_dataset)")
        return

    files = sorted([f for f in os.listdir(DATASET_DIR)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if not files:
        print("SKIP (no images in dataset)")
        return

    if not os.path.exists(GOLDEN_FILE):
        print("SKIP (golden_cuts.json not found)")
        return

    with open(GOLDEN_FILE, 'r') as f:
        golden_data = json.load(f)

    failures = []

    for fname in files:
        path = os.path.join(DATASET_DIR, fname)
        try:
            profile = load_profile_from_image(path)
            H = len(profile)
            target = 1000

            cuts, debug = find_optimal_cuts_dp(profile, target, return_debug_info=True)

            if cuts[0] != 0 or cuts[-1] != H:
                failures.append(f"{fname}: Invalid bounds {cuts}")

            cuts_list = [int(c) for c in cuts]
            expected = golden_data.get(fname)

            if expected is not None and expected != cuts_list:
                failures.append(f"{fname}: Regression! Expected {expected}, got {cuts_list}")

        except Exception as e:
            failures.append(f"{fname}: Exception {str(e)}")

    if failures:
        print(f"FAIL ({len(failures)} failures)")
        for f in failures[:3]:
            print(f"    {f}")
        raise AssertionError(f"{len(failures)} acceptance test failures")

    print("PASS")





def run_all_tests():

    print("=" * 70)
    print("Running Content-Aware Pagination Test Suite")
    print("=" * 70)

    test_groups = [
        ("Algorithm Verification Tests", [
            test_standard_case_gap_alignment,
            test_dense_case_requires_bridge_like_candidates,
            test_smoothing_prefers_wide_band_over_single_row,
            test_last_page_behavior,
        ]),
        ("Property-Based Tests", [
            test_random_configurations_with_engineered_basins,
            test_whitespace_vs_fixed_height_snap_modes,
        ]),
        ("PDF Dimension Tests", [
            test_fixed_size_padding_produces_exact_dimensions,
            test_variable_size_allows_different_heights,
        ]),
        ("Acceptance Tests", [
            test_acceptance_corpus,
        ]),
    ]

    total_passed = 0
    total_failed = 0

    for group_name, tests in test_groups:
        print(f"\n{group_name}:")
        for test_func in tests:
            try:
                test_func()
                total_passed += 1
            except Exception as e:
                print(f"  FAILED: {str(e)}")
                total_failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    print("=" * 70)

    if total_failed > 0:
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED!")

if __name__ == "__main__":
    run_all_tests()
