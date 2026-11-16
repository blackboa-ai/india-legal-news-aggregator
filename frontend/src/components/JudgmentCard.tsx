import React, { useState } from 'react';
import {
  Bookmark as BookmarkIcon,
  BookOpen,
  Calendar,
  Building,
  Sparkles,
  FolderPlus,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import { Judgment, SearchResultItem } from '../types';

interface JudgmentCardProps {
  judgment: Judgment | SearchResultItem;
  isBookmarked: boolean;
  onToggleBookmark: (judgment: Judgment) => void;
  onSelectJudgment: (judgment: Judgment) => void;
  onAddToTopic?: (judgment: Judgment) => void;
}

export const getCourtLevelBadge = (level: number) => {
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

export const getCategoryColor = (category: string) => {
  const normalized = category.toLowerCase();
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
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
};

export const JudgmentCard: React.FC<JudgmentCardProps> = ({
  judgment,
  isBookmarked,
  onToggleBookmark,
  onSelectJudgment,
  onAddToTopic,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const courtInfo = getCourtLevelBadge(judgment.court_level);
  const categoryStyle = getCategoryColor(judgment.subject_category);
  const searchItem = judgment as SearchResultItem;
  const isSearchRanked = typeof searchItem.score === 'number';

  const fullContent = judgment.full_text || judgment.excerpt;
  const isNewsArticle = judgment.source === 'barandbench' || judgment.source === 'livelaw';

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => setIsExpanded(!isExpanded)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setIsExpanded(!isExpanded);
        }
      }}
      className={`bg-white rounded-2xl border transition-all duration-200 p-5 sm:p-6 flex flex-col justify-between group cursor-pointer focus:outline-none focus:ring-2 focus:ring-amber-500 ${
        isExpanded
          ? 'border-amber-400 shadow-md ring-1 ring-amber-400/40'
          : 'border-slate-200 hover:border-amber-400 hover:shadow-lg'
      }`}
    >
      <div>
        {/* Header Metadata Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {/* Court Level Badge */}
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] ${courtInfo.badgeClass}`}
            >
              <Building className="h-3 w-3 mr-1" />
              {judgment.court_name || courtInfo.label}
            </span>

            {/* Subject Category Pill */}
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${categoryStyle}`}
            >
              {judgment.subject_category}
            </span>

            {/* Date */}
            <span className="inline-flex items-center text-slate-500 text-[11px]">
              <Calendar className="h-3 w-3 mr-1 text-slate-400" />
              {formatJudgmentDate(judgment.judgment_date)}
            </span>
          </div>

          {/* Bookmark & Topic Action Buttons */}
          <div className="flex items-center space-x-1">
            {onAddToTopic && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onAddToTopic(judgment);
                }}
                title="Add to Research Folder"
                className="p-2 min-h-[40px] min-w-[40px] flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
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
              className={`p-2 min-h-[40px] min-w-[40px] flex items-center justify-center rounded-lg transition ${
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
        </div>

        {/* Title */}
        <h3
          className={`text-base sm:text-lg font-bold text-slate-900 group-hover:text-amber-700 transition mb-2 leading-snug ${
            isExpanded ? '' : 'line-clamp-2'
          }`}
        >
          {judgment.title}
        </h3>

        {/* Short Title if distinct */}
        {judgment.short_title && judgment.short_title !== judgment.title && (
          <p className="text-xs font-medium text-slate-500 mb-2 italic">
            Case: {judgment.short_title}
          </p>
        )}

        {/* Parties if expanded and available */}
        {isExpanded && judgment.parties && judgment.parties.length > 0 && (
          <div
            onClick={(e) => e.stopPropagation()}
            className="mb-3 p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-600 flex flex-wrap gap-2 cursor-default"
          >
            {judgment.parties.map((p, idx) => {
              const pObj = p as { role?: string; name?: string };
              return (
                <span key={idx}>
                  <strong className="capitalize">{pObj.role || 'Party'}:</strong> {pObj.name || String(p)}
                </span>
              );
            })}
          </div>
        )}

        {/* Summary (Clamped in initial compact view, 100% full judgment/news text when clicked) */}
        {isExpanded ? (
          <div
            onClick={(e) => e.stopPropagation()}
            className="text-xs sm:text-sm text-slate-800 whitespace-pre-line mb-4 leading-relaxed font-sans cursor-text select-text bg-slate-50/70 p-4 rounded-xl border border-slate-200/60"
          >
            {fullContent}
          </div>
        ) : (
          <p className="text-xs sm:text-sm text-slate-600 line-clamp-3 mb-4 leading-relaxed font-sans">
            {judgment.excerpt || judgment.full_text}
          </p>
        )}

        {/* Statutory Citation Badges / Tags */}
        {judgment.tags && judgment.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {(isExpanded ? judgment.tags : judgment.tags.slice(0, 5)).map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
              >
                {tag}
              </span>
            ))}
            {!isExpanded && judgment.tags.length > 5 && (
              <span className="text-[10px] text-slate-400 self-center">
                +{judgment.tags.length - 5} more
              </span>
            )}
          </div>
        )}
      </div>

      {/* Footer Row: Source Attribution & Action Buttons */}
      <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs mt-2">
        <div className="flex items-center space-x-2 text-slate-400">
          <span className="capitalize font-medium text-slate-500">
            Source: {judgment.source || 'Indian Kanoon'}
          </span>
          {isSearchRanked && (
            <span
              className="inline-flex items-center text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full font-semibold"
              title="Most relevant match"
            >
              <Sparkles className="h-3 w-3 mr-1 text-amber-600" />
              Best Match
            </span>
          )}
          {isExpanded && judgment.url && (
            <a
              href={judgment.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center space-x-1 text-amber-700 hover:text-amber-800 underline ml-2"
              title="Open canonical source link in new tab"
            >
              <ExternalLink className="h-3 w-3" />
              <span>Original Source</span>
            </a>
          )}
        </div>

        <div className="flex items-center space-x-1.5">
          {/* Reader View Modal button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onSelectJudgment(judgment);
            }}
            title="Open distraction-free Reader View"
            className="inline-flex items-center space-x-1 font-semibold text-slate-700 hover:text-amber-800 hover:bg-slate-100 rounded-lg px-2.5 py-1.5 transition min-h-[40px]"
          >
            <BookOpen className="h-3.5 w-3.5 text-amber-600" />
            <span>Reader View</span>
          </button>

          {/* Inline Expand / Collapse Toggle */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className={`inline-flex items-center space-x-1 font-semibold rounded-lg px-2.5 py-1.5 transition min-h-[40px] ${
              isExpanded
                ? 'bg-amber-100 text-amber-900 hover:bg-amber-200'
                : 'text-amber-700 hover:text-amber-800 hover:bg-amber-50'
            }`}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" />
                <span>Show Less</span>
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" />
                <span>{isNewsArticle ? 'Read News' : 'Read Judgment'}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
