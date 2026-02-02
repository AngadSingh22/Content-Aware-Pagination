#ifndef CAP_IO_H
#define CAP_IO_H

#include <stdbool.h>
#include "core.h"

// Load image function
// Returns pointer to raw data, sets w, h, c.
// Caller must free data with stbi_image_free (or free if we copy it).
unsigned char* load_image_file(const char* path, int* w, int* h, int* c);

// Save PDF function
// Takes the original image, dimensions, and the list of cuts.
// Generates a PDF with one page per crop.
bool save_pdf(const char* output_path, const unsigned char* image_data, int width, int height,
              const CutList* cuts, int target_height_px, RenderMode mode, int dpi);

#endif // CAP_IO_H
