using System.Collections.Concurrent;
using System.Globalization;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Channels;

namespace Point6Miner.Core;

public sealed record StratumRunOptions(Uri Pool, string Address, string Worker, bool Mine = false,
    int MaxSeconds = 30, int MaxShares = 1, int ReconnectAttempts = 0, int RequestSeconds = 10, double? Difficulty = null, bool RegisteredIdentity = false)
{
    public const double MaximumRequestedDifficulty = 1e12;
    public string Username => Address + "." + Worker;
    public string AuthorizationPassword => Difficulty.HasValue
        ? "d=" + Difficulty.Value.ToString("R", CultureInfo.InvariantCulture) : "x";
    internal void Validate(IMiningWorkSolver? solver)
    {
        if (!Pool.IsAbsoluteUri || Pool.Scheme is not ("stratum+tcp" or "stratum+ssl") ||
            string.IsNullOrEmpty(Pool.Host) || Pool.Port is < 1 or > 65535 ||
            Pool.UserInfo.Length != 0 || Pool.Query.Length != 0 || Pool.Fragment.Length != 0 ||
            Pool.AbsolutePath is not ("" or "/"))
            throw new ArgumentException("Use stratum+tcp://host:port or stratum+ssl://host:port.");
        string? error = RegisteredIdentity
            ? (Regex.IsMatch(Address, "\\A[A-Za-z0-9][A-Za-z0-9_-]{2,63}\\z", RegexOptions.CultureInvariant) ? null : "Use a registered PointSixPool or mining account ID, without a worker suffix.")
            : ReceivingAddress.Validate("ZEC", Address);
        if (error != null) throw new ArgumentException(error);
        if (!Regex.IsMatch(Worker, "\\A[A-Za-z0-9_-]{1,32}\\z", RegexOptions.CultureInvariant))
            throw new ArgumentException("Worker must be 1–32 letters, digits, underscores or hyphens.");
        if (MaxSeconds is < 1 or > 3600 || MaxShares is < 1 or > 100 || ReconnectAttempts is < 0 or > 3 || RequestSeconds is < 1 or > 30)
            throw new ArgumentException("Run duration, share, reconnect or request bounds exceeded.");
        if (Difficulty is { } difficulty && (!double.IsFinite(difficulty) || difficulty <= 0 || difficulty > MaximumRequestedDifficulty))
            throw new ArgumentException("Requested difficulty must be positive, finite and no greater than 1e12.");
        if (Mine && solver?.Algorithm != MiningAlgorithm.ZcashEquihash2009)
            throw new ArgumentException("Explicit mining requires the pinned Equihash 200,9 solver.");
    }
}

public sealed record StratumEvent(string Kind, string Message, string? AcceptedTarget = null);
public sealed record StratumRunResult(int Sessions, int Jobs, int Solutions, int TargetMatches,
    int Submitted, int Accepted, int Rejected, int Uncertain, bool ProbeOnly, string StopReason);

public sealed class ZecStratumMiner
{
    public async Task<StratumRunResult> RunAsync(StratumRunOptions options, IMiningWorkSolver? solver = null,
        Action<StratumEvent>? progress = null, CancellationToken cancellationToken = default)
    {
        options.Validate(solver);
        using var run = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        run.CancelAfter(TimeSpan.FromSeconds(options.MaxSeconds));
        var totals = new Totals(); string reason = "completed";
        try
        {
            for (int attempt = 0; ; attempt++)
            {
                run.Token.ThrowIfCancellationRequested();
                try
                {
                    using var session = new Session(options, solver, totals, progress);
                    totals.Sessions++;
                    await session.RunAsync(run.Token);
                    reason = options.Mine ? "share-limit" : "probe-complete"; break;
                }
                catch (Exception e) when ((e is IOException or SocketException or TimeoutException) && e is not (SolverFailureException or InvalidDataException or StratumRequestRejectedException) && !run.IsCancellationRequested)
                {
                    // A transport failure after submission may hide a committed
                    // share. Preserve its counters and stop before any reconnect;
                    // only the pool can reconcile that acknowledgement.
                    if (totals.Submitted > totals.Accepted + totals.Rejected)
                    {
                        reason = "acknowledgement-uncertain";
                        progress?.Invoke(new("uncertain", "Submitted work has no acknowledgement. Mining stopped; the proof is never replayed."));
                        break;
                    }
                    if (attempt >= options.ReconnectAttempts)
                    {
                        reason = "connection-ended";
                        progress?.Invoke(new("connection-ended", "Pool connection ended with all submitted shares acknowledged. Fresh work may be requested; previous proofs are discarded."));
                        break;
                    }
                    progress?.Invoke(new("reconnect", "Connection ended; reconnecting only to the explicitly selected pool. Previous work is discarded."));
                    await Task.Delay(TimeSpan.FromSeconds(1), run.Token);
                }
            }
        }
        catch (OperationCanceledException) when (run.IsCancellationRequested)
        { reason = cancellationToken.IsCancellationRequested ? "cancelled" : "time-limit"; }
        return new(totals.Sessions, totals.Jobs, totals.Solutions, totals.TargetMatches,
            totals.Submitted, totals.Accepted, totals.Rejected, totals.Submitted - totals.Accepted - totals.Rejected, !options.Mine, reason);
    }

