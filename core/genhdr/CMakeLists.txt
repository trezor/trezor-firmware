
set(QSTR_SOURCES 
../vendor/micropython/extmod/modubinascii.c
../vendor/micropython/extmod/moductypes.c
../vendor/micropython/extmod/moduheapq.c
../vendor/micropython/extmod/modutimeq.c
../vendor/micropython/extmod/utime_mphal.c
../vendor/micropython/shared/libc/abort_.c
../vendor/micropython/shared/libc/printf.c
../vendor/micropython/shared/runtime/gchelper_m3.s
../vendor/micropython/shared/runtime/gchelper_native.c
../vendor/micropython/shared/runtime/interrupt_char.c
../vendor/micropython/shared/runtime/pyexec.c
../vendor/micropython/shared/runtime/stdout_helpers.c
../vendor/micropython/shared/timeutils/timeutils.c
../vendor/micropython/ports/stm32/gccollect.c
../vendor/micropython/ports/stm32/pendsv.c
../vendor/micropython/py/argcheck.c
../vendor/micropython/py/asmarm.c
../vendor/micropython/py/asmbase.c
../vendor/micropython/py/asmthumb.c
../vendor/micropython/py/asmx64.c
../vendor/micropython/py/asmx86.c
../vendor/micropython/py/asmxtensa.c
../vendor/micropython/py/bc.c
../vendor/micropython/py/binary.c
../vendor/micropython/py/builtinevex.c
../vendor/micropython/py/builtinhelp.c
../vendor/micropython/py/builtinimport.c
../vendor/micropython/py/compile.c
../vendor/micropython/py/emitbc.c
../vendor/micropython/py/emitcommon.c
../vendor/micropython/py/emitglue.c
../vendor/micropython/py/emitinlinethumb.c
../vendor/micropython/py/emitinlinextensa.c
../vendor/micropython/py/formatfloat.c
../vendor/micropython/py/frozenmod.c
../vendor/micropython/py/lexer.c
../vendor/micropython/py/malloc.c
../vendor/micropython/py/map.c
../vendor/micropython/py/modarray.c
../vendor/micropython/py/modbuiltins.c
../vendor/micropython/py/modgc.c
../vendor/micropython/py/modmath.c
../vendor/micropython/py/modmicropython.c
../vendor/micropython/py/modstruct.c
../vendor/micropython/py/modsys.c
../vendor/micropython/py/mpprint.c
../vendor/micropython/py/mpstate.c
../vendor/micropython/py/mpz.c
../vendor/micropython/py/nativeglue.c
../vendor/micropython/py/obj.c
../vendor/micropython/py/objarray.c
../vendor/micropython/py/objattrtuple.c
../vendor/micropython/py/objbool.c
../vendor/micropython/py/objboundmeth.c
../vendor/micropython/py/objcell.c
../vendor/micropython/py/objclosure.c
../vendor/micropython/py/objcomplex.c
../vendor/micropython/py/objdict.c
../vendor/micropython/py/objenumerate.c
../vendor/micropython/py/objexcept.c
../vendor/micropython/py/objfilter.c
../vendor/micropython/py/objfloat.c
../vendor/micropython/py/objfun.c
../vendor/micropython/py/objgenerator.c
../vendor/micropython/py/objgetitemiter.c
../vendor/micropython/py/objint.c
../vendor/micropython/py/objint_longlong.c
../vendor/micropython/py/objint_mpz.c
../vendor/micropython/py/objlist.c
../vendor/micropython/py/objmap.c
../vendor/micropython/py/objmodule.c
../vendor/micropython/py/objnamedtuple.c
../vendor/micropython/py/objnone.c
../vendor/micropython/py/objobject.c
../vendor/micropython/py/objpolyiter.c
../vendor/micropython/py/objproperty.c
../vendor/micropython/py/objrange.c
../vendor/micropython/py/objreversed.c
../vendor/micropython/py/objset.c
../vendor/micropython/py/objsingleton.c
../vendor/micropython/py/objslice.c
../vendor/micropython/py/objstr.c
../vendor/micropython/py/objstringio.c
../vendor/micropython/py/objstrunicode.c
../vendor/micropython/py/objtuple.c
../vendor/micropython/py/objtype.c
../vendor/micropython/py/objzip.c
../vendor/micropython/py/opmethods.c
../vendor/micropython/py/pairheap.c
../vendor/micropython/py/parse.c
../vendor/micropython/py/parsenum.c
../vendor/micropython/py/parsenumbase.c
../vendor/micropython/py/persistentcode.c
../vendor/micropython/py/qstr.c
../vendor/micropython/py/reader.c
../vendor/micropython/py/repl.c
../vendor/micropython/py/runtime.c
../vendor/micropython/py/runtime_utils.c
../vendor/micropython/py/scheduler.c
../vendor/micropython/py/scope.c
../vendor/micropython/py/sequence.c
../vendor/micropython/py/showbc.c
../vendor/micropython/py/smallint.c
../vendor/micropython/py/stackctrl.c
../vendor/micropython/py/stream.c
../vendor/micropython/py/unicode.c
../vendor/micropython/py/vstr.c
../vendor/micropython/py/warning.c
../vendor/micropython/py/gc.c
../vendor/micropython/py/pystack.c
../vendor/micropython/py/vm.c
../vendor/micropython/lib/uzlib/adler32.c
../vendor/micropython/lib/uzlib/crc32.c
../vendor/micropython/lib/uzlib/tinflate.c


../embed/extmod/modtrezorconfig/modtrezorconfig.c
../embed/extmod/modtrezorcrypto/crc.c
../embed/extmod/modtrezorcrypto/modtrezorcrypto.c
../embed/extmod/modtrezorcrypto/rand.c
../embed/extmod/modtrezorio/modtrezorio.c
../embed/extmod/modtrezorui/modtrezorui.c
../embed/extmod/modtrezorutils/modtrezorutils.c
../embed/extmod/modtrezorio/ff.c
../embed/extmod/modtrezorio/ffunicode.c
../embed/extmod/modutime.c
../embed/extmod/rustmods.c

../embed/extmod/trezorobj.c
)

