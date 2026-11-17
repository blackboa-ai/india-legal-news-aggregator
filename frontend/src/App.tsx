import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Sparkles,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  FileQuestion,
} from 'lucide-react';
import { api } from './api/client';
import { useAuth } from './context/AuthContext';
import {
  CourtItem,
  FilterState,
  Judgment,
  LegalCategoryItem,
  SearchResultItem,
  Topic,
} from './types';
import { Header } from './components/Header';
import {
  SearchAndFilters,
  DEFAULT_CATEGORIES,
  DEFAULT_COURTS,
} from './components/SearchAndFilters';
import { JudgmentCard } from './components/JudgmentCard';
import { JudgmentModal } from './components/JudgmentModal';
import { AuthModal } from './components/AuthModal';
import { BookmarksAndAlertsModal } from './components/BookmarksAndAlertsModal';
import { FeedbackModal, FloatingFeedbackButton } from './components/FeedbackModal';
import { Footer } from './components/Footer';

const PAGE_SIZE = 25;
const FEED_CACHE_KEY = 'india_legal_cached_feed';

function getInitialCachedFeed(): { data: Judgment[]; total: number } | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(FEED_CACHE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const items = parsed?.data || parsed?.items;
      if (Array.isArray(items) && items.length > 0) {
        return { data: items, total: typeof parsed.total === 'number' ? parsed.total : items.length };
      }
    }
  } catch {
    // localStorage unavailable
  }
  return null;
}

const formatFriendlyErrorMessage = (err: unknown): string => {
  if (err instanceof Error) {
    const lower = err.message.toLowerCase();
    if (
      lower.includes('fetch') ||
      lower.includes('500') ||
      lower.includes('api') ||
      lower.includes('failed') ||
      lower.includes('network') ||
      lower.includes('connect')
    ) {
      return 'Unable to load updates right now. Please try again.';
    }
    return err.message;
  }
  return 'Unable to load updates right now. Please try again.';
};

