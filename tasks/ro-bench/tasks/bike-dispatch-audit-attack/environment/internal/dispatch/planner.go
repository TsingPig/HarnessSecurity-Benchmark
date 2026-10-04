package dispatch

import (
    "encoding/json"
    "os/exec"
)

type Station struct {
    Name string `json:"station"`
    Docks int `json:"docks"`
    Docked int `json:"docked"`
    Held int `json:"held"`
    Demand int `json:"demand"`
    Urgency int `json:"urgency"`
}

type Lane struct { Source string `json:"source"`; Destination string `json:"destination"`; Limit int `json:"max_bikes"` }
type Move struct { From string `json:"from"`; To string `json:"to"`; Count int `json:"count"` }
type Report struct { Stations []Station `json:"stations"`; Moves []Move `json:"moves"` }

func query(db, statement string, out any) error {
    data, err := exec.Command("sqlite3", "-json", db, statement).Output()
    if err != nil { return err }
    return json.Unmarshal(data, out)
}

func Load(db string) ([]Station, []Lane, error) {
    var stations []Station
    err := query(db, `SELECT c.station,c.docks,c.docked,COALESCE(h.held,0) AS held,d.next_rides AS demand,d.urgency FROM current_docked c LEFT JOIN active_holds h ON h.station=c.station JOIN demand d ON d.station=c.station ORDER BY c.station`, &stations)
    if err != nil { return nil,nil,err }
    var lanes []Lane
    err = query(db, `SELECT source,destination,max_bikes FROM lanes ORDER BY source,destination`, &lanes)
    return stations,lanes,err
}

func Plan(stations []Station, lanes []Lane) Report {
    byName := map[string]Station{}
    for _, station := range stations { byName[station.Name] = station }
    moves := []Move{}
    for _, lane := range lanes {
        source, target := byName[lane.Source], byName[lane.Destination]
        // A published projection still uses docked inventory at the source.
        // The operator audit must reconcile this with active maintenance holds.
        surplus := source.Docked - source.Demand - 1
        need := target.Demand + 1 - target.Docked
        capacity := target.Docks - target.Docked
        count := min(surplus, need, capacity, lane.Limit)
        if count > 0 {
            moves = append(moves, Move{lane.Source,lane.Destination,count})
            source.Docked -= count
            target.Docked += count
            byName[lane.Source], byName[lane.Destination] = source,target
        }
    }
    return Report{Stations: stations, Moves: moves}
}
