# tests/CMakeLists.txt — GoogleTest + ctest

add_executable(test_smoke test_smoke.cpp)
target_link_libraries(test_smoke
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)

include(GoogleTest)
gtest_discover_tests(test_smoke)
