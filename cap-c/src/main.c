#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "core.h"
#include "io.h"

void print_usage(const char* prog) {
    printf("Usage: %s <input_image> -o <output_pdf> [options]\n", prog);
    printf("Options:\n");
    printf("  -f <format>    Page format (A4, A3). Default: A4\n");
    printf("  -d <dpi>       DPI. Default: 300\n");
}

int main(int argc, char** argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const char* input_path = NULL;
    const char* output_path = "output.pdf";
    const char* format = "A4";
    int dpi = 300;

    // Manual arg parsing for simplicity/portability
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
            output_path = argv[++i];
        } else if (strcmp(argv[i], "-f") == 0 && i + 1 < argc) {
            format = argv[++i];
        } else if (strcmp(argv[i], "-d") == 0 && i + 1 < argc) {
            dpi = atoi(argv[++i]);
        } else if (argv[i][0] != '-') {
            input_path = argv[i];
        }
    }

    if (!input_path) {
        fprintf(stderr, "Error: No input file specified.\n");
        return 1;
    }

    // Determine target height
    int target_height_px;
    if (strcmp(format, "A3") == 0) {
        // A3: 297 x 420 mm. Height 420.
        target_height_px = (int)(420.0 / 25.4 * dpi);
    } else {
        // A4: 210 x 297 mm. Height 297.
        target_height_px = (int)(297.0 / 25.4 * dpi);
    }

    printf("Processing %s...\n", input_path);
    printf("Format: %s, DPI: %d, Target Height: %d px\n", format, dpi, target_height_px);

    // Load
    int w, h, c;
    unsigned char* img = load_image_file(input_path, &w, &h, &c);
    if (!img) {
        fprintf(stderr, "Error loading image.\n");
        return 1;
    }
    printf("Image loaded: %dx%d (%d channels)\n", w, h, c);

    // Compute Density
    double* density = compute_ink_density(img, w, h, c);
    if (!density) {
        fprintf(stderr, "Error computing density.\n");
        stbi_image_free(img);
        return 1;
    }

    // Cuts
    CutList cuts = find_optimal_cuts_dp(density, h, target_height_px,
                                        0.04, 12, CUT_MODE_WHITESPACE, 40,
                                        2, 0.3);
    
    printf("Found %d pages.\n", cuts.count - 1);

    // Save
    if (cuts.count > 1) {
        bool ok = save_pdf(output_path, img, w, h, &cuts, target_height_px, RENDER_MODE_VARIABLE_SIZE, dpi);
        if (ok) {
            printf("Saved to %s\n", output_path);
        } else {
            fprintf(stderr, "Error saving PDF.\n");
        }
    }

    // Cleanup
    free_cut_list(cuts);
    free(density);
    stbi_image_free(img);

    return 0;
}
