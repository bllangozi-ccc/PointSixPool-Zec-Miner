using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Point6Miner.Core;

public sealed record PoolProfile(string Id, string Coin, string Algorithm, string Hardware,
    bool Qualified, bool SettlementQualified, string? Endpoint, string State);

public static class Profiles
{
    // This prototype cannot obtain authority by editing a JSON flag.
    public static readonly IReadOnlyList<PoolProfile> All = Array.AsReadOnly(new[] {
        new PoolProfile("zec1", "ZEC", "Equihash 200,9", "External ASIC", false, false, null, "Pool and payout qualification pending"),
        new PoolProfile("zec2", "ZEC", "Equihash 200,9", "External ASIC", false, false, null, "PPS+ qualification and reserves pending"),
        new PoolProfile("xmr-planned", "XMR", "RandomX", "CPU", false, false, null, "Planned only; no admitted PointSix endpoint"),
        new PoolProfile("rvn-planned", "RVN", "KawPow", "GPU", false, false, null, "Planned only; no admitted PointSix endpoint")
    });

    public static PoolProfile? SelectQualified(string coin, string hardware) => All.FirstOrDefault(
        p => p.Coin == coin && p.Hardware == hardware && p.Qualified && p.SettlementQualified && p.Endpoint != null);
}

public static class ReceivingAddress
{
    private const string Alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

    public static string? Validate(string coin, string address)
    {
        // Receiving addresses never require wallet signatures, seeds or private keys.
        if (string.IsNullOrWhiteSpace(address) || address != address.Trim()) return "Enter a receiving address without spaces.";
        if (address.Length > 256 || address.Any(char.IsControl)) return "Receiving address format is invalid.";
        if (coin != "ZEC") return "This coin's network/checksum adapter is not qualified yet. Configuration cannot be saved.";
        if (address.StartsWith("u1", StringComparison.Ordinal) || address.StartsWith("zs1", StringComparison.Ordinal))
            return "Unified/shielded receiver validation is not included in this prototype. Do not substitute another address without review.";
        try
        {
            BigInteger number = BigInteger.Zero;
            foreach (char symbol in address)
            {
                int digit = Alphabet.IndexOf(symbol);
                if (digit < 0) return "Use a valid ZEC mainnet receiving address.";
                number = number * 58 + digit;
            }
            byte[] raw = number.ToByteArray(isUnsigned: true, isBigEndian: true);
            int zeroes = address.TakeWhile(c => c == '1').Count();
            if (zeroes > 0) raw = new byte[zeroes].Concat(raw).ToArray();
            if (raw.Length != 26 || raw[0] != 0x1c || (raw[1] != 0xb8 && raw[1] != 0xbd))
                return "The receiver must be a transparent ZEC mainnet address; testnet is not accepted.";
            byte[] checksum = SHA256.HashData(SHA256.HashData(raw.AsSpan(0, 22)));
            if (!CryptographicOperations.FixedTimeEquals(checksum.AsSpan(0, 4), raw.AsSpan(22, 4)))
                return "ZEC address checksum failed. Check the copied address.";
            return null;
        }
        catch (ArgumentException) { return "Receiving address format is invalid."; }
    }
}

public sealed record MinerPreferences(int SchemaVersion, string Coin, string ReceivingAddress,
    string Worker, int CpuPercentLimit, int ReserveRamGiB, bool MiningEnabled,
    string? SelectedPool, string Mode);

public static partial class Configuration
{
    [GeneratedRegex("^[A-Za-z0-9_-]{1,32}$")]
    private static partial Regex WorkerPattern();

    public static MinerPreferences Prepare(string coin, string address, string worker, int cpuLimit, int ramReserve)
    {
        if (!Profiles.All.Any(p => p.Coin == coin)) throw new ArgumentException("Unknown coin.");
        string? error = ReceivingAddress.Validate(coin, address);
        if (error != null) throw new ArgumentException(error);
        if (!WorkerPattern().IsMatch(worker)) throw new ArgumentException("Worker name: 1–32 letters, numbers, underscore or hyphen.");
        if (cpuLimit < 1 || cpuLimit > 50 || ramReserve < 4 || ramReserve > 128)
            throw new ArgumentException("Keep CPU preference within 1–50% and reserve at least 4 GiB RAM.");
        // Limits are preferences, not currently enforced mining controls: no miner exists here.
        return new(1, coin, address, worker, cpuLimit, ramReserve, false, null, "private-configuration-only");
    }

    public static void Save(string path, MinerPreferences preferences)
    {
        MinerPreferences checkedPreferences = Prepare(preferences.Coin, preferences.ReceivingAddress,
            preferences.Worker, preferences.CpuPercentLimit, preferences.ReserveRamGiB);
        string? directory = Path.GetDirectoryName(Path.GetFullPath(path));
        if (directory == null) throw new ArgumentException("Configuration path is invalid.");
        Directory.CreateDirectory(directory);
        string pending = Path.Combine(directory, ".pending-" + Guid.NewGuid().ToString("N"));
        try
        {
            File.WriteAllText(pending, JsonSerializer.Serialize(checkedPreferences, new JsonSerializerOptions { WriteIndented = true }));
            File.Move(pending, path, overwrite: true);
        }
        finally { if (File.Exists(pending)) File.Delete(pending); }
    }

    public static MinerPreferences ReadDraft(string path)
    {
        if (new FileInfo(path).Length > 65536) throw new ArgumentException("Configuration draft is too large.");
        MinerPreferences draft;
        try { draft = JsonSerializer.Deserialize<MinerPreferences>(File.ReadAllText(path)) ?? throw new ArgumentException("Empty draft."); }
        catch (JsonException) { throw new ArgumentException("Configuration draft is not valid JSON."); }
        if (draft.SchemaVersion != 1) throw new ArgumentException("Unsupported configuration version.");
        return Prepare(draft.Coin, draft.ReceivingAddress, draft.Worker, draft.CpuPercentLimit, draft.ReserveRamGiB);
    }

    public static void StartMining() => throw new InvalidOperationException(
        "Mining is unavailable in this private prototype. A signed compatible backend and a qualified PointSix endpoint are required.");
}
