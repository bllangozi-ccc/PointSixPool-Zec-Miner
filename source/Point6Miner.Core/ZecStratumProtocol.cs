using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;

namespace Point6Miner.Core;

// Protocol-specific adapters own serialization and proof interpretation. Transport,
// cancellation and explicitly selected process backends need no coin-specific edits.
public sealed record MiningAlgorithm(string Coin, string Name, int HeaderBytes, int SolutionBytes)
{
    public static MiningAlgorithm ZcashEquihash2009 { get; } = new("ZEC", "Equihash 200,9", 140, 1344);
}

public interface IMiningWorkSolver
{
    MiningAlgorithm Algorithm { get; }
    IAsyncEnumerable<byte[]> SolveAsync(ReadOnlyMemory<byte> header, CancellationToken cancellationToken);
}

public sealed record ZecStratumJob(string Id, string TimeHex, byte[] HeaderPrefix, bool CleanJobs)
{
    public byte[] Header(ReadOnlySpan<byte> extraNonce1, ReadOnlySpan<byte> nonce2)
    {
        if (HeaderPrefix.Length != 108 || extraNonce1.Length != 3 || nonce2.Length != 29)
            throw new ArgumentException("ZEC requires a 108-byte prefix and a 3 + 29 byte nonce.");
        byte[] header = new byte[140];
        HeaderPrefix.CopyTo(header, 0); extraNonce1.CopyTo(header.AsSpan(108)); nonce2.CopyTo(header.AsSpan(111));
        return header;
    }
}

public static class ZecStratumProtocol
{
    public static byte[] Hex(string? value, int bytes)
    {
        if (value == null || value.Length != bytes * 2 || value.Any(c => !Uri.IsHexDigit(c)))
            throw new InvalidDataException("Invalid fixed-width protocol hex.");
        return Convert.FromHexString(value);
    }

    public static ZecStratumJob ParseJob(JsonElement parameters)
    {
        if (parameters.ValueKind != JsonValueKind.Array || parameters.GetArrayLength() != 8)
            throw new InvalidDataException("Expected eight ZEC mining.notify parameters.");
        string id = parameters[0].GetString() ?? "";
        if (id.Length is < 1 or > 128 || id.Any(c => c < 33 || c > 126))
            throw new InvalidDataException("Invalid job identifier.");
        int[] widths = [4, 32, 32, 32, 4, 4];
        byte[] prefix = new byte[108]; int offset = 0;
        for (int i = 0; i < widths.Length; i++)
        {
            byte[] field = Hex(parameters[i + 1].GetString(), widths[i]);
            field.CopyTo(prefix, offset); offset += field.Length;
        }
        if (parameters[7].ValueKind is not (JsonValueKind.True or JsonValueKind.False))
            throw new InvalidDataException("clean_jobs must be boolean.");
        // Miningcore sends every header field already in wire little endian.
        return new(id, parameters[5].GetString()!.ToLowerInvariant(), prefix, parameters[7].GetBoolean());
    }

    public static byte[] ParseTarget(string hex)
    {
        byte[] target = Hex(hex, 32);
        if (target.All(b => b == 0)) throw new InvalidDataException("Zero share target.");
        return target;
    }

    public static byte[] ProofBytes(ReadOnlySpan<byte> header, ReadOnlySpan<byte> solution)
    {
        if (header.Length != 140 || solution.Length != 1344)
            throw new InvalidDataException("Invalid Equihash 200,9 proof length.");
        byte[] proof = new byte[1487]; header.CopyTo(proof); proof[140] = 0xfd; proof[141] = 0x40; proof[142] = 0x05;
        solution.CopyTo(proof.AsSpan(143)); return proof;
    }

    public static bool MeetsTarget(ReadOnlySpan<byte> header, ReadOnlySpan<byte> solution, ReadOnlySpan<byte> targetBigEndian)
    {
        if (targetBigEndian.Length != 32 || targetBigEndian.IndexOfAnyExcept((byte)0) < 0)
            throw new InvalidDataException("Invalid share target.");
        byte[] digest = SHA256.HashData(SHA256.HashData(ProofBytes(header, solution)));
        // Zcash interprets the SHA256d digest as an unsigned little-endian integer;
        // mining.set_target is a padded unsigned big-endian number.
        return new BigInteger(digest, isUnsigned: true, isBigEndian: false) <=
            new BigInteger(targetBigEndian, isUnsigned: true, isBigEndian: true);
    }

    public static string[] Submission(string username, ZecStratumJob job, ReadOnlySpan<byte> nonce2, ReadOnlySpan<byte> solution)
    {
        if (nonce2.Length != 29 || solution.Length != 1344) throw new InvalidDataException("Invalid submission dimensions.");
        return [username, job.Id, job.TimeHex, Convert.ToHexString(nonce2).ToLowerInvariant(),
            "fd4005" + Convert.ToHexString(solution).ToLowerInvariant()];
    }
}
