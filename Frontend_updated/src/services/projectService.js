import apiClient from './apiClient';

/**
 * Projects, Milestones, Members, and Feedback Service.
 */
export const projectService = {
  async fetchProjects(params = {}) {
    const res = await apiClient.get('/projects', params);
    return res?.data || [];
  },

  async fetchProjectById(projectId) {
    const res = await apiClient.get(`/projects/${projectId}`);
    return res?.data || res;
  },

  async createProject(payload) {
    const res = await apiClient.post('/projects', payload);
    return res?.data || res;
  },

  async addProjectMember(projectId, studentId, role = 'member') {
    const res = await apiClient.post(`/projects/${projectId}/members`, {
      student_id: studentId,
      role,
    });
    return res?.data || res;
  },

  async fetchProjectMembers(projectId) {
    const res = await apiClient.get(`/projects/${projectId}/members`);
    return res?.data || [];
  },

  async createMilestone(projectId, milestoneData) {
    const res = await apiClient.post(`/projects/${projectId}/milestones`, milestoneData);
    return res?.data || res;
  },

  async updateMilestone(milestoneId, patchData) {
    const res = await apiClient.patch(`/milestones/${milestoneId}`, patchData);
    return res?.data || res;
  },

  async updateProjectStatus(projectId, status, justification = '') {
    const res = await apiClient.patch(`/projects/${projectId}/status`, {
      status,
      justification,
    });
    return res?.data || res;
  },

  async submitFeedback(projectId, feedbackData) {
    const res = await apiClient.post(`/projects/${projectId}/feedback`, feedbackData);
    return res?.data || res;
  },

  async fetchProjectFeedback(projectId) {
    const res = await apiClient.get(`/projects/${projectId}/feedback`);
    return res?.data || [];
  },

  async fetchProjectImpact(projectId) {
    const res = await apiClient.get(`/projects/${projectId}/impact`);
    return res?.data || res;
  },

  async submitEmployeeInterest(projectId, message) {
    const res = await apiClient.post(`/projects/${projectId}/employee-interest`, { message });
    return res?.data || res;
  },

  async fetchEmployeeInterests(projectId) {
    const res = await apiClient.get(`/projects/${projectId}/employee-interests`);
    return res?.data || [];
  },

  async updateEmployeeInterest(projectId, interestId, status, note = '') {
    const res = await apiClient.patch(`/projects/${projectId}/employee-interests/${interestId}`, {
      status,
      note,
    });
    return res?.data || res;
  },
};

export default projectService;
