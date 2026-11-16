import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { JudgmentCard } from '../components/JudgmentCard';
import { Judgment } from '../types';

describe('JudgmentCard Component', () => {
  const mockJudgment: Judgment = {
    id: 'f87a87e2-411a-4ab0-bbfb-3719bca40001',
    external_id: 'hash123',
    title: 'Gurbaksh Singh Sibbia v. State of Punjab',
    short_title: 'Gurbaksh Singh Sibbia',
    court_code: 'sc',
    court_name: 'Supreme Court of India',
    court_level: 1,
    judgment_date: '2024-04-15',
    subject_category: 'Criminal',
    excerpt: 'Constitution bench ruling on the scope and ambit of Section 438 of the Code of Criminal Procedure.',
    full_text: 'Full judgment text for anticipatory bail principles...',
    url: 'https://indiankanoon.org/doc/12345/',
    parties: [{ role: 'appellant', name: 'Gurbaksh Singh Sibbia' }],
    tags: ['Section 438 CrPC', 'Article 21', 'Anticipatory Bail'],
    source: 'indiankanoon',
    is_archived: true,
    classification_confidence: 0.98,
    created_at: '2024-04-15T10:00:00Z',
    updated_at: '2024-04-15T10:00:00Z',
  };

  it('renders court badge, title, compact preview summary and statute tags', () => {
    render(
      <JudgmentCard
        judgment={mockJudgment}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={vi.fn()}
      />
    );

    expect(screen.getByText('Supreme Court of India')).toBeInTheDocument();
    expect(screen.getByText('Criminal')).toBeInTheDocument();
    expect(screen.getByText('Gurbaksh Singh Sibbia v. State of Punjab')).toBeInTheDocument();
    const summaryEl = screen.getByText(/Constitution bench ruling on the scope and ambit/i);
    expect(summaryEl).toBeInTheDocument();
    expect(summaryEl).toHaveClass('line-clamp-3');
    expect(screen.getByText('Section 438 CrPC')).toBeInTheDocument();
    expect(screen.getByText('Article 21')).toBeInTheDocument();
  });

  it('calls onSelectJudgment when the entire card is clicked or tapped', () => {
    const handleSelect = vi.fn();
    render(
      <JudgmentCard
        judgment={mockJudgment}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={handleSelect}
      />
    );

    const titleEl = screen.getByText('Gurbaksh Singh Sibbia v. State of Punjab');
    fireEvent.click(titleEl);
    expect(handleSelect).toHaveBeenCalledWith(mockJudgment);
  });

  it('calls onToggleBookmark and stops propagation when bookmark button is clicked', () => {
    const handleBookmark = vi.fn();
    const handleSelect = vi.fn();
    render(
      <JudgmentCard
        judgment={mockJudgment}
        isBookmarked={false}
        onToggleBookmark={handleBookmark}
        onSelectJudgment={handleSelect}
      />
    );

    const bookmarkBtn = screen.getByTitle('Save to Bookmarks');
    fireEvent.click(bookmarkBtn);
    expect(handleBookmark).toHaveBeenCalledWith(mockJudgment);
    // Card selection should not be triggered
    expect(handleSelect).not.toHaveBeenCalled();
  });

  it('calls onSelectJudgment when Read Full button is clicked', () => {
    const handleSelect = vi.fn();
    render(
      <JudgmentCard
        judgment={mockJudgment}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={handleSelect}
      />
    );

    const readBtn = screen.getByText('Read Full');
    fireEvent.click(readBtn);
    expect(handleSelect).toHaveBeenCalledWith(mockJudgment);
  });

  it('renders Best Match badge instead of raw float scores when judgment has a search rank score', () => {
    const searchRankedJudgment = {
      ...mockJudgment,
      score: 0.03251,
      keyword_rank: 1,
      semantic_rank: 2,
    };

    render(
      <JudgmentCard
        judgment={searchRankedJudgment}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={vi.fn()}
      />
    );

    expect(screen.getByText('Best Match')).toBeInTheDocument();
    expect(screen.queryByText(/0\.032/)).not.toBeInTheDocument();
  });

  it('triggers judgment prefetch on mouse enter or touch start for instant reader view', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockJudgment,
    } as Response);

    render(
      <JudgmentCard
        judgment={mockJudgment}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectJudgment={vi.fn()}
      />
    );

    const titleEl = screen.getByText('Gurbaksh Singh Sibbia v. State of Punjab');
    const card = titleEl.closest('[role="button"]')!;
    fireEvent.mouseEnter(card);
    expect(fetchSpy).toHaveBeenCalled();
  });
});
