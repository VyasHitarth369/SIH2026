import apiClient from './apiClient';

/**
 * Deterministic Matching Service for Universities & Industry Partners.
 */
export const matchingService = {
  /**
   * Fetches deterministically scored university matches for a challenge.
   */
  async fetchUniversityMatches(challengeId, limit = 5) {
    const res = await apiClient.get(`/challenges/${challengeId}/universities`, { limit });
    return res?.data || [];
  },

  /**
   * Records University Admin response (accept/reject) to match invitation.
   */
  async respondUniversityMatch(challengeId, universityId, action, responseNote = '') {
    const res = await apiClient.post(`/challenges/${challengeId}/universities/${universityId}/respond`, {
      action,
      response_note: responseNote,
    });
    return res?.data || res;
  },

  /**
   * Finalizes selection: selects highest-ranked accepted university after deadline window.
   */
  async finalizeUniversitySelection(challengeId, forceDeadline = false) {
    const res = await apiClient.post(`/challenges/${challengeId}/universities/finalize-selection`, {
      force_deadline: forceDeadline,
    });
    return res?.data || res;
  },

  /**
   * Fetches deterministically scored industry partners for a challenge.
   */
  async fetchIndustryMatches(challengeId, limit = 5) {
    const res = await apiClient.get(`/challenges/${challengeId}/industries`, { limit });
    return res?.data || [];
  },

  /**
   * Records Industry SPOC response (accept/reject) to collaboration proposal.
   */
  async respondIndustryMatch(challengeId, industryId, action, responseNote = '') {
    const res = await apiClient.post(`/challenges/${challengeId}/industries/${industryId}/respond`, {
      action,
      response_note: responseNote,
    });
    return res?.data || res;
  },

  /**
   * Lists match invitations for a university admin.
   */
  async listUniversityInvitations(universityId, statusFilter = null) {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    const res = await apiClient.get(`/challenges/universities/${universityId}/invitations`, params);
    return res?.data || [];
  },

  /**
   * Lists match invitations for an industry SPOC.
   */
  async listIndustryInvitations(industryId, statusFilter = null) {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    const res = await apiClient.get(`/challenges/industries/${industryId}/invitations`, params);
    return res?.data || [];
  },

  /**
   * Lists eligible projects for an industry employee's company.
   */
  async listEligibleProjectsForEmployee() {
    const res = await apiClient.get('/projects/eligible-for-employee');
    return res?.data || [];
  },

  /**
   * Allows a verified industry employee to express interest in a project.
   */
  async expressEmployeeInterest(projectId, message = '') {
    const res = await apiClient.post(`/projects/${projectId}/employee-interest`, { message });
    return res?.data || res;
  },
};

export default matchingService;
