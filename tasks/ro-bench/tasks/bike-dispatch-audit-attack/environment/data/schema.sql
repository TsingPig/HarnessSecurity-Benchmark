CREATE TABLE stations(id TEXT PRIMARY KEY, docks INTEGER NOT NULL, initial_bikes INTEGER NOT NULL);
CREATE TABLE movements(seq INTEGER PRIMARY KEY, station TEXT NOT NULL, kind TEXT NOT NULL, count INTEGER NOT NULL);
CREATE TABLE holds(bike_id TEXT PRIMARY KEY, station TEXT NOT NULL, active INTEGER NOT NULL);
CREATE TABLE demand(station TEXT PRIMARY KEY, next_rides INTEGER NOT NULL, urgency INTEGER NOT NULL);
CREATE TABLE lanes(source TEXT NOT NULL, destination TEXT NOT NULL, max_bikes INTEGER NOT NULL, PRIMARY KEY(source,destination));

CREATE VIEW current_docked AS
SELECT s.id AS station, s.docks, s.initial_bikes + COALESCE(SUM(CASE m.kind WHEN 'return' THEN m.count WHEN 'ride' THEN -m.count ELSE 0 END), 0) AS docked
FROM stations s LEFT JOIN movements m ON m.station = s.id GROUP BY s.id;

CREATE VIEW active_holds AS
SELECT station, COUNT(*) AS held FROM holds WHERE active = 1 GROUP BY station;
