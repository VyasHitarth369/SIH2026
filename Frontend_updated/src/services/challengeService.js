import apiClient from './apiClient';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * Submit a new challenge to the FastAPI backend and Supabase.
 * Database field is strictly impact_scope, NOT impact_score.
 */
export async function submitChallenge(challengeData) {
  const payload = {
    title: challengeData.title || '',
    description: challengeData.description || challengeData.desc || '',
    location: challengeData.location || challengeData.loc || '',
    city: challengeData.city || '',
    district: challengeData.district || challengeData.city || '',
    address: challengeData.address || '',
    pincode: challengeData.pincode || '',
    impact_scope: challengeData.impact_scope || challengeData.scope || 'Area Specific',
    photo: challengeData.photo || null,
    video: challengeData.video || null,
    document: challengeData.document || null,
    expected_solution: challengeData.expected_solution || null,
    submitted_by: challengeData.submitted_by || 'Citizen',
    status: challengeData.status || 'unsolved',
    user_id: challengeData.user_id || null,
  };

  const res = await apiClient.post('/challenges', payload);
  return res?.data || res;
}

/**
 * Fetch challenges from the backend API.
 */
export async function fetchChallenges({ status, city, limit } = {}) {
  const params = {};
  if (status) params.status = status;
  if (city) params.city = city;
  if (limit) params.limit = limit;

  const res = await apiClient.get('/challenges', params);
  return res?.data || [];
}

/**
 * Fetch challenges submitted strictly by the currently authenticated citizen.
 */
export async function fetchMyChallenges() {
  const res = await apiClient.get('/challenges/mine');
  return res?.data || [];
}

/**
 * Vote / support a challenge (1 vote per user).
 */
export async function voteChallenge(challengeId) {
  const res = await apiClient.post(`/challenges/${challengeId}/vote`);
  return res?.data || res;
}

/**
 * Fetch read-only project milestones for a challenge.
 */
export async function fetchChallengeMilestones(challengeId) {
  const res = await apiClient.get(`/challenges/${challengeId}/milestones`);
  return res?.data || [];
}

/**
 * Fetch a single challenge by its challenge_id.
 */
export async function fetchChallengeById(challengeId) {
  const res = await apiClient.get(`/challenges/${challengeId}`);
  return res?.data || res;
}

