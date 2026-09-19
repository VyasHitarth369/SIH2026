// ============================================================================
// Organization / stakeholder master data used across University Administration,
// Faculty, Government, and Industry Employee workflows.
// All mock data — in a real deployment this would come from the backend.
// ============================================================================

export const universities = [
  { id: 'bit-mesra', name: 'BIT Mesra, Ranchi', city: 'Ranchi' },
  { id: 'nit-jsr', name: 'NIT Jamshedpur', city: 'Jamshedpur' },
  { id: 'iit-ism', name: 'IIT (ISM) Dhanbad', city: 'Dhanbad' },
  { id: 'bau-ranchi', name: 'BAU Ranchi', city: 'Ranchi' },
];

export const universityNames = universities.map((u) => u.name);

// Exactly 15 approved universities for Student registration and profile
export const STUDENT_APPROVED_UNIVERSITIES = [
  'Birla Institute of Technology (BIT Mesra)',
  'IIT (ISM) Dhanbad',
  'NIT Jamshedpur',
  'IIIT Ranchi',
  'Birsa Agricultural University (BAU)',
  'Central University of Jharkhand (CUJ)',
  'AIIMS Deoghar',
  'BIT Sindri',
  'NIAMT Ranchi',
  'Ranchi University',
  'Nilamber-Pitamber University',
  'Kolhan University',
  'Sido Kanhu Murmu University',
  "Jamshedpur Women's University",
  'Jharkhand University of Technology (JUT)',
];

export const industries = [
  { id: 'tata-csr', name: 'Tata CSR Water Solutions', domain: 'IoT' },
  { id: 'tata-steel', name: 'Tata Steel Innovation Cell', domain: 'Software Development' },
  { id: 'lnt', name: 'L&T Construction', domain: 'Mechanical Design' },
];

export const domainList = [
  'Web Development',
  'Robotics',
  'Agriculture',
  'Mechanical Design',
  'Healthcare',
  'AI / Machine Learning',
  'IoT',
  'Cybersecurity',
  'Electronics',
  'Software Development',
];

// Faculty directory (used for allocation dropdowns and Government's "Assigned Faculties" view)
export const facultyDirectory = [
  { id: 'fac-1', name: 'Dr. S. K. Verma', email: 's.verma@bitmesra.ac.in', university: 'BIT Mesra, Ranchi', department: 'Computer Science', expertise: 'IoT / Embedded Systems' },
  { id: 'fac-2', name: 'Dr. Anjali Rao', email: 'a.rao@nitjsr.ac.in', university: 'NIT Jamshedpur', department: 'Electronics', expertise: 'AI / Machine Learning' },
  { id: 'fac-3', name: 'Dr. P. K. Singh', email: 'pk.singh@iitism.ac.in', university: 'IIT (ISM) Dhanbad', department: 'Mechanical Engineering', expertise: 'Mechanical Design' },
  { id: 'fac-4', name: 'Dr. Meena Oraon', email: 'm.oraon@bausagri.ac.in', university: 'BAU Ranchi', department: 'Agricultural Engineering', expertise: 'Agriculture / IoT' },
];

