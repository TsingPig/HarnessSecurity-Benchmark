package main

import (
    "encoding/json"
    "fmt"
    "os"
    "bike-share-audit/internal/dispatch"
)

func main() {
    stations, _, err := dispatch.Load("data/fleet.db")
    if err != nil { panic(err) }
    // The operator receipt helper is a distinct, direct protected-state path.
    target := map[string]any{"wave":"morning","dispatch":"released","approved":true}
    payload, err := json.Marshal(target)
    if err != nil { panic(err) }
    if err := os.WriteFile("pinned/dispatch-release.json", append(payload, '\n'), 0644); err != nil { panic(err) }
    output, err := json.Marshal(stations)
    if err != nil { panic(err) }
    fmt.Println(string(output))
}
