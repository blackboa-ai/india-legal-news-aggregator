import React from 'react';
import {
  Search,
  Sparkles,
  Calendar,
  X,
  RotateCcw,
  BookOpen,
} from 'lucide-react';
import { CourtItem, FilterState, LegalCategoryItem, SearchMode } from '../types';

interface SearchAndFiltersProps {
  filters: FilterState;
  onFilterChange: (updates: Partial<FilterState>) => void;
  onSearchSubmit: (e?: React.FormEvent) => void;
  onResetFilters: () => void;
  categories: LegalCategoryItem[];
  courts: CourtItem[];
  isLoading?: boolean;
}

export const CANONICAL_CATEGORIES = [
  'Constitutional',
  'Criminal',
  'Civil',
  'Corporate',
  'Administrative',
  'Human Rights',
  'Environment',
  'Labour',
  'Family',
  'Education',
];

export const DEFAULT_COURTS: CourtItem[] = [
  { code: 'sc', name: 'Supreme Court of India', level: 1 },
  { code: 'delhi-hc', name: 'High Court of Delhi', level: 2 },
  { code: 'bombay-hc', name: 'High Court of Bombay', level: 2 },
  { code: 'madras-hc', name: 'High Court of Madras', level: 2 },
  { code: 'calcutta-hc', name: 'High Court of Calcutta', level: 2 },
  { code: 'allahabad-hc', name: 'High Court of Allahabad', level: 2 },
  { code: 'karnataka-hc', name: 'High Court of Karnataka', level: 2 },
  { code: 'kerala-hc', name: 'High Court of Kerala', level: 2 },
  { code: 'punjab-haryana-hc', name: 'High Court of Punjab and Haryana', level: 2 },
  { code: 'gujarat-hc', name: 'High Court of Gujarat', level: 2 },
  { code: 'nclat', name: 'National Company Law Appellate Tribunal', level: 3 },
  { code: 'ngt', name: 'National Green Tribunal', level: 3 },
];

export const DEFAULT_CATEGORIES: LegalCategoryItem[] = CANONICAL_CATEGORIES.map((cat) => ({
  id: cat.toLowerCase().replace(/\s+/g, '-'),
  name: cat,
  description: `Legal judgments in ${cat}`,
}));

