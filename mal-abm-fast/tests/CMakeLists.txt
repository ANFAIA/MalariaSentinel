# tests/CMakeLists.txt — GoogleTest + ctest
# All test executables for mal-abm-fast (F1.b scaffold + implementations).

include(GoogleTest)

# F1.a: 3 smoke tests (VersionConstant, PrngStub, EipAccumulate).
add_executable(test_smoke test_smoke.cpp)
target_link_libraries(test_smoke
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_smoke)

# F1.b: IO layer tests (env_reader, climate, habitat_engine).
add_executable(test_env_reader test_env_reader.cpp)
target_link_libraries(test_env_reader
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_env_reader)

add_executable(test_habitat_engine test_habitat_engine.cpp)
target_link_libraries(test_habitat_engine
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_habitat_engine)

add_executable(test_climate test_climate.cpp)
target_link_libraries(test_climate
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_climate)

# F1.b: math primitives (prng, eip, dispersal).
add_executable(test_prng test_prng.cpp)
target_link_libraries(test_prng
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_prng)

add_executable(test_eip test_eip.cpp)
target_link_libraries(test_eip
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_eip)

add_executable(test_dispersal test_dispersal.cpp)
target_link_libraries(test_dispersal
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_dispersal)

# F1.b: per-day orchestrator.
add_executable(test_coordinator test_coordinator.cpp)
target_link_libraries(test_coordinator
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_coordinator)

# F1.b: mosquito submodel.
add_executable(test_mosquito_submodel test_mosquito_submodel.cpp)
target_link_libraries(test_mosquito_submodel
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_mosquito_submodel)

# F1.b: state COG writer.
add_executable(test_state_cog test_state_cog.cpp)
target_link_libraries(test_state_cog
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_state_cog)

# F1.b: end-to-end engine (AnophelesABM facade).
add_executable(test_engine test_engine.cpp)
target_link_libraries(test_engine
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_engine)
