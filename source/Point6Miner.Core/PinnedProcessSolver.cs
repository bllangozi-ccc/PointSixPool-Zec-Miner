using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;

namespace Point6Miner.Core;

public sealed record SolverProcessLimits(int WallSeconds = 120, int CpuSeconds = 110, int MemoryMiB = 2048, int Threads = 1)
{
    internal void Validate()
    {
        if (WallSeconds is < 1 or > 300 || CpuSeconds is < 1 or > 120 || MemoryMiB is < 64 or > 2048 || Threads is < 1 or > 16)
            throw new ArgumentException("Solver limits exceed this private CPU test backend's bounds (1–16 threads).");
    }
}

// Explicit backend only: no shell or free-form command arguments, checked hash,
// verified CPU affinity, bounded process budgets and cancellation of its tree.
public sealed class PinnedProcessSolver : IMiningWorkSolver
{
    private readonly string path;
    private readonly byte[] expectedHash;
    private readonly SolverProcessLimits limits;
    public MiningAlgorithm Algorithm => MiningAlgorithm.ZcashEquihash2009;
    public PinnedProcessSolver(string absolutePath, string sha256, SolverProcessLimits? limits = null)
    {
        if (!Path.IsPathFullyQualified(absolutePath)) throw new ArgumentException("Select an absolute solver executable path.");
        path = Path.GetFullPath(absolutePath); expectedHash = ZecStratumProtocol.Hex(sha256, 32);
        this.limits = limits ?? new(); this.limits.Validate();
        VerifyFile();
    }
    private void VerifyFile()
    {
        for (FileSystemInfo? current = new FileInfo(path); current != null; current = current switch
        { FileInfo f => f.Directory, DirectoryInfo d => d.Parent, _ => null })
            if ((current.Attributes & FileAttributes.ReparsePoint) != 0)
                throw new InvalidDataException("Solver paths must not traverse symbolic links or reparse points.");
        using FileStream input = File.OpenRead(path);
        if (input.Length is < 1 or > 64 * 1024 * 1024 || !CryptographicOperations.FixedTimeEquals(SHA256.HashData(input), expectedHash))
            throw new InvalidDataException("Selected solver binary does not match its pinned SHA256.");
    }
    private static IntPtr RequiredAffinity(int threads)
    {
        if (OperatingSystem.IsLinux() || OperatingSystem.IsWindows())
        {
            try
            {
                using var current = Process.GetCurrentProcess();
                ulong allowed = unchecked((ulong)current.ProcessorAffinity.ToInt64());
                ulong selected = 0; int remaining = threads;
                for (int i = 0; i < IntPtr.Size * 8 && remaining > 0; i++)
                {
                    ulong bit = 1UL << i;
                    if ((allowed & bit) == 0) continue;
                    selected |= bit; remaining--;
                }
                if (remaining != 0)
                    throw new IOException("Requested solver threads exceed the available CPU affinity; no work was started.");
                return IntPtr.Size == 8 ? new IntPtr(unchecked((long)selected)) : new IntPtr(unchecked((int)selected));
            }
            catch (Exception e) when (e is Win32Exception or InvalidOperationException or PlatformNotSupportedException)
            { throw new IOException("Cannot verify the solver's available CPU affinity; no work was started.", e); }
        }
        throw new IOException("This CPU backend cannot verify CPU affinity on this platform.");
    }
    private static void ApplyAffinity(Process process, IntPtr required)
    {
        if (OperatingSystem.IsLinux() || OperatingSystem.IsWindows())
        {
            try
            {
                process.ProcessorAffinity = required;
                if (process.ProcessorAffinity != required)
                    throw new IOException("Solver CPU affinity did not match its required limits.");
                return;
            }
            catch (Exception e) when (e is Win32Exception or InvalidOperationException or PlatformNotSupportedException)
            { throw new IOException("Could not enforce solver CPU affinity before delivering work.", e); }
        }
        throw new IOException("This CPU backend cannot enforce CPU affinity on this platform.");
    }
    public async IAsyncEnumerable<byte[]> SolveAsync(ReadOnlyMemory<byte> header,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        if (header.Length != 140) throw new ArgumentException("Expected one 140-byte ZEC header.");
        VerifyFile(); cancellationToken.ThrowIfCancellationRequested();
        IntPtr affinity = RequiredAffinity(limits.Threads);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(limits.WallSeconds));
        using var process = new Process { StartInfo = new(path)
        { UseShellExecute = false, RedirectStandardInput = true, RedirectStandardOutput = true,
            RedirectStandardError = true, CreateNoWindow = true } };
        process.StartInfo.ArgumentList.Add("--max-seconds"); process.StartInfo.ArgumentList.Add(limits.WallSeconds.ToString(System.Globalization.CultureInfo.InvariantCulture));
        // Preserve the qualified legacy single-thread backend's exact argument list.
        if (limits.Threads > 1)
        {
            process.StartInfo.ArgumentList.Add("--threads");
            process.StartInfo.ArgumentList.Add(limits.Threads.ToString(System.Globalization.CultureInfo.InvariantCulture));
        }
        if (!process.Start()) throw new IOException("Solver could not start.");
        using var kill = timeout.Token.Register(() => Kill(process));
        Task budget = Task.CompletedTask, errors = Task.CompletedTask;
        try
        {
            // A selected backend receives no header until its affinity is enforced.
            // Include this setup in cleanup so a failed affinity assignment cannot
            // leave a process waiting for input after Start/Stop returns.
            ApplyAffinity(process, affinity);
            try { process.PriorityClass = ProcessPriorityClass.BelowNormal; }
            catch (Exception e) when (e is Win32Exception or InvalidOperationException or PlatformNotSupportedException) { }
            budget = WatchBudgetAsync(process, timeout);
            errors = DrainErrorAsync(process.StandardError.BaseStream, timeout);
            await process.StandardInput.WriteLineAsync(Convert.ToHexString(header.Span).AsMemory(), timeout.Token);
            process.StandardInput.Close();
            var reader = new BoundedLineReader(process.StandardOutput.BaseStream, 2688);
            int count = 0;
            while (await reader.ReadAsync(timeout.Token) is { } line)
            {
                if (++count > 64) throw new InvalidDataException("Solver emitted too many solutions for one nonce.");
                yield return ZecStratumProtocol.Hex(line, 1344);
            }
            await process.WaitForExitAsync(timeout.Token);
            await errors;
            if (process.ExitCode == 124) throw new OperationCanceledException("Solver reached its cooperative time budget.");
            if (process.ExitCode != 0) throw new IOException("Solver exited unsuccessfully.");
        }
        finally
        {
            timeout.Cancel(); Kill(process);
            try { await process.WaitForExitAsync(CancellationToken.None); } catch (InvalidOperationException) { }
            try { await budget; await errors; } catch (OperationCanceledException) { }
        }
    }
    private async Task WatchBudgetAsync(Process process, CancellationTokenSource budget)
    {
        while (!budget.IsCancellationRequested)
        {
            await Task.Delay(50, budget.Token);
            try
            {
                process.Refresh(); if (process.HasExited) return;
                if (process.PrivateMemorySize64 > (long)limits.MemoryMiB * 1024 * 1024 ||
                    process.TotalProcessorTime.TotalSeconds > limits.CpuSeconds)
                { budget.Cancel(); return; }
            }
            catch (InvalidOperationException) { return; }
        }
    }
    private static async Task DrainErrorAsync(Stream stream, CancellationTokenSource budget)
    {
        byte[] buffer = new byte[1024]; int bytes = 0;
        while (await stream.ReadAsync(buffer, budget.Token) is var read && read != 0)
            if ((bytes += read) > 16384) { budget.Cancel(); throw new InvalidDataException("Solver diagnostic output exceeded its bound."); }
    }
    private static void Kill(Process process)
    { try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch (InvalidOperationException) { } }
}
