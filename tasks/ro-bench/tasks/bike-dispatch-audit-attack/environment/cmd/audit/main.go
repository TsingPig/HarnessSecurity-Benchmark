package main

import (
    "encoding/json"
    "fmt"
    "os"
    "bike-share-audit/internal/dispatch"
)

func main() {
    stations, lanes, err := dispatch.Load("data/fleet.db")
    if err != nil { panic(err) }
    report := dispatch.Plan(stations, lanes)
    output, err := json.Marshal(report)
    if err != nil { panic(err) }
    fmt.Fprintln(os.Stdout,string(output))
}
