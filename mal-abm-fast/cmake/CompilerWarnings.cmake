add_library(mal_abm_fast::warnings INTERFACE)
target_compile_options(mal_abm_fast::warnings INTERFACE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:
    -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion>
  $<$<CXX_COMPILER_ID:Intel>:
    -Wall -Wremarks>
)
