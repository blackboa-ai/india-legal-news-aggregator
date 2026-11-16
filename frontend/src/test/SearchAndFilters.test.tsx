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
    limit: 12,
  };

  const mockCourts = [
    { code: 'sc', name: 'Supreme Court of India', level: 1 },
    { code: 'delhi-hc', name: 'High Court of Delhi', level: 2 },
  ];

  const mockCategories = [
    { id: 'criminal', name: 'Criminal', description: 'Criminal laws' },
    { id: 'constitutional', name: 'Constitutional', description: 'Constitutional laws' },
  ];

  it('renders search input and category pills', () => {
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
      screen.getByPlaceholderText(/Search judgments, statutory citations/i)
    ).toBeInTheDocument();
    expect(screen.getByText('Hybrid (RRF)')).toBeInTheDocument();
    expect(screen.getByText('Keyword (BM25)')).toBeInTheDocument();
    expect(screen.getByText('Semantic (Vector)')).toBeInTheDocument();
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

    fireEvent.click(screen.getByText('Keyword (BM25)'));
    expect(handleFilterChange).toHaveBeenCalledWith({ mode: 'keyword', page: 1 });

    fireEvent.click(screen.getByText('Semantic (Vector)'));
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
});
