import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useToast } from '../../context/ToastContext';
import FileUploadField from '../../components/shared/FileUploadField';
import SpeechToText from '../../components/shared/SpeechToText';
import McqOption from '../../components/shared/McqOption';
import { jharkhandCities } from '../../data/locations';

// Fixed demo definitions strictly per specification
const DEMO_CASES = {
  case1: {
    id: 'demo-p1',
    caseKey: 'case1',
    title: 'Road Potholes & Streetlight Automation',
    titleHi: 'सड़क के गड्ढे एवं स्ट्रीटलाइट स्वचालन',
    desc: 'Highway lighting failure is causing accidents at night.',
    descHi: 'रात में राजमार्ग की लाइट खराब होने से दुर्घटनाएं हो रही हैं।',
    city: 'Jamshedpur',
    address: 'NH-33 Highway Stretch, Near Dimna Lake Chowk',
    pincode: '831012',
    scope: 'City Specific',
    solution: {
      title: 'Smart Highway Streetlight Monitoring & Automation',
      titleHi: 'स्मार्ट हाईवे स्ट्रीटलाइट मॉनिटरिंग एवं ऑटोमेशन',
      description: 'An existing smart streetlight solution uses light sensors and GIS-based monitoring to detect lighting failures and identify affected road locations.',
      descriptionHi: 'एक मौजूदा स्मार्ट स्ट्रीटलाइट समाधान लाइट सेंसर और जीआईएस-आधारित निगरानी का उपयोग करके प्रकाश की विफलता का पता लगाता है और प्रभावित सड़क स्थानों की पहचान करता है।',
      technologies: ['Light Sensors', 'GIS Mapping', 'Automated Streetlight Monitoring'],
      technologiesHi: ['लाइट सेंसर्स', 'जीआईएस मैपिंग', 'स्वचालित स्ट्रीटलाइट निगरानी'],
      whyRelevant: 'The solution addresses highway lighting failures and can help identify and monitor faulty streetlights.',
      whyRelevantHi: 'यह समाधान राजमार्ग प्रकाश विफलताओं का समाधान करता है और दोषपूर्ण स्ट्रीटलाइट्स की पहचान एवं निगरानी में मदद कर सकता है।',
    },
  },
  case2: {
    id: 'demo-p2',
    caseKey: 'case2',
    title: 'Need a air purification system',
    titleHi: 'वायु शोधन प्रणाली की आवश्यकता है',
    desc: 'In our area the air is very polluted we need to purify the air and want it to be adorable',
    descHi: 'हमारे क्षेत्र में हवा बहुत प्रदूषित है, हमें हवा को शुद्ध करने की आवश्यकता है और हम चाहते हैं कि यह किफायती और टिकाऊ हो',
    city: 'Bokaro',
    address: 'Harmu road',
    pincode: '827001',
    scope: 'Area Specific',
    solution: {
      title: 'Community Air Purification / Filtration System',
      titleHi: 'सामुदायिक वायु शोधन एवं निस्पंदन प्रणाली',
      description: 'A localized air purification solution using filtration and air-quality monitoring to improve indoor or community-level air quality.',
      descriptionHi: 'इनडोर या सामुदायिक स्तर की वायु गुणवत्ता में सुधार के लिए निस्पंदन और वायु-गुणवत्ता निगरानी का उपयोग करने वाला एक स्थानीय वायु शोधन समाधान।',
      technologies: ['Localized Air Filtration', 'Particulate Matter (PM2.5/PM10) Sensors', 'Community Monitoring'],
      technologiesHi: ['स्थानीय वायु निस्पंदन', 'पार्टिकुलेट मैटर (PM2.5/PM10) सेंसर्स', 'सामुदायिक निगरानी'],
      whyRelevant: 'The solution provides localized air filtration to address ambient air pollution in residential and community areas.',
      whyRelevantHi: 'यह समाधान आवासीय और सामुदायिक क्षेत्रों में परिवेशी वायु प्रदूषण को दूर करने के लिए स्थानीय वायु निस्पंदन प्रदान करता है।',
    },
  },
};

const REJECTION_REASONS = [
  {
    en: 'The existing solution is too expensive',
    hi: 'मौजूदा समाधान बहुत महंगा है',
  },
  {
    en: 'The solution does not cover the required area',
    hi: 'समाधान आवश्यक क्षेत्र को कवर नहीं करता है',
  },
  {
    en: 'The solution does not solve the actual problem',
    hi: 'समाधान वास्तविक समस्या का समाधान नहीं करता है',
  },
  {
    en: 'The solution is not suitable for local conditions',
    hi: 'समाधान स्थानीय परिस्थितियों के लिए उपयुक्त नहीं है',
  },
  {
    en: 'The existing solution is difficult to maintain',
    hi: 'मौजूदा समाधान का रखरखाव कठिन है',
  },
  {
    en: 'Other reason',
    hi: 'अन्य कारण',
  },
];

