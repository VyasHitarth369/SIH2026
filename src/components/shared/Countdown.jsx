import { useEffect, useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';

export default function Countdown({ deadlineAt }) {
  const { lang } = useLanguage();
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  if (!deadlineAt) return null;
  const remaining = Math.max(0, deadlineAt - now);
  const days = Math.floor(remaining / (24 * 60 * 60 * 1000));
  const hours = Math.floor((remaining % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
  const mins = Math.floor((remaining % (60 * 60 * 1000)) / 60000);
  const secs = Math.floor((remaining % 60000) / 1000);

  let formattedRemaining = '';
  if (days > 0) {
    formattedRemaining = lang === 'hi'
      ? `${days} दिन ${hours} घंटे शेष`
      : `${days}d ${hours}h remaining`;
  } else if (hours > 0) {
    formattedRemaining = lang === 'hi'
      ? `${hours} घंटे ${mins} मिनट शेष`
      : `${hours}h ${mins}m remaining`;
  } else {
    formattedRemaining = lang === 'hi'
      ? `${mins}मि ${secs.toString().padStart(2, '0')}से शेष`
      : `${mins}m ${secs.toString().padStart(2, '0')}s remaining`;
  }

  const finalizingText = lang === 'hi' ? 'अंतिम रूप दिया जा रहा है…' : 'Finalizing…';

  return (
    <span className="countdown">
      {remaining > 0 ? formattedRemaining : finalizingText}
    </span>
  );
}
