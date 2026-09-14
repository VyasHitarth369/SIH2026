import Trans, { translateText } from '../shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { roleFieldsConfig } from './roleFieldsConfig';

export default function RoleFields({ role, values, onChange }) {
  const { lang } = useLanguage();
  const fields = roleFieldsConfig[role] || [];
  if (fields.length === 0) return null;

  return (
    <div className="role-fields">
      {fields.map((f) => (
        <div className="field" key={f.key}>
          <label><Trans text={f.label} />{f.required ? ' *' : ''}</label>
          {f.type === 'select' ? (
            <select
              value={values[f.key] || ''}
              onChange={(e) => onChange(f.key, e.target.value)}
            >
              <option value="">{<Trans text="Select…" />}</option>
              {f.options.map((opt) => (
                <option key={opt} value={opt}>
                  {translateText(opt, lang)}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={values[f.key] || ''}
              onChange={(e) => onChange(f.key, e.target.value)}
              placeholder={translateText(f.label, lang)}
            />
          )}
        </div>
      ))}
    </div>
  );
}

export function validateRoleFields(role, values, lang = 'en') {
  const fields = roleFieldsConfig[role] || [];
  const missing = fields.filter((f) => f.required && !String(values[f.key] || '').trim());
  return missing.map((f) => translateText(f.label, lang));
}

export function normalizeRoleFields(role, values) {
  const fields = roleFieldsConfig[role] || [];
  const normalized = { ...values };
  fields.forEach((f) => {
    if (f.isList && typeof normalized[f.key] === 'string') {
      normalized[f.key] = normalized[f.key].split(',').map((s) => s.trim()).filter(Boolean);
    }
  });
  return normalized;
}
