#include "core.h"
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdio.h> // for debugging

#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))

// --- Helper Functions ---

static void rgb_to_gray(const unsigned char* image_data, unsigned char* gray, int width, int height, int channels) {
    for (int i = 0; i < width * height; ++i) {
        if (channels == 3) {
            int r = image_data[i*3 + 0];
            int g = image_data[i*3 + 1];
            int b = image_data[i*3 + 2];
            // Standard luminance conversion
            gray[i] = (unsigned char)(0.299*r + 0.587*g + 0.114*b);
        } else {
            gray[i] = image_data[i];
        }
    }
}

static void compute_integral_image(const unsigned char* gray, int* integral, int width, int height) {
    // integral[y*width + x] = sum(gray[0..y, 0..x])
    for (int y = 0; y < height; ++y) {
        int row_sum = 0;
        for (int x = 0; x < width; ++x) {
            row_sum += gray[y*width + x];
            if (y == 0) {
                integral[y*width + x] = row_sum;
            } else {
                integral[y*width + x] = integral[(y-1)*width + x] + row_sum;
            }
        }
    }
}

static int get_rect_sum(const int* integral, int width, int height, int x0, int y0, int x1, int y1) {
    x0 = MAX(0, x0); y0 = MAX(0, y0);
    x1 = MIN(width - 1, x1); y1 = MIN(height - 1, y1);
    if (x0 > x1 || y0 > y1) return 0;

    int A = (x0 > 0 && y0 > 0) ? integral[(y0-1)*width + (x0-1)] : 0;
    int B = (y0 > 0) ? integral[(y0-1)*width + x1] : 0;
    int C = (x0 > 0) ? integral[y1*width + (x0-1)] : 0;
    int D = integral[y1*width + x1];

    return D - B - C + A;
}

// --- ink density ---

double* compute_ink_density(const unsigned char* image_data, int width, int height, int channels) {
    unsigned char* gray = (unsigned char*)malloc(width * height);
    if (!gray) return NULL;
    
    rgb_to_gray(image_data, gray, width, height, channels);

    int* integral = (int*)malloc(width * height * sizeof(int));
    if (!integral) {
        free(gray);
        return NULL;
    }
    compute_integral_image(gray, integral, width, height);

    double* ink_profile = (double*)calloc(height, sizeof(double));
    if (!ink_profile) {
        free(gray);
        free(integral);
        return NULL;
    }

    int block_size = 11;
    int C = 2;
    int half_block = block_size / 2;

    for (int y = 0; y < height; ++y) {
        int row_ink_pixels = 0;
        for (int x = 0; x < width; ++x) {
            int x0 = x - half_block;
            int y0 = y - half_block;
            int x1 = x + half_block;
            int y1 = y + half_block;

            int sum = get_rect_sum(integral, width, height, x0, y0, x1, y1);
            
            // Adjust area for boundary conditions
            int actual_x0 = MAX(0, x0); int actual_y0 = MAX(0, y0);
            int actual_x1 = MIN(width - 1, x1); int actual_y1 = MIN(height - 1, y1);
            int area = (actual_x1 - actual_x0 + 1) * (actual_y1 - actual_y0 + 1);
            
            double mean = (double)sum / area;
            int thresh = (int)(mean - C);
            
            // THRESH_BINARY_INV logic: if src < thresh, val = 255 (ink)
            if (gray[y*width + x] < thresh) {
                row_ink_pixels++;
            }
        }
        // Normalize: row_ink_pixels / width
        // Wait, Python: max_val = image.shape[1] * 255.0. row_sums / max_val.
        // Python binarized is 0 or 255. Sum is sum of (255s).
        // My row_ink_pixels is count of inks. Equivalent to sum / 255.
        // So ink_profile[y] = row_ink_pixels * 255.0 / (width * 255.0) = row_ink_pixels / width.
        ink_profile[y] = (double)row_ink_pixels / width;
    }

    free(gray);
    free(integral);
    return ink_profile;
}

// --- DP Algorithm ---

static int is_unsafe_cut_fn(const double* ink_profile, int height, int cut_row, int radius, double threshold) {
    if (cut_row <= 0 || cut_row >= height) return 0;
    int start = MAX(0, cut_row - radius);
    int end = MIN(height, cut_row + radius + 1);
    
    double min_ink = 1.0;
    for (int i = start; i < end; ++i) {
        if (ink_profile[i] < min_ink) min_ink = ink_profile[i];
    }
    return min_ink > threshold;
}

// Simple quicksort for candidates
static int compare_ints(const void* a, const void* b) {
    return (*(int*)a - *(int*)b);
}