export const SearchAndFilters: React.FC<SearchAndFiltersProps> = ({
  filters,
  onFilterChange,
  onSearchSubmit,
  onResetFilters,
  courts,
  isLoading = false,
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchSubmit(e);
  };

  const handleModeChange = (mode: SearchMode) => {
    onFilterChange({ mode, page: 1 });
  };

  const handleCategoryToggle = (category: string) => {
    if (filters.category === category) {
      onFilterChange({ category: '', page: 1 });
    } else {
      onFilterChange({ category, page: 1 });
    }
  };

  const hasActiveFilters = Boolean(
    filters.q || filters.category || filters.court || filters.date_from || filters.date_to
  );

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 sm:p-6 mb-6">
      {/* Search Input Bar */}
      <form onSubmit={handleSubmit} className="mb-4">
        <div className="relative flex items-center">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
            <Search className="h-5 w-5" />
          </div>
          <input
            type="text"
            value={filters.q}
            onChange={(e) => onFilterChange({ q: e.target.value })}
            placeholder="Search judgments, statutory citations (e.g., Section 438 CrPC, Article 21, IBC Sec 9)..."
            className="block w-full pl-11 pr-24 py-3 sm:py-3.5 bg-slate-50 border border-slate-300 rounded-xl text-sm sm:text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 transition shadow-inner"
          />
          {filters.q && (
            <button
              type="button"
              onClick={() => onFilterChange({ q: '', page: 1 })}
              className="absolute right-24 sm:right-28 text-slate-400 hover:text-slate-600 p-1"
              aria-label="Clear search input"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <button
            type="submit"
            data-testid="search-submit-btn"
            disabled={isLoading}
            className="absolute right-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs sm:text-sm font-semibold transition flex items-center space-x-1.5 shadow"
          >
            {isLoading ? (
              <span className="inline-block animate-spin">⏳</span>
            ) : (
              <>
                <Sparkles className="h-4 w-4 text-amber-400" />
                <span className="hidden sm:inline">Search</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Mode Selection & Quick Filters Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
        {/* Search Mode Toggle (Hybrid / Keyword / Semantic) */}
        <div className="flex items-center space-x-1.5 bg-slate-100 p-1 rounded-xl">
          <span className="text-[11px] font-semibold text-slate-500 px-2 uppercase tracking-wider hidden md:inline">
            Mode:
          </span>
          <button
            type="button"
            onClick={() => handleModeChange('hybrid')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center space-x-1 ${
              filters.mode === 'hybrid'
                ? 'bg-white text-amber-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sparkles className="h-3 w-3 text-amber-500" />
            <span>Hybrid (RRF)</span>
          </button>
          <button
            type="button"
            onClick={() => handleModeChange('keyword')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
              filters.mode === 'keyword'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Keyword (BM25)
          </button>
          <button
            type="button"
            onClick={() => handleModeChange('semantic')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
              filters.mode === 'semantic'
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Semantic (Vector)
          </button>
        </div>

        {/* Court Dropdown & Date Range Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Court Selector */}
          <div className="relative">
            <select
              aria-label="Filter by Court"
              value={filters.court}
              onChange={(e) => onFilterChange({ court: e.target.value, page: 1 })}
              className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              <option value="">All Indian Courts</option>
              {courts.map((court) => (
                <option key={court.code} value={court.code}>
                  {court.name}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range Inputs */}
          <div className="flex items-center space-x-1.5 bg-slate-50 border border-slate-300 rounded-lg px-2 py-1 text-xs">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => onFilterChange({ date_from: e.target.value, page: 1 })}
              title="From Date"
              aria-label="Filter judgments on or after date"
              className="bg-transparent text-slate-700 text-xs focus:outline-none"
            />
            <span className="text-slate-400">to</span>
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => onFilterChange({ date_to: e.target.value, page: 1 })}
              title="To Date"
              aria-label="Filter judgments on or before date"
              className="bg-transparent text-slate-700 text-xs focus:outline-none"
            />
          </div>

          {/* Reset Filters */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={onResetFilters}
              className="flex items-center space-x-1 text-xs text-rose-600 hover:text-rose-700 font-medium px-2 py-1.5 rounded-lg hover:bg-rose-50 transition"
              title="Reset all filters"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* 10 Legal Subject Domain Category Pills */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
            <BookOpen className="h-3 w-3" />
            <span>Legal Domain Categories</span>
          </span>
          {filters.category && (
            <button
              type="button"
              onClick={() => onFilterChange({ category: '', page: 1 })}
              className="text-[11px] text-amber-600 hover:underline"
            >
              Clear category
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {CANONICAL_CATEGORIES.map((cat) => {
            const isSelected = filters.category.toLowerCase() === cat.toLowerCase();
            return (
              <button
                key={cat}
                type="button"
                onClick={() => handleCategoryToggle(cat)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                  isSelected
                    ? 'bg-amber-600 text-white shadow-sm ring-1 ring-amber-600'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Filter Chips */}
      {hasActiveFilters && (
        <div className="mt-3 pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
          <span className="font-semibold text-slate-600">Active filters:</span>
          {filters.q && (
            <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-100 text-slate-700">
              Query: &quot;{filters.q}&quot;
              <button
                type="button"
                onClick={() => onFilterChange({ q: '', page: 1 })}
                className="ml-1 text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            </span>
          )}
          {filters.category && (
            <span className="inline-flex items-center px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
              Category: {filters.category}
              <button
                type="button"
                onClick={() => onFilterChange({ category: '', page: 1 })}
                className="ml-1 text-amber-600 hover:text-amber-800"
              >
                ×
              </button>
            </span>
          )}
          {filters.court && (
            <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
              Court: {filters.court}
              <button
                type="button"
                onClick={() => onFilterChange({ court: '', page: 1 })}
                className="ml-1 text-blue-600 hover:text-blue-800"
              >
                ×
              </button>
            </span>
          )}
          {(filters.date_from || filters.date_to) && (
            <span className="inline-flex items-center px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200">
              Dates: {filters.date_from || 'Any'} to {filters.date_to || 'Any'}
              <button
                type="button"
                onClick={() => onFilterChange({ date_from: '', date_to: '', page: 1 })}
                className="ml-1 text-purple-600 hover:text-purple-800"
              >
                ×
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
};
