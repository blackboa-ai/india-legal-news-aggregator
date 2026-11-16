import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { JudgmentModal, normalizeReaderText } from '../components/JudgmentModal';
import { Judgment } from '../types';

describe('JudgmentModal Component', () => {
  const mockJudgment: Judgment = {
    id: 'f87a87e2-411a-4ab0-bbfb-3719bca40001',
    external_id: 'hash123',
    title: 'Maneka Gandhi v. Union of India',
    short_title: 'Maneka Gandhi',
    court_code: 'sc',
    court_name: 'Supreme Court of India',
    court_level: 1,
    judgment_date: '1978-01-25',
    subject_category: 'Constitutional',
    excerpt: 'Landmark decision expanding Article 21 to include procedure established by law that is just, fair and reasonable.',
    full_text: 'Complete landmark judgment on Article 21 and right to travel abroad...',
    url: 'https://indiankanoon.org/doc/1953529/',
    parties: [{ role: 'petitioner', name: 'Maneka Gandhi' }, { role: 'respondent', name: 'Union of India' }],
    tags: ['Article 21', 'Article 14', 'Article 19'],
    source: 'indiankanoon',
    is_archived: true,
    classification_confidence: 0.99,
    created_at: '2024-04-15T10:00:00Z',
    updated_at: '2024-04-15T10:00:00Z',
  };

  it('renders modal with full judgment title, parties, tags, excerpt and full judgment text when open', () => {
    render(
      <JudgmentModal
        judgment={mockJudgment}
        isOpen={true}
        onClose={vi.fn()}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectSimilarJudgment={vi.fn()}
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Maneka Gandhi v. Union of India')).toBeInTheDocument();
    expect(screen.getByText(/Landmark decision expanding Article 21/i)).toBeInTheDocument();
    expect(screen.getByText(/Complete landmark judgment on Article 21 and right to travel abroad/i)).toBeInTheDocument();
    expect(screen.getByText('Article 21')).toBeInTheDocument();
    expect(screen.getAllByText('Maneka Gandhi').length).toBeGreaterThanOrEqual(1);
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <JudgmentModal
        judgment={mockJudgment}
        isOpen={false}
        onClose={vi.fn()}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectSimilarJudgment={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    render(
      <JudgmentModal
        judgment={mockJudgment}
        isOpen={true}
        onClose={handleClose}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectSimilarJudgment={vi.fn()}
      />
    );

    const closeBtn = screen.getByLabelText('Close modal');
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalled();
  });

  it('calls onClose when Escape key is pressed', () => {
    const handleClose = vi.fn();
    render(
      <JudgmentModal
        judgment={mockJudgment}
        isOpen={true}
        onClose={handleClose}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectSimilarJudgment={vi.fn()}
      />
    );

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(handleClose).toHaveBeenCalled();
  });

  it('calls onClose when dimmed backdrop is clicked', () => {
    const handleClose = vi.fn();
    const { container } = render(
      <JudgmentModal
        judgment={mockJudgment}
        isOpen={true}
        onClose={handleClose}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectSimilarJudgment={vi.fn()}
      />
    );

    const backdrop = container.firstChild as HTMLElement;
    fireEvent.click(backdrop);
    expect(handleClose).toHaveBeenCalled();
  });

  it('switches to similar precedents tab when clicked', () => {
    render(
      <JudgmentModal
        judgment={mockJudgment}
        isOpen={true}
        onClose={vi.fn()}
        isBookmarked={false}
        onToggleBookmark={vi.fn()}
        onSelectSimilarJudgment={vi.fn()}
      />
    );

    const similarTab = screen.getByText(/Similar Precedents/i);
    fireEvent.click(similarTab);
    expect(screen.getByText('Related Legal Precedents')).toBeInTheDocument();
  });

  describe('normalizeReaderText helper', () => {
    it('normalizes single-word and wrapped line breaks into clean paragraphs', () => {
      const rawScraped = 'The\nSupreme\nCourt\nof\nIndia\nheld\nthat personal liberty is inviolable.\n\nSecond paragraph here.';
      const normalized = normalizeReaderText(rawScraped);
      expect(normalized).toBe('The Supreme Court of India held that personal liberty is inviolable.\n\nSecond paragraph here.');
    });

    it('handles empty input gracefully', () => {
      expect(normalizeReaderText('')).toBe('');
    });
  });
});