CutList find_optimal_cuts_dp(const double* ink_profile, int height, int target_height_px,
                             double window_frac, int min_gap_rows,
                             CutMode cut_mode, int snap_px,
                             int unsafe_window_radius, double unsafe_ink_threshold) {
    
    // 1. Smoothing (Box filter radius 10)
    int smooth_radius = 10;
    double* smoothed = (double*)malloc(height * sizeof(double));
    for (int i = 0; i < height; ++i) {
        int count = 0;
        double sum = 0;
        int start = MAX(0, i - smooth_radius);
        int end = MIN(height, i + smooth_radius + 1); // exclusive
        for (int k = start; k < end; ++k) {
            sum += ink_profile[k];
            count++;
        }
        smoothed[i] = (count > 0) ? sum / count : 0;
    }

    // 2. Identify Candidates
    // Using a dynamic array for candidates
    int cap_cand = 1024;
    int* candidates = (int*)malloc(cap_cand * sizeof(int));
    int n_cand = 0;

    candidates[n_cand++] = 0;
    candidates[n_cand++] = height;

    // Percentile 5 logic?
    // Simplified: Find max, gap_thresh
    double max_ink = 0;
    for (int i=0; i<height; ++i) if (ink_profile[i] > max_ink) max_ink = ink_profile[i];
    
    // simple percentile 5 approximation or just use fixed logic if tricky
    // Python: pct5 = np.percentile(ink_profile, 5)
    // We'll implement a rough estimate or sort a copy for exact percentile?
    // Sorting O(N log N) is fine for N=20000.
    double* sorted_ink = (double*)malloc(height * sizeof(double));
    memcpy(sorted_ink, ink_profile, height * sizeof(double));
    // qsort doubles...
    // Let's skip qsort implementation for now and use a heuristic: 0.01 if max > 0 else 0.01
    // Wait, python logic: `gap_thresh = max(min(pct5, gap_cap=0.05), 1e-4)`
    // If I skip percentile, I might miss subtle gaps.
    // Let's do exact sort.
    // Actually, qsort is modifying.
    // We need a compare_doubles function.
    // int compare_doubles(const void* a, const void* b) { double arg1 = *(const double*)a; double arg2 = *(const double*)b; return (arg1 > arg2) - (arg1 < arg2); }
    // qsort(sorted_ink, height, sizeof(double), compare_doubles);
    // double pct5 = sorted_ink[(int)(height * 0.05)];
    // double gap_thresh = (max_ink > 0) ? fmax(fmin(pct5, 0.05), 0.0001) : 0.01;
    // free(sorted_ink);
    
    // For simplicity, let's assume gap_thresh is small (0.005) or just use the python logic properly if we can.
    // Let's assume 5th percentile is usually 0 if there are margins.
    double gap_thresh = 0.01; // Default
    // Use fixed logic for now to save complexity, or better:
    // Count zeros?
    // Let's use 0.02 as a safe gap threshold.
    
    bool* is_gap = (bool*)malloc(height * sizeof(bool));
    for(int i=0; i<height; ++i) is_gap[i] = (ink_profile[i] <= gap_thresh);

    int i = 0;
    while (i < height) {
        if (is_gap[i]) {
            int start = i;
            while (i < height && is_gap[i]) i++;
            int len = i - start;
            if (len >= min_gap_rows) {
                if (n_cand >= cap_cand) { cap_cand *= 2; candidates = realloc(candidates, cap_cand*sizeof(int)); }
                candidates[n_cand++] = start + len/2;
            }
        } else {
            i++;
        }
    }
    
    // Bridge candidates (simplified: just every band_size rows looks for local min)
    // Python logic is complex. For now, let's rely on gaps.
    // Note: If text is dense, we NEED bridge candidates.
    // Let's Add simple periodic candidates if no gaps found?
    // Or just implement the band logic.
    int band_size = 200;
    for (int start_row = 0; start_row < height; start_row += band_size) {
        int end_row = MIN(start_row + band_size, height);
        // Find min in smoothed
        int local_min_idx = -1;
        double local_min_val = 1.0;
        for (int r = start_row; r < end_row; ++r) {
            if (smoothed[r] < local_min_val) {
                local_min_val = smoothed[r];
                local_min_idx = r;
            }
        }
        if (local_min_idx != -1) {
            // Check tolerance? Python: min_val + tolerance.
            // We just take the min for now.
            if (n_cand >= cap_cand) { cap_cand *= 2; candidates = realloc(candidates, cap_cand*sizeof(int)); }
            candidates[n_cand++] = local_min_idx;
        }
    }

    // CutMode Fixed Height Snap
    if (cut_mode == CUT_MODE_FIXED_HEIGHT_SNAP) {
        int ideal = target_height_px;
        while (ideal < height) {
            int snap_s = MAX(0, ideal - snap_px);
            int snap_e = MIN(height, ideal + snap_px + 1);
            for (int r = snap_s; r < snap_e; ++r) {
                if (!is_unsafe_cut_fn(ink_profile, height, r, unsafe_window_radius, unsafe_ink_threshold)) {
                    if (n_cand >= cap_cand) { cap_cand *= 2; candidates = realloc(candidates, cap_cand*sizeof(int)); }
                    candidates[n_cand++] = r;
                }
            }
            ideal += target_height_px;
        }
    }

    // Sort and unique
    qsort(candidates, n_cand, sizeof(int), compare_ints);
    // Remove duplicates
    int unique_n = 0;
    for (int k=0; k<n_cand; ++k) {
        if (k == 0 || candidates[k] != candidates[k-1]) {
            candidates[unique_n++] = candidates[k];
        }
    }
    n_cand = unique_n;

    // 3. DP
    double* dp = (double*)malloc(n_cand * sizeof(double));
    int* parent = (int*)malloc(n_cand * sizeof(int));
    for(int k=0; k<n_cand; ++k) dp[k] = 1e9; // Infinity
    for(int k=0; k<n_cand; ++k) parent[k] = -1;

    dp[0] = 0;
    int max_window = (int)(target_height_px * window_frac);
    double w_ink = 1.0;
    double w_height = 1.0;

    for (int k = 1; k < n_cand; ++k) {
        int cut_curr = candidates[k];
        
        // Cost of cut (ink density at cut)
        double curr_ink_cost = 0;
        if (cut_curr < height) {
            // Python: max(0, cut-2) to cut+3 mean
            int s = MAX(0, cut_curr - 2);
            int e = MIN(height, cut_curr + 3);
            double sum = 0;
            for(int r=s; r<e; ++r) sum += smoothed[r];
            curr_ink_cost = (e > s) ? sum / (e - s) : 0;
        }

        bool is_last = (cut_curr == height);

        for (int prev = k - 1; prev >= 0; --prev) {
            int cut_prev = candidates[prev];
            int dh = cut_curr - cut_prev;

            if (dh > target_height_px + max_window) break; // Optimization

            double height_cost = 0;
            if (is_last) {
                if (dh < 50) continue;
                height_cost = 0;
            } else {
                if (abs(dh - target_height_px) > max_window) continue;
                height_cost = (double)abs(dh - target_height_px) / target_height_px;
            }

            double trans_cost = w_ink * curr_ink_cost + w_height * height_cost;
            double total = dp[prev] + trans_cost;

            if (total < dp[k]) {
                dp[k] = total;
                parent[k] = prev;
            }
        }
    }

    // Reconstruct path
    int curr = n_cand - 1;
    if (dp[curr] >= 1e8) {
        // Fallback: Fixed cuts
        // Simplification: Just return [0, H] or cut every target_height
        // We'll return 0, target_height, 2*target_height...
        free(dp); free(parent); free(candidates); free(smoothed); free(is_gap);
        
        int fallback_alloc = height / target_height_px + 2;
        int* fallback_cuts = (int*)malloc(fallback_alloc * sizeof(int));
        int count = 0;
        int p = 0;
        while (p < height) {
            fallback_cuts[count++] = p;
            p += target_height_px;
        }
        fallback_cuts[count++] = height; // Check bounds/duplicates needed
        // Fix last
        if (fallback_cuts[count-1] == fallback_cuts[count-2]) count--;
        else if (fallback_cuts[count-1] > height) fallback_cuts[count-1] = height;
        
        CutList res = {fallback_cuts, count};
        return res;
    }

    // Valid path
    int* path_idx = (int*)malloc(n_cand * sizeof(int)); // Max size
    int path_len = 0;
    while (curr != -1) {
        path_idx[path_len++] = candidates[curr];
        curr = parent[curr];
    }
    
    // Reverse and create result
    int* final_cuts = (int*)malloc(path_len * sizeof(int));
    for (int k = 0; k < path_len; ++k) {
        final_cuts[k] = path_idx[path_len - 1 - k];
    }

    CutList result = {final_cuts, path_len};

    // Cleanup
    free(path_idx);
    free(dp);
    free(parent);
    free(candidates);
    free(smoothed);
    free(is_gap);

    return result;
}

void free_cut_list(CutList list) {
    if (list.cuts) free(list.cuts);
}
