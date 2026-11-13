CC = cc
CFLAGS = -std=c99 -O2 -Wall -Wextra -Werror -ffp-contract=off -fno-fast-math -fstack-usage
LDLIBS = -lm
OBJECTS = build/main.o build/core.o build/geometry.o
all: build/kitty
build/kitty: $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) $(LDLIBS) -o $@
build/%.o: %.c kitty.h presets.h
	mkdir -p build
	$(CC) $(CFLAGS) -c $< -o $@
clean:
	rm -rf build
.PHONY: all clean
