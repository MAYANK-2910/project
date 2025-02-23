#include <stdio.h>
#include <stdlib.h>
#include <sys/io.h>

#define MSR_OC_BASE 0x199
#define PORT_PROTECT 0xCF8
#define PORT_DATA    0xCFC

void set_cpu_multiplier(int core, int multiplier) {
    unsigned long msr = MSR_OC_BASE + core;
    unsigned long value = (multiplier & 0xFF) | 0x10000;
    
    // Requires root access
    if (iopl(3) < 0) {
        perror("iopl");
        exit(1);
    }
    
    outl(msr, PORT_PROTECT);
    outl(value, PORT_DATA);
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <core> <multiplier>\n", argv[0]);
        return 1;
    }
    
    int core = atoi(argv[1]);
    int multi = atoi(argv[2]);
    
    if (core < 0 || core > 15 || multi < 8 || multi > 255) {
        printf("Invalid parameters!\n");
        return 1;
    }
    
    printf("Setting core %d to %dx multiplier\n", core, multi);
    set_cpu_multiplier(core, multi);
    
    return 0;
}