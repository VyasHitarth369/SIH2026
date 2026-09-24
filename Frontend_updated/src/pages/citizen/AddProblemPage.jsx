import Trans from '../../components/shared/Trans.jsx';
import { useState, useRef, useEffect } from 'react';
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
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Known coordinates for key Jharkhand districts
const DISTRICT_COORDS = {
  Ranchi: { lat: 23.3441, lng: 85.3096 },
  Dhanbad: { lat: 23.7957, lng: 86.4304 },
  Jamshedpur: { lat: 22.8046, lng: 86.2029 },
  Bokaro: { lat: 23.6693, lng: 86.1511 },
  Deoghar: { lat: 24.4826, lng: 86.7002 },
  Hazaribagh: { lat: 23.9961, lng: 85.3647 },
  Giridih: { lat: 24.1856, lng: 86.3073 },
  Ramgarh: { lat: 23.6332, lng: 85.5149 },
  Dumka: { lat: 24.2676, lng: 87.2489 },
  Chaibasa: { lat: 22.5517, lng: 85.8078 },
  Palamu: { lat: 24.0416, lng: 84.0722 },
  Gumla: { lat: 23.0435, lng: 84.5414 },
  Khunti: { lat: 23.0734, lng: 85.2787 },
  Lohardaga: { lat: 23.4357, lng: 84.6806 },
  Simdega: { lat: 22.6148, lng: 84.5074 },
  Latehar: { lat: 23.7431, lng: 84.4984 },
  Chatra: { lat: 24.2088, lng: 84.8718 },
  Koderma: { lat: 24.4673, lng: 85.5939 },
  Jamtara: { lat: 23.9624, lng: 86.8028 },
  Godda: { lat: 24.8267, lng: 87.2132 },
  Sahebganj: { lat: 25.2425, lng: 87.6441 },
  Pakur: { lat: 24.6341, lng: 87.8488 },
  Garhwa: { lat: 24.1614, lng: 83.8076 },
  'Saraikela Kharsawan': { lat: 22.7001, lng: 85.9304 },
};

