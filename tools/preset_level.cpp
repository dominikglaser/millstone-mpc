// Level matching without the desktop tools: plays a preset the same way every time and measures its loudest second.
//   preset_level measure FIRST COUNT          -> "index<TAB>dB" for each preset at its own VOLUME
//   preset_level fit INDEX TARGET_DB          -> the VOLUME (0..100) that brings the preset to TARGET_DB
// The test: a C major chord (C3 E3 G3) at velocity 100, held 4 s, released, 2 s more (a single C3 for MONO/LEGATO
// presets); the level is the RMS of the loudest 1 s window, in dBFS. Song clock at 120 BPM, transport stopped.
extern "C" {
#include "engine.h"
}
#include "params.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>

static int vmode_index = -1;
static double level(int p, const char *volume) {
    const mpc_engine_t *E = mpc_engine();
    void *d = E->create(0);
    bool mono = false;
    for (int i = 0; i < PRESETS[p].n; i++) {
        const char *key = PARAMS[PRESETS[p].values[i].param].key;
        const char *val = PRESETS[p].values[i].value;
        if (!strcmp(key, "voice_mode") && atoi(val) != 0) mono = true;
        E->set_param(d, key, val);
    }
    if (volume) E->set_param(d, "volume", volume);
    const int chord[3] = {48, 52, 55};
    for (int k = 0; k < (mono ? 1 : 3); k++) { uint8_t m[3] = {0x90, (uint8_t)chord[k], 100}; E->midi(d, m, 3); }
    std::vector<double> sq; int16_t buf[256];
    const long total = 6 * 44100, hold = 4 * 44100;
    bool off = false;
    for (long f = 0; f < total; f += 128) {
        if (!off && f >= hold) { for (int k = 0; k < 3; k++) { uint8_t m[3] = {0x80, (uint8_t)chord[k], 0}; E->midi(d, m, 3); } off = true; }
        E->render(d, buf, 128);
        double s = 0; for (int i = 0; i < 256; i++) s += (double)buf[i] * buf[i];
        sq.push_back(s / 256);
    }
    E->destroy(d);
    const int win = 44100 / 128;   // 1 s of blocks
    double best = 0, run = 0;
    for (size_t i = 0; i < sq.size(); i++) { run += sq[i]; if (i >= (size_t)win) run -= sq[i - win]; if (i + 1 >= (size_t)win) best = fmax(best, run / win); }
    return 10 * log10(best / (32768.0 * 32768.0) + 1e-14);
}

int main(int argc, char **argv) {
    if (argc >= 4 && !strcmp(argv[1], "measure")) {
        int first = atoi(argv[2]), n = atoi(argv[3]);
        for (int p = first; p < first + n && p < NPRESETS; p++) printf("%d\t%.2f\n", p, level(p, 0));
        return 0;
    }
    if (argc >= 4 && !strcmp(argv[1], "fit")) {
        int p = atoi(argv[2]); double target = atof(argv[3]);
        double lo = 0, hi = 100; char v[16];
        for (int it = 0; it < 14; it++) {   // the level rises with VOLUME (squared, then a soft saturation): bisect
            double mid = (lo + hi) / 2; snprintf(v, sizeof v, "%.2f", mid);
            if (level(p, v) < target) lo = mid; else hi = mid;
        }
        snprintf(v, sizeof v, "%.1f", (lo + hi) / 2);
        printf("%d\t%s\t%.2f\n", p, v, level(p, v));
        return 0;
    }
    fprintf(stderr, "usage: preset_level measure FIRST COUNT | fit INDEX TARGET_DB\n");
    return 1;
}
