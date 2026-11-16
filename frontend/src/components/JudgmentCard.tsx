import React from 'react';
import {
  Bookmark as BookmarkIcon,
  BookOpen,
  Calendar,
  Building,
  Sparkles,
  FolderPlus,
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
  const courtInfo = getCourtLevelBadge(judgment.court_level);
  const categoryStyle = getCategoryColor(judgment.subject_category);
  const searchItem = judgment as SearchResultItem;
  const isSearchRanked = typeof searchItem.score === 'number';

  return (
    <div className="bg-white rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all duration-200 p-5 flex flex-col justify-between group">
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
                onClick={() => onAddToTopic(judgment)}
                title="Add to Research Topic Folder"
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              >
                <FolderPlus className="h-4 w-4" />
              </button>
            )}

            <button
              type="button"
              onClick={() => onToggleBookmark(judgment)}
              title={isBookmarked ? 'Remove Bookmark' : 'Save to Bookmarks'}
              className={`p-1.5 rounded-lg transition ${
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
          onClick={() => onSelectJudgment(judgment)}
          className="text-base sm:text-lg font-semibold text-slate-900 group-hover:text-amber-700 transition cursor-pointer line-clamp-2 mb-1.5 leading-snug"
        >
          {judgment.title}
        </h3>

        {/* Short Title if distinct */}
        {judgment.short_title && judgment.short_title !== judgment.title && (
          <p className="text-xs font-medium text-slate-500 mb-2 italic">
            Citation / Case: {judgment.short_title}
          </p>
        )}

        {/* Excerpt Summary */}
        <p className="text-xs sm:text-sm text-slate-600 line-clamp-3 mb-3 leading-relaxed">
          {judgment.excerpt}
        </p>

        {/* Statutory Citation Badges / Tags */}
        {judgment.tags && judgment.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {judgment.tags.slice(0, 5).map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
              >
                {tag}
              </span>
            ))}
            {judgment.tags.length > 5 && (
              <span className="text-[10px] text-slate-400 self-center">
                +{judgment.tags.length - 5} more
              </span>
            )}
          </div>
        )}
      </div>

      {/* Footer Row: Source Attribution & Reader CTA */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs mt-2">
        <div className="flex items-center space-x-2 text-slate-400">
          <span className="capitalize font-medium text-slate-500">
            Source: {judgment.source || 'Indian Kanoon'}
          </span>
          {isSearchRanked && (
            <span
              className="inline-flex items-center text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-mono"
              title={`RRF Score: ${searchItem.score.toFixed(4)}`}
            >
              <Sparkles className="h-2.5 w-2.5 mr-1" />
              Score: {searchItem.score.toFixed(3)}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => onSelectJudgment(judgment)}
          className="inline-flex items-center space-x-1 font-semibold text-amber-700 hover:text-amber-800 transition"
        >
          <BookOpen className="h-3.5 w-3.5" />
          <span>Read Judgment</span>
        </button>
      </div>
    </div>
  );
};
