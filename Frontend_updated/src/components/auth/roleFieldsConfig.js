import { universityNames, domainList, STUDENT_APPROVED_UNIVERSITIES } from '../../data/orgData';

// Stakeholder-specific registration fields (Section 16). Each entry can be
// a plain text input or a select with predefined options. `required: true`
// fields must be filled in before registration can complete.
export const roleFieldsConfig = {
  citizen: [],
  student: [
    { key: 'university', label: 'University', type: 'select', options: STUDENT_APPROVED_UNIVERSITIES, required: true },
    { key: 'department', label: 'Department', required: true },
    { key: 'studentId', label: 'Student ID', required: true },
    { key: 'semester', label: 'Semester / Year' },
    { key: 'domain', label: 'Domain', type: 'select', options: domainList, required: true },
    { key: 'skills', label: 'Skills (comma separated)', isList: true },
    { key: 'technologies', label: 'Technologies (comma separated)', isList: true },
  ],
  faculty: [
    { key: 'university', label: 'University', type: 'select', options: universityNames, required: true },
    { key: 'department', label: 'Department', required: true },
    { key: 'designation', label: 'Designation', required: true },
    { key: 'facultyId', label: 'Faculty ID', required: true },
    { key: 'researchArea', label: 'Research Area', required: true },
    { key: 'expertise', label: 'Expertise', required: true },
    { key: 'technologies', label: 'Technologies (comma separated)', isList: true },
    { key: 'experience', label: 'Experience (years)', required: false },
  ],
  'university-admin': [
    { key: 'university', label: 'University', type: 'select', options: universityNames, required: true },
    { key: 'department', label: 'Administration / Department', required: true },
    { key: 'designation', label: 'Designation', required: true },
    { key: 'adminId', label: 'Administration ID', required: true },
  ],
  university_admin: [
    { key: 'university', label: 'University', type: 'select', options: universityNames, required: true },
    { key: 'department', label: 'Administration / Department', required: true },
    { key: 'designation', label: 'Designation', required: true },
    { key: 'adminId', label: 'Administration ID', required: true },
  ],
  government: [
    { key: 'department', label: 'Government Department', required: true },
    { key: 'officerName', label: 'Officer / Representative Name', required: true },
    { key: 'authorityId', label: 'Authority ID', required: true },
  ],
  industry: [
    { key: 'company', label: 'Company Name', required: true },
    { key: 'companyEmail', label: 'Company Email', required: true },
    { key: 'employeeId', label: 'Employee ID', required: true },
    { key: 'designation', label: 'Designation', required: true },
    { key: 'department', label: 'Department' },
    { key: 'domain', label: 'Industry / Domain', type: 'select', options: domainList, required: true },
    { key: 'expertise', label: 'Areas of Expertise' },
    { key: 'technologies', label: 'Technologies (comma separated)', isList: true },
  ],
  industry_employee: [
    { key: 'company', label: 'Company Name', required: true },
    { key: 'companyEmail', label: 'Company Email', required: true },
    { key: 'employeeId', label: 'Employee ID', required: true },
    { key: 'designation', label: 'Designation', required: true },
    { key: 'department', label: 'Department' },
    { key: 'domain', label: 'Industry / Domain', type: 'select', options: domainList, required: true },
    { key: 'expertise', label: 'Areas of Expertise' },
    { key: 'technologies', label: 'Technologies (comma separated)', isList: true },
  ],
};
