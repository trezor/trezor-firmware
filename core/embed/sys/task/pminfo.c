/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifdef KERNEL_MODE

#include <inttypes.h>

#include <sys/systask.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

#ifdef USE_DBG_CONSOLE
static const char* irq_name(int irqn) {
  switch (irqn) {
    case -15:
      return "NMI";
    case -14:
      return "HardFault";
    case -13:
      return "MemManage";
    case -12:
      return "BusFault";
    case -11:
      return "UsageFault";
    case -10:
      return "SecureFault";
    case -5:
      return "SVCall";
    case -4:
      return "DebugMonitor";
    case -2:
      return "PendSV";
    case -1:
      return "SysTick";
  }

  return "Unknown";
}

static void print_fault(const system_fault_t* fault) {
  dbg_printf("  PC: 0x%08" PRIx32 "\n", fault->pc);
  dbg_printf("  SP: 0x%08" PRIx32 "\n", fault->sp);
  dbg_printf("  IRQn: %d (%s)\n", (int)fault->irqn, irq_name(fault->irqn));
  dbg_printf("  CFSR: 0x%08" PRIx32 "\n", fault->cfsr);
  dbg_printf("  HFSR: 0x%08" PRIx32 "\n", fault->hfsr);
  dbg_printf("  MMFAR: 0x%08" PRIx32 "\n", fault->mmfar);
  dbg_printf("  BFAR: 0x%08" PRIx32 "\n", fault->bfar);
#if defined(__ARM_FEATURE_CMSE)
  dbg_printf("  SFSR: 0x%08" PRIx32 "\n", fault->sfsr);
  dbg_printf("  SFAR: 0x%08" PRIx32 "\n", fault->sfar);
#endif
}

#endif  // USE_DBG_CONSOLE

void systask_print_pminfo(systask_t* task) {
#ifdef USE_DBG_CONSOLE

  const systask_postmortem_t* pminfo = &task->pminfo;

  if (pminfo->reason == TASK_TERM_REASON_EXIT && pminfo->exit.code == 0) {
    dbg_printf("Task #%u terminated cleanly\n", task->id);
    return;
  }

  dbg_printf("Task #%u terminated.\n", task->id);

  switch (pminfo->reason) {
    case TASK_TERM_REASON_EXIT:
      dbg_printf("Exit code: %d\n", pminfo->exit.code);
      break;

    case TASK_TERM_REASON_ERROR:
      dbg_printf("Error: %s\n", pminfo->error.message);
      if (pminfo->error.title[0] != '\0') {
        dbg_printf("Title: %s\n", pminfo->error.title);
      }
      if (pminfo->error.footer[0] != '\0') {
        dbg_printf("Footer: %s\n", pminfo->error.footer);
      }
      break;

    case TASK_TERM_REASON_FATAL:
      dbg_printf("Fatal: %s", pminfo->fatal.expr);
      if (pminfo->fatal.file[0] != '\0') {
        dbg_printf(" at %s:%" PRId32, pminfo->fatal.file, pminfo->fatal.line);
      }
      dbg_printf("\n");
      break;

    case TASK_TERM_REASON_FAULT:
      dbg_printf("Fault in %s code\n",
                 pminfo->privileged ? "privileged" : "unprivileged");
      print_fault(&pminfo->fault);
      break;
  }
#endif  // USE_DBG_CONSOLE
}

#endif  // KERNEL_MODE