export default function DemoProblemSolutionsPage() {
  const { t, lang } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'add-problem';

  // Active Demo Case State ('case1' or 'case2')
  const [activeCaseKey, setActiveCaseKey] = useState('case1');
  const currentDemo = DEMO_CASES[activeCaseKey];

  // Screen View State: 'form' | 'solutions'
  const [screenView, setScreenView] = useState('form');

  // Form Field States
  const [title, setTitle] = useState(currentDemo.title);
  const [desc, setDesc] = useState(currentDemo.desc);
  const [city, setCity] = useState(currentDemo.city);
  const [address, setAddress] = useState(currentDemo.address);
  const [pincode, setPincode] = useState(currentDemo.pincode);
  const [scope, setScope] = useState(currentDemo.scope);
  const [attachments, setAttachments] = useState({ photo: null, video: null, document: null });

  // Optional GPS Location State
  const [gpsMessage, setGpsMessage] = useState('');
  const [gpsStatus, setGpsStatus] = useState('');

  // Deterministic Demo Flow States
  const [showCaseModal, setShowCaseModal] = useState(true);
  const [analyzingProblem, setAnalyzingProblem] = useState(false);
  const [solutionFound, setSolutionFound] = useState(false);
  const [solutionAccepted, setSolutionAccepted] = useState(false);
  const [showRejectionForm, setShowRejectionForm] = useState(false);
  const [selectedReasons, setSelectedReasons] = useState([]);
  const [additionalExplanation, setAdditionalExplanation] = useState('');
  const [validatingReason, setValidatingReason] = useState(false);
  const [reasonValidated, setReasonValidated] = useState(false);
  const [demoCompleted, setDemoCompleted] = useState(false);

  // Switch between Demo Cases
  const handleCaseChange = (caseKey) => {
    const c = DEMO_CASES[caseKey];
    setActiveCaseKey(caseKey);
    setTitle(c.title);
    setDesc(c.desc);
    setCity(c.city);
    setAddress(c.address);
    setPincode(c.pincode);
    setScope(c.scope);
    setAttachments({ photo: null, video: null, document: null });
    setGpsMessage('');
    setGpsStatus('');
    setShowCaseModal(false);
    setScreenView('form');

    // Reset flow states
    setAnalyzingProblem(false);
    setSolutionFound(false);
    setSolutionAccepted(false);
    setShowRejectionForm(false);
    setSelectedReasons([]);
    setAdditionalExplanation('');
    setValidatingReason(false);
    setReasonValidated(false);
    setDemoCompleted(false);
  };

  const handleDetectLocation = () => {
    setGpsStatus('detecting');
    setGpsMessage(lang === 'hi' ? 'स्थान खोज रहे हैं…' : 'Detecting your location…');
    setTimeout(() => {
      setGpsStatus('captured');
      const lat = activeCaseKey === 'case1' ? 22.8046 : 23.6693;
      const lng = activeCaseKey === 'case1' ? 86.2029 : 86.1511;
      setGpsMessage(
        lang === 'hi'
          ? `📍 जीपीएस निर्देशांक: ${lat.toFixed(4)}°, ${lng.toFixed(4)}° (${city})`
          : `📍 GPS captured: ${lat.toFixed(4)}°, ${lng.toFixed(4)}° (${city})`
      );
    }, 400);
  };

  const setAttachment = (kind) => (value) => {
    setAttachments((prev) => ({ ...prev, [kind]: value }));
  };

  const handleTranscript = (text) => {
    setDesc((prev) => (prev ? `${prev} ${text}` : text));
  };

  // Submit Problem -> Transitions to NEW SCREEN ("Existing Solutions in Your Area")
  const handleSubmitProblem = () => {
    if (!title.trim() || !desc.trim() || !address.trim()) {
      showToast(t.fillRequired || 'Please fill in all required fields.');
      return;
    }

    // Switch to new solutions screen matching the screenshot
    setScreenView('solutions');
    setAnalyzingProblem(true);
    setSolutionFound(false);
    setSolutionAccepted(false);
    setShowRejectionForm(false);
    setReasonValidated(false);
    setDemoCompleted(false);

    // Scroll to top of the new screen
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Deterministic delay simulating AI search
    setTimeout(() => {
      setAnalyzingProblem(false);
      setSolutionFound(true);
    }, 1200);
  };

  // CASE 1: Accept Existing Solution
  const handleAcceptSolution = () => {
    setSolutionAccepted(true);
    showToast(
      lang === 'hi'
        ? 'मौजूदा समाधान सफलतापूर्वक स्वीकार किया गया!'
        : 'Existing solution accepted for this problem!'
    );
  };

  // CASE 2: Not Suitable -> Open reasons form (blank for user to manually fill)
  const handleRejectSolution = () => {
    setShowRejectionForm(true);
    setSelectedReasons([]);
    setAdditionalExplanation('');
  };

  const toggleReason = (reasonEn) => {
    setSelectedReasons((prev) =>
      prev.includes(reasonEn) ? prev.filter((r) => r !== reasonEn) : [...prev, reasonEn]
    );
  };

  // CASE 2: Submit Rejection Reason for AI Validation
  const handleSubmitRejectionReason = () => {
    if (selectedReasons.length === 0 && !additionalExplanation.trim()) {
      showToast(
        lang === 'hi'
          ? 'कृपया कम से कम एक कारण चुनें या विवरण दें।'
          : 'Please select at least one reason or provide an explanation.'
      );
      return;
    }

    setValidatingReason(true);

    setTimeout(() => {
      setValidatingReason(false);
      setReasonValidated(true);
      showToast(
        lang === 'hi'
          ? '✓ आपका कारण सफलतापूर्वक सत्यापित हुआ!'
          : '✓ Your rejection reason has been validated by AI!'
      );
    }, 1100);
  };

  // Continue with My Problem
  const handleContinueWithProblem = () => {
    setDemoCompleted(true);
    showToast(
      lang === 'hi'
        ? 'आपकी समस्या नए समाधान हेतु आगे बढ़ा दी गई है।'
        : 'Your problem has been registered and forwarded for further evaluation.'
    );
  };

  // Pop-up Scenario Selection Modal (displays both Option 1 and Option 2 prominently)
  const renderCaseModal = () => {
    if (!showCaseModal) return null;
    return (
      <div className="modal-overlay" onClick={() => setShowCaseModal(false)}>
        <div
          className="modal-box"
          onClick={(e) => e.stopPropagation()}
          style={{ maxWidth: 620, padding: '26px 28px', borderRadius: 14 }}
        >
          <button
            className="modal-box__close"
            onClick={() => setShowCaseModal(false)}
            aria-label="Close"
          >
            ✕
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span style={{ fontSize: 24 }}>⚡</span>
            <h3 className="modal-box__name" style={{ margin: 0, fontSize: 20 }}>
              {lang === 'hi' ? 'डेमो परिदृश्य चुनें (Select Demo Scenario)' : 'Select Demo Scenario'}
            </h3>
          </div>
          <p style={{ fontSize: 13.5, color: 'var(--text-muted)', marginBottom: 18, lineHeight: 1.45 }}>
            {lang === 'hi'
              ? 'कृपया नीचे दिए गए दो निश्चित परिदृश्यों में से एक चुनें। फॉर्म स्वतः भर जाएगा और आप निर्धारित एआई समाधान प्रवाह का परीक्षण कर सकते हैं:'
              : 'Choose one of the two demo scenarios below. The form will load automatically to test the AI solution flow:'}
          </p>

          {/* Option 1 Card */}
          <div
            className="card"
            style={{
              cursor: 'pointer',
              marginBottom: 16,
              padding: '16px 18px',
              border: '2px solid var(--border)',
              borderLeft: '5px solid #0d9488',
              borderRadius: 12,
              background: activeCaseKey === 'case1' ? '#f0fdfa' : '#fff',
              transition: 'all .15s ease',
            }}
            onClick={() => handleCaseChange('case1')}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
              <span className="badge badge-teal" style={{ fontWeight: 700, fontSize: 12 }}>
                ✓ {lang === 'hi' ? 'विकल्प 1: समाधान स्वीकृत प्रवाह' : 'Option 1: Solution Accepted Flow'}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                📍 Jamshedpur, Jharkhand
              </span>
            </div>
            <h4 style={{ fontSize: 16, color: 'var(--ink)', margin: '4px 0 6px', fontWeight: 700 }}>
              Road Potholes & Streetlight Automation
            </h4>
            <p style={{ fontSize: 13, color: 'var(--text)', margin: '0 0 10px', lineHeight: 1.45 }}>
              Highway lighting failure is causing accidents at night.
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 10, borderTop: '1px solid rgba(0,0,0,0.06)', flexWrap: 'wrap', gap: 8 }}>
              <span style={{ fontSize: 12, color: '#0f766e', fontWeight: 600 }}>
                ⚡ {lang === 'hi' ? 'एआई मौजूदा समाधान ढूंढता है → नागरिक स्वीकार करता है' : 'AI finds existing solution → Citizen accepts'}
              </span>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCaseChange('case1');
                }}
              >
                {lang === 'hi' ? 'विकल्प 1 चुनें →' : 'Select Option 1 →'}
              </button>
            </div>
          </div>

          {/* Option 2 Card */}
          <div
            className="card"
            style={{
              cursor: 'pointer',
              marginBottom: 4,
              padding: '16px 18px',
              border: '2px solid var(--border)',
              borderLeft: '5px solid #ea580c',
              borderRadius: 12,
              background: activeCaseKey === 'case2' ? '#fff7ed' : '#fff',
              transition: 'all .15s ease',
            }}
            onClick={() => handleCaseChange('case2')}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
              <span className="badge badge-coral" style={{ fontWeight: 700, fontSize: 12 }}>
                🚫 {lang === 'hi' ? 'विकल्प 2: अस्वीकृति एवं एआई सत्यापन प्रवाह' : 'Option 2: Rejection & AI Validated Flow'}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                📍 Harmu road, Bokaro - 827001
              </span>
            </div>
            <h4 style={{ fontSize: 16, color: 'var(--ink)', margin: '4px 0 6px', fontWeight: 700 }}>
              Need a air purification system
            </h4>
            <p style={{ fontSize: 13, color: 'var(--text)', margin: '0 0 10px', lineHeight: 1.45 }}>
              In our area the air is very polluted we need to purify the air and want it to be adorable
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 10, borderTop: '1px solid rgba(0,0,0,0.06)', flexWrap: 'wrap', gap: 8 }}>
              <span style={{ fontSize: 12, color: '#c2410c', fontWeight: 600 }}>
                ⚡ {lang === 'hi' ? 'उपयुक्त नहीं → नागरिक कारण भरें → एआई कारण सत्यापित करे' : 'Not suitable → Citizen fills custom reasons → AI validates'}
              </span>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCaseChange('case2');
                }}
              >
                {lang === 'hi' ? 'विकल्प 2 चुनें →' : 'Select Option 2 →'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  /* ------------------------------------------------------------------------- */
  /* TAB: MY PROBLEMS (Zero Auth Required)                                    */
  /* ------------------------------------------------------------------------- */
  if (currentTab === 'problems') {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>{lang === 'hi' ? '🔎 मेरी समस्याएं' : '🔎 My Problems'}</h1>
            <p>
              {lang === 'hi'
                ? 'नागरिक पोर्टल - दर्ज की गई समस्याओं की स्थिति एवं समाधान ट्रैक करें'
                : 'Citizen Portal — Track status and progress of reported problems'}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setScreenView('form');
              navigate('/demo/problem-solutions');
            }}
          >
            ➕ {lang === 'hi' ? 'नई समस्या दर्ज करें' : 'Submit New Problem'}
          </button>
        </div>

        {/* Problem Card: Case 1 */}
        <div className="card" style={{ borderLeft: '4px solid var(--teal)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
            <span className="badge badge-teal">✓ {lang === 'hi' ? 'मौजूदा समाधान स्वीकृत' : 'Existing Solution Accepted'}</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>📍 Jamshedpur, Jharkhand</span>
          </div>
          <h3 className="problem-title" style={{ fontSize: 17, color: 'var(--ink)' }}>
            Road Potholes & Streetlight Automation
          </h3>
          <p className="problem-desc" style={{ marginTop: 4 }}>
            Highway lighting failure is causing accidents at night.
          </p>
          <div className="section-box section-box--muted" style={{ marginTop: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--teal-dark)' }}>
              🔗 {lang === 'hi' ? 'स्वीकृत समाधान: ' : 'Accepted Solution: '}
              <span style={{ color: 'var(--ink)' }}>Smart Highway Streetlight Monitoring & Automation</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              Technologies: Light Sensors, GIS Mapping · Status: Approved for Deployment
            </div>
          </div>
          <div className="tracking-box" style={{ marginTop: 10 }}>
            <div className="tracking-stepper">
              <div className="tracking-step">
                <div className="tracking-step__icon is-done">✓</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'दर्ज' : 'Submitted'}</div>
              </div>
              <div className="tracking-step">
                <div className="tracking-step__icon is-done">✓</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'एआई विश्लेषण' : 'AI Review'}</div>
              </div>
              <div className="tracking-step">
                <div className="tracking-step__icon is-done">✓</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'समाधान मिलान' : 'Solution Matched'}</div>
              </div>
              <div className="tracking-step">
                <div className="tracking-step__icon is-active">⚡</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'कार्यान्वयन' : 'Deployment'}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Problem Card: Case 2 */}
        <div className="card" style={{ borderLeft: '4px solid var(--primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
            <span className="badge badge-blue">⏳ {lang === 'hi' ? 'सत्यापित नवीन समस्या' : 'Validated Novel Problem'}</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>📍 Harmu road, Bokaro - 827001</span>
          </div>
          <h3 className="problem-title" style={{ fontSize: 17, color: 'var(--ink)' }}>
            Need a air purification system
          </h3>
          <p className="problem-desc" style={{ marginTop: 4 }}>
            In our area the air is very polluted we need to purify the air and want it to be adorable
          </p>
          <div className="section-box section-box--muted" style={{ marginTop: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12.5, fontWeight: 700, color: '#1e40af' }}>
              ℹ️ {lang === 'hi' ? 'एआई स्थिति: ' : 'AI Status: '}
              <span style={{ color: 'var(--text)' }}>
                Rejection of generic solution validated. Forwarded to university researchers for localized design.
              </span>
            </div>
          </div>
          <div className="tracking-box" style={{ marginTop: 10 }}>
            <div className="tracking-stepper">
              <div className="tracking-step">
                <div className="tracking-step__icon is-done">✓</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'दर्ज' : 'Submitted'}</div>
              </div>
              <div className="tracking-step">
                <div className="tracking-step__icon is-done">✓</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'एआई विश्लेषण' : 'AI Review'}</div>
              </div>
              <div className="tracking-step">
                <div className="tracking-step__icon is-done">✓</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'कारण सत्यापित' : 'Reason Validated'}</div>
              </div>
              <div className="tracking-step">
                <div className="tracking-step__icon is-active">🏫</div>
                <div className="tracking-step__label">{lang === 'hi' ? 'विश्वविद्यालय आवंटन' : 'University R&D'}</div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            type="button"
            className="btn btn-light"
            onClick={() => {
              setScreenView('form');
              navigate('/demo/problem-solutions');
            }}
          >
            ← {lang === 'hi' ? 'डेमो फॉर्म पर वापस जाएं' : 'Back to Problem Form'}
          </button>
        </div>
      </div>
    );
  }

  /* ------------------------------------------------------------------------- */
  /* TAB: ALL PROBLEMS                                                        */
  /* ------------------------------------------------------------------------- */
  if (currentTab === 'all-problems') {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>{lang === 'hi' ? '🌐 सभी नागरिक समस्याएं' : '🌐 All Civic Problems'}</h1>
            <p>
              {lang === 'hi'
                ? 'झारखंड भर से नागरिकों द्वारा दर्ज की गई सार्वजनिक समस्याएं'
                : 'Public civic issues reported across Jharkhand'}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setScreenView('form');
              navigate('/demo/problem-solutions');
            }}
          >
            ➕ {lang === 'hi' ? 'नई समस्या दर्ज करें' : 'Submit New Problem'}
          </button>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span className="badge badge-amber">⚡ Active Case 1</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>📍 Jamshedpur</span>
          </div>
          <h3 className="problem-title">Road Potholes & Streetlight Automation</h3>
          <p className="problem-desc">Highway lighting failure is causing accidents at night.</p>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span className="badge badge-amber">⚡ Active Case 2</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>📍 Bokaro</span>
          </div>
          <h3 className="problem-title">Need a air purification system</h3>
          <p className="problem-desc">In our area the air is very polluted we need to purify the air and want it to be adorable</p>
        </div>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            type="button"
            className="btn btn-light"
            onClick={() => {
              setScreenView('form');
              navigate('/demo/problem-solutions');
            }}
          >
            ← {lang === 'hi' ? 'डेमो फॉर्म पर वापस जाएं' : 'Back to Problem Form'}
          </button>
        </div>
      </div>
    );
  }

  /* ------------------------------------------------------------------------- */
  /* TAB: PROFILE                                                             */
  /* ------------------------------------------------------------------------- */
  if (currentTab === 'profile') {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>{lang === 'hi' ? '👤 नागरिक प्रोफ़ाइल' : '👤 Citizen Profile'}</h1>
            <p>{lang === 'hi' ? 'सक्रिय नागरिक खाता विवरण (डेमो मोड)' : 'Active Citizen Account Details (Demo Mode)'}</p>
          </div>
        </div>
        <div className="card">
          <div className="profile-header">
            <div className="profile-avatar">CU</div>
            <div>
              <h3 style={{ fontSize: 18, color: 'var(--ink)' }}>Citizen User</h3>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>citizen.jharkhand@vidysetu.gov.in</p>
              <span className="badge badge-blue" style={{ marginTop: 6 }}>Citizen Portal Verified</span>
            </div>
          </div>
          <div className="section-box section-box--muted" style={{ marginTop: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, fontSize: 13 }}>
              <div>📍 <strong>{lang === 'hi' ? 'राज्य:' : 'State:'}</strong> Jharkhand</div>
              <div>🏙️ <strong>{lang === 'hi' ? 'क्षेत्र:' : 'District:'}</strong> Jamshedpur / Bokaro</div>
              <div>📋 <strong>{lang === 'hi' ? 'सक्रिय समस्याएं:' : 'Active Problems:'}</strong> 2 Problems</div>
              <div>🔒 <strong>{lang === 'hi' ? 'प्रमाणीकरण:' : 'Authentication:'}</strong> Open Access (Demo)</div>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 16 }}
            onClick={() => {
              setScreenView('form');
              navigate('/demo/problem-solutions');
            }}
          >
            ← {lang === 'hi' ? 'डेमो फॉर्म पर वापस जाएं' : 'Back to Demo Form'}
          </button>
        </div>
      </div>
    );
  }

  /* ------------------------------------------------------------------------- */
  /* SCREEN VIEW 2: "EXISTING SOLUTIONS IN YOUR AREA" (MATCHES SCREENSHOT)      */
  /* ------------------------------------------------------------------------- */
  if (screenView === 'solutions') {
    return (
      <div>
        {/* Scenario Selection Modal */}
        {renderCaseModal()}

        {/* Page Head matching screenshot */}
        <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1>{<Trans text="Existing Solutions in Your Area" />}</h1>
            <p>{<Trans text="Before your problem is routed to Government and University Administration, let's check whether a solution already exists." />}</p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-light btn-sm"
              onClick={() => setShowCaseModal(true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700 }}
            >
              🔄 {lang === 'hi' ? 'डेमो परिदृश्य बदलें' : 'Switch Demo Scenario'}
            </button>
            <button
              type="button"
              className="btn btn-light btn-sm"
              onClick={() => setScreenView('form')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700 }}
            >
              ← {lang === 'hi' ? 'फॉर्म संपादित करें' : 'Edit Submitted Form'}
            </button>
          </div>
        </div>

        {/* Card 1: Your Submitted Problem (Matching screenshot top card) */}
        <div className="card">
          <span className="badge badge-blue">{<Trans text="Your Submitted Problem" />}</span>
          <h3 className="problem-title" style={{ marginTop: 8, fontSize: 18 }}>
            {title}
          </h3>
          <p className="problem-desc" style={{ marginTop: 6, color: 'var(--text-muted)' }}>
            {desc}
          </p>
        </div>

        {/* AI Searching State */}
        {analyzingProblem && (
          <div className="card" style={{ textAlign: 'center', padding: '36px 20px', marginTop: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, fontSize: 16, fontWeight: 700, color: 'var(--primary)' }}>
              <span className="spinner" style={{ width: 22, height: 22, borderWidth: 3 }} />
              <span>{lang === 'hi' ? 'एआई आपकी समस्या का विश्लेषण कर रहा है...' : 'AI is searching government databases and existing solutions for matches...'}</span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>
              {lang === 'hi'
                ? 'सरकारी योजनाओं एवं तकनीकी ज्ञानकोष में प्रासंगिक समाधान खोजा जा रहा है...'
                : 'Searching public schemes, technical repositories, and existing solutions for matches...'}
            </p>
          </div>
        )}

        {/* Relevant Existing Solution Found (Matching VidySetu solution card) */}
        {solutionFound && (
          <div className="card solution-result-card" style={{ marginTop: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              <span className="badge badge-teal">🤖 {<Trans text="AI Analysis" />}</span>
              <span className="badge badge-blue">✓ {lang === 'hi' ? 'प्रासंगिक मौजूदा समाधान मिला' : 'Relevant Existing Solution Found'}</span>
            </div>

            <h3 className="problem-title" style={{ fontSize: 18, color: 'var(--ink)' }}>
              {lang === 'hi' ? currentDemo.solution.titleHi : currentDemo.solution.title}
            </h3>

            <p className="problem-desc" style={{ marginTop: 8, fontSize: 14, color: 'var(--text)' }}>
              {lang === 'hi' ? currentDemo.solution.descriptionHi : currentDemo.solution.description}
            </p>

            {/* Relevant Technologies */}
            <div style={{ marginTop: 14 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)', marginBottom: 6 }}>
                🛠️ {lang === 'hi' ? 'प्रासंगिक तकनीकें (Relevant Technologies):' : 'Relevant Technologies:'}
              </div>
              <div className="skills-chips">
                {(lang === 'hi' ? currentDemo.solution.technologiesHi : currentDemo.solution.technologies).map((tech, idx) => (
                  <span key={idx} className="skill-chip">• {tech}</span>
                ))}
              </div>
            </div>

            {/* Why it is relevant */}
            <div className="section-box section-box--muted" style={{ marginTop: 14, marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--teal-dark)', marginBottom: 4 }}>
                💡 {lang === 'hi' ? 'यह क्यों प्रासंगिक है (Why it is relevant):' : 'Why it is relevant:'}
              </div>
              <div style={{ fontSize: 13.5, color: '#0f4f46', lineHeight: 1.5 }}>
                {lang === 'hi' ? currentDemo.solution.whyRelevantHi : currentDemo.solution.whyRelevant}
              </div>
            </div>

            {/* Solution Actions */}
            {!solutionAccepted && !showRejectionForm && (
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 16 }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleAcceptSolution}
                >
                  ✓ {lang === 'hi' ? 'मौजूदा समाधान स्वीकार करें' : 'Accept Existing Solution'}
                </button>
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={handleRejectSolution}
                >
                  ✕ {lang === 'hi' ? 'मेरी समस्या के लिए उपयुक्त नहीं है' : 'Not Suitable for My Problem'}
                </button>
              </div>
            )}

            {/* CASE 1: Acceptance State */}
            {solutionAccepted && (
              <div style={{ marginTop: 18 }}>
                <div className="validation-box validation-box--ok">
                  <span style={{ fontSize: 20 }}>✓</span>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 15 }}>
                      {lang === 'hi' ? '✓ मौजूदा समाधान स्वीकार कर लिया गया' : '✓ Existing solution accepted'}
                    </div>
                    <div style={{ fontSize: 13, marginTop: 3, fontWeight: 500 }}>
                      {lang === 'hi'
                        ? 'इस समस्या के लिए मौजूदा समाधान स्वीकार कर लिया गया है।'
                        : 'The existing solution has been accepted for this problem.'}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 16, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      showToast(
                        lang === 'hi'
                          ? 'समस्या कार्यान्वयन अनुरोध दर्ज किया गया।'
                          : 'Solution request routed for local deployment.'
                      );
                      navigate('/demo/problem-solutions?tab=problems');
                    }}
                  >
                    {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'Proceed to Track My Problem →'}
                  </button>
                </div>
              </div>
            )}

            {/* CASE 2: Rejection Form */}
            {showRejectionForm && !reasonValidated && (
              <div
                className="section-box"
                style={{
                  marginTop: 20,
                  background: '#fff',
                  borderColor: 'var(--primary)',
                  borderWidth: 1,
                }}
              >
                <h4 style={{ fontSize: 15, color: 'var(--ink)', marginBottom: 8 }}>
                  {lang === 'hi'
                    ? 'यह मौजूदा समाधान आपकी समस्या के लिए उपयुक्त क्यों नहीं है?'
                    : 'Why is this existing solution not suitable for your problem?'}
                </h4>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
                  {lang === 'hi'
                    ? 'कृपया एक या अधिक कारणों का चयन करें। एआई आपके औचित्य को सत्यापित करेगा।'
                    : 'Select one or more applicable reasons. AI will validate your justification.'}
                </p>

                <div className="checkbox-list">
                  {REJECTION_REASONS.map((r) => {
                    const isChecked = selectedReasons.includes(r.en);
                    return (
                      <label
                        key={r.en}
                        style={{
                          backgroundColor: isChecked ? 'var(--primary-soft)' : '#fff',
                          borderColor: isChecked ? 'var(--primary)' : 'var(--border)',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleReason(r.en)}
                          style={{ marginTop: 2 }}
                        />
                        <span>{lang === 'hi' ? r.hi : r.en}</span>
                      </label>
                    );
                  })}
                </div>

                <div className="field" style={{ marginTop: 14 }}>
                  <label style={{ fontSize: 13, fontWeight: 700 }}>
                    {lang === 'hi' ? 'अतिरिक्त विवरण (Additional Explanation):' : 'Additional Explanation'}
                  </label>
                  <textarea
                    rows={4}
                    placeholder={
                      lang === 'hi'
                        ? 'विस्तार से बताएं कि यह समाधान आपके स्थानीय क्षेत्र या बाधाओं के लिए क्यों काम नहीं करता...'
                        : 'Provide any additional context or local constraints explaining why this solution does not fit...'
                    }
                    value={additionalExplanation}
                    onChange={(e) => setAdditionalExplanation(e.target.value)}
                  />
                </div>

                {validatingReason ? (
                  <div className="validation-box validation-box--checking" style={{ marginTop: 14 }}>
                    <span className="spinner" />
                    <span>
                      {lang === 'hi'
                        ? 'एआई आपके कारण का सत्यापन कर रहा है...'
                        : 'AI is validating your reason...'}
                    </span>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary btn-block"
                    style={{ marginTop: 14 }}
                    onClick={handleSubmitRejectionReason}
                  >
                    {lang === 'hi' ? 'एआई सत्यापन हेतु कारण जमा करें' : 'Submit Reason for AI Validation'}
                  </button>
                )}
              </div>
            )}

            {/* AI Validation Result */}
            {reasonValidated && (
              <div style={{ marginTop: 20 }}>
                <div className="validation-box validation-box--ok">
                  <span style={{ fontSize: 20 }}>✓</span>
                  <span style={{ fontSize: 15, fontWeight: 800 }}>
                    {lang === 'hi' ? '✓ कारण सत्यापित (Reason Validated)' : '✓ Reason Validated'}
                  </span>
                </div>

                <div
                  className="section-box"
                  style={{
                    background: '#f8fafc',
                    border: '1px solid #cbd5e1',
                    borderRadius: '12px',
                    padding: '16px 18px',
                    marginTop: 12,
                  }}
                >
                  <p style={{ fontWeight: 700, fontSize: 14, color: 'var(--ink)', marginBottom: 8 }}>
                    {lang === 'hi'
                      ? 'मौजूदा समाधान को न चुनने का आपका कारण वैध है।'
                      : 'Your reason for not selecting the existing solution is valid.'}
                  </p>
                  <p style={{ fontSize: 13.5, color: 'var(--text)', lineHeight: 1.55, marginBottom: 8 }}>
                    {lang === 'hi'
                      ? 'प्रदान किए गए कारणों से संकेत मिलता है कि मौजूदा समाधान इस समस्या की स्थानीय आवश्यकताओं और कार्यान्वयन बाधाओं को पर्याप्त रूप से संबोधित नहीं कर सकता है।'
                      : 'The provided reasons indicate that the existing solution may not adequately address the local requirements and implementation constraints of this problem.'}
                  </p>
                  {selectedReasons.length > 0 && (
                    <div style={{ margin: '10px 0 8px', fontSize: 13, color: 'var(--ink)' }}>
                      <strong>{lang === 'hi' ? 'सत्यापित आधार (Validated Criteria):' : 'Validated Criteria:'}</strong>
                      <ul style={{ margin: '6px 0 8px 20px', padding: 0 }}>
                        {selectedReasons.map((r, idx) => (
                          <li key={idx} style={{ marginBottom: 3 }}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {additionalExplanation.trim() && (
                    <div style={{ margin: '10px 0 8px', fontSize: 13, color: 'var(--ink)' }}>
                      <strong>{lang === 'hi' ? 'नागरिक द्वारा दर्ज विवरण (Citizen Justification):' : 'Citizen Justification:'}</strong>
                      <div style={{ fontStyle: 'italic', color: 'var(--text)', marginTop: 4, padding: '8px 12px', background: '#fff', borderRadius: 8, border: '1px solid var(--border)' }}>
                        "{additionalExplanation}"
                      </div>
                    </div>
                  )}
                  <p style={{ fontSize: 13.5, color: '#065f46', fontWeight: 600, marginTop: 10 }}>
                    {lang === 'hi'
                      ? 'इसलिए, आपकी समस्या आगे के मूल्यांकन एवं नवीन समाधान विकास के लिए आगे बढ़ सकती है।'
                      : 'Therefore, your problem can proceed for further evaluation.'}
                  </p>
                </div>

                {!demoCompleted ? (
                  <button
                    type="button"
                    className="btn btn-primary btn-block"
                    style={{ marginTop: 16 }}
                    onClick={handleContinueWithProblem}
                  >
                    {lang === 'hi' ? 'मेरी समस्या के साथ जारी रखें →' : 'Continue with My Problem →'}
                  </button>
                ) : (
                  <div style={{ marginTop: 16 }}>
                    <div
                      style={{
                        padding: '12px 16px',
                        background: 'var(--teal-soft)',
                        border: '1px solid var(--teal)',
                        borderRadius: 10,
                        color: 'var(--teal-dark)',
                        fontSize: 13.5,
                        fontWeight: 600,
                        marginBottom: 12,
                      }}
                    >
                      {lang === 'hi'
                        ? '✓ आपकी समस्या नागरिक पोर्टल में पंजीकृत कर ली गई है और विश्वविद्यालयों एवं शोधकर्ताओं को आवंटित करने हेतु अग्रेषित की जा रही है।'
                        : '✓ Your problem has been successfully routed for government review and university research allocation!'}
                    </div>
                    <div>
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => navigate('/demo/problem-solutions?tab=problems')}
                      >
                        {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'Proceed to Track My Problem →'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  /* ------------------------------------------------------------------------- */
  /* SCREEN VIEW 1: PRISTINE REPORT CIVIC PROBLEM FORM (NO EXTRA CLUTTER)       */
  /* ------------------------------------------------------------------------- */
  return (
    <div>
      {/* Page Header */}
      <div className="page-head">
        <div>
          <h1>{t.addProblemTitle || (lang === 'hi' ? '➕ नई नागरिक समस्या दर्ज करें' : '➕ Report Civic Problem')}</h1>
          <p>
            {lang === 'hi'
              ? 'नागरिक पोर्टल - निर्धारित समस्या समाधान डेमो प्रवाह (Deterministic Demo Flow)'
              : 'Citizen Portal — Deterministic Problem Solutions Demo Flow'}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-light btn-sm"
          onClick={() => setShowCaseModal(true)}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700 }}
        >
          🔄 {lang === 'hi' ? 'डेमो परिदृश्य बदलें' : 'Switch Demo Scenario'}
        </button>
      </div>

      {/* Pop-up Scenario Selection Modal on Site Open */}
      {renderCaseModal()}

      {/* Main Problem Form Card — Clean & Identical to Production */}
      <div className="card">
        <div className="field">
          <label>{t.fieldTitle || 'Problem Title'}</label>
          <input
            type="text"
            placeholder={t.fieldTitlePh || 'e.g. Broken water pipeline in Sector 4'}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <label className="section-box__label" style={{ display: 'block', marginBottom: 4 }}>
          {<Trans text="Voice Assistant" />}
        </label>
        <SpeechToText onTranscript={handleTranscript} />

        <div className="field" style={{ marginTop: 14 }}>
          <label>{t.fieldDesc || 'Problem Description'}</label>
          <textarea
            placeholder={t.fieldDescPh || 'Describe the issue in detail…'}
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            rows={5}
          />
        </div>

        {/* Location Section */}
        <div className="section-box">
          <h4>{t.locationHead || 'Location Details'}</h4>

          {/* GPS Location Button */}
          <div style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-light btn-sm"
              onClick={handleDetectLocation}
              disabled={gpsStatus === 'detecting'}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              📍 {gpsStatus === 'detecting'
                ? (lang === 'hi' ? 'स्थान खोज रहे हैं…' : 'Detecting…')
                : (lang === 'hi' ? 'वर्तमान स्थान का उपयोग करें (वैकल्पिक)' : 'Use My Current Location (Optional)')}
            </button>
            {gpsMessage && (
              <span
                style={{
                  fontSize: '0.85rem',
                  color: gpsStatus === 'captured' ? '#059669' : '#6b7280',
                  fontWeight: gpsStatus === 'captured' ? 600 : 400,
                }}
              >
                {gpsMessage}
              </span>
            )}
          </div>

          <div className="grid grid--location">
            <div className="field">
              <label>{t.fieldCity || 'City'}</label>
              <select value={city} onChange={(e) => setCity(e.target.value)}>
                {jharkhandCities.map((c) => (
                  <option key={c.value} value={c.value}>{c[lang] || c.en}</option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>{t.fieldAddress || 'Full Address / Locality'}</label>
              <input
                type="text"
                placeholder={t.fieldAddressPh || 'Street name, colony, landmark'}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
            </div>

            <div className="field">
              <label>{t.fieldPincode || 'Pincode'}</label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder={t.fieldPincodePh || '6-digit pincode'}
                value={pincode}
                onChange={(e) => setPincode(e.target.value.replace(/\D/g, ''))}
              />
            </div>
          </div>

          <div className="field" style={{ marginBottom: 0 }}>
            <label>{t.scopeLabel || 'Impact Scope'}</label>
            <div className="mcq-grid">
              <McqOption
                name="demo-scope"
                value="Area Specific"
                checked={scope === 'Area Specific'}
                onChange={setScope}
                icon="🏡"
                title={t.scopeArea || 'Area Specific'}
                desc={t.scopeAreaDesc || 'Affects a single street or neighborhood'}
              />
              <McqOption
                name="demo-scope"
                value="City Specific"
                checked={scope === 'City Specific'}
                onChange={setScope}
                icon="🏙️"
                title={t.scopeCity || 'City Specific'}
                desc={t.scopeCityDesc || 'Affects entire city or multiple wards'}
              />
            </div>
          </div>
        </div>

        {/* Media Attachments Section */}
        <div className="section-box section-box--muted">
          <h4>{t.mediaHead || 'Attach Media'}</h4>
          <div className="grid grid--uploads">
            <FileUploadField
              label={t.uploadPhoto || 'Upload Photo'}
              accept="image/*"
              kind="photo"
              dragLabel={t.dragDrop || 'Drag & drop image here'}
              onChange={setAttachment('photo')}
            />
            <FileUploadField
              label={t.uploadVideo || 'Upload Video'}
              accept="video/*"
              kind="video"
              dragLabel={t.dragDrop || 'Drag & drop video here'}
              onChange={setAttachment('video')}
            />
            <FileUploadField
              label={t.uploadDoc || 'Upload Document'}
              accept=".pdf,.doc,.docx"
              kind="document"
              dragLabel={t.dragDrop || 'Drag & drop PDF / Word here'}
              onChange={setAttachment('document')}
            />
          </div>
        </div>

        {/* Form Submit Action */}
        <button
          className="btn btn-primary btn-block"
          disabled={analyzingProblem}
          onClick={handleSubmitProblem}
        >
          {analyzingProblem
            ? (lang === 'hi' ? 'एआई समस्या का विश्लेषण कर रहा है…' : 'AI is analyzing your problem…')
            : `${t.submitProblem || 'Submit Problem'} →`}
        </button>
      </div>
    </div>
  );
}
