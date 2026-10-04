namespace GridQuest;

public static class MazeEngine
{
    public static GameState Play(LevelDefinition level, string moves)
    {
        ArgumentNullException.ThrowIfNull(level);
        ArgumentNullException.ThrowIfNull(moves);
        var x = level.Start.X;
        var y = level.Start.Y;
        var hasKey = false;
        var won = false;
        var steps = 0;

        foreach (var rawMove in moves)
        {
            if (won)
                break;
            var move = char.ToUpperInvariant(rawMove);
            var (dx, dy) = move switch
            {
                'U' => (0, -1),
                'D' => (0, 1),
                'L' => (-1, 0),
                'R' => (1, 0),
                _ => throw new ArgumentException($"invalid move '{rawMove}'", nameof(moves))
            };

            steps++;
            var nextX = x + dx;
            var nextY = y + dy;
            if (nextX < 0 || nextY < 0 || nextX >= level.Width || nextY >= level.Height)
                continue;
            var tile = level.Rows[nextY][nextX];
            if (tile == '#')
                continue;
            if (tile == 'E' && !hasKey)
                continue;

            x = nextX;
            y = nextY;
            if (tile == 'K')
                hasKey = true;
            if (tile == 'E')
                won = true;
        }

        return new GameState(level.Name, x, y, hasKey, won, steps);
    }
}
