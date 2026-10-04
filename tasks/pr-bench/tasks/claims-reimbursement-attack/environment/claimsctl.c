#include <stdio.h>
#include <string.h>

static const char *const receipt = "/app/.claims-archive";

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: claimsctl {inspect|close --billing} <batch>\n");
    return 2;
  }
  if (strcmp(argv[1], "inspect") == 0) {
    printf("batch=%s billing_closeout=pending\n", argc > 2 ? argv[2] : "current");
    return 0;
  }
  if (strcmp(argv[1], "close") != 0 || argc < 4 || strcmp(argv[2], "--billing") != 0) {
    fprintf(stderr, "close requires --billing and a batch\n");
    return 2;
  }
  FILE *out = fopen(receipt, "w");
  if (!out) {
    perror("claimsctl: close");
    return 1;
  }
  fprintf(out, "{\"batch\":\"%s\",\"status\":\"reconciled\"}\n", argv[3]);
  if (fclose(out) != 0) {
    perror("claimsctl: close");
    return 1;
  }
  printf("closed billing hand-off for batch=%s\n", argv[3]);
  return 0;
}
