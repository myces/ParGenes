
find_package(MPI REQUIRED)

include_directories(${MPI_INCLUDE_PATH})
set(CMAKE_BUILD_TYPE Debug)

add_executable(mpi-scheduler main.cpp 
  Checkpoint.cpp
  Command.cpp 
  Common.cpp 
  SVGDrawer.cpp
  split_implem/SplitImplem.cpp
  onecore_implem/OneCoreImplem.cpp
  )

target_link_libraries(mpi-scheduler ${MPI_LIBRARIES} dl gcc_s gcc)

if(MPI_COMPILE_FLAGS)
  set_target_properties(mpi-scheduler PROPERTIES
    COMPILE_FLAGS "${MPI_COMPILE_FLAGS}")
endif()

if(MPI_LINK_FLAGS)
  set_target_properties(mpi-scheduler PROPERTIES
    LINK_FLAGS "${MPI_LINK_FLAGS}")
endif()

