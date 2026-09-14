import Trans from './Trans.jsx';

// Lightweight, dependency-free SVG chart primitives used across the
// dashboards. No charting library is installed in this project, so
// these render plain, responsive SVG — no extra network/install needed.

const PALETTE = ['#1E4FD8', '#0E9C8F', '#EC9B1D', '#E1435C', '#7657F0', '#5AC8E8', '#93590E', '#4E36B8'];

/**
 * Horizontal bar chart. `data` = [{ label, value }]
 */
export function BarChart({ data, height, color = 'var(--primary)' }) {
  const rows = (data || []).filter((d) => d && d.label !== undefined);
  const max = Math.max(1, ...rows.map((d) => d.value || 0));
  const rowH = 30;
  const chartHeight = height || rows.length * rowH + 10;

  if (rows.length === 0) {
    return <p className="problem-desc"><Trans text="No data available yet." /></p>;
  }

  return (
    <div className="svg-chart">
      <svg viewBox={`0 0 320 ${chartHeight}`} width="100%" height={chartHeight} preserveAspectRatio="none" role="img">
        {rows.map((d, i) => {
          const y = i * rowH;
          const barW = Math.max(2, (d.value / max) * 210);
          return (
            <g key={d.label} transform={`translate(0, ${y})`}>
              <text x="0" y="12" fontSize="10.5" fill="var(--text)" fontWeight="600">
                {(d.label.length > 22 ? `${d.label.slice(0, 21)}…` : d.label)}
              </text>
              <rect x="0" y="18" width="210" height="8" rx="4" fill="var(--bg)" stroke="var(--border)" />
              <rect x="0" y="18" width={barW} height="8" rx="4" fill={d.color || color} />
              <text x="216" y="25" fontSize="11" fontWeight="700" fill="var(--text-muted)">{d.value}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/**
 * Donut (ring) chart with a legend. `data` = [{ label, value }]
 */
export function DonutChart({ data, size = 168, thickness = 26 }) {
  const rows = (data || []).filter((d) => d && (d.value || 0) > 0);
  const total = rows.reduce((sum, d) => sum + (d.value || 0), 0);

  if (total === 0) {
    return <p className="problem-desc"><Trans text="No data available yet." /></p>;
  }

  const r = (size - thickness) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  let offsetAcc = 0;

  return (
    <div className="donut-chart">
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--bg)" strokeWidth={thickness} />
        {rows.map((d, i) => {
          const frac = d.value / total;
          const dash = frac * circumference;
          const gap = circumference - dash;
          const circle = (
            <circle
              key={d.label}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={d.color || PALETTE[i % PALETTE.length]}
              strokeWidth={thickness}
              strokeDasharray={`${dash} ${gap}`}
              strokeDashoffset={-offsetAcc}
              transform={`rotate(-90 ${cx} ${cy})`}
              strokeLinecap={rows.length > 1 ? 'butt' : 'round'}
            />
          );
          offsetAcc += dash;
          return circle;
        })}
        <text x={cx} y={cy - 3} textAnchor="middle" fontSize="20" fontWeight="800" fill="var(--ink)">{total}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize="9.5" fill="var(--text-muted)"><Trans text="Total" /></text>
      </svg>
      <div className="donut-chart__legend">
        {rows.map((d, i) => (
          <div className="donut-chart__legend-row" key={d.label}>
            <span className="donut-chart__dot" style={{ background: d.color || PALETTE[i % PALETTE.length] }} />
            <span className="donut-chart__legend-label"><Trans text={d.label} /></span>
            <span className="donut-chart__legend-value">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
