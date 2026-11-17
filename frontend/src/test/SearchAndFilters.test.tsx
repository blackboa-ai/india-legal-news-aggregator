import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchAndFilters } from '../components/SearchAndFilters';
import { FilterState } from '../types';

describe('SearchAndFilters Component', () => {
  const defaultFilters: FilterState = {
    q: '',
    mode: 'hybrid',
    category: '',
    court: '',
    date_from: '',
    date_to: '',
    page: 1,
    limit: 25,
  };

  const mockCourts = [
    { code: 'sc', name: 'Supreme Court of India', level: 1 },
    { code: 'delhi-hc', name: 'High Court of Delhi', level: 2 },
  ];

  const mockCategories = [
    { id: 'criminal', name: 'Criminal', description: 'Criminal laws' },
    { id: 'constitutional', name: 'Constitutional', description: 'Constitutional laws' },
  ];

  it('renders prominent search input and category pills', () => {
    render(
      <SearchAndFilters
        filters={defaultFilters}
        onFilterChange={vi.fn()}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    expect(
      screen.getByPlaceholderText(/Search judgments, sections/i)
    ).toBeInTheDocument();
    expect(screen.getByText('Smart Search')).toBeInTheDocument();
    expect(screen.getByText('Exact Words')).toBeInTheDocument();
    expect(screen.getByText('By Meaning')).toBeInTheDocument();
    expect(screen.getByText('Criminal')).toBeInTheDocument();
    expect(screen.getByText('Constitutional')).toBeInTheDocument();
  });

  it('triggers onFilterChange when search mode is switched', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={defaultFilters}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    fireEvent.click(screen.getByText('Exact Words'));
    expect(handleFilterChange).toHaveBeenCalledWith({ mode: 'keyword', page: 1 });

    fireEvent.click(screen.getByText('By Meaning'));
    expect(handleFilterChange).toHaveBeenCalledWith({ mode: 'semantic', page: 1 });
  });

  it('triggers onFilterChange when category pill is clicked', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={defaultFilters}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    fireEvent.click(screen.getByText('Criminal'));
    expect(handleFilterChange).toHaveBeenCalledWith({ category: 'Criminal', page: 1 });
  });

  it('triggers onSearchSubmit on form submit', () => {
    const handleSearchSubmit = vi.fn();
    render(
      <SearchAndFilters
        filters={{ ...defaultFilters, q: 'Article 21' }}
        onFilterChange={vi.fn()}
        onSearchSubmit={handleSearchSubmit}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    const submitBtn = screen.getByTestId('search-submit-btn');
    fireEvent.click(submitBtn);
    expect(handleSearchSubmit).toHaveBeenCalled();
  });

  it('toggles mobile collapsible filters when clicked', () => {
    render(
      <SearchAndFilters
        filters={defaultFilters}
        onFilterChange={vi.fn()}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    const toggleBtn = screen.getByText(/Filters \(Court & Date\)/i);
    expect(toggleBtn).toBeInTheDocument();
    fireEvent.click(toggleBtn);
  });

  it('renders 3 content type navigation pills (All Updates, Judgments & Orders, Legal News)', () => {
    render(
      <SearchAndFilters
        filters={defaultFilters}
        onFilterChange={vi.fn()}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    expect(screen.getByTestId('filter-pill-all')).toHaveTextContent('All Updates');
    expect(screen.getByTestId('filter-pill-judgment')).toHaveTextContent('⚖️ Judgments & Orders');
    expect(screen.getByTestId('filter-pill-news')).toHaveTextContent('📰 Legal News');
  });

  it('calls onFilterChange with judgment content type when Judgments & Orders pill is clicked', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={defaultFilters}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    fireEvent.click(screen.getByTestId('filter-pill-judgment'));
    expect(handleFilterChange).toHaveBeenCalledWith({ content_type: 'judgment', page: 1 });
  });

  it('calls onFilterChange with news content type when Legal News pill is clicked', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={defaultFilters}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    fireEvent.click(screen.getByTestId('filter-pill-news'));
    expect(handleFilterChange).toHaveBeenCalledWith({ content_type: 'news', page: 1 });
  });

  it('calls onFilterChange with undefined content type when All Updates pill is clicked', () => {
    const handleFilterChange = vi.fn();
    render(
      <SearchAndFilters
        filters={{ ...defaultFilters, content_type: 'judgment' }}
        onFilterChange={handleFilterChange}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    fireEvent.click(screen.getByTestId('filter-pill-all'));
    expect(handleFilterChange).toHaveBeenCalledWith({ content_type: undefined, page: 1 });
  });

  it('applies active styling to the currently selected content type pill', () => {
    const { rerender } = render(
      <SearchAndFilters
        filters={{ ...defaultFilters, content_type: undefined }}
        onFilterChange={vi.fn()}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    expect(screen.getByTestId('filter-pill-all').className).toContain('bg-slate-900');
    expect(screen.getByTestId('filter-pill-judgment').className).toContain('bg-slate-100');

    rerender(
      <SearchAndFilters
        filters={{ ...defaultFilters, content_type: 'judgment' }}
        onFilterChange={vi.fn()}
        onSearchSubmit={vi.fn()}
        onResetFilters={vi.fn()}
        categories={mockCategories}
        courts={mockCourts}
      />
    );

    expect(screen.getByTestId('filter-pill-judgment').className).toContain('bg-slate-900');
    expect(screen.getByTestId('filter-pill-all').className).toContain('bg-slate-100');
  });
});