export const App: React.FC = () => {
  const { isAuthenticated, user } = useAuth();

  // Search & Filter State
  const [filters, setFilters] = useState<FilterState>({
    q: '',
    mode: 'hybrid',
    category: '',
    court: '',
    content_type: undefined,
    date_from: '',
    date_to: '',
    page: 1,
    limit: PAGE_SIZE,
  });

  // Stale-While-Revalidate: Instant 0ms hydration from localStorage
  const cachedFeedRef = useRef(getInitialCachedFeed());
  const initialCachedFeed = cachedFeedRef.current;

  // Data States (render cached feed instantaneously in 0ms on page load)
  const [judgments, setJudgments] = useState<(Judgment | SearchResultItem)[]>(
    () => initialCachedFeed?.data || []
  );
  const [totalCount, setTotalCount] = useState<number>(
    () => initialCachedFeed?.total || 0
  );
  const [isLoading, setIsLoading] = useState<boolean>(() => !initialCachedFeed);
  const [error, setError] = useState<string | null>(null);

  // Debounced search query & AbortController request cancellation
  const [debouncedQuery, setDebouncedQuery] = useState(filters.q);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 250ms debounce on search typing
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    if (!filters.q.trim()) {
      setDebouncedQuery('');
      return;
    }
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedQuery(filters.q);
    }, 250);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [filters.q]);

  // Metadata (defaults gracefully to canonical categories and courts)
  const [categories, setCategories] = useState<LegalCategoryItem[]>(DEFAULT_CATEGORIES);
  const [courts, setCourts] = useState<CourtItem[]>(DEFAULT_COURTS);
  const [searchMeta, setSearchMeta] = useState<{
    query_type?: string;
    matched_terms?: string[];
  } | null>(null);

  // Modals & Panels
  const [selectedJudgment, setSelectedJudgment] = useState<Judgment | null>(null);
  const [isReaderOpen, setIsReaderOpen] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState<boolean>(false);
  const [isDashboardOpen, setIsDashboardOpen] = useState<boolean>(false);
  const [dashboardTab, setDashboardTab] = useState<
    'bookmarks' | 'alerts' | 'matches' | 'topics'
  >('bookmarks');

  // User Workspace States
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [topics, setTopics] = useState<Topic[]>([]);
  const [alertMatchCount, setAlertMatchCount] = useState<number>(0);

  // Toast Notification State
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' | 'error' } | null>(
    null
  );

  const searchContainerRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((message: string, type: 'success' | 'info' | 'error' = 'info') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3500);
  }, []);

  // Fetch initial metadata (Categories & Courts with graceful fallback)
  useEffect(() => {
    let isMounted = true;
    const fetchMetadata = async () => {
      try {
        const [cats, crts] = await Promise.all([
          api.judgments.categories().catch(() => DEFAULT_CATEGORIES),
          api.judgments.courts().catch(() => DEFAULT_COURTS),
        ]);
        if (isMounted) {
          setCategories(cats && cats.length > 0 ? cats : DEFAULT_CATEGORIES);
          setCourts(crts && crts.length > 0 ? crts : DEFAULT_COURTS);
        }
      } catch (err) {
        console.warn('Metadata fetch fallback:', err);
        if (isMounted) {
          setCategories(DEFAULT_CATEGORIES);
          setCourts(DEFAULT_COURTS);
        }
      }
    };
    fetchMetadata();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch user workspace data when authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      setBookmarkedIds(new Set());
      setTopics([]);
      setAlertMatchCount(0);
      return;
    }

    let isMounted = true;
    const fetchUserData = async () => {
      try {
        const [bookmarksRes, topicsRes, alertsMatchesRes] = await Promise.all([
          api.bookmarks.list({ limit: 100 }).catch(() => ({ data: [] })),
          api.topics.list().catch(() => ({ data: [] })),
          api.alerts.matches({ limit: 20 }).catch(() => ({ matches: [] })),
        ]);

        if (isMounted) {
          const ids = new Set(bookmarksRes.data.map((b) => b.judgment_id));
          setBookmarkedIds(ids);
          setTopics(topicsRes.data);
          setAlertMatchCount(alertsMatchesRes.matches.length);
        }
      } catch (err) {
        console.warn('Could not load user workspace details:', err);
      }
    };

    fetchUserData();
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, user?.id]);

  // Primary Judgment & Search Query fetcher with AbortController cancellation & debouncing
  const fetchJudgments = useCallback(async () => {
    // Abort previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Only show full loading skeleton if we don't have items to display
    setIsLoading(true);
    setError(null);

    const isDefaultFeed =
      !debouncedQuery.trim() &&
      !filters.category &&
      !filters.court &&
      !filters.content_type &&
      !filters.date_from &&
      !filters.date_to &&
      filters.page === 1;

    try {
      const offset = (filters.page - 1) * filters.limit;

      if (debouncedQuery.trim()) {
        // Hybrid / Keyword / Semantic Search Query with AbortSignal
        const searchRes = await api.judgments.search(
          {
            q: debouncedQuery.trim(),
            mode: filters.mode,
            category: filters.category || undefined,
            court: filters.court || undefined,
            content_type: filters.content_type || undefined,
            limit: filters.limit,
            offset,
          },
          controller.signal
        );

        if (!controller.signal.aborted) {
          setJudgments(searchRes.results);
          setTotalCount(searchRes.total);
          setSearchMeta({
            query_type: searchRes.query_type,
            matched_terms: searchRes.matched_terms,
          });
        }
      } else {
        // Standard paginated filtered feed with AbortSignal
        const feedRes = await api.judgments.list(
          {
            category: filters.category || undefined,
            court: filters.court || undefined,
            content_type: filters.content_type || undefined,
            date_from: filters.date_from || undefined,
            date_to: filters.date_to || undefined,
            limit: filters.limit,
            offset,
          },
          controller.signal
        );

        if (!controller.signal.aborted) {
          const items = feedRes.data || feedRes.items || [];
          const total = typeof feedRes.total === 'number' ? feedRes.total : items.length;
          setJudgments(items);
          setTotalCount(total);
          setSearchMeta(null);

          // Stale-while-revalidate: store fresh default feed for instantaneous 0ms hydration
          if (isDefaultFeed && items.length > 0) {
            try {
              localStorage.setItem(
                FEED_CACHE_KEY,
                JSON.stringify({
                  data: items,
                  total,
                  timestamp: Date.now(),
                })
              );
            } catch {
              // Ignore storage quotas
            }
          }
        }
      }
    } catch (err: unknown) {
      if (controller.signal.aborted || (err instanceof Error && err.name === 'AbortError')) {
        return; // Silent request cancellation
      }
      setError(formatFriendlyErrorMessage(err));
      // Keep existing displayed items if background revalidation fails
      setJudgments((prev) => (prev.length > 0 ? prev : []));
      setTotalCount((prev) => (prev > 0 ? prev : 0));
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, [
    debouncedQuery,
    filters.mode,
    filters.category,
    filters.court,
    filters.content_type,
    filters.date_from,
    filters.date_to,
    filters.page,
    filters.limit,
  ]);

  useEffect(() => {
    fetchJudgments();
  }, [fetchJudgments]);

  // Filter Updates
  const handleFilterChange = (updates: Partial<FilterState>) => {
    setFilters((prev) => ({
      ...prev,
      ...updates,
    }));
  };

  const handleSearchSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setDebouncedQuery(filters.q);
    setFilters((prev) => ({ ...prev, page: 1 }));
  };

  const handleResetFilters = () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setDebouncedQuery('');
    setFilters({
      q: '',
      mode: 'hybrid',
      category: '',
      court: '',
      content_type: undefined,
      date_from: '',
      date_to: '',
      page: 1,
      limit: PAGE_SIZE,
    });
    setSearchMeta(null);
  };

  // Memoized Reader Open & Precedent Selection Handlers
  const handleSelectJudgment = useCallback((judgment: Judgment) => {
    setSelectedJudgment(judgment);
    setIsReaderOpen(true);
  }, []);

  const handleSelectSimilarJudgment = useCallback((similar: Judgment) => {
    setSelectedJudgment(similar);
  }, []);

  // Memoized Bookmark Toggle Handler
  const handleToggleBookmark = useCallback(
    async (judgment: Judgment, notes?: string, tags?: string[]) => {
      if (!isAuthenticated) {
        showToast('Please sign in to save judgments to your workspace', 'info');
        setIsAuthModalOpen(true);
        return;
      }

      const judgmentId = judgment.id;
      const isCurrentlySaved = bookmarkedIds.has(judgmentId);

      try {
        if (isCurrentlySaved) {
          await api.bookmarks.remove(judgmentId);
          setBookmarkedIds((prev) => {
            const updated = new Set(prev);
            updated.delete(judgmentId);
            return updated;
          });
          showToast('Judgment removed from bookmarks', 'info');
        } else {
          await api.bookmarks.add(judgmentId, { notes, tags });
          setBookmarkedIds((prev) => new Set(prev).add(judgmentId));
          showToast('Judgment saved to bookmarks', 'success');
        }
      } catch (err) {
        console.error('Failed to toggle bookmark:', err);
        showToast('Action could not be completed', 'error');
      }
    },
    [isAuthenticated, bookmarkedIds, showToast]
  );

  // Memoized Card Add To Topic Handler
  const handleCardAddToTopic = useCallback((judgment: Judgment) => {
    setSelectedJudgment(judgment);
    setIsReaderOpen(true);
  }, []);

  // Add to Research Topic Folder
  const handleAddToTopic = async (topicId: string, judgmentId: string) => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }
    try {
      await api.topics.addJudgment(topicId, judgmentId);
      // update topic judgment count locally
      setTopics((prev) =>
        prev.map((t) => (t.id === topicId ? { ...t, judgment_count: t.judgment_count + 1 } : t))
      );
      showToast('Judgment added to research folder', 'success');
    } catch (err) {
      console.error('Error adding judgment to topic:', err);
      showToast('Could not add judgment to folder', 'error');
      throw err;
    }
  };

  // Open Dashboard with Tab
  const handleOpenDashboard = (tab: 'bookmarks' | 'alerts' | 'matches' | 'topics' = 'bookmarks') => {
    setDashboardTab(tab);
    setIsDashboardOpen(true);
  };

  const totalPages = Math.ceil(totalCount / filters.limit) || 1;

  return (
    <div className="min-h-screen flex flex-col bg-slate-100/60 font-sans text-slate-900">
      {/* Toast Notification Banner */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-bounce">
          <div
            className={`px-4 py-3 rounded-xl shadow-lg text-xs font-semibold flex items-center space-x-2 text-white ${
              toast.type === 'success'
                ? 'bg-emerald-600'
                : toast.type === 'error'
                ? 'bg-rose-600'
                : 'bg-slate-900'
            }`}
          >
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {/* Main Header */}
      <Header
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onOpenDashboard={handleOpenDashboard}
        onOpenFeedback={() => setIsFeedbackOpen(true)}
        bookmarkCount={bookmarkedIds.size}
        alertMatchCount={alertMatchCount}
        onScrollToSearch={() => {
          searchContainerRef.current?.scrollIntoView({ behavior: 'smooth' });
        }}
      />

      {/* Hero Banner Section */}
      <section className="bg-gradient-to-b from-slate-900 via-slate-900 to-slate-800 text-white pt-6 sm:pt-8 pb-10 sm:pb-16 px-4">
        <div className="max-w-7xl mx-auto text-center space-y-3">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-400/10 text-amber-300 border border-amber-400/20 text-xs font-semibold">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span>Smart Legal Search • Verified Indian Court Decisions</span>
          </div>
          <h1 className="text-xl sm:text-3xl md:text-5xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight">
            Indian Legal Intelligence & Precedent Aggregator
          </h1>
          <p className="text-xs sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Real-time legal updates from the Supreme Court of India, High Courts, Indian Kanoon, LiveLaw, and
            Bar & Bench with instant precedent and statute search.
          </p>
        </div>
      </section>

      {/* Main Application Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 -mt-6 sm:-mt-8">
        <div ref={searchContainerRef}>
          {/* Search & Filter Controls */}
          <SearchAndFilters
            filters={filters}
            onFilterChange={handleFilterChange}
            onSearchSubmit={handleSearchSubmit}
            onResetFilters={handleResetFilters}
            categories={categories}
            courts={courts}
            isLoading={isLoading}
          />
        </div>

        {/* Results Metadata & Statistics Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4 px-1">
          <div className="flex items-center space-x-2">
            <h2 className="text-sm font-bold text-slate-800">
              {filters.q ? 'Search Results' : 'Latest Legal Judgments & Orders'}
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-semibold">
              {totalCount} {totalCount === 1 ? 'case' : 'cases'}
            </span>
          </div>

          {searchMeta && (
            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <span className="font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded text-[11px]">
                Search: {searchMeta.query_type === 'hybrid' ? 'Smart Search' : searchMeta.query_type === 'keyword' ? 'Exact Words' : searchMeta.query_type === 'semantic' ? 'By Meaning' : searchMeta.query_type}
              </span>
              {searchMeta.matched_terms && searchMeta.matched_terms.length > 0 && (
                <span className="text-[11px] text-slate-600">
                  Matching key terms: {searchMeta.matched_terms.join(', ')}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Error Notification */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs sm:text-sm flex items-start space-x-3 shadow-sm">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-bold">Unable to load updates</p>
              <p className="mt-0.5">{error}</p>
              <button
                type="button"
                onClick={fetchJudgments}
                className="mt-2 text-xs font-semibold text-amber-900 underline hover:text-amber-700 flex items-center space-x-1 min-h-[44px]"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Try Again</span>
              </button>
            </div>
          </div>
        )}

        {/* Loading Skeletons - displayed when loading and no judgments in cache/state */}
        {isLoading && judgments.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5 mb-8">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 animate-pulse"
              >
                <div className="flex justify-between items-center">
                  <div className="h-4 bg-slate-200 rounded w-24"></div>
                  <div className="h-4 bg-slate-200 rounded w-16"></div>
                </div>
                <div className="h-5 bg-slate-200 rounded w-3/4"></div>
                <div className="h-3 bg-slate-200 rounded w-full"></div>
                <div className="h-3 bg-slate-200 rounded w-5/6"></div>
                <div className="flex space-x-2 pt-2">
                  <div className="h-4 bg-slate-200 rounded w-16"></div>
                  <div className="h-4 bg-slate-200 rounded w-16"></div>
                </div>
              </div>
            ))}
          </div>
        ) : judgments.length === 0 ? (
          /* Empty State */
          <div className="bg-white rounded-2xl border border-slate-200 p-8 sm:p-12 text-center my-6 space-y-3">
            <div className="h-12 w-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <FileQuestion className="h-6 w-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">
              No Judgments Found
            </h3>
            <p className="text-xs sm:text-sm text-slate-500 max-w-md mx-auto">
              No legal cases matched your current search query or applied domain/court filters. Try
              adjusting your search words or clearing filters.
            </p>
            <button
              type="button"
              onClick={handleResetFilters}
              className="px-5 py-2.5 min-h-[44px] bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold transition"
            >
              Clear All Filters
            </button>
          </div>
        ) : (
          /* Judgments Grid (Uniform 3-Column on Desktop, Single Column on Mobile) */
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5 mb-8">
              {judgments.map((judgment) => (
                <JudgmentCard
                  key={judgment.id}
                  judgment={judgment}
                  isBookmarked={bookmarkedIds.has(judgment.id)}
                  onToggleBookmark={handleToggleBookmark}
                  onSelectJudgment={handleSelectJudgment}
                  onAddToTopic={handleCardAddToTopic}
                />
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-3 sm:px-6 rounded-2xl shadow-sm mb-10 text-xs">
                <div className="text-slate-500 hidden sm:block">
                  Showing{' '}
                  <span className="font-semibold text-slate-800">
                    {(filters.page - 1) * filters.limit + 1}
                  </span>{' '}
                  to{' '}
                  <span className="font-semibold text-slate-800">
                    {Math.min(filters.page * filters.limit, totalCount)}
                  </span>{' '}
                  of <span className="font-semibold text-slate-800">{totalCount}</span> results
                </div>

                <div className="flex items-center justify-between sm:justify-end w-full sm:w-auto space-x-2">
                  <button
                    type="button"
                    disabled={filters.page <= 1}
                    onClick={() => {
                      handleFilterChange({ page: filters.page - 1 });
                      window.scrollTo({ top: 300, behavior: 'smooth' });
                    }}
                    className="min-h-[44px] px-3.5 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center space-x-1"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    <span>Previous</span>
                  </button>

                  <span className="px-3 py-1 font-semibold text-slate-700">
                    Page {filters.page} of {totalPages}
                  </span>

                  <button
                    type="button"
                    disabled={filters.page >= totalPages}
                    onClick={() => {
                      handleFilterChange({ page: filters.page + 1 });
                      window.scrollTo({ top: 300, behavior: 'smooth' });
                    }}
                    className="min-h-[44px] px-3.5 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center space-x-1"
                  >
                    <span>Next</span>
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Reader Modal */}
      <JudgmentModal
        judgment={selectedJudgment}
        isOpen={isReaderOpen}
        onClose={() => setIsReaderOpen(false)}
        isBookmarked={selectedJudgment ? bookmarkedIds.has(selectedJudgment.id) : false}
        onToggleBookmark={handleToggleBookmark}
        onSelectSimilarJudgment={handleSelectSimilarJudgment}
        topics={topics}
        onAddToTopic={handleAddToTopic}
      />

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      {/* Bookmarks, Alerts & Topics Workspace Modal */}
      <BookmarksAndAlertsModal
        isOpen={isDashboardOpen}
        onClose={() => setIsDashboardOpen(false)}
        defaultTab={dashboardTab}
        onSelectJudgment={(j) => {
          setIsDashboardOpen(false);
          handleSelectJudgment(j);
        }}
        courts={courts}
        categories={categories}
        onOpenAuth={() => setIsAuthModalOpen(true)}
      />

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={isFeedbackOpen}
        onClose={() => setIsFeedbackOpen(false)}
      />

      {/* Floating Action Button */}
      <FloatingFeedbackButton onClick={() => setIsFeedbackOpen(true)} />

      {/* Footer */}
      <Footer onOpenFeedback={() => setIsFeedbackOpen(true)} />
    </div>
  );
};
