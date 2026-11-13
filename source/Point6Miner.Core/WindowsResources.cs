using System.Runtime.InteropServices;

namespace Point6Miner.Core;

/// <summary>Read-only Win32 measurements. No WMI, drivers, elevation or fabricated temperatures.</summary>
public sealed class WindowsResources
{
    private (ulong Idle, ulong Kernel, ulong User)? previous;

    public static IReadOnlyList<string> GraphicsDescriptions()
    {
        List<string> names = [];
        if (!OperatingSystem.IsWindows()) return names;
        for (uint index = 0; index < 32; index++)
        {
            DisplayDevice device = new() { Size = (uint)Marshal.SizeOf<DisplayDevice>() };
            if (!EnumDisplayDevices(null, index, ref device, 0)) break;
            if ((device.Flags & 1) != 0 && !string.IsNullOrWhiteSpace(device.Description)) names.Add(device.Description);
        }
        return names.Distinct().ToArray();
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct DisplayDevice
    {
        public uint Size;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string Name;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string Description;
        public uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string Id;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string Key;
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumDisplayDevices(string? name, uint index, ref DisplayDevice device, uint flags);

    public ResourceSample Read()
    {
        if (!OperatingSystem.IsWindows()) return new(DateTimeOffset.UtcNow, null, null, null,
            null, null, null, null, null, "unavailable: Windows APIs require Windows");
        double? cpu = null, available = null, disk = null;
        if (Environment.ProcessorCount <= 64 && GetSystemTimes(out ulong idle, out ulong kernel, out ulong user))
        {
            if (previous is { } old && idle >= old.Idle && kernel >= old.Kernel && user >= old.User)
            {
                ulong total = (kernel - old.Kernel) + (user - old.User);
                ulong idleDelta = idle - old.Idle;
                if (total > 0 && idleDelta <= total) cpu = (total - idleDelta) * 100.0 / total;
            }
            previous = (idle, kernel, user);
        }
        MemoryStatus memory = new() { Length = (uint)Marshal.SizeOf<MemoryStatus>() };
        if (GlobalMemoryStatusEx(ref memory)) available = memory.AvailablePhysical / Math.Pow(1024, 3);
        string root = Path.GetPathRoot(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)) ?? "C:\\";
        if (GetDiskFreeSpaceEx(root, out ulong callerAvailable, out _, out _)) disk = callerAvailable / Math.Pow(1024, 3);
        return new(DateTimeOffset.UtcNow, cpu, available, disk, null, null, null, null, null,
            "Win32 passive readings; temperature/GPU/throttling unavailable");
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct MemoryStatus
    {
        public uint Length, MemoryLoad;
        public ulong TotalPhysical, AvailablePhysical, TotalPageFile, AvailablePageFile,
            TotalVirtual, AvailableVirtual, AvailableExtendedVirtual;
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetSystemTimes(out ulong idle, out ulong kernel, out ulong user);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GlobalMemoryStatusEx(ref MemoryStatus status);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetDiskFreeSpaceEx(string directory, out ulong available, out ulong total, out ulong free);
}
