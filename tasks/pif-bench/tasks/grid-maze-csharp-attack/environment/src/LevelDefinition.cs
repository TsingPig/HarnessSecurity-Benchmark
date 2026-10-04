namespace GridQuest;

public readonly record struct Position(int X, int Y);

public sealed class LevelDefinition
{
    public LevelDefinition(string name, string[] rows, Position start, Position key, Position exit)
    {
        Name = name;
        Rows = rows;
        Start = start;
        Key = key;
        Exit = exit;
    }

    public string Name { get; }
    public string[] Rows { get; }
    public int Width => Rows[0].Length;
    public int Height => Rows.Length;
    public Position Start { get; }
    public Position Key { get; }
    public Position Exit { get; }
}

public sealed record GameState(string Level, int X, int Y, bool HasKey, bool Won, int Steps);
