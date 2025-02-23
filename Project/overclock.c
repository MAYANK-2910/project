#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
  #include <windows.h>
  #define EXPORT __declspec(dllexport)
#else
  #include <sys/io.h>
  #define EXPORT
#endif

#define MSR_OC_BASE 0x199
#define PORT_PROTECT 0xCF8
#define PORT_DATA    0xCFC

// Export the function so that ctypes can find it.
EXPORT void set_cpu_multiplier(int core, int multiplier) {
#ifdef _WIN32
    // Windows does not provide iopl() or outl() in user mode.
    // You would need a kernel mode driver to perform low-level port I/O.
    MessageBoxA(NULL, "Direct I/O not supported in user mode.", "Error", MB_OK);
    exit(EXIT_FAILURE);
#else
    unsigned long msr = MSR_OC_BASE + core;
    unsigned long value = (multiplier & 0xFF) | 0x10000;
    if (iopl(3) < 0) {
        perror("iopl");
        exit(EXIT_FAILURE);
    }
    outl(msr, PORT_PROTECT);
    outl(value, PORT_DATA);
#endif
}
