import React from 'react';

/**
 * VidySetu Standalone Logo & Mark Component
 *
 * Visual Concept:
 * - Graduation Cap (Knowledge / Academic Empowerment)
 * - Lightbulb Body with Glow Rays (Innovation & Problem Solving)
 * - Green Sprouting Leaves with Central Figure (Growth, Community, Building India)
 * - "Vidy" in Navy Blue + "Setu" in Emerald Green
 */
export function VidySetuMark({ size = 32, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 }}
      aria-label="VidySetu Logo Mark"
    >
      {/* Glow Rays (4 Radiating Light Rays) */}
      <line x1="16" y1="42" x2="8" y2="40" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />
      <line x1="19" y1="58" x2="11" y2="63" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />
      <line x1="84" y1="42" x2="92" y2="40" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />
      <line x1="81" y1="58" x2="89" y2="63" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />

      {/* Graduation Cap - Skull Base Under Mortarboard */}
      <path
        d="M 28 28 L 28 37 C 28 45, 72 45, 72 37 L 72 28 Z"
        fill="#0E387A"
      />

      {/* Graduation Cap - Mortarboard Diamond */}
      <path
        d="M 50 8 L 89 22 L 50 36 L 11 22 Z"
        fill="#154B9A"
      />
      <path
        d="M 50 8 L 89 22 L 50 25 L 11 22 Z"
        fill="#1E5BB5"
        opacity="0.5"
      />

      {/* Tassel Button & String */}
      <circle cx="50" cy="22" r="2.5" fill="#F59E0B" />
      <path
        d="M 50 22 Q 80 23 88 35 L 88 43"
        stroke="#0E387A"
        strokeWidth="2.2"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="88" cy="44" r="2" fill="#0E387A" />

      {/* Lightbulb Body - Left Green Leaf */}
      <path
        d="M 50 76 C 36 76 23 64 23 48 C 23 37 34 35 41 42 C 45 46 48 57 50 76 Z"
        fill="#10B981"
      />
      {/* Lightbulb Body - Right Green Leaf */}
      <path
        d="M 50 76 C 64 76 77 64 77 48 C 77 37 66 35 59 42 C 55 46 52 57 50 76 Z"
        fill="#059669"
      />

      {/* Central Learner / Innovator Figure (Student Head & Body) */}
      <circle cx="50" cy="45" r="6" fill="#0E387A" />
      <path
        d="M 46 54 C 46 63 48.5 71 50 76 C 51.5 71 54 63 54 54 C 52 56 48 56 46 54 Z"
        fill="#0E387A"
      />

      {/* Lightbulb Base (Threaded Collar) */}
      <rect x="40" y="80" width="20" height="4" rx="2" fill="#0E387A" />
      <rect x="43" y="86" width="14" height="3.5" rx="1.75" fill="#0E387A" />
      <path d="M 46 91.5 C 46 91, 54 91, 54 91.5 L 53 94.5 C 53 95.5, 47 95.5, 47 94.5 Z" fill="#154B9A" />
    </svg>
  );
}

export default function VidySetuLogo({
  size = 32,
  markOnly = false,
  showTagline = false,
  className = '',
  style = {},
  variant = 'default', // 'default' | 'dark' | 'light'
}) {
  const textColorNavy = variant === 'light' ? '#ffffff' : '#0E387A';
  const textColorGreen = variant === 'light' ? '#34D399' : '#059669';
  const taglineColor = variant === 'light' ? '#94A3B8' : '#64748B';

  if (markOnly) {
    return <VidySetuMark size={size} className={className} />;
  }

  return (
    <div
      className={`vidysetu-brand ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: Math.max(8, Math.round(size * 0.28)),
        textDecoration: 'none',
        lineHeight: 1,
        ...style,
      }}
    >
      <VidySetuMark size={size} />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span
          style={{
            fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
            fontWeight: 800,
            fontSize: Math.round(size * 0.72),
            letterSpacing: '-0.02em',
            display: 'inline-flex',
            alignItems: 'baseline',
          }}
        >
          <span style={{ color: textColorNavy }}>Vidy</span>
          <span style={{ color: textColorGreen }}>Setu</span>
        </span>
        {showTagline && (
          <span
            style={{
              fontSize: Math.max(10, Math.round(size * 0.26)),
              fontWeight: 500,
              color: taglineColor,
              letterSpacing: '0.01em',
              marginTop: 3,
            }}
          >
            Learn. Solve. Build a Smarter India.
          </span>
        )}
      </div>
    </div>
  );
}
