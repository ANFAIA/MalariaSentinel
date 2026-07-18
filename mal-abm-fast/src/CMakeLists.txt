# src/CMakeLists.txt — mal_abm_fast core library + CLI binary

add_library(mal_abm_fast_core STATIC
    env_reader.cpp
    prng.cpp
    dispersal.cpp
    eip.cpp
    climate.cpp
    habitat_engine.cpp
    mosquito_state.cpp
    mosquito_submodel.cpp
    coordinator.cpp
    output_contract.cpp
    engine.cpp
    seeding.cpp
)
target_include_directories(mal_abm_fast_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/../include
        ${CMAKE_CURRENT_SOURCE_DIR}/../include/mal_abm_fast
)
target_link_libraries(mal_abm_fast_core
    PUBLIC mal_abm_fast::warnings
)
# F1.b deps: GDAL (env_reader, climate, habitat_engine, output_contract),
# nlohmann_json (output_contract sidecar), Eigen (numerical helpers in F2).
target_link_libraries(mal_abm_fast_core
    PUBLIC GDAL::GDAL nlohmann_json::nlohmann_json Eigen3::Eigen
)
if(OpenMP_CXX_FOUND)
    target_link_libraries(mal_abm_fast_core PUBLIC OpenMP::OpenMP_CXX)
endif()

add_executable(mal_abm_fast main.cpp)
target_link_libraries(mal_abm_fast
    PRIVATE mal_abm_fast_core mal_abm_fast::warnings CLI11::CLI11
)
