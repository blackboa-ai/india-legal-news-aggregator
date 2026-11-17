import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  handleUrlTokenHandoff,
  getStoredToken,
  setStoredTokens,
  clearStoredTokens,
  api,
  fetchJudgments,
  searchJudgments,
  API_BASE_URL,
} from '../api/client';

describe('API Client & Token Management', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('stores and retrieves JWT tokens properly', () => {
    expect(getStoredToken()).toBeNull();
    setStoredTokens('test-access-token', 'test-refresh-token');
    expect(getStoredToken()).toBe('test-access-token');
    expect(localStorage.getItem('india_legal_refresh_token')).toBe('test-refresh-token');

    clearStoredTokens();
    expect(getStoredToken()).toBeNull();
    expect(localStorage.getItem('india_legal_refresh_token')).toBeNull();
  });

  it('handles ?token= URL parameter handoff and strips it from address bar', () => {
    window.history.pushState({}, '', '/?token=sso-jwt-token-123&foo=bar');
    const replaceStateSpy = vi.spyOn(window.history, 'replaceState');

    const extracted = handleUrlTokenHandoff();
    expect(extracted).toBe('sso-jwt-token-123');
    expect(localStorage.getItem('india_legal_jwt_token')).toBe('sso-jwt-token-123');
    expect(replaceStateSpy).toHaveBeenCalled();
  });

  it('returns null when no token query param is in URL', () => {
    window.history.pushState({}, '', '/?view=feed');

    const extracted = handleUrlTokenHandoff();
    expect(extracted).toBeNull();
  });

  it('calls fetch with proper URL and parameters for judgments list', async () => {
    const mockResponse = { data: [], total: 0, limit: 10, offset: 0 };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    } as Response);

    const res = await api.judgments.list({ category: 'Criminal', court: 'sc', limit: 10 });
    expect(res).toEqual(mockResponse);
    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_BASE_URL}/judgments?category=Criminal&court=sc&limit=10`,
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    );
  });

  it('calls fetch with proper hybrid search query and mode', async () => {
    const mockResponse = { results: [], query_type: 'hybrid', matched_terms: ['Section 438'], total: 0 };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    } as Response);

    const res = await api.judgments.search({
      q: 'anticipatory bail',
      mode: 'hybrid',
      limit: 10,
    });
    expect(res).toEqual(mockResponse);
    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_BASE_URL}/search?q=anticipatory+bail&mode=hybrid&limit=10`,
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    );
  });

  it('manages in-memory prefetch cache for judgments detail', async () => {
    const mockJudgment = {
      id: 'pre-123',
      title: 'Prefetched Judgment',
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockJudgment,
    } as Response);

    const detail = await api.judgments.getById('pre-123');
    expect(detail).toEqual(mockJudgment);
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    // Second call should return directly from in-memory cache without fetch
    const cachedDetail = await api.judgments.getById('pre-123');
    expect(cachedDetail).toEqual(mockJudgment);
    expect(fetchSpy).toHaveBeenCalledTimes(1); // No additional fetch
  });

  it('forwards AbortSignal to fetch request for query cancellation', async () => {
    const controller = new AbortController();
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: [], total: 0, limit: 10, offset: 0 }),
    } as Response);

    await api.judgments.list({ limit: 10 }, controller.signal);
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        signal: controller.signal,
      })
    );
  });

  it('fetchJudgments appends content_type=judgment to search params when defined', async () => {
    const mockResponse = { data: [], total: 0, limit: 10, offset: 0 };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    } as Response);

    await fetchJudgments({ content_type: 'judgment', limit: 10 });
    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_BASE_URL}/judgments?content_type=judgment&limit=10`,
      expect.anything()
    );
  });

  it('searchJudgments appends content_type=news to search params when defined', async () => {
    const mockResponse = { results: [], query_type: 'hybrid', matched_terms: [], total: 0 };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    } as Response);

    await searchJudgments({ q: 'collegium', content_type: 'news' });
    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_BASE_URL}/search?q=collegium&content_type=news`,
      expect.anything()
    );
  });

  it('omits content_type from URL search params when set to all or undefined', async () => {
    const mockResponse = { data: [], total: 0, limit: 10, offset: 0 };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    } as Response);

    await fetchJudgments({ content_type: 'all' });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      `${API_BASE_URL}/judgments`,
      expect.anything()
    );

    await fetchJudgments({ content_type: undefined });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      `${API_BASE_URL}/judgments`,
      expect.anything()
    );
  });
});
