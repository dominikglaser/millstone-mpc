// Developer check: does any factory preset keep sounding long after the keys are released?
// Loads each preset the way the plugin wrapper does (every listed parameter through set_param), plays a short
// phrase at the MPC's rate and block size, releases everything, and measures the level 20-30 s later, once with
// the preset's own FX and once with the FX bypassed. A tail that only exists with FX points at the FX chain.
// Usage: preset_tails [first] [count]      (prints one line per preset that rings, then a summary)
extern "C" {
#include "engine.h"
}
#include "params.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <initializer_list>

static const int kBlock = 128;

// PRESSURE=<0..127>: channel aftertouch sent with every note-on (the Key 37 sends it when keys are pressed in).
// PRESSURE_STUCK=1: no pressure 0 after the release (a keyboard that never sends it). OCT=<n>: phrase n octaves up.
static int pressure() { const char *e = getenv("PRESSURE"); return e ? atoi(e) : 0; }
static void note(const mpc_engine_t *E, void *d, int n, int on) {
    uint8_t m[3] = {(uint8_t)(on ? 0x90 : 0x80), (uint8_t)n, (uint8_t)(on ? (getenv("VEL") ? atoi(getenv("VEL")) : 100) : 0)};
    E->midi(d, m, 3);
    if (on && pressure()) { uint8_t a[2] = {0xd0, (uint8_t)pressure()}; E->midi(d, a, 2); }
}

// Render `secs` seconds; return the RMS (dBFS) of the whole span.
static double render_db(const mpc_engine_t *E, void *d, double secs, double *peak_db) {
    int16_t out[kBlock * 2];
    long n = (long)(secs * 44100 / kBlock);
    double sum = 0; int peak = 0;
    for (long b = 0; b < n; b++) {
        E->render(d, out, kBlock);
        for (int i = 0; i < kBlock * 2; i++) { sum += (double)out[i] * out[i]; if (abs(out[i]) > peak) peak = abs(out[i]); }
    }
    if (peak_db) *peak_db = peak ? 20 * log10(peak / 32768.0) : -120;
    double rms = sqrt(sum / (n * kBlock * 2.0));
    return rms > 0 ? 20 * log10(rms / 32768.0) : -120;
}

struct Result { double play, tail, tail_peak; };

static Result run(const mpc_engine_t *E, int p, bool fx) {
    void *d = E->create(0);
    for (int i = 0; i < PRESETS[p].n; i++)
        E->set_param(d, PARAMS[PRESETS[p].values[i].param].key, PRESETS[p].values[i].value);
    if (!fx) for (const char *k : {"fx_ph_mix", "fx_dl_mix", "fx_rv_mix"}) E->set_param(d, k, "0");
    if (!fx) E->set_param(d, "fx_ch_mode", "0");
    if (E->song_pos) E->song_pos(d, 0, 120.0, 1, 0);
    // A short phrase: C4 E4 G4 C5, each held 0.4 s with a 0.1 s gap, then a C4-E4-G4 chord held 1.5 s.
    double play = -120;
    const int o = getenv("OCT") ? 12 * atoi(getenv("OCT")) : 0;
    const int phrase[4] = {60 + o, 64 + o, 67 + o, 72 + o};
    for (int k = 0; k < 4; k++) {
        note(E, d, phrase[k], 1); double a = render_db(E, d, 0.4, 0); note(E, d, phrase[k], 0);
        render_db(E, d, 0.1, 0); if (a > play) play = a;
    }
    for (int n : {60, 64, 67}) note(E, d, n + o, 1);
    double a = render_db(E, d, 1.5, 0); if (a > play) play = a;
    for (int n = 0; n < 128; n++) note(E, d, n, 0);
    uint8_t pedal[3] = {0xb0, 64, 0}; E->midi(d, pedal, 3);
    if (!getenv("PRESSURE_STUCK")) { uint8_t a[2] = {0xd0, 0}; E->midi(d, a, 2); }
    render_db(E, d, 20.0, 0);                  // let release, reverb and normal echoes die
    Result r; r.play = play;
    r.tail = render_db(E, d, 10.0, &r.tail_peak); // 20-30 s after release
    E->destroy(d);
    return r;
}

int main(int argc, char **argv) {
    const mpc_engine_t *E = mpc_engine();
    int first = argc > 1 ? atoi(argv[1]) : 0, count = argc > 2 ? atoi(argv[2]) : NPRESETS;
    int ringing = 0, fx_only = 0;
    for (int p = first; p < first + count && p < NPRESETS; p++) {
        Result w = run(E, p, true);
        if (w.tail < -70) continue;            // quiet 20 s after release: fine
        Result dry = run(E, p, false);
        bool fxcause = dry.tail < -70;
        ringing++; if (fxcause) fx_only++;
        char dl[16] = "", fb[16] = "", mix[16] = "", rv[16] = "";
        void *d = E->create(0);
        for (int i = 0; i < PRESETS[p].n; i++)
            E->set_param(d, PARAMS[PRESETS[p].values[i].param].key, PRESETS[p].values[i].value);
        E->get_param(d, "fx_dl_mix", mix, 16); E->get_param(d, "fx_dl_fb", fb, 16);
        E->get_param(d, "fx_dl_time", dl, 16); E->get_param(d, "fx_rv_mix", rv, 16);
        E->destroy(d);
        printf("%3d %-24s play %6.1f dB  tail(20-30s) %6.1f dB peak %6.1f | no-fx tail %6.1f  %s  dl_mix=%s fb=%s time=%s rv_mix=%s\n",
               p, PRESETS[p].name, w.play, w.tail, w.tail_peak, dry.tail, fxcause ? "FX" : "VOICE", mix, fb, dl, rv);
        fflush(stdout);
    }
    printf("\n%d of %d presets still sound 20-30 s after release; %d only with FX on\n", ringing, count, fx_only);
    return 0;
}