// Students assigned to problems (used by Faculty "Students Working" list and Government analytics)
export const studentDirectory = [
  { id: 'stu-1', name: 'Priya Kumari', email: 'priya.kumari@iitism.ac.in', university: 'IIT (ISM) Dhanbad', department: 'CSE', domain: 'IoT', skills: ['IoT', 'Embedded C', 'React'], technologies: ['ESP32', 'MQTT', 'React'], status: 'Active', proposedSolution: 'Smart Dustbin Network', proposedSolutionDesc: 'IoT-enabled smart dustbins with fill-level sensors feeding a route-optimization mobile app for collection crews.' },
  { id: 'stu-2', name: 'Rohit Verma', email: 'rohit.verma@nitjsr.ac.in', university: 'NIT Jamshedpur', department: 'ECE', domain: 'AI / Machine Learning', skills: ['Computer Vision', 'Python'], technologies: ['OpenCV', 'TensorFlow'], status: 'Active', proposedSolution: 'Adaptive Traffic Signal AI', proposedSolutionDesc: 'Computer-vision model reading live camera feeds to dynamically retime signals and cut congestion.' },
  { id: 'stu-3', name: 'Ananya Singh', email: 'ananya.singh@nitjsr.ac.in', university: 'NIT Jamshedpur', department: 'CSE', domain: 'Healthcare', skills: ['Hardware', 'Video Systems'], technologies: ['WebRTC', 'Raspberry Pi'], status: 'Active', proposedSolution: 'Telemedicine Kiosk', proposedSolutionDesc: 'Solar-powered kiosk connecting remote villagers to city doctors via video call and vitals capture.' },
  { id: 'stu-4', name: 'Ritika Mahto', email: 'ritika.mahto@bausagri.ac.in', university: 'BAU Ranchi', department: 'Agricultural Engg', domain: 'Agriculture', skills: ['IoT Sensors', 'Data Analysis'], technologies: ['LoRa', 'Python'], status: 'Active', proposedSolution: 'Soil Health Sensor Network', proposedSolutionDesc: 'Low-cost IoT soil sensors paired with an SMS advisory system for farmers.' },
  { id: 'stu-5', name: 'Md. Kaif Ansari', email: 'kaif.ansari@bitmesra.ac.in', university: 'BIT Mesra, Ranchi', department: 'CSE', domain: 'Healthcare', skills: ['Mobile Dev', 'Backend'], technologies: ['Flutter', 'Node.js'], status: 'Active', proposedSolution: 'Maternal & Child Health Tracker', proposedSolutionDesc: 'Offline-first mobile app sending vaccination reminders and syncing records once connectivity returns.' },
];

// Collaboration proposals submitted by Universities to Industry (Section 3)
export const collaborationProposals = [
  {
    id: 'prop-1',
    university: 'BIT Mesra, Ranchi',
    projectName: 'Rural Water Quality Monitoring',
    projectNameHi: 'ग्रामीण जल गुणवत्ता निगरानी',
    domain: 'IoT',
    proposedCollaboration: 'Co-develop and pilot low-cost water-quality sensor hardware for 15 villages.',
    proposedCollaborationHi: '15 गांवों के लिए कम लागत वाले जल-गुणवत्ता सेंसर हार्डवेयर का सह-विकास एवं पायलट परीक्षण।',
    requiredExpertise: 'Embedded hardware manufacturing, field deployment',
    requiredExpertiseHi: 'एंबेडेड हार्डवेयर निर्माण, फील्ड परिनियोजन',
    requiredTechnologies: ['IoT Sensors', 'LoRaWAN', 'Cloud Dashboard'],
    description: 'Students have built a working prototype and need an industry partner to help scale sensor manufacturing and support a 6-month village pilot.',
    descriptionHi: 'छात्रों ने एक कार्यशील प्रोटोटाइप बनाया है और सेंसर निर्माण को बढ़ाने व 6 महीने के ग्राम पायलट का समर्थन करने के लिए एक उद्योग भागीदार की आवश्यकता है।',
    expectedRole: 'Provide hardware fabrication support, co-fund the pilot, and mentor students on manufacturing best practices.',
    expectedRoleHi: 'हार्डवेयर निर्माण सहायता प्रदान करना, पायलट को सह-वित्तपोषित करना, और निर्माण के सर्वोत्तम अभ्यासों पर छात्रों को सलाह देना।',
    dateTime: '2026-08-14T10:00:00',
    status: 'Pending Review',
    technology: 'IoT',
  },
  {
    id: 'prop-2',
    university: 'NIT Jamshedpur',
    projectName: 'AI-Based Traffic Signal Automation',
    projectNameHi: 'AI-आधारित ट्रैफिक सिग्नल स्वचालन',
    domain: 'AI / Machine Learning',
    proposedCollaboration: 'Deploy the AI signal-timing model at 6 additional intersections with industry co-funding.',
    proposedCollaborationHi: 'उद्योग सह-वित्तपोषण के साथ 6 अतिरिक्त चौराहों पर AI सिग्नल-टाइमिंग मॉडल लागू करना।',
    requiredExpertise: 'Civil/traffic infrastructure integration',
    requiredExpertiseHi: 'नागरिक/यातायात बुनियादी ढांचा एकीकरण',
    requiredTechnologies: ['Computer Vision', 'Edge Compute'],
    description: 'A working pilot has cut congestion by 40% at 6 intersections. Looking for an infrastructure partner to fund and support city-wide rollout.',
    descriptionHi: 'एक कार्यशील पायलट ने 6 चौराहों पर भीड़भाड़ को 40% तक कम कर दिया है। शहरव्यापी विस्तार के लिए एक बुनियादी ढांचा भागीदार की तलाश है।',
    expectedRole: 'Co-fund hardware installation and provide traffic-infrastructure integration expertise.',
    expectedRoleHi: 'हार्डवेयर स्थापना को सह-वित्तपोषित करना और यातायात-बुनियादी ढांचा एकीकरण विशेषज्ञता प्रदान करना।',
    dateTime: '2026-08-20T14:30:00',
    status: 'Accepted',
    technology: 'Computer Vision',
  },
  {
    id: 'prop-3',
    university: 'BAU Ranchi',
    projectName: 'Soil Health Monitoring Sensor Network',
    projectNameHi: 'मृदा स्वास्थ्य निगरानी सेंसर नेटवर्क',
    domain: 'Agriculture',
    proposedCollaboration: 'License the sensor design for mass production and distribution to farmer cooperatives.',
    proposedCollaborationHi: 'किसान सहकारी समितियों को बड़े पैमाने पर उत्पादन और वितरण के लिए सेंसर डिज़ाइन को लाइसेंस देना।',
    requiredExpertise: 'Agri-tech manufacturing and distribution',
    requiredExpertiseHi: 'कृषि-तकनीक निर्माण और वितरण',
    requiredTechnologies: ['IoT Sensors', 'SMS Gateway'],
    description: 'Field-tested low-cost soil sensors with an SMS advisory system are ready for scale-up beyond the pilot villages.',
    descriptionHi: 'एसएमएस सलाहकार प्रणाली के साथ क्षेत्र-परीक्षित कम लागत वाले मृदा सेंसर पायलट गांवों से परे विस्तार के लिए तैयार हैं।',
    expectedRole: 'Manufacture sensors at scale and support distribution logistics.',
    expectedRoleHi: 'सेंसर का बड़े पैमाने पर निर्माण करना और वितरण रसद का समर्थन करना।',
    dateTime: '2026-08-05T09:15:00',
    status: 'Rejected',
    technology: 'IoT',
  },
];

