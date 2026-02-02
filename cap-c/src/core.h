#ifndef CAP_CORE_H
#define CAP_CORE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

// Enums
typedef enum {
    CUT_MODE_WHITESPACE,
    CUT_MODE_FIXED_HEIGHT_SNAP
} CutMode;

typedef enum {
    RENDER_MODE_VARIABLE_SIZE,
    RENDER_MODE_FIXED_SIZE_WITH_PADDING
} RenderMode;

// Data structures
typedef struct {
    int* cuts;
    int count;
} CutList;

// Core functions

/**
 * Computes the ink density profile of an image.
 * 
 * @param image_data Pointer to the image data (RGB or Grayscale).
 * @param width Image width.
 * @param height Image height.
 * @param channels Number of channels (1 or 3).
 * @return Array of doubles of size 'height' representing row ink density (0.0 to 1.0).
 *         Caller must free() the result.
 */
double* compute_ink_density(const unsigned char* image_data, int width, int height, int channels);

/**
 * Finds optimal cut locations using Dynamic Programming.
 * 
 * @param ink_profile The ink density profile (array of doubles).
 * @param height Height of the image (length of ink_profile).
 * @param target_height_px Target page height in pixels.
 * @param window_frac Search window fraction of page height.
 * @param min_gap_rows Minimum gap rows to consider safe.
 * @param cut_mode Strategy for cutting.
 * @param snap_px Snap neighborhood radius (for fixed_height_snap).
 * @param unsafe_window_radius Window radius for unsafe cut detection.
 * @param unsafe_ink_threshold Ink threshold for unsafe cut detection.
 * @return CutList containing the optimal row indices for cuts.
 *         Caller must free() the result.cuts and the result structure itself (if allocated).
 */
CutList find_optimal_cuts_dp(const double* ink_profile, int height, int target_height_px,
                             double window_frac, int min_gap_rows,
                             CutMode cut_mode, int snap_px,
                             int unsafe_window_radius, double unsafe_ink_threshold);

// Helper to free CutList internals
void free_cut_list(CutList list);

#endif // CAP_CORE_H
