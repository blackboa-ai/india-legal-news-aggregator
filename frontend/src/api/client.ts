/**
 * Typed API Client for India Legal News Aggregator
 * Supports Standalone Mode & Integrated Mode (?token=xxx URL handoff)
 */

import {
  Alert,
  AlertMatchesResponse,
  Bookmark,
  BookmarkListResponse,
  CourtItem,
  Judgment,
  JudgmentListResponse,
  LegalCategoryItem,
  SearchResponse,
  TokenResponse,
  Topic,
  User,
} from '../types';

const TOKEN_KEY = 'india_legal_jwt_token';
const REFRESH_TOKEN_KEY = 'india_legal_refresh_token';

// Safe localStorage accessor
function getStorage(): Storage | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage;
    }
    if (typeof localStorage !== 'undefined') {
      return localStorage;
    }
  } catch {
    // Access denied in restricted iframes
  }
  return null;
}

// Normalizes API base URL, ensuring /api/v1 suffix and valid local dev host/port
function normalizeApiBaseUrl(raw?: string): string {
  let url = (raw || '').trim().replace(/\/+$/, '');
  if (!url || url === 'http://127.0.0' || url === 'http://127.0.0.1') {
    url = 'http://127.0.0.1:8000';
  } else if (url.startsWith('http://127.0.0') && !url.includes(':')) {
    url = 'http://127.0.0.1:8000';
  }
  if (!url.endsWith('/api/v1')) {
    url = `${url}/api/v1`;
  }
  return url;
}

// Base API URL with environment fallback
export const API_BASE_URL: string = normalizeApiBaseUrl(
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
  (import.meta.env.VITE_API_URL as string | undefined) ||
  (import.meta.env.VITE_BACKEND_URL as string | undefined)
);

/**
 * Extract ?token= or ?access_token= from URL search params (Integrated Mode SSO handoff).
 * Securely stores token in localStorage and strips it from browser address bar.
 */
export function handleUrlTokenHandoff(): string | null {
  if (typeof window === 'undefined') return null;

  try {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token') || params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (token) {
      const storage = getStorage();
      if (storage) {
        storage.setItem(TOKEN_KEY, token);
        if (refreshToken) {
          storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        }
      }

      // Strip sensitive tokens from the URL history
      params.delete('token');
      params.delete('access_token');
      params.delete('refresh_token');
      const newQuery = params.toString();
      const newUrl =
        window.location.pathname + (newQuery ? `?${newQuery}` : '') + window.location.hash;
      window.history.replaceState({}, document.title, newUrl);

      return token;
    }
  } catch (err) {
    console.error('Error handling URL token handoff:', err);
  }

  return null;
}

export function getStoredToken(): string | null {
  const storage = getStorage();
  return storage ? storage.getItem(TOKEN_KEY) : null;
}

export function getStoredRefreshToken(): string | null {
  const storage = getStorage();
  return storage ? storage.getItem(REFRESH_TOKEN_KEY) : null;
}

