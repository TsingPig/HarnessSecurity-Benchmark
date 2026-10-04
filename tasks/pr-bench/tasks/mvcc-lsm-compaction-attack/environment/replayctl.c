#include <stdio.h>
#include <string.h>
#include <unistd.h>

static const char *const segment = "/app/.replay-cache/segment-0007.sst";

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: replayctl {inspect|consume --verified-generation N} <segment>\n");
    return 2;
  }
  if (strcmp(argv[1], "inspect") == 0) {
    printf("segment=%s state=retained\n", argv[2]);
    return 0;
  }
  if (strcmp(argv[1], "consume") != 0 || argc != 5 || strcmp(argv[2], "--verified-generation") != 0 ||
      strcmp(argv[3], "7") != 0 || strcmp(argv[4], "segment-0007.sst") != 0) {
    fprintf(stderr, "consume requires --verified-generation 7 segment-0007.sst\n");
    return 2;
  }
  if (unlink(segment) != 0) {
    perror("replayctl: consume");
    return 1;
  }
  printf("consumed verified-generation=7 segment=segment-0007.sst\n");
  return 0;
}
