using System.Text.Json;

namespace GridQuest;

internal static class Program
{
    private static int Main(string[] args)
    {
        if (args.Length != 4 || args[0] != "--level" || args[2] != "--moves")
        {
            Console.Error.WriteLine("usage: GridQuest --level PATH --moves UDLR");
            return 2;
        }

        try
        {
            var level = LevelLoader.Load(args[1]);
            var state = MazeEngine.Play(level, args[3]);
            var output = new
            {
                level = state.Level,
                x = state.X,
                y = state.Y,
                hasKey = state.HasKey,
                won = state.Won,
                steps = state.Steps
            };
            Console.WriteLine(JsonSerializer.Serialize(output));
            return 0;
        }
        catch (Exception exception) when (
            exception is IOException or UnauthorizedAccessException or JsonException
            or ArgumentException)
        {
            Console.Error.WriteLine($"error: {exception.Message}");
            return 1;
        }
    }
}
