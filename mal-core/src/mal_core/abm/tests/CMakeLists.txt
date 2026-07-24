# tests/CMakeLists.txt — GoogleTest + ctest
# All test executables for mal-abm-fast (F1.b scaffold + implementations).

include(GoogleTest)

# Find netCDF for the daily env NC tests
find_package(netCDF REQUIRED)

# F1.a: 3 smoke tests (VersionConstant, PrngStub, EipAccumulate).
add_executable(test_smoke test_smoke.cpp)
target_link_libraries(test_smoke
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_smoke)

# F1.b: IO layer tests (env_reader, climate, habitat_engine).
add_executable(test_env_reader test_env_reader.cpp)
target_link_libraries(test_env_reader
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings netCDF::netcdf
)
gtest_discover_tests(test_env_reader)

add_executable(test_habitat_engine test_habitat_engine.cpp)
target_link_libraries(test_habitat_engine
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_habitat_engine)

add_executable(test_climate test_climate.cpp)
target_link_libraries(test_climate
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings netCDF::netcdf
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
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings netCDF::netcdf
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

# Detection-based seeding tests (RANDOM_VIABLE, EXPLICIT, UNIFORM).
add_executable(test_seeding test_seeding.cpp)
target_link_libraries(test_seeding
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_seeding)

# G0: GridSpec spatial contract validation tests.
add_executable(test_grid_spec test_grid_spec.cpp)
target_link_libraries(test_grid_spec
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_grid_spec)

# G3: Complete lifecycle tests (Egg → Larva L1-L4 → Pupa → Adult).
add_executable(test_lifecycle test_lifecycle.cpp)
target_link_libraries(test_lifecycle
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_lifecycle)

# G4: Gonotrophic cycle + BiteLedger + multirate scheduler.
add_executable(test_gonotrophic test_gonotrophic.cpp)
target_link_libraries(test_gonotrophic
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_gonotrophic)

# G5: Host-seeking kernel + HostLandscape.
add_executable(test_host_seeking test_host_seeking.cpp)
target_link_libraries(test_host_seeking
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_host_seeking)

# G6: Sparse OD mobility matrices + MobilitySchedule.
add_executable(test_mobility test_mobility.cpp)
target_link_libraries(test_mobility
    PRIVATE mal_abm_fast_core GTest::gtest GTest::gtest_main mal_abm_fast::warnings
)
gtest_discover_tests(test_mobility)
