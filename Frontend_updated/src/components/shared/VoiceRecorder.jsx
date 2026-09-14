import { useRef, useState } from 'react';
import { uploadVoiceNote, revokeUploadUrl } from '../../services/uploadService';

export default function VoiceRecorder({ labels, onChange }) {
  const [status, setStatus] = useState('idle'); // idle | recording | uploading | done | error
  const [audioUrl, setAudioUrl] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const startRecording = async () => {
    setErrorMsg('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        if (audioUrl) revokeUploadUrl(audioUrl);
        setStatus('uploading');
        try {
          const uploaded = await uploadVoiceNote(blob);
          setAudioUrl(uploaded.url);
          setStatus('done');
          onChange?.(uploaded);
        } catch {
          setStatus('error');
          setErrorMsg('Could not save the recording. Please try again.');
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus('recording');
    } catch {
      setStatus('error');
      setErrorMsg('Microphone access was denied or is unavailable.');
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
  };

  const reRecord = () => {
    if (audioUrl) revokeUploadUrl(audioUrl);
    setAudioUrl(null);
    setStatus('idle');
    onChange?.(null);
  };

  return (
    <div className="voice-box">
      {status !== 'done' && (
        <button
          type="button"
          className={`btn ${status === 'recording' ? 'btn-danger' : 'btn-light'} btn-block`}
          onClick={status === 'recording' ? stopRecording : startRecording}
        >
          {status === 'recording' ? labels.stop : status === 'uploading' ? '⏳…' : labels.start}
        </button>
      )}

      {status === 'recording' && <div className="voice-box__rec">● {labels.recordingHint || 'Recording…'}</div>}

      {status === 'done' && audioUrl && (
        <div className="voice-box__playback">
          <audio src={audioUrl} controls />
          <button type="button" className="btn btn-light btn-sm" onClick={reRecord}>{labels.rerecord}</button>
        </div>
      )}

      {errorMsg && <div className="voice-box__error">{errorMsg}</div>}
    </div>
  );
}
