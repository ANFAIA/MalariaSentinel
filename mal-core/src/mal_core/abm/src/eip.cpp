// SPDX-License-Identifier: MIT
// eip.cpp — F1.c keeps this translation unit minimal.
//
// The `accumulate_eip` and `is_infective` helpers are `inline` in
// `eip.hpp` and are the canonical implementation. The .cpp is compiled
// so the build system has a translation unit to link; we add a single
// `extern` anchor to prevent the linker from stripping the inline defs
// if a future optimisation pass decides they're unused at the call
// site (this is defensive — currently `tests/test_eip.cpp` and the
// `EipAccumulate` smoke test reference them directly).
#include "eip.hpp"

namespace mal_abm_fast {

// Anchor: forces the linker to keep the inline defs available. The
// address is never taken; this is purely a presence signal.
extern "C" const volatile void* eip_inline_anchor =
    reinterpret_cast<const volatile void*>(&accumulate_eip);

}  // namespace mal_abm_fast
