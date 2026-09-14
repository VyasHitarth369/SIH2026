export const jharkhandCities = [
  { value: 'Ranchi', hi: 'राँची', en: 'Ranchi' },
  { value: 'Jamshedpur', hi: 'जमशेदपुर', en: 'Jamshedpur' },
  { value: 'Dhanbad', hi: 'धनबाद', en: 'Dhanbad' },
  { value: 'Bokaro', hi: 'बोकारो', en: 'Bokaro' },
  { value: 'Hazaribagh', hi: 'हजारीबाग', en: 'Hazaribagh' },
  { value: 'Deoghar', hi: 'देवघर', en: 'Deoghar' },
  { value: 'Giridih', hi: 'गिरिडीह', en: 'Giridih' },
  { value: 'Ramgarh', hi: 'रामगढ़', en: 'Ramgarh' },
];

export function cityLabel(value, lang) {
  const match = jharkhandCities.find((c) => c.value === value);
  if (!match) return value;
  return match[lang] || match.en;
}