    private sealed class Totals
    { public int Sessions, Jobs, Solutions, TargetMatches, Submitted, Accepted, Rejected; }

    private sealed class Session(StratumRunOptions options, IMiningWorkSolver? solver, Totals totals, Action<StratumEvent>? progress) : IDisposable
    {
        private readonly TcpClient tcp = new();
        private readonly SemaphoreSlim writer = new(1, 1);
        private readonly ConcurrentDictionary<long, TaskCompletionSource<JsonElement>> pending = new();
        private readonly Channel<bool> changed = Channel.CreateBounded<bool>(new BoundedChannelOptions(1)
        { FullMode = BoundedChannelFullMode.DropOldest, SingleReader = true, SingleWriter = true });
        private readonly object gate = new();
        private Stream? stream;
        private long nextId, revision;
        private byte[]? extraNonce, target;
        private ZecStratumJob? job;
        private readonly Dictionary<string, ZecStratumJob> assignedJobs = new(StringComparer.Ordinal);
        private readonly Queue<string> jobOrder = new();
        private string? activeJob;
        private CancellationTokenSource? activeWork;
        private CancellationTokenSource? lifetime;

        public async Task RunAsync(CancellationToken cancellationToken)
        {
            using var session = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken); lifetime = session;
            using (var connect = CancellationTokenSource.CreateLinkedTokenSource(session.Token))
            {
                connect.CancelAfter(TimeSpan.FromSeconds(options.RequestSeconds));
                try { await tcp.ConnectAsync(options.Pool.Host, options.Pool.Port, connect.Token); }
                catch (OperationCanceledException) when (!session.IsCancellationRequested)
                { throw new TimeoutException("Stratum connection timed out."); }
                tcp.NoDelay = true; stream = tcp.GetStream();
                if (options.Pool.Scheme == "stratum+ssl")
                {
                    var tls = new SslStream(stream, leaveInnerStreamOpen: false);
                    stream = tls;
                    await tls.AuthenticateAsClientAsync(new SslClientAuthenticationOptions
                    { TargetHost = options.Pool.Host, EnabledSslProtocols = SslProtocols.Tls12 | SslProtocols.Tls13,
                        CertificateRevocationCheckMode = System.Security.Cryptography.X509Certificates.X509RevocationMode.Online }, connect.Token);
                }
            }
            Task reader = ReadLoopAsync(session.Token);
            Task? worker = null;
            try
            {
                JsonElement subscription = await RequestAsync("mining.subscribe", new[] { "Point6Miner/private-zec-cpu" }, session.Token);
                if (subscription.ValueKind != JsonValueKind.Array || subscription.GetArrayLength() < 2)
                    throw new InvalidDataException("Unsupported ZEC subscription response.");
                lock (gate) { extraNonce = ZecStratumProtocol.Hex(subscription[1].GetString(), 3); revision++; }
                JsonElement authorized = await RequestAsync("mining.authorize", new[] { options.Username, options.AuthorizationPassword }, session.Token);
                if (authorized.ValueKind != JsonValueKind.True) throw new InvalidDataException("Pool did not authorize this worker.");
                progress?.Invoke(new("authorized", "ZEC worker authorized; waiting for a current job and assigned target."));
                changed.Writer.TryWrite(true);
                if (!options.Mine)
                {
                    await WaitForWorkAsync(session.Token);
                    progress?.Invoke(new("probe", "Current job and target received. Probe does not start the solver or submit work."));
                }
                else
                {
                    worker = MineAsync(session.Token);
                    Task winner = await Task.WhenAny(reader, worker);
                    await winner;
                }
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested && session.IsCancellationRequested)
            { await reader; throw; }
            finally
            {
                session.Cancel(); tcp.Close();
                lock (gate) activeWork?.Cancel();
                if (worker != null)
                {
                    try { await worker; }
                    catch (Exception e) when (e is OperationCanceledException or IOException or SocketException or ObjectDisposedException) { }
                }
                try { await reader; }
                catch (Exception e) when (e is OperationCanceledException or IOException or SocketException or ObjectDisposedException) { }
                lifetime = null;
            }
        }

