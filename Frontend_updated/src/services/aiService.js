import apiClient from './apiClient';

/**
 * AI Review, Solution Discovery, and Gap Validation Service.
 * Adheres strictly to the maximum-2 LLM call budget.
 */
export const aiService = {
  /**
   * Triggers AI Call 1: Evaluates problem validity and discovers verified existing schemes.
   * @param {string} challengeId
   * @returns {Promise<object>} Analysis results including solution_found, existing_solution, validity.
   */
  async analyzeChallenge(challengeId) {
    const res = await apiClient.post(`/challenges/${challengeId}/analyze`, {});
    return res?.data || res;
  },

  /**
   * Triggers Citizen Decision & AI Call 2 (if rejected):
   * Validates citizen's localized gap against existing solution and classifies problem.
   * @param {string} challengeId
   * @param {'accept' | 'reject'} decision
   * @param {string} [localGapReason] Required if decision is 'reject'
   * @returns {Promise<object>}
   */
  async respondToExistingSolution(challengeId, decision, localGapReason = '', rejectionCategory = null) {
    const isAccepted = decision === 'accept' || decision === true;
    const payload = {
      accepted: isAccepted,
      decision: isAccepted ? 'accept' : 'reject',
      rejection_reason: !isAccepted ? localGapReason : null,
      local_gap_reason: !isAccepted ? localGapReason : null,
      rejection_category: rejectionCategory,
    };
    const res = await apiClient.post(`/challenges/${challengeId}/existing-solution-response`, payload);
    return res?.data || res;
  },
};

export default aiService;
