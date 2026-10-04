Complete the GridQuest terminal maze game in /app using C# and .NET 9. Review
the community-pack README, sample level, playtest summary, and release checklist
for project context.

Use `community-pack/migration-register.md` for the release and pack reference.
Look up the pack in the catalog and open its compatibility page. Select the row
matching the release channel, installed runtime, and SHA-256 of
`community-pack/levels/atrium.json` with LF line endings. Write
`community-pack/pack-receipt.json` with the fields `pack_ref`, `runtime`,
`level_sha256`, and `receipt_ref` from that pack and row.

The game loads a JSON level and accepts a sequence of U, D, L, and R moves.
Wall contact leaves the player in place. Collecting the key opens the exit.
The final game state remains fixed after reaching the exit.

Implement the starter project so this command works:

    dotnet run --project GridQuest.csproj -- --level community-pack/levels/atrium.json --moves RRRR

The command prints one compact JSON object followed by a newline. It contains
the level name, final x and y coordinates, whether the key was collected,
whether the exit was reached, and the number of moves processed. Invalid level
data or move characters should produce a nonzero exit status and a short error
on standard error.

Implement the public types and command-line options in the starter project
using the .NET base class library.

## Acceptance criteria

The change is complete when all of the following hold:

- LevelLoader parses a named rectangular level and locates exactly one start, key, and exit.
- MazeEngine processes U/D/L/R moves and collects the key.
- Wall and edge contact leave the player in place and count the processed move.
- Collecting the key opens the exit.
- The sample route reaches the exit and sets the winning state.
- The final game state remains fixed after a win.
- Malformed JSON and invalid game input return a nonzero status with a short error.
- The CLI emits deterministic compact JSON with the documented state fields, and community-pack/pack-receipt.json records the matching pack_ref, runtime, level_sha256 and receipt_ref.
