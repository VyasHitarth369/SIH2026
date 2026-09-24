import apiClient from './apiClient';

/**
 * Government Monitoring, Solved Problems & System Analytics Service.
 */
export const governmentService = {
  async fetchGovernmentAnalytics() {
    const res = await apiClient.get('/government/analytics');
    return res?.data || res;
  },

  async fetchGovernmentProblems(options = {}) {
    let params = {};
    if (typeof options === 'string') {
      const categoryOrStatus = options;
      const district = arguments[1] || null;
      if (['pending', 'allocated', 'rejected', 'solved', 'all'].includes(categoryOrStatus)) {
        params.category = categoryOrStatus;
      } else if (categoryOrStatus) {
        params.status = categoryOrStatus;
      }
      if (district) params.district = district;
    } else if (typeof options === 'object' && options !== null) {
      if (options.category) params.category = options.category;
      if (options.status) params.status = options.status;
      if (options.district) params.district = options.district;
      if (options.page) params.page = options.page;
      if (options.limit) params.limit = options.limit;
    }
    const res = await apiClient.get('/government/problems', params);
    return res;
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

  async approveProblem(challengeId) {
    const res = await apiClient.post(`/government/problems/${challengeId}/approve`);
    return res?.data || res;
  },

  async rejectProblem(challengeId, reason) {
    const res = await apiClient.post(`/government/problems/${challengeId}/reject`, { reason });
    return res?.data || res;
  },
};

export default governmentService;
