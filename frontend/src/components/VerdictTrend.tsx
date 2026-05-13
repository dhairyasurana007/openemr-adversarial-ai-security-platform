export function VerdictTrend({
  points,
}: {
  points: Array<{ day: string; verdict: string; count: number }>;
}) {
  return (
    <ul style={{ margin: 0, paddingLeft: "1rem" }}>
      {points.map((point, idx) => (
        <li key={`${point.day}-${point.verdict}-${idx}`}>
          {new Date(point.day).toLocaleDateString()} | {point.verdict}: {point.count}
        </li>
      ))}
    </ul>
  );
}
