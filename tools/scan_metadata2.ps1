$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public class MemScan2 {
    [DllImport("kernel32.dll")] public static extern IntPtr OpenProcess(int access, bool inherit, int pid);
    [DllImport("kernel32.dll")] public static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out IntPtr read);
    [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32.dll")] public static extern void GetSystemInfo(out SYSTEM_INFO si);

    [StructLayout(LayoutKind.Sequential)]
    public struct SYSTEM_INFO {
        public ushort wProcessorArchitecture;
        public ushort wReserved;
        public uint dwPageSize;
        public IntPtr lpMinimumApplicationAddress;
        public IntPtr lpMaximumApplicationAddress;
        public IntPtr dwActiveProcessorMask;
        public uint dwNumberOfProcessors;
        public uint dwProcessorType;
        public uint dwAllocationGranularity;
        public ushort wProcessorLevel;
        public ushort wProcessorRevision;
    }

    public static List<ulong> Scan(int pid, byte[] pattern, long minAddr, long maxAddr) {
        var hits = new List<ulong>();
        IntPtr h = OpenProcess(0x0410, false, pid);
        if (h == IntPtr.Zero) throw new Exception("OpenProcess failed: " + Marshal.GetLastWin32Error());
        try {
            byte[] buf = new byte[4 << 20];
            for (long addr = minAddr; addr < maxAddr; addr += buf.Length) {
                IntPtr got;
                if (!ReadProcessMemory(h, new IntPtr(addr), buf, buf.Length, out got)) continue;
                int n = (int)got;
                for (int i = 0; i <= n - pattern.Length; i++) {
                    bool ok = true;
                    for (int j = 0; j < pattern.Length; j++) {
                        if (buf[i + j] != pattern[j]) { ok = false; break; }
                    }
                    if (ok) hits.Add((ulong)(addr + i));
                }
            }
        } finally { CloseHandle(h); }
        return hits;
    }

    public static byte[] ReadBytes(int pid, ulong addr, int size) {
        IntPtr h = OpenProcess(0x0410, false, pid);
        if (h == IntPtr.Zero) return null;
        try {
            byte[] buf = new byte[size];
            IntPtr got;
            if (!ReadProcessMemory(h, new IntPtr((long)addr), buf, size, out got)) return null;
            if ((int)got < size) Array.Resize(ref buf, (int)got);
            return buf;
        } finally { CloseHandle(h); }
    }
}
'@

$p = Get-Process | Where-Object { $_.ProcessName -like '*Umamusume*' } | Select-Object -First 1
if (-not $p) { Write-Output "game-not-running"; exit 1 }
Write-Output ("PID=" + $p.Id + "  WorkingSet=" + [math]::Round($p.WorkingSet64/1MB) + "MB")

$si = New-Object MemScan2+SYSTEM_INFO
[MemScan2]::GetSystemInfo([ref]$si)
$min = $si.lpMinimumApplicationAddress.ToInt64()
$max = $si.lpMaximumApplicationAddress.ToInt64()
Write-Output ("scan-range: 0x{0:x} .. 0x{1:x}" -f $min, $max)

$pat = [byte[]](0xAF, 0x1B, 0xB1, 0xFA)   # 0xFAB11BAF little-endian
$sw = [Diagnostics.Stopwatch]::StartNew()
$hits = [MemScan2]::Scan($p.Id, $pat, $min, $max)
$sw.Stop()
Write-Output ("sanity-hits: " + $hits.Count + "  elapsed=" + [math]::Round($sw.Elapsed.TotalSeconds,1) + "s")

for ($k = 0; $k -lt [Math]::Min($hits.Count, 8); $k++) {
    $a = $hits[$k]
    Write-Output ("  [hit " + $k + "] 0x{0:x}" -f $a)
    $bytes = [MemScan2]::ReadBytes($p.Id, $a, 256)
    if ($bytes) {
        $ver = [BitConverter]::ToInt32($bytes, 4)
        $hex = ($bytes[0..31] | ForEach-Object { $_.ToString('x2') }) -join ' '
        Write-Output ("      version=" + $ver + "  head=" + $hex)
        if ($ver -eq 31 -and $bytes.Length -ge 0x80) {
            $off = [BitConverter]::ToUInt32($bytes, 8)
            $size = [BitConverter]::ToUInt32($bytes, 12)
            Write-Output ("      field0=0x{0:x} field1=0x{1:x}" -f $off, $size)
        }
    }
}
