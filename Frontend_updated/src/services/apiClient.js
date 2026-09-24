import { supabase } from './supabaseClient';

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const strippedBaseUrl = rawBaseUrl.replace(/\/+$/, '');
const API_BASE_URL = strippedBaseUrl.endsWith('/api') ? strippedBaseUrl : `${strippedBaseUrl}/api`;

/**
 * Universal API Client for VidySetu / Concordia.
 * Centralizes authentication headers, base URLs, and response/error parsing.
 */
async function request(endpoint, options = {}) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE_URL}${cleanEndpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  // Dynamically attach active Supabase access token if not explicitly provided
  if (!headers['Authorization']) {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
    } catch {
      // ignore
    }
  }

  const config = {
    ...options,
    headers,
  };

  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
  }

  const res = await fetch(url, config);

  let data = null;
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    let msg = 'Request failed';
    if (data) {
      if (typeof data.detail === 'string') msg = data.detail;
      else if (data.error && typeof data.error.message === 'string') msg = data.error.message;
      else if (typeof data.message === 'string') msg = data.message;
    } else {
      msg = `${res.status} ${res.statusText}`;
    }
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

export const apiClient = {
  get: (endpoint, params = {}, options = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.append(k, String(v));
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return request(`${endpoint}${suffix}`, { method: 'GET', ...options });
  },

  post: (endpoint, body) => request(endpoint, { method: 'POST', body }),

  patch: (endpoint, body) => request(endpoint, { method: 'PATCH', body }),

  delete: (endpoint) => request(endpoint, { method: 'DELETE' }),

  setToken: () => {},

  getToken: async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      return session?.access_token || null;
    } catch {
      return null;
    }
  },

  downloadBlob: async (endpoint, defaultFilename = 'document.pdf') => {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${cleanEndpoint}`;
    const { data: { session } } = await supabase.auth.getSession();
    const headers = {};
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }
    const res = await fetch(url, { headers });
    if (!res.ok) {
      let msg = 'Failed to download file';
      try {
        const errJson = await res.json();
        if (errJson.detail) msg = errJson.detail;
      } catch {
        // ignore
      }
      throw new Error(msg);
    }
    const blob = await res.blob();
    let saveName = defaultFilename;
    const cd = res.headers.get('content-disposition');
    if (cd && cd.includes('filename=')) {
      const match = cd.match(/filename=["']?([^"';]+)["']?/);
      if (match && match[1]) saveName = match[1].trim();
    }
    const objectUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = saveName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(objectUrl);
    document.body.removeChild(a);
    return saveName;
  },
};

export default apiClient;
