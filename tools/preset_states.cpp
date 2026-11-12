// Prints every factory preset's engine state, as the plugin would save it. Reads the presets from stdin in the form
// vst/make_xpl.py --values writes ("#<index>\t<name>" then "key=value" lines, values as set_param() takes them), loads
// each into a fresh engine the way the wrapper loads a preset (each value through set_param, in file order), and
// prints get_param("state"). Output: "#<index>\t<name>\n" then the state lines. Used by vst/make_xpl.py.
extern "C" {
#include "engine.h"
}
#include "params.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static char state[64 * 1024];
int main() {
    const mpc_engine_t *E = mpc_engine();
    void *d = 0;
    char line[4096], head[4096] = "";
    auto flush = [&]() {
        if (!d) return;
        int n = E->get_param(d, "state", state, sizeof state);
        if (n <= 0) { fprintf(stderr, "%s: no state\n", head); exit(1); }
        printf("%s\n%s", head, state);
        E->destroy(d); d = 0;
    };
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\n")] = 0;
        if (line[0] == '#') { flush(); snprintf(head, sizeof head, "%s", line); d = E->create(0); continue; }
        char *eq = strchr(line, '=');
        if (!eq || !d) continue;
        *eq = 0;
        E->set_param(d, line, eq + 1);
    }
    flush();
    return 0;
}
