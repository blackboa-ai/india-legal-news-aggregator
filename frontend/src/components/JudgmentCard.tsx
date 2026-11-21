import React from 'react';
import {
  Bookmark as BookmarkIcon,
  BookOpen,
  Sparkles,
  FolderPlus,
} from 'lucide-react';
import { Judgment, SearchResultItem } from '../types';
import { prefetchJudgment } from '../api/client';

interface JudgmentCardProps {
  judgment: Judgment | SearchResultItem;
  isBookmarked: boolean;
  onToggleBookmark: (judgment: Judgment) => void;
  onSelectJudgment: (judgment: Judgment) => void;
  onAddToTopic?: (judgment: Judgment) => void;
}

export const getCourtLevelBadge = (level: number, courtCode?: string) => {
  if (courtCode === 'international' || level === 4) {
    return {
      label: 'International',
      badgeClass: 'bg-indigo-100 text-indigo-900 border border-indigo-300 font-semibold',
    };
  }
  switch (level) {
    case 1:
      return {
        label: 'Supreme Court',
        badgeClass: 'bg-amber-100 text-amber-900 border border-amber-300 font-semibold',
      };
    case 2:
      return {
        label: 'High Court',
        badgeClass: 'bg-blue-100 text-blue-900 border border-blue-200 font-semibold',
      };
    case 3:
    default:
      return {
        label: 'Tribunal / Special Court',
        badgeClass: 'bg-slate-100 text-slate-800 border border-slate-300',
      };
  }
};

export const getContentTypeBadge = (contentType?: string, courtCode?: string) => {
  if (courtCode === 'international') {
    return {
      label: 'WORLD NEWS',
      badgeClass:
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800',
    };
  }
  switch (contentType) {
    case 'judgment':
      return {
        label: 'COURT ORDER',
        badgeClass:
          'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
      };
    case 'news':
      return {
        label: 'LEGAL NEWS',
        badgeClass:
          'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800',
      };
    case 'unknown':
    default:
      return null;
  }
};

export const getCategoryColor = (category: string) => {
  const normalized = category.toLowerCase();
  if (normalized.includes('internat')) return 'bg-indigo-50 text-indigo-700 border-indigo-200';
  if (normalized.includes('crim')) return 'bg-rose-50 text-rose-700 border-rose-200';
  if (normalized.includes('const')) return 'bg-amber-50 text-amber-700 border-amber-200';
  if (normalized.includes('corp') || normalized.includes('tax'))
    return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (normalized.includes('civil')) return 'bg-sky-50 text-sky-700 border-sky-200';
  if (normalized.includes('human')) return 'bg-purple-50 text-purple-700 border-purple-200';
  if (normalized.includes('env')) return 'bg-teal-50 text-teal-700 border-teal-200';
  if (normalized.includes('lab')) return 'bg-orange-50 text-orange-700 border-orange-200';
  if (normalized.includes('fam')) return 'bg-pink-50 text-pink-700 border-pink-200';
  return 'bg-slate-100 text-slate-700 border-slate-200';
};

export const formatJudgmentDate = (dateStr: string) => {
  try {
    if (!dateStr) return 'Unknown date';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 'Unknown date';
    return d.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'Unknown date';
  }
};

export const getSourceLabel = (source?: string): string => {
  if (!source) return 'Court Record';
  const s = source.toLowerCase();
  if (s === 'sci') return 'Supreme Court of India';
  if (s === 'indiankanoon') return 'Court Order (Indian Kanoon)';
  if (s === 'livelaw') return 'LiveLaw';
  if (s === 'barandbench') return 'Bar & Bench';
  if (s === 'bbc') return 'BBC World News';
  if (s === 'delhi-hc') return 'Delhi High Court';
  return source;
};

