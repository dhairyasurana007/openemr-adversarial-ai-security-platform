import { useQuery } from "@tanstack/react-query";

import { fetchSeeds } from "../api/service";

export function SeedManager() {
  const seeds = useQuery({ queryKey: ["seeds"], queryFn: fetchSeeds });

  if (seeds.isLoading) {
    return <p>Loading seeds...</p>;
  }

  return (
    <section>
      <h3>Seed Manager</h3>
      <ul>
        {(seeds.data ?? []).map((seed) => (
          <li key={seed.id}>
            <strong>{seed.id}</strong> - {seed.name} ({seed.deprecated ? "RETIRED" : "ACTIVE"})
            <button type="button" style={{ marginLeft: "0.5rem" }}>
              Promote
            </button>
            <button type="button" style={{ marginLeft: "0.5rem" }}>
              Retire
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
