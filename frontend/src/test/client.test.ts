import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  handleUrlTokenHandoff,
  getStoredToken,
  setStoredTokens,
  clearStoredTokens,
  api,
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
});