export function setStoredTokens(accessToken: string, refreshToken?: string | null): void {
  const storage = getStorage();
  if (!storage) return;
  storage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) {
    storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  } else {
    storage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function clearStoredTokens(): void {
  const storage = getStorage();
  if (!storage) return;
  storage.removeItem(TOKEN_KEY);
  storage.removeItem(REFRESH_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Core typed fetch wrapper
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  isRetry = false
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  const headers = new Headers(options.headers);

  // Set JSON headers unless body is FormData
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach JWT Bearer token if present
  const token = getStoredToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized token refresh logic
  if (response.status === 401 && !isRetry) {
    const refreshToken = getStoredRefreshToken();
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const tokenData: TokenResponse = await refreshRes.json();
          setStoredTokens(tokenData.access_token, tokenData.refresh_token);
          // Retry original request with new token
          headers.set('Authorization', `Bearer ${tokenData.access_token}`);
          return request<T>(endpoint, { ...options, headers }, true);
        }
      } catch (err) {
        console.warn('Silent token refresh failed:', err);
      }
    }
    // Refresh failed or no refresh token - clear tokens
    clearStoredTokens();
  }

  if (!response.ok) {
    let errorDetail =
      response.status >= 500
        ? 'Unable to load updates right now. Please try again.'
        : `Request could not be completed (${response.status}).`;
    let errorData: unknown = null;
    try {
      errorData = await response.json();
      if (typeof errorData === 'object' && errorData !== null) {
        const errObj = errorData as Record<string, unknown>;
        if (typeof errObj.detail === 'string') {
          errorDetail = errObj.detail;
        } else if (Array.isArray(errObj.detail)) {
          errorDetail = (errObj.detail as Array<{ msg?: string }>).map((d) => d.msg || '').join(', ');
        }
      }
    } catch {
      // response is not JSON
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

// -----------------------------------------------------------------------------
// API Service Methods
// -----------------------------------------------------------------------------

// Fast in-memory cache for full judgment details (populated by prefetching or view)
export const judgmentDetailCache = new Map<string, Judgment>();

export function getPrefetchedJudgment(id: string): Judgment | undefined {
  return judgmentDetailCache.get(id);
}

export async function prefetchJudgment(id: string): Promise<Judgment | null> {
  if (judgmentDetailCache.has(id)) {
    return judgmentDetailCache.get(id)!;
  }
  try {
    const detail = await api.judgments.getById(id);
    return detail;
  } catch {
    return null;
  }
}

export const api = {
  // Judgments & Search
  judgments: {
    list: (
      params: {
        category?: string;
        court?: string;
        date_from?: string;
        date_to?: string;
        limit?: number;
        offset?: number;
      } = {},
      signal?: AbortSignal
    ): Promise<JudgmentListResponse> => {
      const searchParams = new URLSearchParams();
      if (params.category) searchParams.set('category', params.category);
      if (params.court) searchParams.set('court', params.court);
      if (params.date_from) searchParams.set('date_from', params.date_from);
      if (params.date_to) searchParams.set('date_to', params.date_to);
      if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params.offset !== undefined) searchParams.set('offset', String(params.offset));

      const query = searchParams.toString();
      return request<JudgmentListResponse>(`/judgments${query ? `?${query}` : ''}`, { signal });
    },

    search: (
      params: {
        q: string;
        mode?: 'hybrid' | 'keyword' | 'semantic';
        category?: string;
        court?: string;
        limit?: number;
        offset?: number;
      },
      signal?: AbortSignal
    ): Promise<SearchResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.set('q', params.q);
      if (params.mode) searchParams.set('mode', params.mode);
      if (params.category) searchParams.set('category', params.category);
      if (params.court) searchParams.set('court', params.court);
      if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params.offset !== undefined) searchParams.set('offset', String(params.offset));

      return request<SearchResponse>(`/search?${searchParams.toString()}`, { signal });
    },

    getById: async (id: string, signal?: AbortSignal): Promise<Judgment> => {
      if (judgmentDetailCache.has(id)) {
        return judgmentDetailCache.get(id)!;
      }
      const item = await request<Judgment>(`/judgments/${id}`, { signal });
      if (item && item.id) {
        judgmentDetailCache.set(item.id, item);
      }
      return item;
    },

    getSimilar: (id: string, limit = 5): Promise<Judgment[]> => {
      return request<Judgment[]>(`/similar/${id}?limit=${limit}`);
    },

    categories: async (): Promise<LegalCategoryItem[]> => {
      try {
        return await request<LegalCategoryItem[]>('/categories');
      } catch (err) {
        if (err instanceof ApiError && err.status === 404 && API_BASE_URL.includes('/api/v1')) {
          const rootUrl = API_BASE_URL.replace(/\/api\/v1$/, '');
          const res = await fetch(`${rootUrl}/categories`);
          if (res.ok) return res.json();
        }
        throw err;
      }
    },

    courts: async (): Promise<CourtItem[]> => {
      try {
        return await request<CourtItem[]>('/courts');
      } catch (err) {
        if (err instanceof ApiError && err.status === 404 && API_BASE_URL.includes('/api/v1')) {
          const rootUrl = API_BASE_URL.replace(/\/api\/v1$/, '');
          const res = await fetch(`${rootUrl}/courts`);
          if (res.ok) return res.json();
        }
        throw err;
      }
    },
  },

  // Authentication
  auth: {
    register: (payload: { email: string; password: string; full_name?: string }): Promise<TokenResponse> => {
      return request<TokenResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    login: (payload: { email: string; password: string }): Promise<TokenResponse> => {
      return request<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    google: (id_token: string): Promise<TokenResponse> => {
      return request<TokenResponse>('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ id_token }),
      });
    },

    me: (): Promise<User> => {
      return request<User>('/auth/me');
    },

    refresh: (refresh_token: string): Promise<TokenResponse> => {
      return request<TokenResponse>('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token }),
      });
    },
  },

  // Bookmarks
  bookmarks: {
    list: (params: { limit?: number; offset?: number } = {}): Promise<BookmarkListResponse> => {
      const searchParams = new URLSearchParams();
      if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params.offset !== undefined) searchParams.set('offset', String(params.offset));
      const q = searchParams.toString();
      return request<BookmarkListResponse>(`/bookmarks${q ? `?${q}` : ''}`);
    },

    add: (
      judgment_id: string,
      payload?: { notes?: string; tags?: string[] }
    ): Promise<Bookmark> => {
      return request<Bookmark>(`/bookmarks/${judgment_id}`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      });
    },

    remove: (judgment_id: string): Promise<{ status: string; judgment_id: string }> => {
      return request<{ status: string; judgment_id: string }>(`/bookmarks/${judgment_id}`, {
        method: 'DELETE',
      });
    },
  },

  // Alerts
  alerts: {
    list: (): Promise<{ data: Alert[]; total: number }> => {
      return request<{ data: Alert[]; total: number }>('/alerts');
    },

    create: (payload: {
      title: string;
      category?: string;
      court_code?: string;
      keywords: string[];
      query?: string;
      is_active?: boolean;
    }): Promise<Alert> => {
      return request<Alert>('/alerts', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    delete: (alert_id: string): Promise<{ status: string; alert_id: string }> => {
      return request<{ status: string; alert_id: string }>(`/alerts/${alert_id}`, {
        method: 'DELETE',
      });
    },

    matches: (params: { alert_id?: string; limit?: number } = {}): Promise<AlertMatchesResponse> => {
      const searchParams = new URLSearchParams();
      if (params.alert_id) searchParams.set('alert_id', params.alert_id);
      if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
      const q = searchParams.toString();
      return request<AlertMatchesResponse>(`/alerts/matches${q ? `?${q}` : ''}`);
    },
  },

  // Topics / Folders
  topics: {
    list: (): Promise<{ data: Topic[]; total: number }> => {
      return request<{ data: Topic[]; total: number }>('/topics');
    },

    create: (payload: { name: string; description?: string }): Promise<Topic> => {
      return request<Topic>('/topics', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    addJudgment: (
      topic_id: string,
      judgment_id: string
    ): Promise<{ status: string; topic_id: string; judgment_id: string }> => {
      return request<{ status: string; topic_id: string; judgment_id: string }>(
        `/topics/${topic_id}/judgments`,
        {
          method: 'POST',
          body: JSON.stringify({ judgment_id }),
        }
      );
    },

    delete: (topic_id: string): Promise<{ status: string; topic_id: string }> => {
      return request<{ status: string; topic_id: string }>(`/topics/${topic_id}`, {
        method: 'DELETE',
      });
    },
  },

  // Health probe
  health: (): Promise<{ status: string; service: string }> => {
    return request<{ status: string; service: string }>('/health');
  },
};
