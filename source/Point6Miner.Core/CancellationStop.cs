using System.ComponentModel;
using System.Runtime.CompilerServices;
[assembly: InternalsVisibleTo("EngineLifecycle")]
namespace Point6Miner.Core;
// OS process-exit races must be reported on the owning task, not thrown on a timer thread.
internal sealed class CancellationStop(Action stop)
{
    private Exception? failure;
    internal void Request()
    {
        try { stop(); }
        catch (Exception error) when (error is Win32Exception or InvalidOperationException)
        { Interlocked.CompareExchange(ref failure, error, null); }
    }
    internal void ThrowIfFailed()
    {
        if (failure is { } error) throw new IOException("Solver process cleanup failed; mining is stopped.", error);
    }
}
