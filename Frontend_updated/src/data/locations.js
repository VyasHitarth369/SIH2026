export const jharkhandCities = [
  { value: 'Bokaro', hi: 'बोकारो', en: 'Bokaro' },
  { value: 'Chaibasa', hi: 'चाईबासा', en: 'Chaibasa' },
  { value: 'Chatra', hi: 'चतरा', en: 'Chatra' },
  { value: 'Deoghar', hi: 'देवघर', en: 'Deoghar' },
  { value: 'Dhanbad', hi: 'धनबाद', en: 'Dhanbad' },
  { value: 'Dumka', hi: 'दुमका', en: 'Dumka' },
  { value: 'Garhwa', hi: 'गढ़वा', en: 'Garhwa' },
  { value: 'Giridih', hi: 'गिरिडीह', en: 'Giridih' },
  { value: 'Godda', hi: 'गोड्डा', en: 'Godda' },
  { value: 'Gumla', hi: 'गुमला', en: 'Gumla' },
  { value: 'Hazaribagh', hi: 'हजारीबाग', en: 'Hazaribagh' },
  { value: 'Jamshedpur', hi: 'जमशेदपुर', en: 'Jamshedpur' },
  { value: 'Jamtara', hi: 'जामताड़ा', en: 'Jamtara' },
  { value: 'Khunti', hi: 'खूंटी', en: 'Khunti' },
  { value: 'Koderma', hi: 'कोडरमा', en: 'Koderma' },
  { value: 'Latehar', hi: 'लातेहार', en: 'Latehar' },
  { value: 'Lohardaga', hi: 'लोहरदगा', en: 'Lohardaga' },
  { value: 'Pakur', hi: 'पाकुड़', en: 'Pakur' },
  { value: 'Palamu', hi: 'पलामू', en: 'Palamu' },
  { value: 'Ramgarh', hi: 'रामगढ़', en: 'Ramgarh' },
  { value: 'Ranchi', hi: 'राँची', en: 'Ranchi' },
  { value: 'Sahebganj', hi: 'साहिबगंज', en: 'Sahebganj' },
  { value: 'Saraikela Kharsawan', hi: 'सरायकेला खरसावां', en: 'Saraikela Kharsawan' },
  { value: 'Simdega', hi: 'सिमडेगा', en: 'Simdega' },
];

export function cityLabel(value, lang) {
  const match = jharkhandCities.find((c) => c.value === value);
  if (!match) return value;
  return match[lang] || match.en;
}