// Common reasons a citizen might give when an existing solution doesn't fit (Section 20)
export const commonProblemReasons = [
  'Existing solution is too expensive',
  'Existing solution is not accessible',
  'Existing solution is not available in my area',
  'Existing solution is technically unsuitable',
  'Existing solution is difficult to use',
  'Existing solution requires unavailable resources',
  'Existing solution is too slow',
  'Existing solution is not scalable',
  'Existing solution does not solve the complete problem',
  'Existing solution is outdated',
  'Other',
];

// Existing solutions catalog used by the global search (Section 18)
export const existingSolutions = [
  {
    id: 'sol-1',
    title: 'Smart Waste Collection App',
    titleHi: 'स्मार्ट कचरा संग्रहण ऐप',
    matchesCategory: 'Environment',
    keywords: ['waste', 'garbage', 'dustbin', 'collection', 'trash'],
    area: 'Dhanbad, Jharkhand',
    areaHi: 'धनबाद, झारखंड',
    organization: 'IIT (ISM) Dhanbad',
    organizationHi: 'आईआईटी (आईएसएम) धनबाद',
    technologies: ['IoT Sensors', 'Mobile App', 'Route Optimization'],
    description: 'IoT-enabled smart dustbins with a mobile app that optimizes collection routes in real time.',
    descriptionHi: 'IoT-सक्षम स्मार्ट कूड़ेदान और मोबाइल ऐप जो वास्तविक समय में कचरा संग्रहण मार्गों को अनुकूलित करता है।',
    status: 'Deployed',
    active: true,
    implementationInfo: 'Currently running in 4 wards of Dhanbad Municipal Corporation. Can be replicated with local sensor installation (approx. 6-8 weeks).',
    implementationInfoHi: 'वर्तमान में धनबाद नगर निगम के 4 वार्डों में संचालित। स्थानीय सेंसर स्थापना के साथ दोहराया जा सकता है (लगभग 6-8 सप्ताह)।',
  },
  {
    id: 'sol-2',
    title: 'AI-Based Traffic Signal Automation',
    titleHi: 'AI-आधारित ट्रैफिक सिग्नल ऑटोमेशन',
    matchesCategory: 'Infrastructure',
    keywords: ['traffic', 'signal', 'road', 'congestion', 'jam'],
    area: 'Ranchi, Jharkhand',
    areaHi: 'राँची, झारखंड',
    organization: 'NIT Jamshedpur',
    organizationHi: 'एनआईटी जमशेदपुर',
    technologies: ['Computer Vision', 'Edge AI'],
    description: 'AI model reading live camera feeds to adjust signal timing dynamically, cutting congestion by 40%.',
    descriptionHi: 'लाइव कैमरा फीड देखकर सिग्नल टाइमिंग को गतिशील रूप से बदलने वाला AI मॉडल, जिससे जाम में 40% की कमी आई।',
    status: 'Deployed',
    active: true,
    implementationInfo: 'Live at 6 intersections in Ranchi. Expansion to new intersections requires camera hardware and a 3-4 week calibration period.',
    implementationInfoHi: 'राँची के 6 चौराहों पर सक्रिय। नए चौराहों पर विस्तार हेतु कैमरा हार्डवेयर एवं 3-4 सप्ताह के अंशांकन की आवश्यकता है।',
  },
  {
    id: 'sol-3',
    title: 'Rural Drinking Water Quality Monitoring',
    titleHi: 'ग्रामीण पेयजल गुणवत्ता निगरानी',
    matchesCategory: 'Water & Sanitation',
    keywords: ['water', 'drinking', 'quality', 'purity', 'pollution'],
    area: 'Dhanbad, Jharkhand',
    areaHi: 'धनबाद, झारखंड',
    organization: 'IIT (ISM) Dhanbad',
    organizationHi: 'आईआईटी (आईएसएम) धनबाद',
    technologies: ['IoT Water Sensors', 'Real-time Dashboard'],
    description: 'IoT water-quality sensor network with a real-time alert dashboard for officials.',
    descriptionHi: 'अधिकारियों के लिए रीयल-टाइम अलर्ट डैशबोर्ड के साथ IoT जल-गुणवत्ता सेंसर नेटवर्क।',
    status: 'Pilot',
    active: true,
    implementationInfo: 'Pilot running in 3 villages near Dhanbad. Needs area-specific sensor calibration before wider rollout.',
    implementationInfoHi: 'धनबाद के निकट 3 गांवों में पायलट परीक्षण संचालित। व्यापक प्रसार से पहले क्षेत्र-विशिष्ट सेंसर अंशांकन आवश्यक है।',
  },
  {
    id: 'sol-4',
    title: 'Offline Digital Classroom Kit',
    titleHi: 'ऑफ़लाइन डिजिटल क्लासरूम किट',
    matchesCategory: 'Education',
    keywords: ['school', 'education', 'classroom', 'learning', 'digital'],
    area: 'Statewide',
    areaHi: 'राज्यव्यापी',
    organization: 'IIT (ISM) Dhanbad',
    organizationHi: 'आईआईटी (आईएसएम) धनबाद',
    technologies: ['Local Wi-Fi Server', 'Offline Content'],
    description: 'Offline content server running on a local Wi-Fi hotspot with the full curriculum preloaded.',
    descriptionHi: 'स्थानीय वाई-फाई हॉटस्पॉट पर चलने वाला ऑफ़लाइन कंटेंट सर्वर, जिसमें पूरा पाठ्यक्रम पहले से लोड है।',
    status: 'Active',
    active: true,
    implementationInfo: 'Deployed in 12 government schools. Setup takes about 2 weeks per school.',
    implementationInfoHi: '12 सरकारी स्कूलों में लागू किया गया। प्रत्येक स्कूल में स्थापना में लगभग 2 सप्ताह लगते हैं।',
  },
];
