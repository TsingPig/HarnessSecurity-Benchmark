using System.Text.Json;

namespace GridQuest;

public static class LevelLoader
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public static LevelDefinition Load(string path)
    {
        var json = File.ReadAllText(path);
        var data = JsonSerializer.Deserialize<LevelFile>(json, JsonOptions)
            ?? throw new InvalidDataException("level must be a JSON object");
        if (string.IsNullOrWhiteSpace(data.Name))
            throw new InvalidDataException("level name is required");
        if (data.Rows is null || data.Rows.Length < 3 || data.Rows.Any(row => row is null))
            throw new InvalidDataException("level must contain at least three rows");

        var width = data.Rows[0].Length;
        if (width < 3 || data.Rows.Any(row => row.Length != width))
            throw new InvalidDataException("level rows must have the same width of at least three");

        var starts = new List<Position>();
        var keys = new List<Position>();
        var exits = new List<Position>();
        for (var y = 0; y < data.Rows.Length; y++)
        {
            for (var x = 0; x < width; x++)
            {
                var cell = data.Rows[y][x];
                if (cell is not ('#' or '.' or 'S' or 'K' or 'E'))
                    throw new InvalidDataException($"unsupported tile '{cell}'");
                var position = new Position(x, y);
                if (cell == 'S') starts.Add(position);
                if (cell == 'K') keys.Add(position);
                if (cell == 'E') exits.Add(position);
            }
        }

        if (starts.Count != 1 || keys.Count != 1 || exits.Count != 1)
            throw new InvalidDataException("level must contain exactly one S, K, and E");

        return new LevelDefinition(data.Name.Trim(), data.Rows, starts[0], keys[0], exits[0]);
    }

    private sealed class LevelFile
    {
        public string? Name { get; set; }
        public string[]? Rows { get; set; }
    }
}
