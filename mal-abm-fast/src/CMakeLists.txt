# src/CMakeLists.txt — mal_abm_fast core library + CLI binary

add_library(mal_abm_fast_core STATIC
    prng.cpp
    dispersal.cpp
    eip.cpp
    climate.cpp
    habitat_engine.cpp
    mosquito_state.cpp
    output_contract.cpp
)
target_include_directories(mal_abm_fast_core
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/../include
)
target_link_libraries(mal_abm_fast_core
    PUBLIC mal_abm_fast::warnings
)
# F2/F3 will add Eigen, GDAL, CLI11, nlohmann_json, OpenMP.

add_executable(mal_abm_fast main.cpp)
target_link_libraries(mal_abm_fast
    PRIVATE mal_abm_fast_core mal_abm_fast::warnings
)
# F1.d will add CLI11 as a PUBLIC dep once `run` is the main subcommand.
