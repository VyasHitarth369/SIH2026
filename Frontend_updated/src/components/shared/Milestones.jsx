import Trans from './Trans.jsx';
import { getMilestones } from '../../utils/milestones';

export default function Milestones({ problem }) {
  const milestones = getMilestones(problem);
  const doneCount = milestones.filter((m) => m.done).length;

  return (
    <div className="milestones">
      <div className="milestones__head">
        <h4><Trans text="Project Milestones" /></h4>
        <span className="badge badge-blue">{doneCount}/{milestones.length} <Trans text="Complete" /></span>
      </div>
      <div className="milestones__list">
        {milestones.map((m, i) => {
          const isCurrent = !m.done && milestones.slice(0, i).every((prev) => prev.done);
          return (
            <div className={`milestone-item${m.done ? ' is-done' : ''}${isCurrent ? ' is-current' : ''}`} key={m.key}>
              <div className="milestone-item__dot">{m.done ? '✓' : i + 1}</div>
              <div className="milestone-item__body">
                <div className="milestone-item__label"><Trans text={m.label} /></div>
                {(m.date || m.detail) && (
                  <div className="milestone-item__meta">
                    {m.date && <span>{m.date}</span>}
                    {m.date && m.detail && ' · '}
                    {m.detail && <span>{m.detail}</span>}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
