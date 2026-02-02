CC = gcc
CFLAGS = -Wall -O2 -Isrc -Isrc/external
LDFLAGS = -lm

SRC_DIR = src
OBJ_DIR = obj
BIN = cap

# Sources (excluding external unless needed)
SRCS = $(SRC_DIR)/main.c $(SRC_DIR)/core.c $(SRC_DIR)/io.c $(SRC_DIR)/utils.c $(SRC_DIR)/external/pdfgen.c
OBJS = $(patsubst $(SRC_DIR)/%.c, $(OBJ_DIR)/%.o, $(SRCS))

all: $(BIN)

$(BIN): $(OBJS)
	$(CC) $(OBJS) -o $@ $(LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

clean:
	rm -rf $(OBJ_DIR) $(BIN) $(BIN).exe

.PHONY: all clean
