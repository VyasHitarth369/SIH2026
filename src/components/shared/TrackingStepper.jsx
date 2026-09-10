export default function TrackingStepper({ step, labels }) {
  const steps = [
    { n: 1, label: labels.stepVerified },
    { n: 2, label: labels.stepAssigned },
    { n: 3, label: labels.stepPrototype },
    { n: 4, label: labels.stepDeployed },
  ];

  return (
    <div className="tracking-stepper">
      {steps.map((s) => {
        const done = step >= s.n;
        const active = step === s.n - 1;
        return (
          <div className="tracking-step" key={s.n}>
            <div className={`tracking-step__icon${done ? ' is-done' : ''}${active ? ' is-active' : ''}`}>
              {done ? '✓' : s.n}
            </div>
            <div className="tracking-step__label">{s.label}</div>
          </div>
        );
      })}
    </div>
  );
}
