export default function McqOption({ name, value, checked, onChange, icon, title, desc }) {
  return (
    <label className={`mcq-option${checked ? ' mcq-option--checked' : ''}`}>
      <input type="radio" name={name} value={value} checked={checked} onChange={() => onChange(value)} />
      <div>
        <strong>{icon} {title}</strong>
        <div className="mcq-option__desc">{desc}</div>
      </div>
    </label>
  );
}
