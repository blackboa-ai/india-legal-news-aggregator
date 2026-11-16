import React, { useState } from 'react';
import {
  Search,
  Sparkles,
  Calendar,
  X,
  RotateCcw,
  BookOpen,
  Filter,
  ChevronDown,
  ChevronUp,
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
  const [isMobileFiltersOpen, setIsMobileFiltersOpen] = useState(
    Boolean(filters.court || filters.date_from || filters.date_to)
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchSubmit(e);
  };

  const handleModeChange = (mode: SearchMode) => {
    onFilterChange({ mode, page: 1 });
  };

  const handleCategoryToggle = (category: string) => {
    if (filters.category.toLowerCase() === category.toLowerCase()) {
      onFilterChange({ category: '', page: 1 });
    } else {
      onFilterChange({ category, page: 1 });
    }
  };

  const activeCourtOrDateCount = [filters.court, filters.date_from, filters.date_to].filter(
    Boolean
  ).length;

  const hasActiveFilters = Boolean(
    filters.q || filters.category || filters.court || filters.date_from || filters.date_to
  );

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 sm:p-6 mb-6">
      {/* 1. Prominent, Full-Width Search Input Field */}
      <form onSubmit={handleSubmit} className="mb-4">
        <div className="relative flex items-center w-full">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
            <Search className="h-5 w-5" />
          </div>

          <input
            type="text"
            value={filters.q}
            onChange={(e) => onFilterChange({ q: e.target.value })}
            placeholder="Search judgments, sections (e.g. Section 438), or topics..."
            className="block w-full min-h-[48px] sm:min-h-[52px] pl-11 pr-24 sm:pr-28 py-3 bg-slate-50 border border-slate-300 rounded-xl text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 transition shadow-inner"
          />

          {filters.q && (
            <button
              type="button"
              onClick={() => onFilterChange({ q: '', page: 1 })}
              className="absolute right-20 sm:right-24 text-slate-400 hover:text-slate-600 p-2 min-h-[44px] min-w-[36px] flex items-center justify-center transition"
              aria-label="Clear search input"
            >
              <X className="h-4 w-4" />
            </button>
          )}

          <button
            type="submit"
            data-testid="search-submit-btn"
            disabled={isLoading}
            className="absolute right-1.5 min-h-[44px] px-3.5 sm:px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs sm:text-sm font-semibold transition flex items-center space-x-1.5 shadow"
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

      {/* 2. Search Mode & Filter Controls Row */}
      <div className="space-y-3 pt-1">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          {/* Segmented Search Mode Toggle: Smart Search | Exact Words | By Meaning */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl overflow-x-auto no-scrollbar shrink-0">
            <span className="text-[11px] font-semibold text-slate-500 px-2 uppercase tracking-wider hidden lg:inline">
              Mode:
            </span>
            <button
              type="button"
              onClick={() => handleModeChange('hybrid')}
              className={`min-h-[44px] px-3.5 py-2 rounded-lg text-xs sm:text-sm font-semibold transition flex items-center space-x-1.5 shrink-0 ${
                filters.mode === 'hybrid'
                  ? 'bg-white text-amber-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="h-4 w-4 text-amber-500" />
              <span>Smart Search</span>
            </button>
            <button
              type="button"
              onClick={() => handleModeChange('keyword')}
              className={`min-h-[44px] px-3.5 py-2 rounded-lg text-xs sm:text-sm font-semibold transition shrink-0 ${
                filters.mode === 'keyword'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Exact Words
            </button>
            <button
              type="button"
              onClick={() => handleModeChange('semantic')}
              className={`min-h-[44px] px-3.5 py-2 rounded-lg text-xs sm:text-sm font-semibold transition shrink-0 ${
                filters.mode === 'semantic'
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              By Meaning
            </button>
          </div>

          {/* Mobile Collapsible Button for Filters (Court & Date) */}
          <div className="md:hidden flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setIsMobileFiltersOpen(!isMobileFiltersOpen)}
              className="flex-1 min-h-[44px] px-4 py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 transition flex items-center justify-between"
            >
              <span className="flex items-center space-x-2">
                <Filter className="h-4 w-4 text-amber-600" />
                <span>Filters (Court & Date)</span>
                {activeCourtOrDateCount > 0 && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-500 text-slate-950 font-bold">
                    {activeCourtOrDateCount}
                  </span>
                )}
              </span>
              {isMobileFiltersOpen ? (
                <ChevronUp className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              )}
            </button>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={onResetFilters}
                className="min-h-[44px] px-3 py-2 bg-rose-50 text-rose-700 border border-rose-200 rounded-xl text-xs font-semibold flex items-center space-x-1"
                title="Reset all filters"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>

          {/* Desktop Filters (Always visible on md:, collapsible on mobile) */}
          <div
            className={`flex-wrap items-center gap-2 ${
              isMobileFiltersOpen ? 'flex' : 'hidden md:flex'
            }`}
          >
            {/* Court Dropdown */}
            <div className="relative flex-1 sm:flex-initial w-full sm:w-auto">
              <select
                aria-label="Filter by Court"
                value={filters.court}
                onChange={(e) => onFilterChange({ court: e.target.value, page: 1 })}
                className="w-full sm:w-auto min-h-[44px] text-xs sm:text-sm bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-slate-700 font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
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
            <div className="flex items-center space-x-1.5 bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 min-h-[44px] text-xs sm:text-sm w-full sm:w-auto">
              <Calendar className="h-4 w-4 text-slate-400 shrink-0" />
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => onFilterChange({ date_from: e.target.value, page: 1 })}
                title="From Date"
                aria-label="Filter judgments on or after date"
                className="bg-transparent text-slate-700 text-xs sm:text-sm focus:outline-none min-h-[30px]"
              />
              <span className="text-slate-400">to</span>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => onFilterChange({ date_to: e.target.value, page: 1 })}
                title="To Date"
                aria-label="Filter judgments on or before date"
                className="bg-transparent text-slate-700 text-xs sm:text-sm focus:outline-none min-h-[30px]"
              />
            </div>

            {/* Desktop Reset Filters Button */}
            {hasActiveFilters && (
              <button
                type="button"
                onClick={onResetFilters}
                className="hidden md:flex items-center space-x-1 text-xs sm:text-sm text-rose-600 hover:text-rose-700 font-semibold px-3.5 py-2 min-h-[44px] rounded-xl hover:bg-rose-50 border border-rose-200 transition"
                title="Reset all filters"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 3. Legal Topics: Touch-Scrollable Horizontal Pill Strip on Mobile, Wrap on Desktop */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center space-x-1.5">
            <BookOpen className="h-3.5 w-3.5 text-slate-400" />
            <span>Legal Topics</span>
          </span>
          {filters.category && (
            <button
              type="button"
              onClick={() => onFilterChange({ category: '', page: 1 })}
              className="text-xs text-amber-600 hover:underline min-h-[32px] px-1 font-medium"
            >
              Clear topic
            </button>
          )}
        </div>

        {/* Horizontal scroll on mobile prevents chips from consuming 4 vertical rows */}
        <div className="flex overflow-x-auto no-scrollbar flex-nowrap md:flex-wrap gap-2 pb-1.5 pt-0.5 -mx-1 px-1 scroll-smooth">
          {CANONICAL_CATEGORIES.map((cat) => {
            const isSelected = filters.category.toLowerCase() === cat.toLowerCase();
            return (
              <button
                key={cat}
                type="button"
                onClick={() => handleCategoryToggle(cat)}
                className={`min-h-[44px] px-4 py-2 rounded-full text-xs font-semibold transition shrink-0 flex items-center ${
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

      {/* 4. Active Filter Chips */}
      {hasActiveFilters && (
        <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
          <span className="font-semibold text-slate-600">Active filters:</span>
          {filters.q && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 min-h-[32px]">
              Query: &quot;{filters.q}&quot;
              <button
                type="button"
                onClick={() => onFilterChange({ q: '', page: 1 })}
                className="ml-1.5 p-1 text-slate-400 hover:text-slate-600"
                aria-label="Remove query filter"
              >
                ×
              </button>
            </span>
          )}
          {filters.category && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 min-h-[32px]">
              Topic: {filters.category}
              <button
                type="button"
                onClick={() => onFilterChange({ category: '', page: 1 })}
                className="ml-1.5 p-1 text-amber-600 hover:text-amber-800"
                aria-label="Remove topic filter"
              >
                ×
              </button>
            </span>
          )}
          {filters.court && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-blue-50 text-blue-800 border border-blue-200 min-h-[32px]">
              Court: {filters.court}
              <button
                type="button"
                onClick={() => onFilterChange({ court: '', page: 1 })}
                className="ml-1.5 p-1 text-blue-600 hover:text-blue-800"
                aria-label="Remove court filter"
              >
                ×
              </button>
            </span>
          )}
          {(filters.date_from || filters.date_to) && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-purple-50 text-purple-800 border border-purple-200 min-h-[32px]">
              Dates: {filters.date_from || 'Any'} to {filters.date_to || 'Any'}
              <button
                type="button"
                onClick={() => onFilterChange({ date_from: '', date_to: '', page: 1 })}
                className="ml-1.5 p-1 text-purple-600 hover:text-purple-800"
                aria-label="Remove date filter"
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
