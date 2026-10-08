// The allocator's settings, set as the engine loads this GDExtension (before the worker threads start).
//
// glibc's malloc kept ~1.4 GB of freed memory in a city on the 1:1 station (2026-10-08): an arena per worker thread
// (19 of them), and big blocks (mesh and image data, parsed data) taken from the heap -- the dynamic mmap threshold
// climbs to 32 MB after the first frees -- whose holes never went back to the system.  Two arenas, blocks of 256 KB
// and up mmapped (returned on free), and the heap's top trimmed past 8 MB: the same game in ~0.8 GB less.
//
// Build (no Godot headers needed: the entry's one struct is declared here):
//   zig cc -target x86_64-linux-gnu.2.17 -O2 -shared -fPIC -o libssc_memtune.linux.x86_64.so memtune.c
//   zig cc -target aarch64-linux-gnu.2.17 -O2 -shared -fPIC -o libssc_memtune.linux.arm64.so memtune.c
// (zig: ~/.venvs/ssc-assets/bin/python -m ziglang cc ...; Windows builds go without it -- export_presets.cfg excludes it)
#include <malloc.h>
#include <stdint.h>

typedef struct {
	int minimum_initialization_level;
	void *userdata;
	void (*initialize)(void *userdata, int level);
	void (*deinitialize)(void *userdata, int level);
} Init;

static void nothing(void *userdata, int level) {
	(void)userdata;
	(void)level;
}

__attribute__((visibility("default"))) uint8_t ssc_memtune_init(void *get_proc_address, void *library, Init *r) {
	(void)get_proc_address;
	(void)library;
	mallopt(M_ARENA_MAX, 2);
	mallopt(M_MMAP_THRESHOLD, 256 * 1024);
	mallopt(M_TRIM_THRESHOLD, 8 * 1024 * 1024);
	r->minimum_initialization_level = 0;
	r->userdata = 0;
	r->initialize = nothing;
	r->deinitialize = nothing;
	return 1;
}
