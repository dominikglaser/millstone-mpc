#pragma once
// mi::clamp is C++17; the shared engine builds as gnu++14 (the vendored eurorack DSP needs it),
// so the fx chain uses this instead. Same behaviour for the non-NaN values the fx code passes.
#include <algorithm>
namespace mi {
template <class T> inline T clamp(T v, T lo, T hi) { return v < lo ? lo : (v > hi ? hi : v); }
}
