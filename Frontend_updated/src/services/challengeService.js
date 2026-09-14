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
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (city) params.append('city', city);
  if (limit) params.append('limit', String(limit));

  const qs = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${API_BASE_URL}/challenges${qs}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch challenges: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data || [];
}

/**
 * Fetch a single challenge by its challenge_id.
 */
export async function fetchChallengeById(challengeId) {
  const response = await fetch(`${API_BASE_URL}/challenges/${challengeId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch challenge: ${response.statusText}`);
  }
  const result = await response.json();
  return result.data;
}
