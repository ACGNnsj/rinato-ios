#import "NativeProbe.h"

#include <errno.h>
#include <mach/mach.h>
#include <stdio.h>
#include <os/proc.h>
#include <pthread.h>
#include <setjmp.h>
#include <signal.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/sysctl.h>
#include <unistd.h>

#if __has_feature(ptrauth_calls)
#include <ptrauth.h>
#endif

// ---------------------------------------------------------------------------
// Fixed-value execution
//
// The value is assembled by real ARM64 instructions so the result can only come
// from executed code, never from a constant folded into the caller.
// ---------------------------------------------------------------------------

__attribute__((noinline))
static int64_t rinato_fixed_value_body(void) {
#if defined(__aarch64__)
    int64_t result;
    __asm__ volatile(
        "movz %0, #0xc0de\n\t"
        "movk %0, #0x5a17, lsl #16"
        : "=r"(result));
    return result;
#else
    return 0x5a17c0de;
#endif
}

// ---------------------------------------------------------------------------
// PAC / indirect call
// ---------------------------------------------------------------------------

__attribute__((noinline))
static int64_t rinato_pac_target(int64_t value) {
    return value ^ 0x11;
}

// ---------------------------------------------------------------------------
// JIT
//
// Calling unmapped or non-executable memory faults the process. A scoped
// signal guard turns that into a recorded failure instead of a silent crash,
// which is the only way to obtain the real error on a device we cannot attach to.
// ---------------------------------------------------------------------------

static sigjmp_buf gFaultJump;
static volatile sig_atomic_t gFaultArmed = 0;
static volatile sig_atomic_t gFaultSignal = 0;

static void RinatoFaultHandler(int signalNumber) {
    if (gFaultArmed) {
        gFaultArmed = 0;
        gFaultSignal = signalNumber;
        siglongjmp(gFaultJump, 1);
    }
    signal(signalNumber, SIG_DFL);
    raise(signalNumber);
}

@interface RinatoFaultGuard : NSObject
@end

@implementation RinatoFaultGuard
/// Returns YES only when every handler was accepted; a NO means a JIT fault
/// would kill the process instead of being reported.
+ (BOOL)install {
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = RinatoFaultHandler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = SA_NODEFER;
    BOOL ok = YES;
    ok = sigaction(SIGSEGV, &action, NULL) == 0 && ok;
    ok = sigaction(SIGBUS, &action, NULL) == 0 && ok;
    ok = sigaction(SIGILL, &action, NULL) == 0 && ok;
    return ok;
}
@end

