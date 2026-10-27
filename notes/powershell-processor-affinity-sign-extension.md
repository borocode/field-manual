# PowerShell: Why `.ProcessorAffinity` Fails with `"The parameter is incorrect"` on Bit 31 (`0x80000000`)

## 1. The Problem
On a 16-core / 32-thread Windows system (logical processors 0 through 31), we wanted to pin a noisy background service to the last two logical processors (threads 30 and 31, bitmask `0xC0000000`) using PowerShell:

```powershell
$proc.ProcessorAffinity = [IntPtr]0xC0000000
```

Instead of pinning the process, PowerShell threw:

```text
Exception setting "ProcessorAffinity": "The parameter is incorrect"
```

However, changing the mask to threads 28 and 29 (`[IntPtr]0x30000000`) worked immediately without error.

## 2. Environment
* **OS:** Windows 11 (64-bit)
* **CPU:** 16 cores / 32 logical processors (valid system affinity mask: `0x00000000FFFFFFFF`)
* **Shells Tested:**
  * Windows PowerShell 5.1 (64-bit and 32-bit `SysWOW64`)
  * PowerShell 7 (`pwsh`, 64-bit)

## 3. What Was Observed

### Disproven Initial Hypothesis: 32-Bit WOW64 Target Process
Because the target background binary was a 32-bit WOW64 process, our first hypothesis was that Windows or .NET rejected bit 31 (`0x80000000`) specifically when setting affinity on a 32-bit WOW64 process.

When we tested `[IntPtr]0xC0000000` on a native **64-bit** PowerShell process, however, it failed with the exact same error:

```powershell
$p = [System.Diagnostics.Process]::GetCurrentProcess()
$p.ProcessorAffinity = [IntPtr]0xC0000000
# Exception setting "ProcessorAffinity": "The parameter is incorrect"
```

### Actual Root Cause: Signed 32-Bit Hex Parsing + 64-Bit `IntPtr` Sign Extension
Inspecting how PowerShell parses `0xC0000000` and converts it to `[IntPtr]` revealed the real mechanism:

```powershell
PS> (0xC0000000).GetType().FullName
System.Int32

PS> 0xC0000000
-1073741824

PS> "0x{0:X16}" -f ([IntPtr]0xC0000000).ToInt64()
0xFFFFFFFFC0000000
```

1. In PowerShell, an unsuffixed hex literal from `0x80000000` to `0xFFFFFFFF` has bit 31 set, so PowerShell parses it as a **negative 32-bit signed integer (`System.Int32`)**.
2. In a 64-bit PowerShell session (`[IntPtr]::Size -eq 8`), casting `[IntPtr]0xC0000000` invokes the `IntPtr(int value)` constructor, which **sign-extends** the negative 32-bit integer into a 64-bit value: `0xFFFFFFFFC0000000`.
3. When `.ProcessorAffinity` passes `0xFFFFFFFFC0000000` to Win32 `SetProcessAffinityMask`, bits **32 through 63** are all set to `1`.
4. On a 32-logical-processor CPU, logical processors 32–63 do not exist (the system affinity mask is `0x00000000FFFFFFFF`). `SetProcessAffinityMask` rejects any mask containing bits outside the system affinity mask with `ERROR_INVALID_PARAMETER` (`"The parameter is incorrect"`).

Why did `0x30000000` work? Because bit 31 is `0`, so `0x30000000` parses as a positive `System.Int32` (`805306368`) and zero-extends to `0x0000000030000000`.

## 4. What Helped

Append the **`L` suffix** (`0xC0000000L` or `0x80000000L`) so PowerShell parses the literal as a 64-bit `System.Int64` (`3221225472`) before casting to `[IntPtr]`:

```powershell
PS> "0x{0:X16}" -f ([IntPtr]0xC0000000L).ToInt64()
0x00000000C0000000
```

We verified that `[IntPtr]0xC0000000L` succeeds from 64-bit PowerShell on **both** 64-bit processes and 32-bit WOW64 processes:

```powershell
# Verified working on both 64-bit and 32-bit WOW64 target processes:
$proc.ProcessorAffinity = [IntPtr]0xC0000000L
```

### Rollback
To restore a process to all available logical processors in its current processor group (up to 64):

```powershell
$count = [Math]::Min([Environment]::ProcessorCount, 64)
$fullMask = if ($count -eq 64) { [IntPtr](-1L) } else { [IntPtr]((1L -shl $count) - 1L) }
$proc.ProcessorAffinity = $fullMask
```

## 5. Limits
* **32-Bit PowerShell Sessions (`SysWOW64`):** In a 32-bit PowerShell process (`[IntPtr]::Size -eq 4`), `[IntPtr]` is 32 bits wide, so `[IntPtr]0xC0000000` works without `L`, while `[IntPtr]0xC0000000L` throws `Arithmetic operation resulted in an overflow` because `3221225472` exceeds `Int32.MaxValue`. If a script must run in both 32-bit and 64-bit hosts, construct the mask safely or check `[Environment]::Is64BitProcess`.
* **Systems With >64 Logical Processors:** Windows systems with more than 64 logical processors use multiple Processor Groups (`SetThreadGroupAffinity` / `GetProcessGroupAffinity`). `.ProcessorAffinity` only operates on the process's current processor group (up to 64 logical processors) and bit 63 (`0x8000000000000000`) is still signed in `Int64`.
* **Permissions:** Changing `.ProcessorAffinity` on an elevated or `LocalSystem` service requires running PowerShell as Administrator; otherwise .NET throws `Access is denied`.

## Related Field Notes
* [Single-GPU Dynamic VFIO Passthrough: Hardware Topology & Driver Rebinding](single-gpu-vfio-passthrough-architecture.md) — CPU core masking and CCX chiplet pinning in virtualization.
* [NVENC Hardware Encoding Architecture & Session Starvation](nvenc-hardware-encoding-architecture.md) — Process resource allocation and driver management.

## 6. Sources & Credit
* [Microsoft Docs: `Process.ProcessorAffinity` Property](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.processoraffinity)
* [Microsoft Win32 Docs: `SetProcessAffinityMask` Function (`ERROR_INVALID_PARAMETER` behavior)](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setprocessaffinitymask)
* [PowerShell Language Specification: Integer Literals & Type Suffixes](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_numeric_literals)
