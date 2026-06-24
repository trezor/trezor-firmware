# Trezor firmware architecture

This document gives a security-focused architectural overview of the Trezor firmware's embedded layer (referred to as "embed" within the codebase).

The document applies primarily to Trezor Safe 3, Trezor Safe 5, and Trezor Safe 7, which are based on **STM32U5** microcontrollers with **Arm Cortex-M33** cores.

Legacy models such as Trezor Model T are based on **STM32F4** microcontrollers and are covered only partially. Because STM32F4 does not support TrustZone, there is no secmon; the firmware consists only of kernel and coreapp, with the kernel taking on the security responsibilities that secmon handles on newer devices.

## 1. Device and platform context

### 1.1 Hardware platform

The firmware is designed to make strong use of the hardware security capabilities built into the STM32U5 microcontroller. Rather than implementing security purely in software, the architecture relies on hardware-enforced isolation, hardware-bound key material, and dedicated hardware crypto blocks wherever possible. This tight coupling between firmware design and silicon features is a deliberate choice: it raises the bar for attackers significantly compared to a software-only approach.

Cortex-M33 TrustZone is used to isolate firmware components across secure and non-secure domains (notably the secmon/kernel boundary), and the MPU enforces strict isolation between the privileged kernel domain and unprivileged app domains.

STM32U5 offers a strong built-in security baseline that aligns well with the firmware architecture and its defense-in-depth design goals. Key security features include:

- BHK (Boot Hardware Key): device-bound hardware root secret used as a trust anchor for key derivation and secure key handling.
- permanent write protection of boardloader code, which serves as an immutable root of trust.
- HDP is used to temporarily hide a flash region containing sensitive data after that data has been transferred into BHK hardware registers.
- JTAG/SWD debugging interfaces are fully locked in production configuration.
- TrustZone attribution controls (SAU/IDAU + GTZC): enforce secure/non-secure memory and peripheral partitioning.
- hardware crypto and entropy blocks are available (SAES/HASH/PKA/TRNG); currently SAES is used for key derivation, HASH accelerates firmware hashing, and TRNG provides hardware entropy. PKA is not currently used and is delegated to firmware crypto libraries.
- selected tamper events (potential attack indicators) trigger deletion/zeroization of critical RAM regions and registers containing sensitive material.

#### Secure elements
Alongside the above MCU security features, the platform also uses dedicated external secure elements:

- Trezor Safe 3, Trezor Safe 5, and Trezor Safe 7 use an **Optiga** secure element.
- Trezor Safe 7 additionally uses a **Tropic** secure element.

Secure elements are used for two primary purposes: deriving keys from secrets stored inside the secure element during production, and providing firmware attestation as a genuineness check.

Only components running in the secure world, namely boardloader, bootloader, and secmon, have direct access to these secure elements.

### 1.2 Firmware language stack
The firmware is currently implemented in three languages for historical and practical reasons:

- **C** is used for low-level hardware drivers, cryptography, and third-party libraries (including the MicroPython runtime).
- **Rust** is used for UI rendering: graphics libraries, layout engine, and visual components.
- **MicroPython** is used for application logic and UI flow control: screen sequencing, user interaction handling, and business logic.

The codebase is continuously being rewritten into Rust. In the long term, the goal is to reduce dependence on MicroPython and most C code.

The diagram below shows the firmware structure from an embedded-developer-centric point of view.
Most firmware source code lives in `/core/embed`. MicroPython sources are located in `/core/src`, and external libraries are stored in `/core/vendor`.

![Modules](arch-modules.drawio.svg)


## 2. Trust boundaries and security policy
The firmware is composed of several independent components:

- **boardloader/bootloader** are roots of execution trust for later stages.
- **secmon** is the secure-world mediator for sensitive peripherals and secrets.
- **kernel** is trusted for privileged non-secure scheduling and driver mediation.
- **coreapp** is unprivileged and must use mediated interfaces.
- **third-party apps** are unprivileged and must use mediated interfaces. Third-party apps have much narrower kernel API access than coreapp.

Our security architecture is designed to achieve the following objectives:

- achieving safe booting, where each earlier stage verifies the next stage before handoff
- enforcing isolation between privilege domains, where less-trusted code can access privileged resources only through mediated APIs
- minimizing the trusted computing base at each stage, keeping security-critical privileged code as small and auditable as possible and moving non-critical logic into less-privileged components behind mediated interfaces

Trust boundaries are enforced by privilege level, TrustZone world, and memory attribution (MPU and SAU):

- only authenticated code is executed
- privilege is reduced as early as possible
- cross-domain access goes through mediated interfaces

In all cases, a detected security violation leads to RSOD (Red Screen of Death), followed by a system reset:

- boot/authentication failure: the next stage is not started
- illegal memory access: a hardware fault fires and the offending task is stopped
- invalid syscall/smcall arguments: the call is rejected before reaching the implementation

## 3. Boot chain and privilege transitions
The following diagram describes the boot-stage sequence:

![Boot stages](boot-stages.drawio.svg)

The immutable **boardloader** verifies the bootloader, which can be updated in the field when needed. "Boardloader" and "bootloader" are internal names for the first-stage and second-stage bootloaders.

The **bootloader** verifies the secure monitor (secmon) and the remaining firmware (kernel + coreapp). Secmon and kernel + coreapp are signed independently. Secmon is always verified against production keys and cannot be replaced by the user — it is a fixed part of the trusted platform. Kernel + coreapp, on the other hand, can be replaced with user-built binaries after [unlocking the bootloader](https://trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/unlocking-the-bootloader-on-trezor-safe-devices?srsltid=AfmBOoo2uZS2aUI5ak_IkU5tzMtrH51HZfLAjOmmVj7pqEvXXvtJOov5), which allows developers and advanced users to run custom firmware on standard devices.

The **bootloader** is also the last stage with access to the flash secrets area containing sensitive root material used to derive other keys (for example, storage-encryption keys). This material is transferred through dedicated BHK registers that are non-readable and usable only through the SAES peripheral. The flash secrets area is then hidden using STM32 HDP until the next reset.

*NOTE:* Applications can place boot arguments in the RAM bootargs region, which persists across resets (see `core/embed/sys/startup/inc/sys/bootargs.h`). These arguments can modify bootloader behavior, trigger specific bootloader actions, or request an RSOD screen after a crash.

**Secmon** does not re-verify the kernel, because verification has already been completed by the bootloader. It initializes secure peripherals, configures TrustZone, isolates itself from the rest of the firmware, and hands off execution to the kernel. Secmon exposes the smcall API to the kernel; this API is callable only from privileged context, not by coreapp or third-party apps.

The **kernel** is the first component to run in non-secure context. It initializes non-secure peripherals, configures MPU isolation from unprivileged applications, and runs coreapp in unprivileged mode with isolated resources. The kernel provides syscalls for unprivileged applications.

## 4. Memory and isolation model

The STM32U5 devices used in this platform provide up to 4 MB of flash and up to 2.5 MB of SRAM. The exact flash and SRAM layout is device-specific. The following diagram shows a representative example:

![Memory layout](memory-layout.drawio.svg)

The firmware uses non-overlapping, properly aligned memory regions whose access permissions are enforced by the MPU, SAU, and STM32 Global TrustZone Controller. Each component is granted access only to the regions it is intended to use.

Although third-party applications execute in the same unprivileged world as coreapp, they do not share SRAM with coreapp. Likewise, if multiple third-party applications are active, they do not share memory or other isolated resources with one another.

Each firmware component occupies a distinct position along two independent isolation axes — TrustZone world (secure vs. non-secure) and Cortex-M privilege level (privileged vs. unprivileged). Together these axes define four execution quadrants: secmon runs in the secure privileged quadrant, the kernel in the non-secure privileged quadrant, and coreapp together with third-party apps in the non-secure unprivileged quadrant. The secure unprivileged quadrant is not currently used. The following diagram shows which components belong to each quadrant:

![TrustZone quadrants](trustzone-quadrants.drawio.svg)

Cortex-M33 TrustZone and the MPU enforce the following isolation properties:
- no direct cross-domain access without controlled call paths
- world transitions require explicit secure gateway and branch-exchange mechanisms
- peripheral access is partitioned by security attribution and gated at the bus/peripheral level

## 5. System components
Each firmware component (boardloader, secmon, etc.) is an independent binary with its own dedicated flash and SRAM regions. Components are built independently from a shared codebase and compose a common set of modules (hardware drivers, cryptography, etc.) alongside component-specific code.

The source tree under `/core/embed` is organized into modules (or layers) that components include in different combinations, as shown in the following diagram:

![Layer model](component-layers.drawio.svg)

Self-contained components such as boardloader and bootloader, which must run independently of any other firmware in flash, require nearly all layers.

The upgradable firmware consists of secmon, kernel, and coreapp, each of which selects only the layers relevant to its role.

### 5.1 Boardloader

The **boardloader** is an immutable first-stage bootloader that cannot be upgraded and serves as the hardware root of trust. It supports in-field bootloader upgrades via a dedicated flash region: the running bootloader or secmon can deposit a new bootloader image in that region, and on the next reset the boardloader verifies the new image and, if valid, replaces the previous one.

### 5.2 Bootloader

The **bootloader** is the second-stage bootloader responsible for firmware update orchestration via USB or Bluetooth, image authentication, and a minimal user interface for operations such as factory reset and Bluetooth pairing.

From a security perspective, the bootloader is the last stage with access to the flash secrets area. Master keys are transferred into BHK hardware registers (usable only via the SAES peripheral), and the secrets area is subsequently hidden using the STM32 HDP feature until the next reset.

The only external input accepted at this stage is the bootargs region in RAM (see `core/embed/sys/startup/inc/sys/bootargs.h`). No callable interface is exposed to the next stage.

### 5.3 Secure monitor (secmon)

The secure monitor protects critical hardware resources and sensitive material from access by the non-secure world. It acts as a secure-world mediator, similar to an internal secure element, manages security-critical hardware peripherals such as Optiga and Tropic, and provides secure storage. It also exposes a limited API to privileged firmware components.

The secure monitor relies on ARMv8-M security extensions to provide system-wide isolation by partitioning hardware and software resources into secure and non-secure worlds. Cortex-M33 duplicates selected system resources (for example, the interrupt controller, SysTick timer, and MPU) and allows access to virtually any MCU peripheral to be restricted by security state.

For coarse-grained memory partitioning, the SAU (Secure Attribution Unit) is used. Its principle is similar to the MPU: it defines memory regions that belong to the secure or non-secure world.

![SAU attribution](sau.drawio.svg)

All bus transactions on Cortex-M33, including transactions that do not pass through the SAU and MPU (for example, DMA transfers), are marked with privilege and security attributes (HPRIV and HNONSEC signals). STM32U5 peripherals process these signals to enforce finer-grained access control.

![TrustZone peripheral attribution](trustzone-periph.drawio.svg)

With appropriate configuration, the secure world is accessible from the non-secure world only through well-defined interfaces. Transitions between secure and non-secure worlds can be performed only through dedicated mechanisms, including Secure Gateway (SG).

![TrustZone transitions](trustzone-transitions.drawio.svg)

### 5.3.1 Secmon Drivers
The secure monitor implements drivers for security-critical hardware peripherals. These drivers are initialized at startup (`core/embed/projects/secmon/main.c`) before execution transfers to the kernel.

Secmon driver source code is located under `core/embed/sec`. The following table summarizes the drivers by area:

| Area | Drivers |
| --- | --- |
| Secure elements | Optiga and Tropic drivers, MCU attestation, and secret handling |
| Hardware acceleration | RNG, HASH, and SAES peripheral drivers |
| Storage | Secure storage and backup RAM drivers |
| Attack detection and mitigation | Tamper handling, consumption masking, and random delays |
| Utilities | Board capabilities, hardware revision, firmware utilities, and unit properties |

Each driver exposes an API; a subset of this functionality is available to other firmware components through the secmon API.

### 5.3.2 Secmon API

The secmon API is exposed through so-called smcalls, which provide a controlled gateway between privileged non-secure firmware and secure-world services.

Adding a new smcall requires changes in four places under `core/embed/sys/smcall`:
- `stm32/smcall_numbers.h` - declares unique smcall IDs
- `stm32/smcall_invoke.h` - declares the callable interface used by non-secure privileged code
- `stm32/smcall_dispatch.c` - dispatches the smcall in the secure world and calls the secmon implementation
- `stm32/smcall_verifiers.c` - validates arguments before the secure-world implementation is executed

The kernel calls the smcall interface rather than invoking secure-world implementations directly. The call is translated into a secure-world transition and passes a limited number of arguments through a well-defined calling convention.

The dispatcher runs in the secure world. It routes each smcall by number to the corresponding secure-world implementation or verifier function.

From a security perspective, verifiers are the most important component. They validate arguments passed from the non-secure world and reject the smcall if the arguments are invalid, for example if references do not originate from an allowed memory region or the caller does not have the required privileges.

The secure monitor API provides the following functions:

| Functions | Description |
| --- | --- |
| `bootargs_*` | Reads and updates boot arguments shared across boot stages. |
| `boot_image_*` | Checks or replaces boot images during secure boot and upgrade flows. |
| `reboot_*` | Performs controlled reboot and power-state transitions. |
| `suspend_*` | Suspends secure drivers and related secure-world state. |
| `resume_*` | Resumes secure drivers and related secure-world state. |
| `get_board_*` | Returns board identification and boardloader version information. |
| `unit_properties_*` | Returns provisioned unit properties such as serial-number-related metadata. |
| `wait_random` | Applies timing-randomization mechanisms. |
| `random_delays_*` | Applies random-delay policy mechanisms. |
| `rng_*` | Fills buffers with random data from secure random sources. |
| `optiga_*` | Mediates access to Optiga secure-element operations. |
| `tropic_*` | Mediates access to Tropic secure-element operations. |
| `storage_*` | Performs secure storage lifecycle, key-value, and counter operations. |
| `firmware_*` | Returns firmware vendor information and computes firmware hashes. |
| `mcu_attestation_*` | Returns attestation certificates and produces attestation signatures. |
| `secret_*` | Accesses secret-related state. |
| `secret_key_*` | Accesses secure key material. |
| `backup_ram_*` | Reads and writes protected backup RAM state. |
| `telemetry_*` | Updates or reads secure telemetry maintained by secmon. |

For a detailed API description, see the header files, where each function is documented.

### 5.4 Kernel
The kernel allows isolated unprivileged tasks to run with restricted access to system resources. It provides cooperative multitasking for the simultaneous execution of multiple unprivileged applications, implements peripheral drivers, and exposes a limited API to unprivileged applications.

The kernel utilizes Cortex-M privileged/unprivileged modes. Kernel code, including interrupt handlers, always runs in privileged mode. When the kernel transfers execution to an application, it switches to unprivileged mode. Unprivileged applications can access only their dedicated memory and use the SVC instruction to invoke syscalls (kernel API).

![Privilege mode transitions](priv-mode.drawio.svg)

The kernel uses the MPU to enforce strict isolation between the privileged kernel domain and unprivileged app domains. If an application attempts to access a memory address it is not permitted to access, a MemFault exception is raised and the device enters RSOD.

![MPU model](mpu.drawio.svg)

Because the Cortex-M33 MPU configuration provides only eight banks, which is insufficient for the full runtime model, MPU regions are reconfigured according to the currently executing code path (see `core/embed/sys/mpu/stm32u5/mpu.c`).

### 5.4.1 Kernel Drivers

The kernel implements drivers for hardware peripherals, initialized at startup (`core/embed/projects/kernel/main.c`) before execution transfers to unprivileged applications.

Kernel driver source code is located in the `core/embed/io` folder. The following table summarizes the drivers by area:

| Area | Contents |
| --- | --- |
| User interface | Display, Touch, Buttons, Haptics, RGB LED, Backlight |
| Hardware acceleration | JPEG decoder, DMA2D |
| Communication | USB, Bluetooth |
| Storage | SD card, Assets |
| Other | Power management |


Each driver exposes an API; a subset of driver functionality is available to unprivileged applications through the kernel API.

### 5.4.2 Cooperative multitasking

The kernel implements a cooperative multitasking scheduler. Although the system uses independent tasks, each with its own stack and dedicated memory, it follows a single-threaded execution model — only one task runs at a time. Tasks are not preemptively switched; each task must yield before another task can run. The kernel itself also runs as a task within this model; unlike application tasks, it always executes in privileged mode and has unrestricted access to system resources.

For task API see `core/embed/sys/task/inc/sys/systask.h`.

Peripheral interrupts run asynchronously on top of cooperative multitasking. In interrupt context, the kernel can stop a running task, for example if it becomes unresponsive, and release its resources.

At the center of cooperative multitasking is a global event loop. Each task polls for the events it is interested in and is awakened by the kernel when relevant events occur (see `core/embed/sys/task/inc/sys/sysevent.h`).

Because of cooperative multitasking, multiple unprivileged applications can run concurrently. They can use kernel syscalls to communicate with the kernel and IPC (see `core/embed/sys/ipc/inc/sys/ipc.h`) to communicate with one another.

### 5.4.3 Kernel API

The kernel API is exposed through syscalls implemented using the ARM Cortex-M SVC instruction. Syscalls provide a controlled gateway between unprivileged applications and the kernel.

Adding a new syscall requires changes in four places under `core/embed/sys/syscall`:
- `inc/sys/syscall_numbers.h` - declares unique syscall IDs
- `stm32/syscall_stubs.c` - provides the unprivileged entry point and translates the C call into an SVC instruction
- `stm32/syscall_dispatch.c` - dispatches the syscall in privileged mode and calls the kernel API implementation
- `stm32/syscall_verifiers.c` - validates arguments before the kernel API implementation is executed

Unprivileged applications link against `syscall_stubs.c`. They can include the kernel driver API header, but they do not call the kernel implementation directly. Instead, they invoke stub functions with the same arguments as the corresponding kernel API. The stubs translate the C call into an SVC instruction and pass a limited number of arguments in well-defined registers.

The dispatcher runs in privileged mode. It routes each syscall by number to the corresponding kernel API implementation or verifier function.

From a security perspective, verifiers are the most important component. They validate arguments passed to APIs invoked from the unprivileged world and reject the syscall if the arguments are invalid, for example if references do not originate from the unprivileged world or the caller does not have the required access privileges.


The kernel API provides the following functions:

| Functions | Description |
| --- | --- |
| `system_*` | Handles task exit and failure conditions. |
| `systick_*` | Returns time and cycle counters. |
| `sysevents_poll` | Polls task events. |
| `syshandle_*` | Accesses system handles. |
| `notify_send` | Sends notifications. |
| `dbg_console_*` | Provides debug-console access. |
| `syslog_*` | Provides system logging. |
| `ipc_*` | Exchanges IPC messages. |
| `display_*` | Controls display output. |
| `usb_*` | Controls USB communication. |
| `sdcard_*` | Accesses the SD card. |
| `touch_*` | Reads touch input. |
| `button_*` | Reads button input. |
| `rgb_led_*` | Controls the RGB LED. |
| `haptic_*` | Controls haptic feedback. |
| `ble_*` | Controls BLE communication. |
| `nrf_*` | Controls the nRF coprocessor. |
| `pm_*` | Controls power management. |
| `jpegdec_*` | Controls the JPEG decoder. |
| `dma2d_*` | Controls DMA2D acceleration. |
| `translations_*` | Manages UI translations. |
| `app_arena_*` | Manages the application arena. |
| `app_image_*` | Manages application images. |

As part of the kernel API there are also functions implemented in the secure monitor. Since the unprivileged app cannot call the secure monitor directly, this part of the API serves as trampolines to the secure world.

| Functions | Description |
| --- | --- |
| `boot_image_*` | Checks or replaces boot images during secure boot and upgrade flows. |
| `reboot_*` | Performs controlled reboot and power-state transitions. |
| `rng_*` | Fills buffers with random data from secure random sources. |
| `telemetry_*` | Updates or reads secure telemetry maintained by secmon. |
| `firmware_*` | Returns firmware vendor information and computes firmware hashes. |
| `optiga_*` | Mediates access to Optiga secure-element operations. |
| `tropic_*` | Mediates access to Tropic secure-element operations. |
| `mcu_attestation_*` | Returns attestation certificates and produces attestation signatures. |
| `secret_*` | Accesses secret-related state and security-policy decisions. |
| `secret_key_*` | Accesses secure key material through the secure-world interface. |
| `storage_*` | Performs secure storage lifecycle, key-value, and counter operations. |
| `unit_properties_*` | Returns provisioned unit properties such as serial-number-related metadata. |

For a detailed API description, see the header files, where each function is documented.

### 5.5 Core application (coreapp)

Most of Trezor's application logic resides in coreapp, which runs in unprivileged mode with tightly limited access to hardware. Coreapp implements the communication stack, renders the user interface, processes touch and button input, and contains the business-logic workflows.

Coreapp has access only to its dedicated flash and SRAM regions and must use kernel syscalls to communicate with privileged or secure-world services. Because it renders the UI, it also has direct access to the SRAM framebuffers.

_Note: while coreapp is limited in terms of hardware privilege, the kernel (and transitively secmon) allows it to call essentially
any privileged APIs. This means in particular that coreapp can ask for access to raw secrets and will just get them. We are gradually improving the separation of layers in this regard._

Coreapp exposes two APIs to third-party applications: a direct-call API and an IPC API, both described in the following chapter.

### 5.6 Third-party applications

Third-party applications allow external developers to run their own code or add-ons on Trezor hardware in a controlled and isolated manner.

Third-party applications are not intended to be general-purpose applications; their primary purpose is to support alternative cryptocurrencies that are not implemented in coreapp.

Accordingly, the interfaces exposed to third-party applications are intentionally narrow and limited to this use case.

#### 5.6.1 Application lifecycle

Third-party application code is executed from SRAM. The portion of SRAM reserved for these applications is called the **application arena**. Currently, only one application can be loaded into the application arena at a time.

Application lifecycle can be described by a simple diagram:

![App Lifecycle](app-lifecycle.drawio.svg)

**LOADING:** The kernel allocates a slot in the arena and validates the application header (magic number, size, and ABI version). The payload is then received in chunks — each chunk is verified against a SHA-256 hash chain anchored to the expected payload hash stored in the header. Once all chunks have been written, the payload is checked for structural integrity (segment bounds, relocation table, entry point). On success the image transitions to READY.

**READY:** The image is fully received and its integrity has been verified. The writable memory region (RW data, stack, and heap) occupies the tail of the same pre-allocated arena block but is not yet initialized. The image can be started or deleted.

**RUNNING:** When the application is started, the RW segment's initialized data is copied from the init-data section embedded in the read-only payload, and position-independent relocations are applied. An applet task is then created with the specified entry point and stack. When the application stops, the entire writable region is zeroed to remove any sensitive data before the arena slot is reused.

For more information, see `core/embed/io/app_arena`.

#### 5.6.2 Kernel syscall limitation

Third-party applications have access only to a limited subset of the kernel API and can invoke only a restricted set of syscalls.

Unlike coreapp, third-party applications cannot draw directly to the display and have no access to the framebuffers. Instead, they can use the coreapp IPC API to request specific screens, which can be customized through the provided parameters.

Third-party apps can only use the following syscalls:

_TODO: list of allowed syscalls to be added._

#### 5.6.3 Coreapp direct-call API

To minimize third-party application size, these applications can reuse selected functions from coreapp. When a third-party application is running, the MPU is configured to allow calls into coreapp.

Only functions that do not depend on coreapp global variables can be reused, because those variables are not visible to third-party applications. Likewise, coreapp functions that invoke syscalls unavailable to third-party applications cannot be called.

The direct-call API is well suited to functions that operate solely on data within the third-party application's own context, such as utility or cryptographic functions.

When the kernel starts a third-party application (calls its `applet_main()`), it passes a getter for the direct-call API.

```c
typedef void* (*trezor_api_getter_t)(uint32_t version);

void applet_main(trezor_api_getter_t api_getter);
```

A third-party app can call the `api_getter()` function to retrieve a pointer
to a structure that defines the callable functions — the so-called direct-call API (for more details see `core/embed/api/trezor_api_v1.h`).

There is no mechanism preventing a third-party app from calling unexposed APIs, or indeed any part of coreapp code. Doing so is unsupported -- function addresses may change between firmware upgrades. Any such invocation operates within the memory space of the third-party app. Legitimate apps are forbidden from doing this by the application review guidelines.

##### Thread-local storage workaround
 The global-variable limitation can be partially overcome by placing a small number of variables in a TLS (thread-local storage) section located at a fixed SRAM address. This section belongs to a single task, and its contents are swapped during task switches, which allows a limited form of task-local "global" state while keeping ownership with the calling application. For example, this mechanism is used for the `__stack_chk_guard` variable, which is accessed by nearly every coreapp function because GCC's stack protector is enabled.


#### 5.6.4 Coreapp IPC API

Because direct-call API functions cannot use coreapp global state or invoke syscalls that are unavailable to third-party applications, coreapp also provides an IPC API for these cases. This API is used to invoke functions that cannot be executed in the context of a third-party application, such as signing with keys that must not be exposed to the application or rendering the user interface on the display.

The coreapp IPC API uses the IPC mechanism provided by the kernel:
- An application task can send an IPC message to another task by calling `ipc_send()`. This function copies an arbitrary payload, including IPC call arguments, into the recipient task's address space.
- An application task can wait for an incoming IPC message using the standard polling mechanism. Once the message is signaled, the application can call `ipc_try_receive()` to retrieve it.

The IPC handler in coreapp is implemented in MicroPython, in `core/src/apps/trezorapp/run.py`.

Each IPC call is identified by a _service_ and a _message id_. The following services are currently supported:

##### (0) Lifecycle service

Coreapp may send a cancellation request to the third-party app. The app should respond by stopping any pending operations and fully unwinding its stack. If it does not respond within a set time, a kernel watchdog will terminate the app.

##### (1) UI service

The third-party app can request displaying one of several predefined screens, and provide their parameters. The coreapp will handle the UI lifecycle and respond with a single result code.

The parameters for the UI are serialized in a `rkyv` binary format, and passed through the MicroPython layer into the Rust UI implementation. That decodes the parameters, constructs the appropriate UI object, and returns it back to MicroPython for handling.

##### (2) Wire service

Third-party apps need to be able to communicate with the host. The wire service acts as an intermediary, and abstract away the difference between the actual transports (USB or Bluetooth).

A third-party app receives and sends back tuples of `(message_type: int, message_payload: bytes)`. Coreapp does not examine contents of the payload. It embeds it in a wrapper message, which gets sent out to the host; and conversely, a message from the host for the app is unwrapped and its binary contents passed on to the app. This way, a third-party app cannot write raw messages to the wire and cause confusion on the host side, and also cannot learn contents of messages not intended for it.

For legitimate apps, the app review guidelines prescribe a codec for converting structured messages to and from the binary payload.

##### (3) Crypto service

Multiple different cryptographic operations with private keys are exposed via this service. An app can generally request (a) a public key on a certain BIP-32 / SLIP-10 path and curve, and (b) a signature of a digest, by a key living on a certain BIP-32 / SLIP-10 path.

The list of allowed path prefixes is pre-registered and signed in the app metadata. By default, requested paths outside the pre-registered prefixes will be rejected.

Trezor has a user setting for permanently or temporarily allowing unsanctioned path access: if this setting is enabled, **and** the app metadata carries a special entitlement, the app can request access to any path. Any such access is gated by a user confirmation dialog automatically displayed by the coreapp.

A different entitlement allows an app to request direct access to a private key on a specified derivation path. The entitlements for "any path" and "direct key access" are mutually exclusive, and exported private keys are always subject to prefix restrictions.

##### (4) Progress service

Separate from the UI screen service, the app can indicate progress of a long-running operation by pinging this IPC service with either a percentage or a generic uncounted progress step signal. The coreapp takes care of displaying a progress bar and handles its interaction with any other UI elements.

##### (5) Error service

In addition to app-specific messages sent over the wire, the third party app can return an error, which gets forwarded to the host. An error signal consists of a _code_ out of a fixed list, and a string _message_. Errors should be sent by this mechanism,
so that they are understandable as errors without needing to decode the app-specific payload format.
