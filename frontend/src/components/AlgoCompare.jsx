import { useState } from "react";
import { api } from "../api/client";

/**
 * Dijkstra against A* on the same pair of junctions.
 *
 * This exists because the project's strongest claim was previously only
 * reachable by curling an endpoint: that A* explores measurably fewer nodes
 * AND returns exactly the same route. A claim you have to take on trust is
 * worth much less than one somebody can press a button and check.
 *
 * The two numbers that matter are next to each other on purpose. Equal
 * durations prove the heuristic never overestimates, so A* is not cutting
 * corners; fewer nodes expanded proves it is actually doing something. Either
 * one alone would be unconvincing.
 */
export default function AlgoCompare() {
  const [source, setSource] = useState(1);
  const [dest, setDest] = useState(300);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.compareRoute(source, dest);
      setData(res.comparison ?? res);
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setBusy(false);
    }
  };

  const saved =
    data && data.dijkstra.nodes_expanded > 0
      ? Math.round(
          ((data.dijkstra.nodes_expanded - data.astar.nodes_expanded) /
            data.dijkstra.nodes_expanded) *
            100
        )
      : 0;

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Dijkstra against A*</h2>
        <p className="note">
          Both searches run on the same road graph between the same two
          junctions. Junction ids run from 1 to 433.
        </p>
      </div>

      <form className="compare-form" onSubmit={run}>
        <label>
          From
          <input
            type="number"
            min="1"
            max="433"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          />
        </label>
        <label>
          To
          <input
            type="number"
            min="1"
            max="433"
            value={dest}
            onChange={(e) => setDest(e.target.value)}
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Running" : "Compare"}
        </button>
      </form>

      {error && <p className="warn-text">{error}</p>}

      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th className="col-grow">Algorithm</th>
                  <th className="numeric">Nodes expanded</th>
                  <th className="numeric">Route time</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="col-grow">Dijkstra</td>
                  <td className="numeric">{data.dijkstra.nodes_expanded}</td>
                  <td className="numeric">{data.dijkstra.duration_minutes} min</td>
                </tr>
                <tr>
                  <td className="col-grow">A*</td>
                  <td className="numeric">{data.astar.nodes_expanded}</td>
                  <td className="numeric">{data.astar.duration_minutes} min</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="compare-verdict">
            <p>
              <strong>
                A* explored {data.nodes_saved} fewer junctions
                {saved > 0 ? `, ${saved}% less work` : ""}.
              </strong>
            </p>
            <p className="sub">
              {data.same_duration
                ? "Both returned a route of the same duration. That is the part that matters: an admissible heuristic never overestimates, so A* reaches the genuine shortest path while skipping work Dijkstra could not."
                : "The durations differ, which should not happen with an admissible heuristic and means the heuristic is overestimating somewhere."}
            </p>
            <p className="note">
              Dispatch still uses Dijkstra. A* needs a single destination, and
              choosing a hospital means scoring all of them at once.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
