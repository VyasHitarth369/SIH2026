// Domain-based leaderboard filters (replaces the old category/type filters).
export const domains = [
  { value: 'web-dev', en: 'Web Development', hi: 'वेब डेवलपमेंट' },
  { value: 'robotics', en: 'Robotics', hi: 'रोबोटिक्स' },
  { value: 'agriculture', en: 'Agriculture', hi: 'कृषि' },
  { value: 'mechanical', en: 'Mechanical Design', hi: 'मैकेनिकल डिज़ाइन' },
  { value: 'healthcare', en: 'Healthcare', hi: 'स्वास्थ्य सेवा' },
  { value: 'ai-ml', en: 'AI / Machine Learning', hi: 'एआई / मशीन लर्निंग' },
  { value: 'iot', en: 'IoT', hi: 'आईओटी' },
  { value: 'cybersecurity', en: 'Cybersecurity', hi: 'साइबर सुरक्षा' },
  { value: 'electronics', en: 'Electronics', hi: 'इलेक्ट्रॉनिक्स' },
  { value: 'software-dev', en: 'Software Development', hi: 'सॉफ्टवेयर डेवलपमेंट' },
];

// Weighted leaderboard score = facultyScore * 0.7 + citizenScore * 0.3 (both out of 5)
const rawLeaderboardStudents = [
  {
    id: 'lb-1',
    name: 'Ananya Singh',
    email: 'ananya.singh@nitjsr.ac.in',
    university: 'NIT Jamshedpur',
    domain: 'healthcare',
    skills: ['Hardware Integration', 'WebRTC', 'Embedded Systems'],
    problemTitle: {
      hi: 'दूरदराज के गांवों हेतु टेलीमेडिसिन कियोस्क',
      en: 'Telemedicine Kiosk for Remote Villages',
    },
    problemDesc: {
      hi: 'ग्रामीण क्षेत्रों में डॉक्टरों की कमी के कारण ग्रामीणों को बुनियादी परामर्श के लिए भी घंटों यात्रा करनी पड़ती थी।',
      en: 'Villagers had to travel hours for basic consultations due to a shortage of doctors in remote areas.',
    },
    solution: {
      hi: 'सौर ऊर्जा से चलने वाला टेलीमेडिसिन कियोस्क बनाया जो वीडियो कॉल के माध्यम से ग्रामीणों को शहर के डॉक्टरों से जोड़ता है।',
      en: 'Built a solar-powered telemedicine kiosk connecting villagers to city doctors via video call and recording basic vitals.',
    },
    role: {
      hi: 'हार्डवेयर एकीकरण का नेतृत्व किया और वीडियो परामर्श मॉड्यूल विकसित किया।',
      en: 'Led hardware integration and built the video-consultation module.',
    },
    facultyReview: {
      score: 4.9,
      comment: {
        hi: 'असाधारण तकनीकी गहराई एवं अनुकरणीय टीम नेतृत्व।',
        en: 'Exceptional technical depth and team leadership.',
      },
    },
    citizenFeedbackScore: 4.5,
    achievements: ['SIH 2026 Finalist', 'Best Hardware Prototype'],
  },
  {
    id: 'lb-2',
    name: 'Md. Kaif Ansari',
    email: 'kaif.ansari@bitmesra.ac.in',
    university: 'BIT Mesra',
    domain: 'healthcare',
    skills: ['Flutter', 'Node.js', 'Offline-first Design'],
    problemTitle: {
      hi: 'मातृ एवं शिशु स्वास्थ्य ट्रैकिंग ऐप',
      en: 'Maternal & Child Health Tracking App',
    },
    problemDesc: {
      hi: 'ग्रामीण आशा कार्यकर्ताओं के पास टीकाकरण कार्यक्रम और नियमित जांच को ट्रैक करने का कोई डिजिटल माध्यम नहीं था।',
      en: 'Rural ASHA workers had no digital way to track vaccination schedules and checkups.',
    },
    solution: {
      hi: 'ऑफ़लाइन-फर्स्ट मोबाइल ऐप बनाया जो टीकाकरण अनुस्मारक भेजता है और नेटवर्क मिलने पर डेटा सिंक करता है।',
      en: 'Built an offline-first mobile app that sends vaccination reminders and syncs data when connectivity is available.',
    },
    role: {
      hi: 'ऐप बैकएंड और ऑफ़लाइन-सिंक लॉजिक का डिज़ाइन किया।',
      en: 'Designed the app backend and offline-sync logic.',
    },
    facultyReview: {
      score: 4.6,
      comment: {
        hi: 'मजबूत और ज़मीनी स्तर पर उपयोग योग्य समाधान।',
        en: 'Solid, field-ready solution.',
      },
    },
    citizenFeedbackScore: 4.2,
    achievements: ['Top 10 Statewide'],
  },
  {
    id: 'lb-3',
    name: 'Ritika Mahto',
    email: 'ritika.mahto@bausagri.ac.in',
    university: 'BAU Ranchi',
    domain: 'agriculture',
    skills: ['IoT Sensors', 'Data Analysis', 'LoRa'],
    problemTitle: {
      hi: 'मृदा स्वास्थ्य निगरानी सेंसर नेटवर्क',
      en: 'Soil Health Monitoring Sensor Network',
    },
    problemDesc: {
      hi: 'किसानों के पास मिट्टी की नमी और पोषक तत्वों की सटीक जानकारी नहीं थी, जिससे उपज में कमी आ रही थी।',
      en: 'Farmers lacked visibility into soil moisture and nutrients, leading to reduced yields.',
    },
    solution: {
      hi: 'किसानों के लिए एसएमएस-आधारित सलाह प्रणाली के साथ कम लागत वाले IoT मृदा सेंसर विकसित किए।',
      en: 'Developed low-cost IoT soil sensors paired with an SMS-based advisory system for farmers.',
    },
    role: {
      hi: 'सेंसर अंशांकन संभाला और डेटा-विश्लेषण मॉडल तैयार किया।',
      en: 'Handled sensor calibration and built the data-analysis model.',
    },
    facultyReview: {
      score: 4.7,
      comment: {
        hi: 'फ़ील्ड परीक्षण में उत्कृष्ट प्रदर्शन।',
        en: 'Excellent performance in field testing.',
      },
    },
    citizenFeedbackScore: 4.7,
    achievements: ['Best AgriTech Solution 2026'],
  },
  {
    id: 'lb-4',
    name: 'Suraj Mahli',
    email: 'suraj.mahli@nitjsr.ac.in',
    university: 'NIT Jamshedpur',
    domain: 'ai-ml',
    skills: ['Machine Learning', 'Python', 'Computer Vision'],
    problemTitle: {
      hi: 'फसल रोग पहचान मोबाइल ऐप',
      en: 'Crop Disease Detection Mobile App',
    },
    problemDesc: {
      hi: 'फसल रोगों का देर से पता चलने के कारण किसानों को भारी नुकसान उठाना पड़ता था।',
      en: 'Farmers suffered heavy losses from late detection of crop diseases.',
    },
    solution: {
      hi: 'एक AI-आधारित ऐप बनाया जो अपलोड की गई फोटो से फसल के रोगों की पहचान करता है।',
      en: 'Built an AI-based app that detects crop diseases from an uploaded photo.',
    },
    role: {
      hi: 'मशीन लर्निंग मॉडल को प्रशिक्षित एवं बेहतर बनाया।',
      en: 'Trained and fine-tuned the machine learning model.',
    },
    facultyReview: {
      score: 4.4,
      comment: {
        hi: 'सराहनीय प्रोटोटाइप, सटीकता में सुधार जारी है।',
        en: 'Good prototype, accuracy improvements ongoing.',
      },
    },
    citizenFeedbackScore: 4.0,
    achievements: [],
  },
  {
    id: 'lb-5',
    name: 'Neha Kumari',
    email: 'neha.kumari@iitism.ac.in',
    university: 'IIT (ISM) Dhanbad',
    domain: 'software-dev',
    skills: ['Systems Design', 'Content Pipelines', 'Networking'],
    problemTitle: {
      hi: 'ऑफ़लाइन डिजिटल क्लासरूम किट',
      en: 'Offline Digital Classroom Kit',
    },
    problemDesc: {
      hi: 'नेटवर्क कवरेज के बिना सरकारी स्कूलों के पास डिजिटल शिक्षण सामग्री तक पहुंचने का कोई साधन नहीं था।',
      en: 'Government schools without network coverage had no way to access digital learning content.',
    },
    solution: {
      hi: 'स्थानीय वाई-फाई हॉटस्पॉट पर चलने वाला ऑफ़लाइन कंटेंट सर्वर बनाया, जिसमें पूरा पाठ्यक्रम पहले से लोड है।',
      en: 'Built an offline content server running on a local Wi-Fi hotspot with the full curriculum preloaded.',
    },
    role: {
      hi: 'सर्वर आर्किटेक्चर और कंटेंट सिंडिकेशन पाइपलाइन का निर्माण किया।',
      en: 'Built the server architecture and content syndication pipeline.',
    },
    facultyReview: {
      score: 4.8,
      comment: {
        hi: 'नवाचार और निष्पादन दोनों में उत्कृष्ट कार्य।',
        en: 'Outstanding on both innovation and execution.',
      },
    },
    citizenFeedbackScore: 4.6,
    achievements: ['SIH 2026 Winner'],
  },
  {
    id: 'lb-6',
    name: 'Abhishek Toppo',
    email: 'abhishek.toppo@bitmesra.ac.in',
    university: 'BIT Mesra',
    domain: 'ai-ml',
    skills: ['NLP', 'Chatbot Design'],
    problemTitle: {
      hi: 'क्षेत्रीय भाषा शिक्षण चैटबॉट',
      en: 'Regional Language Learning Chatbot',
    },
    problemDesc: {
      hi: 'जनजातीय क्षेत्रों के छात्रों को हिंदी/अंग्रेजी माध्यम की पाठ्यपुस्तकों को समझने में कठिनाई होती थी।',
      en: 'Students in tribal areas struggled with Hindi/English medium textbooks.',
    },
    solution: {
      hi: 'एक चैटबॉट विकसित किया जो स्थानीय जनजातीय भाषा में छात्रों के प्रश्नों के उत्तर देता है।',
      en: 'Developed a chatbot that answers student questions in the local tribal language.',
    },
    role: {
      hi: 'भाषा मॉडल को परिष्कृत किया और छात्रों के साथ परीक्षण का नेतृत्व किया।',
      en: 'Fine-tuned the language model and led testing with students.',
    },
    facultyReview: {
      score: 4.3,
      comment: {
        hi: 'सराहनीय सामाजिक प्रभाव।',
        en: 'Commendable social impact.',
      },
    },
    citizenFeedbackScore: 4.1,
    achievements: [],
  },
  {
    id: 'lb-7',
    name: 'Priya Kumari',
    email: 'priya.kumari@iitism.ac.in',
    university: 'IIT (ISM) Dhanbad',
    domain: 'iot',
    skills: ['IoT', 'Embedded C', 'React'],
    problemTitle: {
      hi: 'ग्रामीण पेयजल गुणवत्ता निगरानी',
      en: 'Rural Drinking Water Quality Monitoring',
    },
    problemDesc: {
      hi: 'खराब पानी की गुणवत्ता के कारण कई गांवों में जलजनित बीमारियों का प्रकोप हो रहा था।',
      en: 'Poor water quality was causing waterborne illness outbreaks in several villages.',
    },
    solution: {
      hi: 'अधिकारियों के लिए रीयल-टाइम अलर्ट डैशबोर्ड के साथ IoT जल-गुणवत्ता सेंसर नेटवर्क बनाया।',
      en: 'Built an IoT water-quality sensor network with a real-time alert dashboard for officials.',
    },
    role: {
      hi: 'सेंसर नेटवर्क डिज़ाइन किया और निगरानी डैशबोर्ड तैयार किया।',
      en: 'Designed the sensor network and built the monitoring dashboard.',
    },
    facultyReview: {
      score: 4.9,
      comment: {
        hi: 'उत्कृष्ट तकनीकी निष्पादन एवं दस्तावेज़ीकरण।',
        en: 'Excellent technical execution and documentation.',
      },
    },
    citizenFeedbackScore: 4.6,
    achievements: ['Best IoT Deployment'],
  },
  {
    id: 'lb-8',
    name: 'Vikash Choudhary',
    email: 'vikash.choudhary@nitjsr.ac.in',
    university: 'NIT Jamshedpur',
    domain: 'iot',
    skills: ['App Development', 'Cost Estimation Engines'],
    problemTitle: {
      hi: 'वर्षा जल संचयन योजनाकार ऐप',
      en: 'Rainwater Harvesting Planner App',
    },
    problemDesc: {
      hi: 'घरों को वर्षा जल संचयन की योजना बनाना कठिन लगता था और इसे महंगा माना जाता था।',
      en: 'Households found rainwater harvesting planning difficult and assumed it to be expensive.',
    },
    solution: {
      hi: 'एक ऐप बनाया जो छत के आकार के आधार पर संचयन क्षमता और लागत का अनुमान लगाता है।',
      en: 'Built an app that estimates harvesting potential and cost based on rooftop size.',
    },
    role: {
      hi: 'गणना इंजन और ऐप यूआई का निर्माण किया।',
      en: 'Built the calculation engine and app UI.',
    },
    facultyReview: {
      score: 4.2,
      comment: {
        hi: 'व्यावहारिक और उपयोग में आसान।',
        en: 'Practical and user-friendly.',
      },
    },
    citizenFeedbackScore: 4.3,
    achievements: [],
  },
  {
    id: 'lb-9',
    name: 'Rohit Verma',
    email: 'rohit.verma@nitjsr.ac.in',
    university: 'NIT Jamshedpur',
    domain: 'ai-ml',
    skills: ['Computer Vision', 'TensorFlow', 'Edge AI'],
    problemTitle: {
      hi: 'AI-आधारित ट्रैफिक सिग्नल ऑटोमेशन',
      en: 'AI-Based Traffic Signal Automation',
    },
    problemDesc: {
      hi: 'पारंपरिक टाइमर-आधारित सिग्नल लाइव ट्रैफिक के अनुसार नहीं बदलने से व्यस्त चौराहों पर लंबा जाम रहता था।',
      en: 'Busy intersections faced long jams because traditional timer-based signals could not adapt to live traffic.',
    },
    solution: {
      hi: 'लाइव कैमरा फीड के अनुसार सिग्नल टाइमिंग को गतिशील रूप से समायोजित करने वाला AI मॉडल तैनात किया।',
      en: 'Deployed an AI model reading live camera feeds to adjust signal timing dynamically.',
    },
    role: {
      hi: 'कंप्यूटर-विज़न मॉडल और सिग्नल नियंत्रण लॉजिक का निर्माण किया।',
      en: 'Built the computer-vision model and signal control logic.',
    },
    facultyReview: {
      score: 4.8,
      comment: {
        hi: 'शहर स्तर पर ठोस प्रभाव डालने वाला उत्कृष्ट कार्य।',
        en: 'Solid work with city-scale impact.',
      },
    },
    citizenFeedbackScore: 4.8,
    achievements: ['SIH 2026 Finalist', 'City Impact Award'],
  },
  {
    id: 'lb-10',
    name: 'Ankita Devi',
    email: 'ankita.devi@bitmesra.ac.in',
    university: 'BIT Mesra',
    domain: 'electronics',
    skills: ['GIS Mapping', 'Sensor Networks'],
    problemTitle: {
      hi: 'स्मार्ट स्ट्रीटलाइट ऑटोमेशन',
      en: 'Smart Streetlight Automation',
    },
    problemDesc: {
      hi: 'रात के समय प्रमुख सड़कों पर स्ट्रीटलाइट बंद रहने से दुर्घटनाएं हो रही थीं।',
      en: 'Streetlight failures on major roads at night were contributing to accidents.',
    },
    solution: {
      hi: 'स्ट्रीटलाइट्स के लिए लाइट-सेंसर और जीआईएस-आधारित खराबी पहचान प्रणाली विकसित की।',
      en: 'Developed a light-sensor and GIS-based fault-detection system for streetlights.',
    },
    role: {
      hi: 'जीआईएस मैपिंग और फॉल्ट-अलर्ट सिस्टम तैयार किया।',
      en: 'Built the GIS mapping and fault-alert system.',
    },
    facultyReview: {
      score: 4.5,
      comment: {
        hi: 'ज़मीनी स्तर पर मजबूत तैनाती।',
        en: 'Strong field deployment.',
      },
    },
    citizenFeedbackScore: 4.4,
    achievements: [],
  },
  {
    id: 'lb-11',
    name: 'Sameer Iqbal',
    email: 'sameer.iqbal@bitmesra.ac.in',
    university: 'BIT Mesra',
    domain: 'cybersecurity',
    skills: ['Network Security', 'Penetration Testing'],
    problemTitle: {
      hi: 'नगर निगम पोर्टल सुरक्षा सुदृढ़ीकरण',
      en: 'Municipal Portal Security Hardening',
    },
    problemDesc: {
      hi: 'शहर के नागरिक-सेवा पोर्टल में पुराना प्रमाणीकरण था और यह सामान्य हमलों के प्रति संवेदनशील था।',
      en: 'The city\u2019s citizen-services portal had outdated authentication and was vulnerable to common attacks.',
    },
    solution: {
      hi: 'आधुनिक प्रमाणीकरण, रेट लिमिटिंग और भेद्यता-निगरानी डैशबोर्ड लागू किया।',
      en: 'Implemented modern authentication, rate limiting, and a vulnerability-monitoring dashboard.',
    },
    role: {
      hi: 'सुरक्षा ऑडिट का नेतृत्व किया और सुधारात्मक उपाय लागू किए।',
      en: 'Led the security audit and implemented the fixes.',
    },
    facultyReview: {
      score: 4.6,
      comment: {
        hi: 'विस्तृत ऑडिट एवं स्वच्छ कार्यान्वयन।',
        en: 'Thorough audit and clean implementation.',
      },
    },
    citizenFeedbackScore: 4.2,
    achievements: [],
  },
  {
    id: 'lb-12',
    name: 'Divya Prakash',
    email: 'divya.prakash@nitjsr.ac.in',
    university: 'NIT Jamshedpur',
    domain: 'web-dev',
    skills: ['React', 'Node.js', 'Accessibility'],
    problemTitle: {
      hi: 'एकीकृत शिकायत निवारण पोर्टल',
      en: 'Unified Grievance Redressal Portal',
    },
    problemDesc: {
      hi: 'नागरिकों को विभिन्न विभागों के लिए अलग-अलग पोर्टलों का उपयोग करना पड़ता था, जिससे भ्रम और देरी होती थी।',
      en: 'Citizens had to use different portals for different departments, causing confusion and delays.',
    },
    solution: {
      hi: 'एक एकल उत्तरदायी वेब पोर्टल बनाया जो शिकायतों को स्वचालित रूप से सही विभाग में भेजता है।',
      en: 'Built a single responsive web portal routing grievances to the right department automatically.',
    },
    role: {
      hi: 'फ्रंटएंड और रूटिंग लॉजिक का निर्माण किया।',
      en: 'Built the frontend and the routing logic.',
    },
    facultyReview: {
      score: 4.4,
      comment: {
        hi: 'सुलभ, स्पष्ट एवं भली-भांति परीक्षण किया हुआ समाधान।',
        en: 'Clean, accessible, and well-tested.',
      },
    },
    citizenFeedbackScore: 4.3,
    achievements: [],
  },
];
 
export const leaderboardStudents = rawLeaderboardStudents.map((s) => ({
  ...s,
  linkedin: s.linkedin || `https://www.linkedin.com/in/${s.name.toLowerCase().replace(/[^a-z0-9]/g, '')}`,
  github: s.github || `https://github.com/${s.name.toLowerCase().replace(/[^a-z0-9]/g, '')}`,
}));

export function weightedScore(student) {
  return +(student.facultyReview.score * 0.7 + student.citizenFeedbackScore * 0.3).toFixed(2);
}
