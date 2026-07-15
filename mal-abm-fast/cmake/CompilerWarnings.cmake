# cmake/CompilerWarnings.cmake
#
# F1.b fix: CMake 3.18+ reserves the `::` syntax in target names for
# imported targets (policy CMP0028 NEW). The F1.a scaffold used
# `mal_abm_fast::warnings` directly which now errors out. We create
# the warnings library under a plain name and add an ALIAS so the
# downstream `target_link_libraries(... mal_abm_fast::warnings)`
# calls (in src/CMakeLists.txt and tests/CMakeLists.txt) keep
# working unchanged.
add_library(mal_abm_fast_warnings INTERFACE)
target_compile_options(mal_abm_fast_warnings INTERFACE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:
    -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion>
  $<$<CXX_COMPILER_ID:Intel>:
    -Wall -Wremarks>
)
# ALIAS: forward the legacy `mal_abm_fast::warnings` name to the
# plain in-project target above. Tests and src keep their existing
# `mal_abm_fast::warnings` link lines unchanged.
add_library(mal_abm_fast::warnings ALIAS mal_abm_fast_warnings)
