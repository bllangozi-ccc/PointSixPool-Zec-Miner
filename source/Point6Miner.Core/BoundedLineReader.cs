using System.Text;

namespace Point6Miner.Core;

internal sealed class BoundedLineReader(Stream stream, int maximum)
{
    private readonly byte[] buffer = new byte[4096];
    private int offset, end;
    private static readonly UTF8Encoding Utf8 = new(false, true);
    public async Task<string?> ReadAsync(CancellationToken cancellationToken)
    {
        using var line = new MemoryStream();
        while (true)
        {
            if (offset == end)
            {
                end = await stream.ReadAsync(buffer, cancellationToken); offset = 0;
                if (end == 0)
                {
                    if (line.Length != 0) throw new InvalidDataException("Connection ended within a protocol line.");
                    return null;
                }
            }
            byte value = buffer[offset++];
            if (value == 10)
            {
                byte[] text = line.ToArray();
                int length = text.Length > 0 && text[^1] == 13 ? text.Length - 1 : text.Length;
                return Utf8.GetString(text, 0, length);
            }
            if (line.Length >= maximum && !(line.Length == maximum && value == 13))
                throw new InvalidDataException("Protocol line exceeds its size bound.");
            line.WriteByte(value);
        }
    }
}
