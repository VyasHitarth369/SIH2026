import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import FileUploadField from '../../components/shared/FileUploadField';
import SpeechToText from '../../components/shared/SpeechToText';
import McqOption from '../../components/shared/McqOption';
import { jharkhandCities, cityLabel } from '../../data/locations';
import { submitChallenge } from '../../services/challengeService';

export default function AddProblemPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const { addProblem } = useProblems();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [city, setCity] = useState(jharkhandCities[0].value);
  const [address, setAddress] = useState('');
  const [pincode, setPincode] = useState('');
  const [scope, setScope] = useState('Area Specific');
  const [attachments, setAttachments] = useState({ photo: null, video: null, document: null });
  const [submitting, setSubmitting] = useState(false);

  const setAttachment = (kind) => (value) => {
    setAttachments((prev) => ({ ...prev, [kind]: value }));
  };

  // Voice Assistant transcript is appended into the description field so the
  // citizen can keep speaking, pause, and continue editing manually.
  const handleTranscript = (text) => {
    setDesc((prev) => (prev ? `${prev} ${text}` : text));
  };

  const handleSubmit = async () => {
    if (!title.trim() || !desc.trim() || !address.trim()) {
      showToast(t.fillRequired);
      return;
    }
    if (!/^\d{6}$/.test(pincode.trim())) {
      showToast(t.pincodeInvalid);
      return;
    }

    const files = Object.entries(attachments)
      .filter(([, v]) => v)
      .map(([kind, v]) => ({ kind, ...v }));

    const composedLoc = `${address.trim()}, ${cityLabel(city, lang)} - ${pincode.trim()}`;

    const isGov = user?.role === 'government';
    const isInd = user?.role === 'industry';
    const source = isGov ? 'government' : isInd ? 'industry' : 'citizen';
    const category = isGov ? 'Government Problem' : isInd ? 'Industry Problem' : 'Civic Issue';

    setSubmitting(true);
    let createdChallenge = null;

    try {
      // Post to FastAPI backend which inserts into Supabase challenges table
      createdChallenge = await submitChallenge({
        title: title.trim(),
        description: desc.trim(),
        location: composedLoc,
        city,
        district: city,
        address: address.trim(),
        pincode: pincode.trim(),
        impact_scope: scope, // strictly impact_scope, NOT impact_score
        photo: attachments.photo?.url || null,
        video: attachments.video?.url || null,
        document: attachments.document?.url || null,
        submitted_by: user?.email || user?.name || source,
        status: 'unsolved',
        user_id: user?.email || null,
      });
    } catch (err) {
      console.warn('Backend submission warning:', err.message);
    } finally {
      setSubmitting(false);
    }

    const newId = addProblem({
      id: createdChallenge?.challenge_id || createdChallenge?.id,
      title: { [lang]: title.trim(), hi: title.trim(), en: title.trim() },
      desc: { [lang]: desc.trim(), hi: desc.trim(), en: desc.trim() },
      loc: composedLoc,
      city,
      district: city,
      address: address.trim(),
      pincode: pincode.trim(),
      category,
      domain: isGov ? 'Government Initiative' : isInd ? 'Industry Innovation' : 'General Civic',
      expertise: isGov ? 'Public Administration' : isInd ? 'Industrial Development' : 'General Civic',
      scope,
      source,
      attachments: files,
      rawSupabase: createdChallenge,
    });

    showToast(t.submitted);

    if (isGov) {
      navigate('/government/active-problems');
    } else if (isInd) {
      navigate('/industry-employee/dashboard');
    } else {
      // Rather than dropping the citizen straight back into the problem list,
      // take them to a dedicated global-search page to check whether a
      // solution already exists for a similar problem (Section 18).
      navigate(`/global-search?problemId=${newId}`);
    }
  };

  const getPageHeading = () => {
    if (user?.role === 'government') {
      return lang === 'hi' ? '🏛️ नई सरकारी समस्या दर्ज करें' : '🏛️ Report Government Problem';
    }
    if (user?.role === 'industry') {
      return lang === 'hi' ? '🏢 नई उद्योग समस्या दर्ज करें' : '🏢 Report Industry Problem';
    }
    return t.addProblemTitle;
  };

  return (
    <div>
      <div className="page-head"><h1>{getPageHeading()}</h1></div>

      <div className="card">
        <div className="field">
          <label>{t.fieldTitle}</label>
          <input type="text" placeholder={t.fieldTitlePh} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>

        <label className="section-box__label" style={{ display: 'block', marginBottom: 4 }}>{<Trans text="Voice Assistant" />}</label>
        <SpeechToText onTranscript={handleTranscript} />

        <div className="field">
          <label>{t.fieldDesc}</label>
          <textarea placeholder={t.fieldDescPh} value={desc} onChange={(e) => setDesc(e.target.value)} rows={5} />
        </div>

        <div className="section-box">
          <h4>{t.locationHead}</h4>

          <div className="grid grid--location">
            <div className="field">
              <label>{t.fieldCity}</label>
              <select value={city} onChange={(e) => setCity(e.target.value)}>
                {jharkhandCities.map((c) => (
                  <option key={c.value} value={c.value}>{c[lang] || c.en}</option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>{t.fieldAddress}</label>
              <input type="text" placeholder={t.fieldAddressPh} value={address} onChange={(e) => setAddress(e.target.value)} />
            </div>

            <div className="field">
              <label>{t.fieldPincode}</label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder={t.fieldPincodePh}
                value={pincode}
                onChange={(e) => setPincode(e.target.value.replace(/\D/g, ''))}
              />
            </div>
          </div>

          <div className="field" style={{ marginBottom: 0 }}>
            <label>{t.scopeLabel}</label>
            <div className="mcq-grid">
              <McqOption
                name="scope" value="Area Specific" checked={scope === 'Area Specific'} onChange={setScope}
                icon="🏡" title={t.scopeArea} desc={t.scopeAreaDesc}
              />
              <McqOption
                name="scope" value="City Specific" checked={scope === 'City Specific'} onChange={setScope}
                icon="🏙️" title={t.scopeCity} desc={t.scopeCityDesc}
              />
            </div>
          </div>
        </div>

        <div className="section-box section-box--muted">
          <h4>{t.mediaHead}</h4>
          <div className="grid grid--uploads">
            <FileUploadField label={t.uploadPhoto} accept="image/*" kind="photo" dragLabel={t.dragDrop} onChange={setAttachment('photo')} />
            <FileUploadField label={t.uploadVideo} accept="video/*" kind="video" dragLabel={t.dragDrop} onChange={setAttachment('video')} />
            <FileUploadField label={t.uploadDoc} accept=".pdf,.doc,.docx" kind="document" dragLabel={t.dragDrop} onChange={setAttachment('document')} />
          </div>
        </div>

        <button className="btn btn-primary btn-block" disabled={submitting} onClick={handleSubmit}>
          {submitting ? (lang === 'hi' ? 'जमा कर रहे हैं…' : 'Submitting…') : `${t.submitProblem} →`}
        </button>
      </div>
    </div>
  );
}
