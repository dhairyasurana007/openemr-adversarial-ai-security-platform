import { useQuery } from "@tanstack/react-query";

import { fetchSeeds } from "../api/service";

export function SeedManager() {
  const seeds = useQuery({ queryKey: ["seeds"], queryFn: fetchSeeds });

  if (seeds.isLoading) {
    return <div className="empty"><div className="empty-text">Loading seeds…</div></div>;
  }

  const items = seeds.data ?? [];

  return (
    <div className="card">
      <div className="card-title">Seed Cases — {items.length} techniques</div>
      {items.length === 0 ? (
        <div className="empty mt-2"><div className="empty-text">No taxonomy techniques loaded yet</div></div>
      ) : (
        <div className="table-wrap mt-2">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((seed) => (
                <tr key={seed.id}>
                  <td className="mono">{seed.id}</td>
                  <td><strong>{seed.name}</strong></td>
                  <td className="text-muted">{seed.category}</td>
                  <td><span className={`badge badge-${seed.severity_prior.toLowerCase()}`}>{seed.severity_prior}</span></td>
                  <td>
                    <span className={seed.deprecated ? "badge badge-failure" : "badge badge-success"}>
                      {seed.deprecated ? "Retired" : "Active"}
                    </span>
                  </td>
                  <td>
                    <div className="flex gap-1">
                      <button type="button" className="btn btn-secondary btn-xs">Promote</button>
                      {!seed.deprecated && (
                        <button type="button" className="btn btn-ghost btn-xs">Retire</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