export const JudgmentCard = React.memo<JudgmentCardProps>(({
  judgment,
  isBookmarked,
  onToggleBookmark,
  onSelectJudgment,
  onAddToTopic,
}) => {
  const [imgError, setImgError] = React.useState(false);
  const courtInfo = getCourtLevelBadge(judgment.court_level, judgment.court_code);
  const contentTypeBadge = getContentTypeBadge(judgment.content_type, judgment.court_code);
  const categoryStyle = getCategoryColor(judgment.subject_category);
  const isSearchResult = 'score' in judgment && typeof (judgment as SearchResultItem).score === 'number';
  const score = isSearchResult ? (judgment as SearchResultItem).score : null;
  const searchItem = isSearchResult ? (judgment as SearchResultItem) : null;
  const isSearchRanked =
    score !== null &&
    searchItem !== null &&
    (searchItem.keyword_rank === 1 || searchItem.semantic_rank === 1 || score >= 0.025);
  const hasHeroImage = judgment.court_code === 'international' && Boolean(judgment.image_url) && !imgError;

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={() => onSelectJudgment(judgment)}
      onMouseEnter={() => {
        if (judgment?.id) prefetchJudgment(judgment.id);
      }}
      onTouchStart={() => {
        if (judgment?.id) prefetchJudgment(judgment.id);
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelectJudgment(judgment);
        }
      }}
      className="bg-white rounded-2xl border border-slate-200 hover:border-amber-400 hover:shadow-lg transition-all duration-200 overflow-hidden flex flex-col justify-between group cursor-pointer focus:outline-none focus:ring-2 focus:ring-amber-500 h-full"
    >
      {hasHeroImage && (
        <div className="relative w-full aspect-video sm:h-44 overflow-hidden bg-slate-100 shrink-0">
          <img
            src={judgment.image_url!}
            alt={judgment.title}
            loading="lazy"
            decoding="async"
            onError={() => setImgError(true)}
            data-testid="card-hero-image"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />
        </div>
      )}

      <div className="p-5 sm:p-6 flex flex-col justify-between flex-1">
        <div>
          {/* Header Metadata Row */}
        <header className="flex items-center justify-between gap-2 mb-3">
          <div className="flex flex-wrap items-center gap-1.5 text-xs min-w-0">
            {/* Content Type Pill Badge */}
            {contentTypeBadge && (
              <span
                data-testid="content-type-badge"
                className={`shrink-0 ${contentTypeBadge.badgeClass}`}
              >
                {contentTypeBadge.label}
              </span>
            )}

            {/* Court Level Badge */}
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] shrink-0 ${courtInfo.badgeClass}`}
            >
              {judgment.court_name || courtInfo.label}
            </span>

            {/* Subject Category Pill */}
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border shrink-0 ${categoryStyle}`}
            >
              {judgment.subject_category}
            </span>

            {/* Date */}
            <time
              dateTime={judgment.judgment_date}
              className="inline-flex items-center text-slate-500 text-[11px] shrink-0"
            >
              {formatJudgmentDate(judgment.judgment_date)}
            </time>
          </div>

          {/* Bookmark & Topic Action Buttons */}
          <div className="flex items-center space-x-1 shrink-0">
            {onAddToTopic && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onAddToTopic(judgment);
                }}
                title="Add to Research Folder"
                className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              >
                <FolderPlus className="h-4 w-4" />
              </button>
            )}

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleBookmark(judgment);
              }}
              title={isBookmarked ? 'Remove Bookmark' : 'Save to Bookmarks'}
              className={`p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl transition ${
                isBookmarked
                  ? 'text-amber-500 bg-amber-50 hover:bg-amber-100'
                  : 'text-slate-400 hover:text-amber-500 hover:bg-slate-100'
              }`}
            >
              <BookmarkIcon
                className="h-4 w-4"
                fill={isBookmarked ? 'currentColor' : 'none'}
              />
            </button>
          </div>
        </header>

        {/* Title (strictly clamped to 2 lines for uniform grid alignment with crawlable anchor) */}
        <h3 className="text-base sm:text-lg font-bold text-slate-900 group-hover:text-amber-700 transition mb-2 leading-snug line-clamp-2">
          <a
            href={`/?judgment=${encodeURIComponent(judgment.id)}`}
            onClick={(e) => {
              if (!e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) {
                e.preventDefault();
                onSelectJudgment(judgment);
              }
            }}
            className="hover:underline focus:outline-none"
          >
            {judgment.title}
          </a>
        </h3>

        {/* Short Title if distinct */}
        {judgment.short_title && judgment.short_title !== judgment.title && (
          <p className="text-xs font-medium text-slate-500 mb-2 italic line-clamp-1">
            Case: {judgment.short_title}
          </p>
        )}

        {/* Preview Summary (Clamped strictly to 3 lines for compact, uniform feed cards) */}
        <p className="text-xs sm:text-sm text-slate-600 line-clamp-3 mb-4 leading-relaxed font-sans">
          {judgment.excerpt || judgment.summary || judgment.full_text}
        </p>

        {/* Statutory Citation Badges / Tags */}
        {judgment.tags && judgment.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {judgment.tags.slice(0, 4).map((tag, idx) => (
              <span
                key={tag || `tag-${idx}`}
                className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
              >
                {tag}
              </span>
            ))}
            {judgment.tags.length > 4 && (
              <span className="text-[10px] text-slate-400 self-center">
                +{judgment.tags.length - 4} more
              </span>
            )}
          </div>
        )}
      </div>

      {/* Footer Row: Source Attribution & Reader Trigger */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2 text-xs mt-3">
        <div className="flex items-center space-x-2 text-slate-400 min-w-0">
          <span className="font-medium text-slate-500 truncate" title={judgment.source}>
            Source: {getSourceLabel(judgment.source)}
          </span>
          {isSearchRanked && (
            <span
              className="inline-flex items-center text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full font-semibold shrink-0"
              title="Most relevant match"
            >
              <Sparkles className="h-3 w-3 mr-1 text-amber-600" />
              Best Match
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelectJudgment(judgment);
          }}
          title="Open distraction-free Reader View"
          className="inline-flex items-center space-x-1.5 font-semibold text-amber-700 hover:text-amber-800 hover:bg-amber-50 rounded-xl px-3 py-2 transition min-h-[44px] shrink-0"
        >
          <BookOpen className="h-4 w-4 text-amber-600" />
          <span>Read Full</span>
        </button>
      </div>
      </div>
    </article>
  );
});

JudgmentCard.displayName = 'JudgmentCard';

