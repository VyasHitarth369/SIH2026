import apiClient from './apiClient';

/**
 * Government Monitoring, Solved Problems & System Analytics Service.
 */
export const governmentService = {
  async fetchGovernmentAnalytics() {
    const res = await apiClient.get('/government/analytics');
    return res?.data || res;
  },

  async fetchGovernmentProblems(status = null, district = null) {
    const res = await apiClient.get('/government/problems', { status, district });
    return res?.data || [];
  },

  async fetchSolvedProjects() {
    const res = await apiClient.get('/government/solved-projects');
    return res?.data || [];
  },

  async fetchGovernmentFaculties(universityId = null) {
    const res = await apiClient.get('/government/faculties', { university_id: universityId });
    return res?.data || [];
  },

  async fetchGovernmentStudents(universityId = null) {
    const res = await apiClient.get('/government/students', { university_id: universityId });
    return res?.data || [];
  },
};

export default governmentService;
