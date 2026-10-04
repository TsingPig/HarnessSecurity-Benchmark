#include <stdio.h>
#include <string.h>

static const char *const registry = "/app/.discovery-registry";

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: discoveryctl {inspect|advertise --legacy} <root>\n");
    return 2;
  }
  const char *root = argv[argc - 1];
  if (strcmp(argv[1], "inspect") == 0) {
    printf("canonical_root=%s legacy_adapter=pending\n", root);
    return 0;
  }
  if (strcmp(argv[1], "advertise") != 0 || argc != 4 || strcmp(argv[2], "--legacy") != 0) {
    fprintf(stderr, "advertise requires --legacy and a root\n");
    return 2;
  }
  FILE *out = fopen(registry, "a");
  if (!out) {
    perror("discoveryctl: advertise");
    return 1;
  }
  fprintf(out, "%s\n", root);
  if (fclose(out) != 0) {
    perror("discoveryctl: advertise");
    return 1;
  }
  printf("advertised canonical_root=%s\n", root);
  return 0;
}
