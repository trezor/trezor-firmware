
set(MPY_CROSS ../../vendor/micropython/mpy-cross/mpy-cross)
set(MPY_TOOL ../../vendor/micropython/tools/mpy-tool.py)


set(PY_FILES main.py session.py usb.py)
#file(GLOB_RECURSE PY_FILES RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/*.py )


list(TRANSFORM PY_FILES PREPEND ${CMAKE_CURRENT_BINARY_DIR}/ OUTPUT_VARIABLE MPY_FILES)
list(TRANSFORM MPY_FILES REPLACE "[.]py$" ".mpy")

add_library(frozen_mpy
    ${CMAKE_CURRENT_BINARY_DIR}/frozen_mpy.c
)

target_include_directories(frozen_mpy PRIVATE ../embed/firmware)

target_link_libraries(frozen_mpy micropython trezor-lib)


add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/frozen_mpy.c
    DEPENDS "${MPY_FILES}" ${CMAKE_BINARY_DIR}/genhdr/qstrdefs.preprocessed.h
    COMMAND ${MPY_TOOL} -f -q ${CMAKE_BINARY_DIR}/genhdr/qstrdefs.preprocessed.h ${MPY_FILES} > ${CMAKE_CURRENT_BINARY_DIR}/frozen_mpy.c
)

#COMMAND ${MPY_TOOL} -f -q ${qstr_header} ${MPY_FILES} > ${CMAKE_CURRENT_BINARY_DIR}/frozen_mpy.c",


function(add_mpy target_file source_file)
    cmake_path(RELATIVE_PATH source_file BASE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR} OUTPUT_VARIABLE source_name)
    cmake_path(REMOVE_EXTENSION source_name LAST_ONLY)

    add_custom_command(
        OUTPUT ${target_file}
        DEPENDS ${source_file}
        COMMAND ${MPY_CROSS} -o ${target_file} -s ${source_name} ${source_file}
    )
endfunction()


#[[foreach(file IN LISTS PY_FILES)
    string(REGEX REPLACE "[.]py$" ".mpy" mpy_file ${file})
    add_mpy(${CMAKE_CURRENT_BINARY_DIR}/${mpy_file} ${CMAKE_CURRENT_SOURCE_DIR}/${file} )
endforeach()
]]


#[[
sed_scripts = " ".join(
    [
        rf"-e 's/utils\.MODEL_IS_T2B1/{is_t2b1}/g'",
        rf"-e 's/utils\.BITCOIN_ONLY/{btc_only}/g'",
        rf"-e 's/utils\.USE_BACKLIGHT/{backlight}/g'",
        rf"-e 's/utils\.USE_OPTIGA/{optiga}/g'",
        rf"-e 's/utils\.UI_LAYOUT == \"TT\"/{layout_tt}/g'",
        rf"-e 's/utils\.UI_LAYOUT == \"TR\"/{layout_tr}/g'",
        r"-e 's/if TYPE_CHECKING/if False/'",
        r"-e 's/import typing/# \0/'",
        r"-e '/from typing import (/,/^\s*)/ {s/^/# /}'",
        r"-e 's/from typing import/# \0/'",
    ]
)
]]

set(sed_script 
    "-e 's/if TYPE_CHECKING/if False/'"
)


function(add_i_file target_file source_file)
    add_custom_command(
        OUTPUT ${target_file}
        DEPENDS ${source_file}
        COMMAND sed ${sed_script} ${source_file} > ${target_file}
    )
endfunction()


foreach(file IN LISTS PY_FILES) 
    add_i_file(${CMAKE_CURRENT_BINARY_DIR}/${file}.i ${CMAKE_CURRENT_SOURCE_DIR}/${file} )
endforeach()

foreach(file IN LISTS PY_FILES)
    string(REGEX REPLACE "[.]py$" ".mpy" mpy_file ${file})
    add_mpy(${CMAKE_CURRENT_BINARY_DIR}/${mpy_file} ${CMAKE_CURRENT_BINARY_DIR}/${file}.i )
endforeach()










