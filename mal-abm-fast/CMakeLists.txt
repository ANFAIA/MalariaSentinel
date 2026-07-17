cmake_minimum_required(VERSION 3.20)

project(mal_abm_fast VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Eigen3 REQUIRED CONFIG)
find_package(GDAL   REQUIRED)
find_package(CLI11  REQUIRED CONFIG)
find_package(nlohmann_json REQUIRED)
find_package(OpenMP REQUIRED)
if(OpenMP_CXX_FOUND)
    message(STATUS "OpenMP found: ${OpenMP_CXX_FLAGS}")
endif()
find_package(GTest REQUIRED)

include(cmake/CompilerWarnings.cmake)

# F1.a: src/ and tests/ may not exist yet (they ship in p_f5447082 / f1a-cxx).
# Guard so this scaffold's CMake configure succeeds even before the child
# CMakeLists land. The if(EXISTS) is a no-op once both children are present.
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/src/CMakeLists.txt)
  add_subdirectory(src)
endif()
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/CMakeLists.txt)
  enable_testing()
  add_subdirectory(tests)
endif()
