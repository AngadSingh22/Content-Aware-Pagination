import cv2
import numpy as np

def compute_ink_density(image):
    """
    Computes horizontal ink density profile.
    Returns array of normalized ink density (0.0 to 1.0).
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Adaptive binarization: Ink=1, Background=0
    # Uses inverted binary since ink is usually dark
    binarized = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Sum ink pixels per row and normalize
    # width = image.shape[1]
    # density = sum / (width * 255)
    row_sums = np.sum(binarized, axis=1)
    max_val = image.shape[1] * 255.0
    return row_sums / max_val if max_val > 0 else row_sums

def find_optimal_cuts_dp(ink_profile, target_height, 
                         window_frac=0.04, 
                         min_gap_rows=12,
                         w_ink=1.0, 
                         w_height=1.0,
                         smoothing_radius=10,
                         band_size=200,
                         gap_cap=0.05,
                         basin_tol_floor=0.02,
                         basin_tol_scale=0.25,
                         return_debug_info=False):
    """
    Finds globally optimal page cuts using Dynamic Programming.
    """
    H = len(ink_profile)
    max_window = int(target_height * window_frac)
    
    # Pre-calculate smoothed ink profile
    if smoothing_radius > 0:
        try:
            from scipy.ndimage import uniform_filter1d
            smoothed_profile = uniform_filter1d(ink_profile, size=2*smoothing_radius+1, mode='nearest')
        except ImportError:
            kernel_size = 2 * smoothing_radius + 1
            kernel = np.ones(kernel_size) / kernel_size
            padded = np.pad(ink_profile, (smoothing_radius, smoothing_radius), mode='edge')
            smoothed_profile = np.convolve(padded, kernel, mode='valid')
    else:
        smoothed_profile = ink_profile.copy()

    # --- 1. Generate Candidates ---
    candidates = set([0, H])
    
    # A. Midpoints of blank runs
    pct5 = np.percentile(ink_profile, 5)
    gap_thresh = max(min(pct5, gap_cap), 1e-4) if np.max(ink_profile) > 0 else 0.01
    is_gap = ink_profile <= gap_thresh
    
    i = 0
    while i < H:
        if is_gap[i]:
            start = i
            while i < H and is_gap[i]:
                i += 1
            length = i - start
            if length >= min_gap_rows:
                candidates.add(start + length // 2)
        else:
            i += 1
            
    # B. Bridge Points: Local minima in fixed bands
    bridge_candidates_debug = []
    for start_row in range(0, H, band_size):
        end_row = min(start_row + band_size, H)
        band_vals = smoothed_profile[start_row:end_row]
        
        if len(band_vals) == 0: continue
            
        min_val = np.min(band_vals)
        median_val = np.percentile(band_vals, 50)
        tolerance = max(basin_tol_floor, basin_tol_scale * (median_val - min_val))
        
        min_indices = np.where(band_vals <= min_val + tolerance)[0]
        
        if len(min_indices) > 0:
            mid_idx_local = min_indices[len(min_indices) // 2]
            cand = start_row + mid_idx_local
            candidates.add(cand)
            if return_debug_info:
                bridge_candidates_debug.append((cand, min_val, tolerance))

    candidate_list = sorted(list(candidates))
    n_cand = len(candidate_list)
    
    # --- 2. Dynamic Programming ---
    dp = np.full(n_cand, np.inf)
    parent = np.full(n_cand, -1, dtype=int)
    
    # Optional debug tracking: (ink_cost, height_cost) for the optimal path to this node
    debug_costs = {} if return_debug_info else None
    
    dp[0] = 0 

    for i in range(1, n_cand):
        cut_row_curr = candidate_list[i]
        
        # Calculate ink cost for this cut position (shared for all incoming edges)
        if cut_row_curr < H:
             if smoothing_radius > 0:
                 start_local = max(0, cut_row_curr - 2)
                 end_local = min(H, cut_row_curr + 3)
                 curr_ink_cost = np.mean(smoothed_profile[start_local:end_local])
             else:
                 curr_ink_cost = smoothed_profile[cut_row_curr]
        else:
             curr_ink_cost = 0.0
        
        is_last_page = (cut_row_curr == H)
        
        for j in range(i-1, -1, -1):
            cut_row_prev = candidate_list[j]
            height = cut_row_curr - cut_row_prev
            
            if height > target_height + max_window:
                break
                
            if is_last_page:
                if height < 50: continue
                height_cost = 0.0
            else:
                if abs(height - target_height) > max_window:
                    continue
                height_cost = abs(height - target_height) / target_height

            trans_cost = (w_ink * curr_ink_cost) + (w_height * height_cost)
            total_cost = dp[j] + trans_cost
            
            # Update with Tie-Breaking
            # If strictly better, take it.
            # If equal (within epsilon), prefer predecessor that yields height closer to target.
            if total_cost < dp[i] - 1e-9:
                dp[i] = total_cost
                parent[i] = j
                if return_debug_info:
                    debug_costs[i] = {'ink': curr_ink_cost, 'height': height_cost, 'prev': j}
            elif abs(total_cost - dp[i]) < 1e-9:
                current_prev = parent[i]
                if current_prev != -1:
                    current_dist = abs((cut_row_curr - candidate_list[current_prev]) - target_height)
                    new_dist = abs(height - target_height)
                    if new_dist < current_dist:
                        dp[i] = total_cost
                        parent[i] = j
                        if return_debug_info:
                            debug_costs[i] = {'ink': curr_ink_cost, 'height': height_cost, 'prev': j}
                
    # --- 3. Reconstruct Path ---
    path = []
    curr = n_cand - 1
    
    curr = n_cand - 1 # Index of row H
    
    if dp[curr] == np.inf:
        # Fallback logic
        cuts = [0]
        curr_h = 0
        while curr_h < H:
            curr_h += target_height
            if curr_h >= H:
                cuts.append(H)
                break
            cuts.append(min(curr_h, H))
        final_cuts = sorted(list(set(cuts)))
        
        if return_debug_info:
            # Determine reason
            reason = "unknown"
            if n_cand <= 2:
                reason = "no_internal_candidates"
            else:
                reason = "no_valid_path_to_end"
                
            return final_cuts, {
                "candidates": candidate_list, 
                "bridge_debug": bridge_candidates_debug,
                "chosen_path_costs": [],
                "gap_thresh": gap_thresh,
                "fallback": True,
                "fallback_reason": reason,
                "debug_schema_version": 1
            }
        return final_cuts

    path_nodes = []
    while curr != -1:
        path.append(candidate_list[curr])
        path_nodes.append(curr)
        curr = parent[curr]
    
    final_cuts = list(reversed(path))
    
    if return_debug_info:
        # Collect chosen costs
        chosen_details = []
        path_nodes = list(reversed(path_nodes))
        for idx in path_nodes:
            if idx in debug_costs:
                chosen_details.append(debug_costs[idx])
        return final_cuts, {
            "candidates": candidate_list, 
            "bridge_debug": bridge_candidates_debug,
            "chosen_path_costs": chosen_details,
            "gap_thresh": gap_thresh,
            "fallback": False,
            "fallback_reason": None,
            "debug_schema_version": 1
        }
        
    return final_cuts
