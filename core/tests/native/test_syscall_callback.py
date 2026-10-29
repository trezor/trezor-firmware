"""Compile the actual syscall IPC module with a simulated storage callback.

Run directly with Python. A pre-fix IPC module fails the preservation assertions.
"""

import subprocess
import tempfile
from pathlib import Path

HEADERS = {
    "trezor_rtl.h": """#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define UNUSED(x) (void)(x)
""",
    "sys/sysevent_source.h": """#pragma once
#include <sys/systask.h>
typedef struct {
 void (*task_created)(void*,unsigned); void (*task_killed)(void*,unsigned);
 void (*poll)(void*,bool,bool); bool (*check_read_ready)(void*,unsigned,void*);
 bool (*check_write_ready)(void*,unsigned,void*);
} syshandle_vmt_t;
#define SYSHANDLE_SYSCALL 1
static inline bool syshandle_register(int h,const syshandle_vmt_t*v,void*c){return true;}
static inline void syshandle_signal_read_ready(int h,void*p){}
""",
    "sys/syscall_ipc.h": """#pragma once
void syscall_ipc_enqueue(uint32_t*,unsigned); void syscall_ipc_dequeue(void);
""",
    "sys/syscall.h": """#pragma once
typedef unsigned syscall_number_t;
void syscall_handler(uint32_t*,uint32_t,void*);
""",
    "sys/systask.h": """#pragma once
typedef unsigned systask_id_t;
typedef struct { unsigned id; void *applet; bool in_callback; } systask_t;
systask_t *systask_active(void); systask_t *systask_kernel(void);
void systask_yield_to(systask_t*); bool systask_is_alive(systask_t*);
void systask_set_r0r1(systask_t*,uint32_t,uint32_t);

void systask_exit_fatal(systask_t*, const char*, size_t, const char*, size_t, int);
""",
}

PROGRAM = r"""#include <trezor_rtl.h>
#include <stdio.h>
#include <assert.h>
#include <sys/systask.h>
#include "syscall_ipc_under_test.c"
static systask_t app={.id=1}, kernel;
static bool rejected, nested_switch;
systask_t *systask_active(void){return &app;}
systask_t *systask_kernel(void){return &kernel;}
bool systask_is_alive(systask_t*t){return !rejected;}
void systask_set_r0r1(systask_t*t,uint32_t a,uint32_t b){}
void systask_exit_fatal(systask_t*t,const char*m,size_t n,const char*f,size_t z,int l){
 assert(t==&app); rejected=true;
}
void systask_yield_to(systask_t*t){
 if(app.in_callback && t==&kernel) nested_switch=true;
}
void syscall_handler(uint32_t *args,uint32_t number,void *applet){
 assert(number==100 && args[0]==11);
 app.in_callback=true;
 uint32_t nested[6]={22};
 syscall_ipc_enqueue(nested,200);
 assert(rejected && !nested_switch);
 assert(g_syscall_ipc.syscall.number==100 && args[0]==11);
}
int main(void){
 uint32_t args[6]={11}; assert(syscall_ipc_init());
 syscall_ipc_enqueue(args,100); syscall_ipc_dequeue();
 assert(rejected && !nested_switch);
 puts("callback thread syscall rejected before overwriting storage IPC");
}
"""


def main():
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="syscall-callback-") as directory:
        work = Path(directory)
        for name, content in HEADERS.items():
            path = work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        (work / "syscall_ipc_under_test.c").write_text(
            (root / "embed/sys/syscall/stm32/syscall_ipc.c").read_text()
        )
        (work / "test.c").write_text(PROGRAM)
        binary = work / "test"
        subprocess.run(
            [
                "cc",
                "-DKERNEL",
                "-I",
                str(work),
                str(work / "test.c"),
                "-o",
                str(binary),
            ],
            check=True,
        )
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
