import Trans from './Trans.jsx';
import { useEffect, useRef, useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Voice Assistant for the problem-description field.
 *
 * Unlike VoiceRecorder (which records an audio *attachment*), this
 * component uses the browser's native SpeechRecognition API to convert
 * speech directly into editable text, which the caller inserts into the
 * problem description field in real time.
 */
export default function SpeechToText({ onTranscript }) {
  const { lang } = useLanguage();
  const [state, setState] = useState('idle'); // idle | listening | error | unsupported
  const [errorMsg, setErrorMsg] = useState('');
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setState('unsupported');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';

    recognition.onresult = (event) => {
      let finalText = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalText += event.results[i][0].transcript;
        }
      }
      if (finalText.trim()) onTranscript(finalText.trim());
    };

    recognition.onerror = (event) => {
      setState('error');
      setErrorMsg(
        event.error === 'not-allowed' || event.error === 'permission-denied'
          ? 'Microphone permission was denied. Please allow microphone access and try again.'
          : 'Speech recognition is currently unavailable. Please type your description instead.'
      );
    };

    recognition.onend = () => {
      setState((prev) => (prev === 'listening' ? 'idle' : prev));
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  const start = async () => {
    setErrorMsg('');
    try {
      // Explicitly request microphone permission so the browser prompt
      // appears even on browsers that don't prompt for SpeechRecognition alone.
      await navigator.mediaDevices.getUserMedia({ audio: true });
      recognitionRef.current?.start();
      setState('listening');
    } catch {
      setState('error');
      setErrorMsg('Microphone access was denied or is unavailable.');
    }
  };

  const stop = () => {
    recognitionRef.current?.stop();
    setState('idle');
  };

  if (state === 'unsupported') {
    return (
      <div className="voice-assistant voice-assistant--unsupported">
        <span className="voice-assistant__icon">🎤</span>
        <div>
          <strong>{<Trans text="Voice Assistant unavailable" />}</strong>
          <p>{<Trans text="Speech recognition is not supported in this browser. Please type your problem description manually below." />}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="voice-assistant">
      <div className="voice-assistant__row">
        <button
          type="button"
          className={`btn ${state === 'listening' ? 'btn-danger' : 'btn-primary'} btn-block`}
          onClick={state === 'listening' ? stop : start}
        >
          {state === 'listening'
            ? (lang === 'hi' ? '⏹ रिकॉर्डिंग रोकें' : '⏹ Stop Recording')
            : (lang === 'hi' ? '🎤 अपनी समस्या बोलें' : '🎤 Speak Your Problem')}
        </button>
      </div>
      {state === 'listening' && (
        <div className="voice-assistant__status voice-assistant__status--live">
          <span className="voice-assistant__dot" /> {lang === 'hi' ? 'सुन रहे हैं… अब बोलें, समस्या का विवरण अपने आप भर जाएगा।' : 'Listening… speak now, the description field will fill in automatically.'}
        </div>
      )}
      {state === 'idle' && !errorMsg && (
        <div className="voice-assistant__status">
          {lang === 'hi' ? 'बटन दबाकर बोलें — आपके शब्द नीचे विवरण बॉक्स में दर्ज होंगे। आप बाद में टेक्स्ट संपादित कर सकते हैं।' : 'Tap the button and speak — your words will appear in the description field below. You can edit the text afterwards.'}
        </div>
      )}
      {state === 'error' && <div className="voice-assistant__status voice-assistant__status--error">{<Trans text={errorMsg} />}</div>}
    </div>
  );
}
