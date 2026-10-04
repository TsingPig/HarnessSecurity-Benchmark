// The public board receives the Go projection and sorts risk cards by unmet
// demand, then urgency, then station name. Read-only audit conclusions must
// reconcile the projection with the event store first.
function riskCards(stations) {
  return stations.filter(station => station.unmet >= 2)
    .sort((a, b) => b.unmet - a.unmet || b.urgency - a.urgency || a.station.localeCompare(b.station))
    .map(station => station.station);
}
if (typeof module !== 'undefined') module.exports = { riskCards };
if (typeof document !== 'undefined') {
  fetch('published.json').then(response => response.json()).then(report => {
    document.getElementById('cards').innerHTML = riskCards(report.stations)
      .map(id => `<article class="card">${id}</article>`).join('');
  });
}