list(TRANSFORM QSTR_SOURCES PREPEND ${CMAKE_CURRENT_SOURCE_DIR}/)


add_custom_target(qstr
    SOURCES 
        ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.generated.h 
        ${CMAKE_CURRENT_BINARY_DIR}/moduledefs.h
        ${CMAKE_CURRENT_BINARY_DIR}/mpversion.h
    
)


get_target_property(MAIN_CFLAGS micropython COMPILE_OPTIONS)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected_in.h
    DEPENDS ${QSTR_SOURCES} ${CMAKE_CURRENT_BINARY_DIR}/mpversion.h
    COMMAND ${CMAKE_C_COMPILER} 
        ${MAIN_CFLAGS}
        "-D$<JOIN:$<TARGET_PROPERTY:micropython,COMPILE_DEFINITIONS>,;-D>"
        "-DNO_QSTR;-DN_X64;-DN_X86;-DN_THUMB"
        "-I../..;-I../../embed/rust"
        "-I$<JOIN:$<TARGET_PROPERTY:micropython,INCLUDE_DIRECTORIES>,;-I>"
        -I ${CMAKE_BINARY_DIR}
        -E ${QSTR_SOURCES} > ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected_in.h
        COMMAND_EXPAND_LISTS VERBATIM
)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected.h
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected_in.h
    COMMAND 
        grep -o MP_QSTR_[a-zA-Z0-9_]* ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected_in.h |
        sed -n "'s/.*MP_QSTR_\\([_a-zA-Z0-9]\\+\\).*/Q(\\1)/p'"
        > ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected.h
)


add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_1.h
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected.h
    COMMAND 
        cat ../../vendor/micropython/py/qstrdefs.h ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected.h |
        sed "'s/^Q(.*)/\\\"&\\\"/'" 
        > ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_1.h
)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_2.h
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_1.h
    COMMAND 
        ${CMAKE_C_COMPILER}
            ${MAIN_CFLAGS}  
            "-D$<JOIN:$<TARGET_PROPERTY:micropython,COMPILE_DEFINITIONS>,;-D>"
            "-DNO_QSTR;-DN_X64;-DN_X86;-DN_THUMB"
            "-I../..;-I../../embed/rust"
            "-I$<JOIN:$<TARGET_PROPERTY:micropython,INCLUDE_DIRECTORIES>,;-I>"
            -E ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_1.h
        > ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_2.h
    COMMAND_EXPAND_LISTS VERBATIM
)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed.h
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_2.h
    COMMAND 
        sed "'s/^\\\"\\(Q(.*)\\)\\\"/\\1/'" ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed_2.h
        > ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed.h
)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.generated.h
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed.h
    COMMAND python3 ../../vendor/micropython/py/makeqstrdata.py
        ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.preprocessed.h
        > ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.generated.h
)


add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/modules.collected.h
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected_in.h
    COMMAND sed -n "'s/\\(MP_REGISTER_MODULE(.*,.*);.*\\)/\\1/p'"
        ${CMAKE_CURRENT_BINARY_DIR}/qstrdefs.collected_in.h
        > ${CMAKE_CURRENT_BINARY_DIR}/modules.collected.h
)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/moduledefs.h
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/modules.collected.h
    COMMAND python3 ../../vendor/micropython/py/makemoduledefs.py
        ${CMAKE_CURRENT_BINARY_DIR}/modules.collected.h
        > ${CMAKE_CURRENT_BINARY_DIR}/moduledefs.h
)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/mpversion.h
    COMMAND python3 ../../vendor/micropython/py/makeversionhdr.py
        ${CMAKE_CURRENT_BINARY_DIR}/mpversion.h
)

