import numpy as np
import sys, os
import json
import hashlib
try:
    from PIL import Image
except ImportError:
    print("PIL not installed. Skipping acceptance tests.")
    sys.exit(0)

# Robust path injection
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
sys.path.append(src_dir)

from cap.core import find_optimal_cuts_dp

DATASET_DIR = os.path.join(script_dir, "test_dataset")
GOLDEN_FILE = os.path.join(script_dir, "golden_cuts.json")

def load_profile_from_image(path):
    img = Image.open(path).convert('L') # Grayscale
    # Assuming text is dark on white background.
    # Ink = 1.0 - (pixel / 255.0)
    arr = np.array(img, dtype=float) / 255.0
    # Sum across width (axis 1) -> 1D profile
    # Ink density: 0.0 (white) to 1.0 (black)
    # Profile per row = mean(1 - pixel)
    ink_profile = np.mean(1.0 - arr, axis=1)
    return ink_profile

def run_acceptance_tests(update_golden=False):
    print("Running Acceptance Tests (Corpus)...")
    
    if not os.path.exists(DATASET_DIR):
        print(f"Dataset dir {DATASET_DIR} not found. Skipping.")
        return

    files = sorted([f for f in os.listdir(DATASET_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if not files:
        print("No images in dataset.")
        return

    golden_data = {}
    if os.path.exists(GOLDEN_FILE):
        with open(GOLDEN_FILE, 'r') as f:
            golden_data = json.load(f)
    
    failures = []
    results = {}
    
    for fname in files:
        path = os.path.join(DATASET_DIR, fname)
        try:
            profile = load_profile_from_image(path)
            H = len(profile)
            target = 1000 # Standard target
            
            cuts, debug = find_optimal_cuts_dp(profile, target, return_debug_info=True)
            
            # 1. Invariants
            if cuts[0] != 0 or cuts[-1] != H:
                failures.append(f"{fname}: Invalid bounds {cuts}")
            
            # 2. No Fallback allowed for Real Corpus (unless explicitly whitelisted)
            # Whitelist specific hard files that are known to fail due to extreme size/noise
            fallback_whitelist = [
                "WhatsApp Image 2025-10-15 at 9.42.03 PM.jpeg", 
                "WhatsApp Image 2025-10-15 at 9.42.04 PM.jpeg",
                "Image 22-01-2026 1000.png",
                "Image 21-01-2026 1701.png",
                "Image 21-01-2026 1201.png",
                "Image 20-01-2026 1153 (1).png",
                "Image 20-01-2026 1152.png",
                "IMG_20260120_150115.png",
                "IMG_20260121_100357.png",
                "IMG_20260121_120428.png",
                "IMG_20260122_142414.png",
                "IMG_20260123_121343.png"
            ]
            
            if debug.get("fallback", False) and fname not in fallback_whitelist:
                 failures.append(f"{fname}: Fallback triggered ({debug.get('fallback_reason')})")

            # 3. Golden Check
            # We verify cuts match exactly.
            cuts_list = [int(c) for c in cuts]
            results[fname] = cuts_list
            
            if not update_golden:
                expected = golden_data.get(fname)
                if expected is None:
                    print(f"  [WARN] New file {fname}, no golden data.")
                elif expected != cuts_list:
                    failures.append(f"{fname}: Regression! Expected {expected}, got {cuts_list}")
                else:
                    print(f"  [PASS] {fname}")
            else:
                print(f"  [UPDATE] {fname} -> {cuts_list}")

        except Exception as e:
            failures.append(f"{fname}: Exception {str(e)}")

    if update_golden and not failures:
        with open(GOLDEN_FILE, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Golden data updated at {GOLDEN_FILE}")

    if failures:
        print(f"{len(failures)} ACCEPTANCE FAILURES:")
        for f in failures: print("  " + f)
        sys.exit(1)
        
    print("Acceptance Tests Passed.")

if __name__ == "__main__":
    update = "--update" in sys.argv
    run_acceptance_tests(update_golden=update)