/// Calls function(argument) and returns "ok", or reports the fault that stopped it.
/// AAPCS64 passes the argument in x0 and the result in x0, which is the convention
/// the game's own ARM64 code follows; a mismatched convention shows up as a fault here.
static NSString *RinatoCallGuarded(int64_t (*function)(int64_t), int64_t argument,
                                  int64_t *outValue) {
    gFaultSignal = 0;
    if (sigsetjmp(gFaultJump, 1) == 0) {
        gFaultArmed = 1;
        *outValue = function(argument);
        gFaultArmed = 0;
        return @"ok";
    }
    char text[96];
    snprintf(text, sizeof(text), "FAULT signal=%d (%s)", (int)gFaultSignal,
             strsignal((int)gFaultSignal));
    return [NSString stringWithUTF8String:text];
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

@interface NativeProbe ()
+ (void)probeIdentity:(void (^)(NSString *line))log;
+ (void)probeFixedValue:(void (^)(NSString *line))log;
+ (void)probePointerAuthentication:(void (^)(NSString *line))log;
+ (void)probeJit:(void (^)(NSString *line))log;
+ (void)probeMemory:(void (^)(NSString *line))log;
+ (void)probeDocuments:(void (^)(NSString *line))log;
@end

@implementation NativeProbe

+ (void)runAllWithLog:(void (^)(NSString *line))log {
    BOOL guarded = [RinatoFaultGuard install];
    log([NSString stringWithFormat:@"PROBE fault_guard=%@",
         guarded ? @"installed" : @"FAILED errno_not_checked"]);

    [self probeIdentity:log];
    [self probeFixedValue:log];
    [self probePointerAuthentication:log];
    [self probeJit:log];
    [self probeMemory:log];
    [self probeDocuments:log];
}

+ (void)probeIdentity:(void (^)(NSString *))log {
#if defined(__arm64e__)
    log(@"PROBE abi=arm64e");
#elif defined(__aarch64__)
    log(@"PROBE abi=arm64");
#else
    log(@"PROBE abi=other");
#endif
#if __has_feature(ptrauth_calls)
    log(@"PROBE ptrauth_compile=1");
#else
    log(@"PROBE ptrauth_compile=0");
#endif
    log(@"PROBE pointer_bits=%zu", sizeof(void *) * 8);

    int cpusubtype = 0;
    size_t subtypeSize = sizeof(cpusubtype);
    if (sysctlbyname("hw.cpusubtype", &cpusubtype, &subtypeSize, NULL, 0) == 0) {
        // CPU_SUBTYPE_ARM64E is 2; CPU_SUBTYPE_ARM64_ALL is 0.
        log(@"PROBE hw_cpusubtype=%d%s", cpusubtype, cpusubtype == 2 ? " (arm64e)" : "");
    } else {
        log(@"PROBE hw_cpusubtype=FAILED errno=%d strerror=\"%s\"", errno, strerror(errno));
    }

    int cputype = 0;
    size_t size = sizeof(cputype);
    if (sysctlbyname("hw.cputype", &cputype, &size, NULL, 0) == 0) {
        log(@"PROBE hw_cputype=0x%08x", (unsigned)cputype);
    } else {
        log(@"PROBE hw_cputype=FAILED errno=%d strerror=\"%s\"", errno, strerror(errno));
    }

    char machine[64] = {0};
    size = sizeof(machine);
    if (sysctlbyname("hw.machine", machine, &size, NULL, 0) == 0) {
        log(@"PROBE hw_machine=%s", machine);
    } else {
        log(@"PROBE hw_machine=FAILED errno=%d strerror=\"%s\"", errno, strerror(errno));
    }
    log(@"PROBE os_version=%s", NSProcessInfo.processInfo.operatingSystemVersionString.UTF8String);
}

+ (void)probeFixedValue:(void (^)(NSString *))log {
    // A volatile pointer keeps the compiler from folding the call away.
    int64_t (*volatile direct)(void) = rinato_fixed_value_body;
    int64_t value = direct();
    log(@"PROBE fixed_value=0x%llx", (unsigned long long)value);
    log(@"PROBE fixed_value_expected=0x%llx", (unsigned long long)0x5a17c0de);
    log(@"PROBE fixed_value_match=%s", value == 0x5a17c0de ? "yes" : "no");
}

+ (void)probePointerAuthentication:(void (^)(NSString *))log {
    int64_t (*target)(int64_t) = rinato_pac_target;
    int64_t (*volatile indirect)(int64_t) = target;

#if __has_feature(ptrauth_calls)
    void *signedPointer = ptrauth_sign_unauthenticated((void *)indirect,
                                                      ptrauth_key_function_pointer, 0);
    indirect = (int64_t (*)(int64_t))signedPointer;
    void *stripped = ptrauth_strip((void *)indirect, ptrauth_key_function_pointer);
    log(@"PROBE pac_sign=ok");
    log(@"PROBE pac_strip_match=%s", stripped == (void *)target ? "yes" : "no");
#else
    // A sideloaded app is built for arm64, where ptrauth instructions are not
    // emitted. The device may still be arm64e hardware; that is reported by
    // hw_cpusubtype. Signing is therefore not measurable from this slice.
    log(@"PROBE pac_sign=unsupported reason=compiled_slice_is_arm64_not_arm64e");
#endif

    int64_t value = 0;
    NSString *outcome = RinatoCallGuarded(indirect, 0x5a17c0de, &value);
    log(@"PROBE pac_indirect=%@ value=0x%llx", outcome, (unsigned long long)value);
    log(@"PROBE pac_indirect_expected=0x%llx",
        (unsigned long long)(0x5a17c0de ^ 0x11));
    log(@"PROBE pac_indirect_match=%s",
        [outcome isEqualToString:@"ok"] && value == (0x5a17c0de ^ 0x11) ? "yes" : "no");

    // Return-path check: the host receives a value produced by foreign code that
    // follows the plain AAPCS64 convention (what the game's ARM64 code uses).
    int64_t returned = 0;
    NSString *returnOutcome = RinatoCallGuarded(target, 0x11, &returned);
    log(@"PROBE pac_return=%@ value=0x%llx", returnOutcome, (unsigned long long)returned);
    log(@"PROBE pac_return_match=%s",
        [returnOutcome isEqualToString:@"ok"] && returned == 0 ? "yes" : "no");
}

+ (void)probeJit:(void (^)(NSString *))log {
    const size_t page = (size_t)getpagesize();

    // movz x0, #0x2a2a ; ret  -- returns 0x2a2a when it actually executes.
    uint32_t code[2] = {0xD2800000u | (0x2a2au << 5), 0xD65F03C0u};

    // Stage 1: classic RWX mapping.
    errno = 0;
    void *rwx = mmap(NULL, page, PROT_READ | PROT_WRITE | PROT_EXEC,
                     MAP_PRIVATE | MAP_ANON, -1, 0);
    if (rwx == MAP_FAILED) {
        log(@"PROBE jit_mmap=FAILED errno=%d strerror=\"%s\"", errno, strerror(errno));
    } else {
        log(@"PROBE jit_mmap=ok");
        memcpy(rwx, code, sizeof(code));
        int64_t value = 0;
        NSString *outcome = RinatoCallGuarded((int64_t (*)(int64_t))rwx, 0, &value);
        log(@"PROBE jit_mmap_call=%@ value=0x%llx", outcome, (unsigned long long)value);
        log(@"PROBE jit_mmap_call_expected=0x%x match=%s", 0x2a2a,
            [outcome isEqualToString:@"ok"] && value == 0x2a2a ? "yes" : "no");
        munmap(rwx, page);
    }

    // Stage 2: MAP_JIT + write-protect toggle, the path a JIT entitlement provides.
    errno = 0;
    void *jit = mmap(NULL, page, PROT_READ | PROT_WRITE | PROT_EXEC,
                     MAP_PRIVATE | MAP_ANON | MAP_JIT, -1, 0);
    if (jit == MAP_FAILED) {
        log(@"PROBE jit_map_jit=FAILED errno=%d strerror=\"%s\"", errno, strerror(errno));
    } else {
        log(@"PROBE jit_map_jit=ok");
#if defined(__APPLE__) && defined(MAP_JIT)
        if (@available(iOS 14.0, *)) {
            pthread_jit_write_protect_np(0);
        }
#endif
        memcpy(jit, code, sizeof(code));
#if defined(__APPLE__) && defined(MAP_JIT)
        if (@available(iOS 14.0, *)) {
            pthread_jit_write_protect_np(1);
        }
#endif
        int64_t value = 0;
        NSString *outcome = RinatoCallGuarded((int64_t (*)(int64_t))jit, 0, &value);
        log(@"PROBE jit_map_jit_call=%@ value=0x%llx", outcome, (unsigned long long)value);
        log(@"PROBE jit_map_jit_call_expected=0x%x match=%s", 0x2a2a,
            [outcome isEqualToString:@"ok"] && value == 0x2a2a ? "yes" : "no");
        munmap(jit, page);
    }
}

+ (void)probeMemory:(void (^)(NSString *))log {
    unsigned long long physical = NSProcessInfo.processInfo.physicalMemory;
    log(@"PROBE mem_physical=%llu", physical);

    size_t available = 0;
    if (@available(iOS 13.0, *)) {
        available = os_proc_available_memory();
    }
    if (available > 0) {
        log(@"PROBE mem_available=%zu", available);
    } else {
        log(@"PROBE mem_available=FAILED reason=os_proc_available_memory_returned_0");
    }

    task_vm_info_data_t info;
    mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    kern_return_t status = task_info(mach_task_self(), TASK_VM_INFO,
                                     (task_info_t)&info, &count);
    if (status == KERN_SUCCESS) {
        log(@"PROBE mem_footprint=%llu", (unsigned long long)info.phys_footprint);
        log(@"PROBE mem_resident=%llu", (unsigned long long)info.resident_size);
    } else {
        log(@"PROBE mem_footprint=FAILED kern_return=%d", (int)status);
    }

    // Bounded allocation: at most a quarter of what the system says is available,
    // hard-capped so the probe cannot itself provoke jetsam.
    const size_t step = 16u * 1024u * 1024u;
    const size_t hardCap = 256u * 1024u * 1024u;
    size_t budget = available > 0 ? available / 4 : 32u * 1024u * 1024u;
    if (budget > hardCap) {
        budget = hardCap;
    }
    log(@"PROBE mem_alloc_budget=%zu", budget);

    size_t allocated = 0;
    while (allocated + step <= budget) {
        void *block = mmap(NULL, step, PROT_READ | PROT_WRITE,
                           MAP_PRIVATE | MAP_ANON, -1, 0);
        if (block == MAP_FAILED) {
            log(@"PROBE mem_alloc=FAILED allocated=%zu errno=%d strerror=\"%s\"",
                allocated, errno, strerror(errno));
            return;
        }
        // Touch one word per page so the pages are actually committed.
        for (size_t offset = 0; offset < step; offset += (size_t)getpagesize()) {
            ((volatile char *)block)[offset] = 1;
        }
        munmap(block, step);
        allocated += step;
    }
    log(@"PROBE mem_alloc=ok budget=%zu allocated=%zu", budget, allocated);
}

+ (void)probeDocuments:(void (^)(NSString *))log {
    NSFileManager *manager = NSFileManager.defaultManager;
    NSURL *documents = [manager URLsForDirectory:NSDocumentDirectory
                                       inDomains:NSUserDomainMask].firstObject;
    if (documents == nil) {
        log(@"PROBE documents=FAILED reason=no_document_directory");
        return;
    }
    NSURL *probe = [documents URLByAppendingPathComponent:@"probe-write-test.txt"];
    BOOL wrote = [@"rinato" writeToURL:probe
                            atomically:YES
                              encoding:NSUTF8StringEncoding
                                 error:NULL];
    BOOL removed = [manager removeItemAtURL:probe error:NULL];
    log(@"PROBE documents=%@ writable=%s", wrote ? "ok" : "FAILED",
        wrote && removed ? "yes" : "no");
}

@end
