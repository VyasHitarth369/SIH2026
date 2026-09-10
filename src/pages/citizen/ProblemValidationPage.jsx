import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '../../context/ToastContext';
import { useLanguage } from '../../context/LanguageContext';
import { commonProblemReasons } from '../../data/orgData';

export default function ProblemValidationPage() {
  const [searchParams] = useSearchParams();
  const problemId = searchParams.get('problemId');
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { lang } = useLanguage();

  const [selectedReasons, setSelectedReasons] = useState([]);
  const [explanation, setExplanation] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [validationState, setValidationState] = useState('idle'); // idle | checking | valid | needsReview

  const toggleReason = (reason) => {
    setSelectedReasons((prev) => (prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason]));
  };

  const submitReasons = () => {
    if (selectedReasons.length === 0 && !explanation.trim()) {
      showToast(<Trans text="Please select at least one reason or describe your problem." />);
      return;
    }
    setSubmitted(true);
    setValidationState('checking');

    // Frontend-only mock of an AI validation step. A real backend would
    // analyze the citizen's explanation for genuineness before routing the
    // problem onward — only the meaningful result is shown to the user.
    setTimeout(() => {
      const looksSubstantive = selectedReasons.length > 0 || explanation.trim().length > 25;
      setValidationState(looksSubstantive ? 'valid' : 'needsReview');
    }, 1600);
  };

  const proceed = () => {
    showToast(<Trans text="Your problem has been routed to Government and University Administration for review." />);
    navigate('/citizen/problems');
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Tell Us Why the Existing Solution Doesn't Work" />}</h1>
          <p>{<Trans text="This helps Government and University Administration understand why a new solution is needed." />}</p>
        </div>
      </div>

      {!submitted && (
        <div className="card">
          <h4>{<Trans text="Common Reasons" />}</h4>
          <div className="checkbox-list">
            {commonProblemReasons.map((reason) => (
              <label key={reason}>
                <input type="checkbox" checked={selectedReasons.includes(reason)} onChange={() => toggleReason(reason)} />
                <Trans text={reason} />
              </label>
            ))}
          </div>

          <div className="field">
            <label>{<Trans text="Explain your problem (optional but recommended)" />}</label>
            <textarea
              placeholder={lang === 'hi' ? 'अतिरिक्त विवरण जोड़ें जिससे समझाया जा सके कि मौजूदा समाधान आपके लिए क्यों काम नहीं करता...' : "Add any extra detail that helps explain why the existing solution doesn't work for you..."}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              rows={4}
            />
          </div>

          <button className="btn btn-primary btn-block" onClick={submitReasons}>{<Trans text="Submit Reasons" />}</button>
        </div>
      )}

      {submitted && (
        <div className="card">
          <h4>{<Trans text="Selected Reasons" />}</h4>
          <ul className="plain-list">
            {selectedReasons.map((r) => <li key={r}>• <Trans text={r} /></li>)}
          </ul>
          {explanation.trim() && <p className="problem-desc"><strong>{<Trans text="Additional detail:" />}</strong> {explanation}</p>}

          {validationState === 'checking' && (
            <div className="validation-box validation-box--checking">
              <span className="spinner" /> <Trans text="Checking reason…" />
            </div>
          )}
          {validationState === 'valid' && (
            <>
              <div className="validation-box validation-box--ok">{<Trans text="✅ Reason validated" />}</div>
              <p className="problem-desc">{<Trans text="Your explanation looks genuine and sufficiently detailed. Your problem can now proceed to Government and University Administration." />}</p>
              <button className="btn btn-primary btn-block" onClick={proceed}>{<Trans text="Continue" />}</button>
            </>
          )}
          {validationState === 'needsReview' && (
            <>
              <div className="validation-box validation-box--review">{<Trans text="⚠️ Reason requires review" />}</div>
              <p className="problem-desc">{<Trans text="Your explanation doesn't yet have enough detail. Please add more context about why the existing solution doesn't work for you." />}</p>
              <button className="btn btn-light" onClick={() => { setSubmitted(false); setValidationState('idle'); }}>{<Trans text="Improve My Explanation" />}</button>
            </>
          )}
        </div>
      )}

      {problemId && <p className="spoc-note">{lang === 'hi' ? `संबंधित समस्या आईडी: #${problemId}` : `Related problem ID: #${problemId}`}</p>}
    </div>
  );
}
