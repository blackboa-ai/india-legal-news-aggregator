import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchAndFilters } from '../components/SearchAndFilters';
import { JudgmentCard, getContentTypeBadge } from '../components/JudgmentCard';
import { FilterState, Judgment, SearchResultItem } from '../types';
import { api, fetchJudgments, searchJudgments } from '../api/client';

describe('Phase 4: Content Type Filter Tabs & Card Badges', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockCategories = [
    { id: 'criminal', name: 'Criminal', description: 'Criminal law' },
    { id: 'constitutional', name: 'Constitutional', description: 'Constitutional law' },
  ];

  const mockCourts = [
    { code: 'sc', name: 'Supreme Court of India', level: 1 },
  ];

  const initialFilters: FilterState = {
    q: '',
    mode: 'hybrid',
    category: '',
    court: '',
    content_type: undefined,
    date_from: '',
    date_to: '',
    page: 2, // starting on page 2 to verify reset to page 1
    limit: 25,
  };

  it('clicking "Judgments & Orders" pill updates filter and resets to page 1', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={initialFilters}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    const judgmentPill = screen.getByTestId('filter-pill-judgment');
    expect(judgmentPill).toHaveTextContent('Judgments & Orders');
    fireEvent.click(judgmentPill);

    expect(handleFilterChange).toHaveBeenCalledTimes(1);
    expect(handleFilterChange).toHaveBeenCalledWith({
      content_type: 'judgment',
      page: 1,
    });
  });

  it('clicking "Legal News" pill updates filter to news and resets to page 1', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={initialFilters}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    const newsPill = screen.getByTestId('filter-pill-news');
    expect(newsPill).toHaveTextContent('Legal News');
    fireEvent.click(newsPill);

    expect(handleFilterChange).toHaveBeenCalledTimes(1);
    expect(handleFilterChange).toHaveBeenCalledWith({
      content_type: 'news',
      page: 1,
    });
  });

  it('clicking "All Updates" pill clears content_type and resets to page 1', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={{ ...initialFilters, content_type: 'judgment' }}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    const allPill = screen.getByTestId('filter-pill-all');
    expect(allPill).toHaveTextContent('All Updates');
    fireEvent.click(allPill);

    expect(handleFilterChange).toHaveBeenCalledTimes(1);
    expect(handleFilterChange).toHaveBeenCalledWith({
      content_type: undefined,
      page: 1,
    });
  });

  it('passes content_type=judgment to the API call when fetching judgments feed', async () => {
    const listSpy = vi.spyOn(api.judgments, 'list').mockResolvedValueOnce({
      items: [],
      total: 0,
      limit: 25,
      offset: 0,
    });

    await fetchJudgments({
      category: 'Criminal',
      content_type: 'judgment',
      limit: 25,
      offset: 0,
    });

    expect(listSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'Criminal',
        content_type: 'judgment',
        limit: 25,
        offset: 0,
      }),
      undefined
    );
  });

  it('passes content_type=news to the API call when searching judgments', async () => {
    const searchSpy = vi.spyOn(api.judgments, 'search').mockResolvedValueOnce({
      results: [],
      query_type: 'hybrid',
      matched_terms: ['collegium'],
      total: 0,
    });

    await searchJudgments({
      q: 'collegium',
      content_type: 'news',
      limit: 25,
      offset: 0,
    });

    expect(searchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        q: 'collegium',
        content_type: 'news',
        limit: 25,
        offset: 0,
      }),
      undefined
    );
  });

  it('renders distinct color-coded badges on JudgmentCard for judgment vs news', () => {
    const baseItem: Judgment = {
      id: 'item-1',
      external_id: 'ext-1',
      title: 'State v. Accused [Read Order]',
      short_title: 'State v. Accused',
      court_code: 'sc',
      court_name: 'Supreme Court of India',
      court_level: 1,
      judgment_date: '2024-06-01',
      subject_category: 'Criminal',
      excerpt: 'Bail order issued.',
      full_text: null,
      url: 'https://example.com/1',
      parties: [],
      tags: ['bail'],
      source: 'sci',
      is_archived: true,
      classification_confidence: 0.95,
      content_type: 'judgment',
      content_type_confidence: 0.99,
      created_at: '2024-06-01T00:00:00Z',
      updated_at: '2024-06-01T00:00:00Z',
    };

    // 1. Render judgment item -> verify emerald badge
    const { rerender } = render(
      <JudgmentCard
        judgment={baseItem}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={vi.fn()}
      />
    );

    const judgmentBadge = screen.getByTestId('content-type-badge');
    expect(judgmentBadge).toHaveTextContent('COURT ORDER');
    expect(judgmentBadge.className).toContain('bg-emerald-50');
    expect(judgmentBadge.className).toContain('text-emerald-700');
    expect(judgmentBadge.className).toContain('border-emerald-200');

    // 2. Render news item -> verify sky blue badge
    const newsItem: SearchResultItem = {
      ...baseItem,
      id: 'item-2',
      title: 'Bar Council conducts elections across states',
      content_type: 'news',
      content_type_confidence: 0.88,
      score: 0.045,
      keyword_rank: 1,
      semantic_rank: 1,
    };

    rerender(
      <JudgmentCard
        judgment={newsItem}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={vi.fn()}
      />
    );

    const newsBadge = screen.getByTestId('content-type-badge');
    expect(newsBadge).toHaveTextContent('LEGAL NEWS');
    expect(newsBadge.className).toContain('bg-sky-50');
    expect(newsBadge.className).toContain('text-sky-700');
    expect(newsBadge.className).toContain('border-sky-200');

    // 3. Render unknown item -> verify no content-type badge
    const unknownItem: Judgment = {
      ...baseItem,
      id: 'item-3',
      content_type: 'unknown',
    };

    rerender(
      <JudgmentCard
        judgment={unknownItem}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={vi.fn()}
      />
    );

    expect(screen.queryByTestId('content-type-badge')).not.toBeInTheDocument();
  });

  it('getContentTypeBadge utility returns expected labels and classes', () => {
    const judgmentBadge = getContentTypeBadge('judgment');
    expect(judgmentBadge?.label).toBe('COURT ORDER');
    expect(judgmentBadge?.badgeClass).toContain('bg-emerald-50 text-emerald-700');

    const newsBadge = getContentTypeBadge('news');
    expect(newsBadge?.label).toBe('LEGAL NEWS');
    expect(newsBadge?.badgeClass).toContain('bg-sky-50 text-sky-700');

    const unknownBadge = getContentTypeBadge('unknown');
    expect(unknownBadge).toBeNull();

    const fallbackBadge = getContentTypeBadge(undefined);
    expect(fallbackBadge).toBeNull();
  });
});