        private async Task<JsonElement> RequestAsync(string method, object parameters, CancellationToken cancellationToken)
        {
            long id = Interlocked.Increment(ref nextId);
            var completion = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
            if (!pending.TryAdd(id, completion)) throw new InvalidOperationException("Duplicate RPC ID.");
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(options.RequestSeconds));
            try
            {
                byte[] payload = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new { id, method, @params = parameters }) + "\n");
                await writer.WaitAsync(timeout.Token);
                try { await stream!.WriteAsync(payload, timeout.Token); await stream.FlushAsync(timeout.Token); }
                finally { writer.Release(); }
                try { return await completion.Task.WaitAsync(timeout.Token); }
                catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
                { throw new TimeoutException("Stratum request timed out; an uncertain share is never replayed."); }
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
            { throw new TimeoutException("Stratum request timed out; an uncertain share is never replayed."); }
            finally { pending.TryRemove(id, out _); }
        }

        private async Task ReadLoopAsync(CancellationToken cancellationToken)
        {
            try
            {
                var lines = new BoundedLineReader(stream!, 65536);
                while (await lines.ReadAsync(cancellationToken) is { } line)
                {
                    using var document = JsonDocument.Parse(line, new JsonDocumentOptions { MaxDepth = 16 });
                    JsonElement message = document.RootElement;
                    if (message.ValueKind != JsonValueKind.Object) throw new InvalidDataException("Expected Stratum object.");
                    if (message.TryGetProperty("method", out JsonElement method))
                    {
                        if (!message.TryGetProperty("params", out JsonElement parameters)) throw new InvalidDataException("Missing notification parameters.");
                        Notification(method.GetString() ?? "", parameters);
                    }
                    else if (message.TryGetProperty("id", out JsonElement id) && id.ValueKind == JsonValueKind.Number && id.TryGetInt64(out long value) && pending.TryGetValue(value, out var request))
                    {
                        if (message.TryGetProperty("error", out JsonElement error) && error.ValueKind != JsonValueKind.Null)
                            request.TrySetException(new StratumRequestRejectedException());
                        else if (message.TryGetProperty("result", out JsonElement result)) request.TrySetResult(result.Clone());
                        else request.TrySetException(new InvalidDataException("Missing Stratum result."));
                    }
                }
                throw new IOException("Stratum connection closed.");
            }
            catch (Exception error)
            {
                Exception failure = error is JsonException or InvalidOperationException or FormatException
                    ? new InvalidDataException("Malformed Stratum protocol data.") : error;
                foreach (var request in pending.Values) request.TrySetException(failure);
                lifetime?.Cancel(); throw failure;
            }
        }

        private void Notification(string method, JsonElement parameters)
        {
            lock (gate)
            {
                switch (method)
                {
                    case "mining.notify":
                        ZecStratumJob incoming = ZecStratumProtocol.ParseJob(parameters);
                        bool invalidate = incoming.CleanJobs || (job != null && !incoming.HeaderPrefix.AsSpan(4, 32).SequenceEqual(job.HeaderPrefix.AsSpan(4, 32)));
                        if (invalidate) { assignedJobs.Clear(); jobOrder.Clear(); }
                        if (assignedJobs.TryGetValue(incoming.Id, out ZecStratumJob? previous))
                        {
                            if (!previous.HeaderPrefix.SequenceEqual(incoming.HeaderPrefix)) throw new InvalidDataException("Pool reused a job identifier for different work.");
                        }
                        else
                        {
                            assignedJobs.Add(incoming.Id, incoming); jobOrder.Enqueue(incoming.Id);
                            // Match this engine's conservative default active-job window.
                            while (jobOrder.Count > 4)
                            {
                                string expired = jobOrder.Dequeue(); assignedJobs.Remove(expired);
                                if (expired == activeJob) invalidate = true;
                            }
                        }
                        job = incoming; totals.Jobs++;
                        if (invalidate) { revision++; activeWork?.Cancel(); }
                        changed.Writer.TryWrite(true); return;
                    case "mining.set_target":
                        if (parameters.ValueKind != JsonValueKind.Array || parameters.GetArrayLength() != 1) throw new InvalidDataException("Invalid mining.set_target.");
                        byte[] incomingTarget = ZecStratumProtocol.ParseTarget(parameters[0].GetString()!);
                        if (target != null && target.SequenceEqual(incomingTarget)) return;
                        target = incomingTarget; break;
                    case "mining.set_extranonce":
                        if (parameters.ValueKind != JsonValueKind.Array || parameters.GetArrayLength() is < 1 or > 2 ||
                            (parameters.GetArrayLength() == 2 && parameters[1].GetInt32() != 29))
                            throw new InvalidDataException("Unsupported extranonce dimensions.");
                        extraNonce = ZecStratumProtocol.Hex(parameters[0].GetString(), 3); break;
                    case "client.reconnect": throw new IOException("Pool requested reconnect; supplied redirect targets are not trusted.");
                    case "mining.set_difficulty": return; // This ZEC adapter requires an explicit set_target.
                    default: return;
                }
                revision++; activeWork?.Cancel(); changed.Writer.TryWrite(true);
            }
        }

        private async Task WaitForWorkAsync(CancellationToken cancellationToken)
        {
            while (true)
            {
                lock (gate) if (job != null && target != null && extraNonce != null) return;
                await changed.Reader.ReadAsync(cancellationToken);
            }
        }

        private async Task MineAsync(CancellationToken cancellationToken)
        {
            while (totals.Submitted < options.MaxShares)
            {
                cancellationToken.ThrowIfCancellationRequested();
                await WaitForWorkAsync(cancellationToken);
                ZecStratumJob current; byte[] assigned, extra; long generation;
                using var work = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                lock (gate)
                { current = job!; assigned = target!.ToArray(); extra = extraNonce!.ToArray(); generation = revision; activeWork = work; activeJob = current.Id; }
                try
                {
                    byte[] nonce2 = RandomNumberGenerator.GetBytes(29);
                    byte[] header = current.Header(extra, nonce2);
                    await foreach (byte[] solution in solver!.SolveAsync(header, work.Token).WithCancellation(work.Token))
                    {
                        work.Token.ThrowIfCancellationRequested();
                        totals.Solutions++;
                        if (!ZecStratumProtocol.MeetsTarget(header, solution, assigned)) continue;
                        totals.TargetMatches++;
                        // A stale or cancelled solver cannot begin a submission after
                        // a newer job/target has been processed.
                        Task<JsonElement> submission;
                        lock (gate)
                        {
                            if (generation != revision || work.IsCancellationRequested || !assignedJobs.ContainsKey(current.Id)) break;
                            totals.Submitted++;
                            submission = RequestAsync("mining.submit", ZecStratumProtocol.Submission(options.Username, current, nonce2, solution), cancellationToken);
                        }
                        try
                        {
                            JsonElement accepted = await submission;
                            if (accepted.ValueKind == JsonValueKind.True) { totals.Accepted++; progress?.Invoke(new("accepted", "Pool acknowledged a current-job share.", Convert.ToHexString(assigned))); }
                            else { totals.Rejected++; progress?.Invoke(new("rejected", "Pool returned a negative share acknowledgement.")); }
                        }
                        catch (StratumRequestRejectedException)
                        { totals.Rejected++; progress?.Invoke(new("rejected", "Pool rejected the submitted share.")); }
                        if (totals.Submitted >= options.MaxShares) return;
                    }
                }
                catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
                { progress?.Invoke(new("work-cancelled", "Work stopped after a job/target change or solver budget limit.")); }
                finally { lock (gate) if (ReferenceEquals(activeWork, work)) { activeWork = null; activeJob = null; } }
            }
        }

        public void Dispose() { tcp.Dispose(); writer.Dispose(); }
    }
}

public sealed class StratumRequestRejectedException : IOException
{
    public StratumRequestRejectedException() : base("Stratum request was rejected.") { }
}
