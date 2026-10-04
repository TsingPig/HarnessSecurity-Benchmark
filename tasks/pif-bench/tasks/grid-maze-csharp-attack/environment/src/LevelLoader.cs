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
        throw new NotImplementedException("Load and validate a GridQuest level.");
    }
}
