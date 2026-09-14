// Role-based navigation with full bilingual support for Hindi & English.
export function getNavItems(user, t, lang = 'en') {
  if (!user) return [];

  let items = [];
  switch (user.role) {
    case 'citizen':
      items = [
        { to: '/citizen/problems', label: lang === 'hi' ? '🔎 मेरी समस्याएं' : '🔎 My Problems' },
        { to: '/citizen/add-problem', label: lang === 'hi' ? '➕ नई समस्या दर्ज करें' : '➕ Submit New Problem' },
        { to: '/profile', label: lang === 'hi' ? '👤 मेरी प्रोफ़ाइल' : '👤 Profile' },
      ];
      break;

    case 'student':
      items = [
        { to: '/student/projects', label: lang === 'hi' ? '📁 मेरे प्रोजेक्ट्स' : '📁 My Projects' },
        { to: '/leaderboard', label: lang === 'hi' ? '🏆 लीडरबोर्ड' : '🏆 Leaderboard' },
        { to: '/profile', label: lang === 'hi' ? '👤 मेरी प्रोफ़ाइल' : '👤 Profile' },
      ];
      break;

    case 'faculty':
      items = [
        { to: '/faculty/projects', label: lang === 'hi' ? '📁 मेरे प्रोजेक्ट्स' : '📁 My Projects' },
        { to: '/faculty/university-problems', label: lang === 'hi' ? '🏫 विश्वविद्यालय समस्याएं' : '🏫 University Problems' },
        { to: '/profile', label: lang === 'hi' ? '👤 मेरी प्रोफ़ाइल' : '👤 Profile' },
      ];
      break;

    case 'university_admin':
    case 'university-admin':
      items = [
        { to: '/university-admin/dashboard', label: lang === 'hi' ? '📊 डैशबोर्ड' : '📊 Dashboard' },
        { to: '/university-admin/problems', label: lang === 'hi' ? '📥 प्राप्त समस्याएं' : '📥 Incoming Problems' },
        { to: '/university-admin/allocations', label: lang === 'hi' ? '📌 आवंटन' : '📌 Allocations' },
        { to: '/profile', label: lang === 'hi' ? '👤 मेरी प्रोफ़ाइल' : '👤 Profile' },
      ];
      break;

    case 'government':
      items = [
        { to: '/government/dashboard', label: lang === 'hi' ? '📊 डैशबोर्ड' : '📊 Dashboard' },
        { to: '/government/add-problem', label: lang === 'hi' ? '➕ नई समस्या दर्ज करें' : '➕ Add Problem' },
        { to: '/government/active-problems', label: lang === 'hi' ? '📋 सक्रिय समस्याएं' : '📋 Active Problems' },
        { to: '/government/faculties', label: lang === 'hi' ? '👨‍🏫 आवंटित फैकल्टी' : '👨‍🏫 Assigned Faculties' },
        { to: '/government/students', label: lang === 'hi' ? '👨‍🎓 समाधान कर रहे छात्र' : '👨‍🎓 Students Solving Problems' },
        { to: '/government/solved', label: lang === 'hi' ? '✅ हल की गई समस्याएं' : '✅ Solved Problems' },
        { to: '/profile', label: lang === 'hi' ? '👤 मेरी प्रोफ़ाइल' : '👤 Profile' },
      ];
      break;

    case 'industry_employee':
    case 'industry':
      items = [
        { to: '/industry-employee/dashboard', label: lang === 'hi' ? '📊 डैशबोर्ड' : '📊 Dashboard' },
        { to: '/industry-employee/add-problem', label: lang === 'hi' ? '➕ नई समस्या दर्ज करें' : '➕ Add Problem' },
        { to: '/industry-employee/proposals', label: lang === 'hi' ? '🤝 सहयोग प्रस्ताव' : '🤝 Collaboration Proposals' },
        { to: '/industry-employee/collaboration', label: lang === 'hi' ? '🔗 सक्रिय सहयोग' : '🔗 Active Collaborations' },
        { to: '/industry-employee/past-projects', label: lang === 'hi' ? '📁 पूर्व परियोजनाएं' : '📁 Past Projects' },
        { to: '/leaderboard', label: lang === 'hi' ? '🏆 लीडरबोर्ड' : '🏆 Leaderboard' },
        { to: '/profile', label: lang === 'hi' ? '👤 मेरी प्रोफ़ाइल' : '👤 Profile' },
      ];
      break;

    default:
      items = [];
  }

  return items;
}

export function getRoleBadge(user, t, lang = 'en') {
  if (!user) return '';
  const badgesEn = {
    citizen: 'Citizen Portal',
    student: 'Student Portal',
    faculty: 'Faculty Portal',
    university_admin: 'University Administration Portal',
    'university-admin': 'University Administration Portal',
    government: 'Government Portal',
    industry_employee: 'Industry Employee Portal',
    industry: 'Industry Employee Portal',
  };
  const badgesHi = {
    citizen: 'नागरिक पोर्टल',
    student: 'छात्र पोर्टल',
    faculty: 'फैकल्टी पोर्टल',
    university_admin: 'विश्वविद्यालय प्रशासन पोर्टल',
    'university-admin': 'विश्वविद्यालय प्रशासन पोर्टल',
    government: 'सरकार पोर्टल',
    industry_employee: 'उद्योग कर्मचारी पोर्टल',
    industry: 'उद्योग कर्मचारी पोर्टल',
  };
  return (lang === 'hi' ? badgesHi[user.role] : badgesEn[user.role]) || '';
}