// Create custom pin icon helper for Leaflet
const createPinIcon = () =>
  L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="position:relative; display:flex; flex-direction:column; align-items:center; transform:translate(-50%, -100%); pointer-events:auto; cursor:grab;">
        <div style="background:#dc2626; color:#ffffff; font-size:10px; font-weight:700; padding:2px 7px; border-radius:10px; white-space:nowrap; box-shadow:0 2px 6px rgba(0,0,0,0.35); margin-bottom:2px; letter-spacing:0.02em;">
          📍 Pinned
        </div>
        <svg width="30" height="40" viewBox="0 0 24 32" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 4px 6px rgba(0,0,0,0.45));">
          <path d="M12 0C5.37258 0 0 5.37258 0 12C0 21 12 32 12 32C12 32 24 21 24 12C24 5.37258 18.6274 0 12 0Z" fill="#ef4444"/>
          <circle cx="12" cy="11" r="4.5" fill="#ffffff"/>
        </svg>
      </div>
    `,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });

export default function AddProblemPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const { addProblem } = useProblems();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [city, setCity] = useState('Ranchi');
  const [address, setAddress] = useState('');
  const [pincode, setPincode] = useState('');
  const [scope, setScope] = useState('Area Specific');
  const [attachments, setAttachments] = useState({ photo: null, video: null, document: null });
  const [submitting, setSubmitting] = useState(false);

  // GPS / Interactive Map State (Defaults to Ranchi center)
  const [gpsCoords, setGpsCoords] = useState({ lat: 23.3441, lng: 85.3096 });
  const [gpsStatus, setGpsStatus] = useState('default'); // 'default', 'detecting', 'captured', 'pinned', 'denied'
  const [gpsMessage, setGpsMessage] = useState(
    lang === 'hi' ? '📍 राँची (डिफ़ॉल्ट पिन सेट)' : '📍 Centered on Ranchi (Default Pin)'
  );

  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);

  // Quick district presets
  const quickDistricts = ['Ranchi', 'Dhanbad', 'Jamshedpur', 'Bokaro', 'Deoghar', 'Hazaribagh'];

  // Initialize interactive Leaflet road map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const initialLat = gpsCoords.lat || 23.3441;
    const initialLng = gpsCoords.lng || 85.3096;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLng],
      zoom: 12,
      scrollWheelZoom: true,
    });

    // Real interactive Leaflet road map with OpenStreetMap tiles (100% token-free and no API key required)
    const tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    const attribution = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors';

    L.tileLayer(tileUrl, {
      attribution,
      maxZoom: 19,
    }).addTo(map);

    const marker = L.marker([initialLat, initialLng], {
      icon: createPinIcon(),
      draggable: true,
    }).addTo(map);

    marker.on('dragend', (e) => {
      const pos = e.target.getLatLng();
      setGpsCoords({ lat: pos.lat, lng: pos.lng });
      setGpsStatus('pinned');
      setGpsMessage(
        lang === 'hi'
          ? `📍 पिन स्थान: ${pos.lat.toFixed(6)}°, ${pos.lng.toFixed(6)}°`
          : `📍 Pinned Location: ${pos.lat.toFixed(6)}°, ${pos.lng.toFixed(6)}°`
      );
    });

    map.on('click', (e) => {
      const { lat, lng } = e.latlng;
      marker.setLatLng([lat, lng]);
      setGpsCoords({ lat, lng });
      setGpsStatus('pinned');
      setGpsMessage(
        lang === 'hi'
          ? `📍 मानचित्र पिन: ${lat.toFixed(6)}°, ${lng.toFixed(6)}°`
          : `📍 Map Pin: ${lat.toFixed(6)}°, ${lng.toFixed(6)}°`
      );
    });

    mapInstanceRef.current = map;
    markerRef.current = marker;

    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 250);

    return () => {
      clearTimeout(timer);
      map.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
    };
  }, []);

  // Option A: Use My Current Location via Geolocation API
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setGpsStatus('denied');
      setGpsMessage(
        lang === 'hi'
          ? 'ब्राउज़र में जीपीएस उपलब्ध नहीं है'
          : 'Geolocation is not supported by your browser.'
      );
      return;
    }
    setGpsStatus('detecting');
    setGpsMessage(lang === 'hi' ? 'स्थान खोज रहे हैं…' : 'Detecting your location…');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        setGpsCoords({ lat, lng });
        setGpsStatus('captured');
        setGpsMessage(
          lang === 'hi'
            ? `📍 लाइव जीपीएस: ${lat.toFixed(6)}°, ${lng.toFixed(6)}°`
            : `📍 Live GPS: ${lat.toFixed(6)}°, ${lng.toFixed(6)}°`
        );

        if (mapInstanceRef.current && markerRef.current) {
          mapInstanceRef.current.flyTo([lat, lng], 15, { duration: 1.2 });
          markerRef.current.setLatLng([lat, lng]);
        }

        // Find closest district if within Jharkhand bounds
        let closestCity = city;
        let minDistance = Infinity;
        Object.entries(DISTRICT_COORDS).forEach(([cName, cCoords]) => {
          const d = Math.hypot(cCoords.lat - lat, cCoords.lng - lng);
          if (d < minDistance) {
            minDistance = d;
            closestCity = cName;
          }
        });
        if (closestCity && minDistance < 1.0) {
          setCity(closestCity);
        }
      },
      (error) => {
        setGpsStatus('denied');
        setGpsMessage(
          lang === 'hi'
            ? 'जीपीएस अनुमति अस्वीकृत। कृपया मानचित्र पर क्लिक करके या मार्कर खींचकर पिन लगाएं।'
            : 'GPS permission denied. Please click on the map or drag the marker to pin location.'
        );
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  // Select district from preset or dropdown
  const handleSelectDistrict = (distName) => {
    setCity(distName);
    const coords = DISTRICT_COORDS[distName] || DISTRICT_COORDS.Ranchi;
    setGpsCoords(coords);
    setGpsStatus('pinned');
    setGpsMessage(
      lang === 'hi'
        ? `📍 ${cityLabel(distName, lang)}: ${coords.lat.toFixed(6)}°, ${coords.lng.toFixed(6)}°`
        : `📍 ${distName}: ${coords.lat.toFixed(6)}°, ${coords.lng.toFixed(6)}°`
    );
    if (mapInstanceRef.current && markerRef.current) {
      mapInstanceRef.current.flyTo([coords.lat, coords.lng], 13, { duration: 1.2 });
      markerRef.current.setLatLng([coords.lat, coords.lng]);
    }
  };

  const setAttachment = (kind) => (value) => {
    setAttachments((prev) => ({ ...prev, [kind]: value }));
  };

  const handleTranscript = (text) => {
    setDesc((prev) => (prev ? `${prev} ${text}` : text));
  };

  const handleSubmit = async () => {
    // Address writing is NO LONGER mandatory
    if (!title.trim() || !desc.trim()) {
      showToast(t.fillRequired);
      return;
    }
    if (pincode.trim() && !/^\d{6}$/.test(pincode.trim())) {
      showToast(t.pincodeInvalid);
      return;
    }

    const files = Object.entries(attachments)
      .filter(([, v]) => v)
      .map(([kind, v]) => ({ kind, ...v }));

    const currentCoords = gpsCoords || { lat: 23.3441, lng: 85.3096 };
    const latStr = currentCoords.lat.toFixed(6);
    const lngStr = currentCoords.lng.toFixed(6);

    // Deterministic location formatting
    const addrPart = address.trim() ? `${address.trim()}, ` : '';
    const pinPart = pincode.trim() ? ` - ${pincode.trim()}` : '';
    const composedLoc = addrPart
      ? `${addrPart}${cityLabel(city, lang)}${pinPart} (GPS: ${latStr}, ${lngStr})`
      : `Lat: ${latStr}, Lng: ${lngStr} (${cityLabel(city, lang)}, Jharkhand)`;

    const isGov = user?.role === 'government';
    const isInd = user?.role === 'industry';
    const source = isGov ? 'government' : isInd ? 'industry' : 'citizen';
    const category = isGov ? 'Government Problem' : isInd ? 'Industry Problem' : 'Civic Issue';

    setSubmitting(true);
    let createdChallenge = null;

    try {
      createdChallenge = await submitChallenge({
        title: title.trim(),
        description: desc.trim(),
        location: composedLoc,
        city,
        district: city,
        address: address.trim() || `Lat: ${latStr}, Lng: ${lngStr}`,
        pincode: pincode.trim() || '834001',
        impact_scope: scope,
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

        {/* REDESIGNED MODERN PROBLEM LOCATION & INTERACTIVE MAP SECTION */}
        <div className="section-box">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
            <h4 style={{ margin: 0 }}>📍 <Trans text="Problem Location & Interactive GPS Mapping" /></h4>
            <span className="badge badge-teal" style={{ fontSize: 11.5 }}>
              ✓ <Trans text="No Manual Postal Writing Required" />
            </span>
          </div>

          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
            {lang === 'hi'
              ? 'समस्या के स्थान को चिह्नित करने के लिए "वर्तमान स्थान का उपयोग करें" चुनें या सीधे नीचे दिए गए मानचित्र पर क्लिक करें।'
              : 'Pinpoint the issue location using GPS or click anywhere on the Jharkhand interactive map.'}
          </p>

          {/* ACTION BUTTONS & PRESETS */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 14 }}>
            {/* OPTION A: CURRENT LOCATION */}
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleDetectLocation}
              disabled={gpsStatus === 'detecting'}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              🎯 {gpsStatus === 'detecting'
                ? (lang === 'hi' ? 'स्थान खोज रहे हैं…' : 'Detecting GPS…')
                : (lang === 'hi' ? 'वर्तमान स्थान का उपयोग करें' : 'Use My Current Location')}
            </button>

            {/* RESET BUTTON */}
            <button
              type="button"
              className="btn btn-light btn-sm"
              onClick={() => handleSelectDistrict('Ranchi')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              🔄 <Trans text="Center Ranchi" />
            </button>

            {/* QUICK DISTRICT PRESET PILLS */}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginLeft: 'auto' }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                <Trans text="Quick Presets:" />
              </span>
              {quickDistricts.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => handleSelectDistrict(d)}
                  className={`btn btn-sm ${city === d ? 'btn-teal' : 'btn-outline'}`}
                  style={{ padding: '4px 10px', fontSize: 11.5, borderRadius: 16 }}
                >
                  {cityLabel(d, lang)}
                </button>
              ))}
            </div>
          </div>

          {/* OPTION B: REAL INTERACTIVE LEAFLET ROAD MAP */}
          <style>{`
            .custom-map-pin {
              background: transparent !important;
              border: none !important;
            }
          `}</style>
          <div style={{ position: 'relative', marginBottom: 14 }}>
            <div
              ref={mapContainerRef}
              style={{
                height: 350,
                width: '100%',
                borderRadius: 12,
                overflow: 'hidden',
                border: '2px solid #0284c7',
                boxShadow: '0 4px 14px rgba(2, 132, 199, 0.15)',
                zIndex: 1,
              }}
            />
            {/* Real-time map guidance overlay */}
            <div
              style={{
                position: 'absolute',
                bottom: 12,
                left: 12,
                zIndex: 400,
                background: 'rgba(15, 23, 42, 0.85)',
                backdropFilter: 'blur(6px)',
                padding: '6px 14px',
                borderRadius: 8,
                fontSize: 12,
                color: '#e2e8f0',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                pointerEvents: 'none',
              }}
            >
              <span>👆</span>
              <span>
                {lang === 'hi'
                  ? 'सटीक स्थान तय करने के लिए मानचित्र पर क्लिक करें या लाल पिन को खींचें।'
                  : 'Click anywhere on the map or drag the red pin marker to pinpoint location.'}
              </span>
            </div>
          </div>

          {/* CONFIRMATION / VERIFICATION READOUT BANNER */}
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 8,
              background: '#f0fdf4',
              border: '1px solid #86efac',
              color: '#15803d',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 8,
              fontSize: 13,
              fontWeight: 600,
              marginBottom: 16,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>✓</span>
              <span>
                <Trans text="Pinned Coordinates:" />{' '}
                <strong style={{ fontFamily: 'monospace', color: '#166534' }}>
                  {gpsCoords.lat.toFixed(6)}° N, {gpsCoords.lng.toFixed(6)}° E
                </strong>{' '}
                ({cityLabel(city, lang)}, Jharkhand)
              </span>
            </div>
            <span style={{ fontSize: 11.5, color: '#166534', fontWeight: 500 }}>
              {gpsMessage}
            </span>
          </div>

          {/* DISTRICT, OPTIONAL LANDMARK, AND OPTIONAL PINCODE */}
          <div className="grid grid--location">
            <div className="field">
              <label>{t.fieldCity} *</label>
              <select value={city} onChange={(e) => handleSelectDistrict(e.target.value)}>
                {jharkhandCities.map((c) => (
                  <option key={c.value} value={c.value}>{c[lang] || c.en}</option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>
                <Trans text="Landmark / Street (Optional)" />
              </label>
              <input
                type="text"
                placeholder={lang === 'hi' ? 'उदा. मुख्य चौराहा, विद्यालय के पास' : 'e.g. Near Main Market, Sector 4'}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
            </div>

            <div className="field">
              <label>
                <Trans text="Pincode (Optional)" />
              </label>
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
