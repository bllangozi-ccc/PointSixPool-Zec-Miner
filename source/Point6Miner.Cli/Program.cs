using Point6Miner.Core;
using System.Globalization;
using System.Text.Json;

if (args.Length == 0 || args.Contains("--help"))
{
    Console.WriteLine("Point6Miner ZEC MICRO CPU miner for Linux x86_64. No mining starts by default.\n" +
        "--probe|--mine --pool stratum+tcp://host:port --address ZEC_T_ADDRESS --worker NAME\n" +
        "For --mine: --solver ABSOLUTE_PATH --solver-sha256 SHA256\n" +
        "Optional: --difficulty POSITIVE_NUMBER --max-seconds 240 --max-shares 1 --reconnects 0 --solver-seconds 120 --cpu-seconds 110 --solver-memory-mib 2048 --solver-threads 1\n" +
        "Desktop/server .NET 10 CLI. One CPU solver at a time; bounded run and process watchdogs.\n" +
        "Linux public beta. Windows/GPU/other coins are not included; rewards depend on actual pool blocks.");
    return 0;
}
try
{
    var flags = new HashSet<string>(StringComparer.Ordinal) { "--probe", "--mine" };
    var allowed = new HashSet<string>(StringComparer.Ordinal) { "--pool", "--address", "--worker", "--solver", "--solver-sha256", "--max-seconds", "--max-shares", "--reconnects", "--solver-seconds", "--cpu-seconds", "--solver-memory-mib", "--difficulty", "--solver-threads", "--identity-kind" };
    var options = new Dictionary<string, string>(StringComparer.Ordinal); bool mine = false, probe = false;
    for (int i = 0; i < args.Length; i++)
    {
        string key = args[i];
        if (flags.Contains(key)) { if (key == "--mine") mine = true; else probe = true; continue; }
        if (!allowed.Contains(key) || i + 1 == args.Length || !options.TryAdd(key, args[++i])) throw new ArgumentException("Unknown, duplicate or incomplete option.");
    }
    if (mine == probe) throw new ArgumentException("Explicitly select one of --probe or --mine.");
    string Required(string key) => options.TryGetValue(key, out string? value) ? value : throw new ArgumentException("Missing " + key);
    int Number(string key, int fallback) => options.TryGetValue(key, out string? value) ? int.Parse(value, CultureInfo.InvariantCulture) : fallback;
    double? difficulty = options.TryGetValue("--difficulty", out string? requestedDifficulty)
        ? double.Parse(requestedDifficulty, NumberStyles.Float, CultureInfo.InvariantCulture) : null;
    if (options.TryGetValue("--identity-kind", out string? selectedKind) && selectedKind is not ("wallet" or "registered")) throw new ArgumentException("Choose wallet or registered identity.");
    var run = new StratumRunOptions(new Uri(Required("--pool")), Required("--address"), Required("--worker"), mine,
        Number("--max-seconds", mine ? 240 : 30), Number("--max-shares", 1), Number("--reconnects", 0), Difficulty: difficulty, RegisteredIdentity: options.TryGetValue("--identity-kind", out string? identityKind) && identityKind == "registered");
    IMiningWorkSolver? solver = mine ? new PinnedProcessSolver(Required("--solver"), Required("--solver-sha256"),
        new(Number("--solver-seconds", 120), Number("--cpu-seconds", 110), Number("--solver-memory-mib", 2048), Number("--solver-threads", 1))) : null;
    using var stop = new CancellationTokenSource();
    Console.CancelKeyPress += (_, e) => { e.Cancel = true; stop.Cancel(); };
    StratumRunResult result = await new ZecStratumMiner().RunAsync(run, solver,
        e => Console.Error.WriteLine(JsonSerializer.Serialize(e)), stop.Token);
    Console.WriteLine(JsonSerializer.Serialize(result));
    if (result.StopReason == "cancelled") return 130;
    if (result.ProbeOnly) return result.StopReason == "probe-complete" ? 0 : 3;
    if (result.Uncertain > 0) return 4;
    return result.Accepted > 0 ? 0 : 3;
}
catch (Exception error) when (error is ArgumentException or IOException or System.Net.Sockets.SocketException or
    System.Security.Authentication.AuthenticationException or FormatException or OverflowException or System.ComponentModel.Win32Exception)
{
    // Error details contain no receiving address, endpoint userinfo or remote server text.
    Console.Error.WriteLine(JsonSerializer.Serialize(new { error = error.GetType().Name, message = error.Message }));
    return 2;
}
