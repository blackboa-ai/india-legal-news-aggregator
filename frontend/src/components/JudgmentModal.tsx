import React, { useEffect, useState } from 'react';
import {
  X,
  Building,
  Calendar,
  Bookmark as BookmarkIcon,
  ExternalLink,
  Copy,
  Check,
  FolderPlus,
  BookOpen,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import { Judgment, Topic } from '../types';
import {
  getCourtLevelBadge,
  getCategoryColor,
  getContentTypeBadge,
  formatJudgmentDate,
} from './JudgmentCard';

interface JudgmentModalProps {
  judgment: Judgment | null;
  isOpen: boolean;
  onClose: () => void;
  isBookmarked: boolean;
  onToggleBookmark: (judgment: Judgment, notes?: string, tags?: string[]) => void;
  onSelectSimilarJudgment: (judgment: Judgment) => void;
  topics?: Topic[];
  onAddToTopic?: (topicId: string, judgmentId: string) => Promise<void>;
}

/**
 * Normalizes stray single-word or short line breaks from RSS/HTML scraping
 * into clean, readable paragraphs while preserving legitimate list items and multi-line breaks.
 */
export const normalizeReaderText = (rawText: string): string => {
  if (!rawText) return '';
  // Standardize carriage returns to newlines
  const standardized = rawText.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  // Split into structural paragraph chunks separated by 2 or more linebreaks
  const rawParagraphs = standardized.split(/\n{2,}/);

  const cleanedParagraphs = rawParagraphs
    .map((chunk) => {
      const lines = chunk
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);

      let merged = '';
      for (let i = 0; i < lines.length; i++) {
        const currentLine = lines[i];
        if (i === 0) {
          merged = currentLine;
        } else {
          const prevLine = lines[i - 1];
          // Check if current line is a bullet/numbered list item
          const isListItem = /^(\d+[\.\)]|\([a-zA-Z0-9]+\)|[-•*])\s/.test(currentLine);
          // Check if previous line ended with a hyphen indicating a broken word
          const endsWithHyphen = prevLine.endsWith('-') && /^[a-zA-Z]/.test(currentLine);

          if (endsWithHyphen) {
            merged = merged.slice(0, -1) + currentLine;
          } else if (isListItem) {
            merged += '\n' + currentLine;
          } else {
            // Stray scraped line-break or wrapped word: join with space
            merged += ' ' + currentLine;
          }
        }
      }
      return merged;
    })
    .filter(Boolean);

  return cleanedParagraphs.join('\n\n');
};

export const JudgmentModal: React.FC<JudgmentModalProps> = ({
  judgment,
  isOpen,
  onClose,
  isBookmarked,
  onToggleBookmark,
  onSelectSimilarJudgment,
  topics = [],
  onAddToTopic,
}) => {
  const [copied, setCopied] = useState(false);
  const [fontSize, setFontSize] = useState<'normal' | 'large'>('normal');
  const [activeTab, setActiveTab] = useState<'judgment' | 'precedents'>('judgment');
  const [similarJudgments, setSimilarJudgments] = useState<Judgment[]>([]);
  const [isLoadingSimilar, setIsLoadingSimilar] = useState(false);
  const [selectedTopicId, setSelectedTopicId] = useState('');
  const [topicAdding, setTopicAdding] = useState(false);
  const [topicSuccess, setTopicSuccess] = useState(false);

  // Bookmark notes state
  const [showNotesModal, setShowNotesModal] = useState(false);
  const [bookmarkNote, setBookmarkNote] = useState('');
  const [bookmarkTagsInput, setBookmarkTagsInput] = useState('');

  // Fallback to fetch full judgment details if full_text or parties were omitted in list/search
  const [fullJudgment, setFullJudgment] = useState<Judgment | null>(judgment);

  useEffect(() => {
    setFullJudgment(judgment);
    setActiveTab('judgment');
    if (!judgment?.id || !isOpen) return;

    let isMounted = true;
    if (!judgment.full_text) {
      api.judgments
        .getById(judgment.id)
        .then((detail) => {
          if (isMounted && detail) {
            setFullJudgment(detail);
          }
        })
        .catch(() => {});
    }
    return () => {
      isMounted = false;
    };
  }, [judgment, isOpen]);

  // Fetch similar precedents whenever selected judgment changes
  useEffect(() => {
    if (!judgment?.id || !isOpen) return;

    let isMounted = true;
    const fetchSimilar = async () => {
      setIsLoadingSimilar(true);
      try {
        const results = await api.judgments.getSimilar(judgment.id, 5);
        if (isMounted) {
          setSimilarJudgments(results);
        }
      } catch (err) {
        console.warn('Failed to fetch similar precedents:', err);
      } finally {
        if (isMounted) {
          setIsLoadingSimilar(false);
        }
      }
    };

    fetchSimilar();
    return () => {
      isMounted = false;
    };
  }, [judgment?.id, isOpen]);

  // Handle Escape key to close modal
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen || !judgment) return null;

  const activeJudgment = fullJudgment || judgment;
  const courtInfo = getCourtLevelBadge(activeJudgment.court_level, activeJudgment.court_code);
  const contentTypeBadge = getContentTypeBadge(activeJudgment.content_type, activeJudgment.court_code);
  const categoryStyle = getCategoryColor(activeJudgment.subject_category);
  const rawContent = activeJudgment.full_text || activeJudgment.excerpt || '';
  const normalizedContent = normalizeReaderText(rawContent);

  const handleCopyCitation = () => {
    const citationText = `${activeJudgment.short_title || activeJudgment.title} (${activeJudgment.court_name}, ${formatJudgmentDate(activeJudgment.judgment_date)}). Available at: ${activeJudgment.url}`;
    navigator.clipboard.writeText(citationText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveBookmark = () => {
    const tags = bookmarkTagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    onToggleBookmark(activeJudgment, bookmarkNote || undefined, tags.length ? tags : undefined);
    setShowNotesModal(false);
  };

  const handleAddToTopicClick = async () => {
    if (!selectedTopicId || !onAddToTopic) return;
    setTopicAdding(true);
    try {
      await onAddToTopic(selectedTopicId, activeJudgment.id);
      setTopicSuccess(true);
      setTimeout(() => setTopicSuccess(false), 2000);
    } finally {
      setTopicAdding(false);
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex md:items-center md:justify-center items-end p-0 md:p-6 animate-fadeIn"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white w-full h-[92vh] rounded-t-2xl mt-auto md:mt-0 md:h-auto md:max-h-[85vh] md:max-w-2xl md:w-full md:rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden relative"
        role="dialog"
        aria-modal="true"
        aria-labelledby="judgment-title"
      >
        {/* Sticky Top Header Bar */}
        <div className="px-4 py-3 sm:px-6 sm:py-3.5 border-b border-slate-200 bg-white/95 backdrop-blur-sm sticky top-0 z-20 shrink-0 flex items-center justify-between gap-2">
          {/* Left: Court Badge & Date */}
          <div className="flex items-center space-x-2 min-w-0">
            {contentTypeBadge && (
              <span className={contentTypeBadge.badgeClass}>
                {contentTypeBadge.label}
              </span>
            )}
            <span
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold shrink-0 ${courtInfo.badgeClass}`}
            >
              <Building className="h-3.5 w-3.5 mr-1" />
              {courtInfo.label}
            </span>
            <span
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border shrink-0 ${categoryStyle}`}
            >
              {activeJudgment.subject_category}
            </span>
            <span className="text-xs text-slate-500 hidden sm:inline-flex items-center shrink-0">
              <Calendar className="h-3.5 w-3.5 mr-1 text-slate-400" />
              {formatJudgmentDate(activeJudgment.judgment_date)}
            </span>
          </div>

          {/* Right: Font size toggle (desktop) + Prominent 44x44px Close Button */}
          <div className="flex items-center space-x-2 shrink-0">
            <div className="hidden sm:flex items-center space-x-1 border border-slate-200 rounded-xl p-1 bg-slate-50">
              <button
                type="button"
                onClick={() => setFontSize('normal')}
                className={`min-h-[32px] px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                  fontSize === 'normal'
                    ? 'bg-white shadow-sm text-slate-900 font-bold'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
                title="Normal font size"
              >
                A
              </button>
              <button
                type="button"
                onClick={() => setFontSize('large')}
                className={`min-h-[32px] px-2.5 py-1 rounded-lg text-sm font-medium transition ${
                  fontSize === 'large'
                    ? 'bg-white shadow-sm text-slate-900 font-bold'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
                title="Large font size"
              >
                A+
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="min-h-[44px] min-w-[44px] rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition flex items-center justify-center"
              aria-label="Close modal"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs (Full Judgment vs Similar Precedents) */}
        <div className="flex items-center space-x-4 px-4 sm:px-6 border-b border-slate-200 bg-white text-xs font-semibold shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab('judgment')}
            className={`min-h-[44px] flex items-center space-x-1.5 border-b-2 transition ${
              activeTab === 'judgment'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <BookOpen className="h-4 w-4" />
            <span>Full Judgment & Summary</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('precedents')}
            className={`min-h-[44px] flex items-center space-x-1.5 border-b-2 transition ${
              activeTab === 'precedents'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Sparkles className="h-4 w-4 text-amber-500" />
            <span>Similar Precedents ({similarJudgments.length})</span>
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="overflow-y-auto scroll-smooth overscroll-contain p-4 sm:p-6 flex-1 space-y-5">
          {activeTab === 'judgment' ? (
            <>
              {/* Title & Court attribution */}
              <div>
                <h1
                  id="judgment-title"
                  className="text-lg sm:text-xl font-bold text-slate-900 leading-snug mb-1.5"
                >
                  {activeJudgment.title}
                </h1>
                {activeJudgment.short_title && activeJudgment.short_title !== activeJudgment.title && (
                  <p className="text-xs sm:text-sm font-medium text-slate-600 italic mb-1">
                    Case: <cite className="not-italic font-semibold text-slate-700">{activeJudgment.short_title}</cite>
                  </p>
                )}
                <p className="text-xs text-slate-500">
                  <cite className="not-italic font-medium text-slate-700">{activeJudgment.court_name}</cite> • Pronounced on{' '}
                  <time dateTime={activeJudgment.judgment_date}>
                    {formatJudgmentDate(activeJudgment.judgment_date)}
                  </time>
                </p>
              </div>

              {/* Parties if available */}
              {activeJudgment.parties && activeJudgment.parties.length > 0 && (
                <div className="bg-slate-50 rounded-xl p-3 border border-slate-200">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                    Parties to Proceeding
                  </span>
                  <div className="flex flex-wrap gap-2 text-xs text-slate-700">
                    {activeJudgment.parties.map((p, idx) => {
                      const pObj = p as { role?: string; name?: string };
                      return (
                        <span key={idx} className="bg-white px-2.5 py-1 rounded-md border border-slate-200">
                          <strong className="capitalize">{pObj.role || 'Party'}:</strong>{' '}
                          {pObj.name || String(p)}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Statutory Citation Badges */}
              {activeJudgment.tags && activeJudgment.tags.length > 0 && (
                <div>
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                    Statutory Citations & Legal Tags
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {activeJudgment.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-200/80"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Add to Research Topic Folder Selector */}
              {topics.length > 0 && onAddToTopic && (
                <div className="flex flex-wrap items-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs">
                  <FolderPlus className="h-4 w-4 text-indigo-600 shrink-0" />
                  <span className="font-semibold text-slate-700">Save to Research Topic:</span>
                  <select
                    value={selectedTopicId}
                    onChange={(e) => setSelectedTopicId(e.target.value)}
                    className="border border-slate-300 rounded-md px-2 py-1 bg-white text-slate-800 min-h-[36px]"
                  >
                    <option value="">Select Topic Folder...</option>
                    {topics.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} ({t.judgment_count} cases)
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={!selectedTopicId || topicAdding}
                    onClick={handleAddToTopicClick}
                    className="px-3 py-1.5 min-h-[36px] bg-indigo-600 hover:bg-indigo-700 text-white rounded-md font-semibold transition disabled:opacity-50"
                  >
                    {topicSuccess ? 'Saved!' : topicAdding ? 'Adding...' : 'Add'}
                  </button>
                </div>
              )}

              {/* Summary / Key Points (Semantic blockquote for AI extraction & reader focus) */}
              {activeJudgment.excerpt && (
                <blockquote
                  cite={activeJudgment.url || undefined}
                  className="bg-amber-50/60 rounded-xl border border-amber-200/80 p-4"
                >
                  <span className="text-[11px] font-bold text-amber-900 uppercase tracking-wider block mb-1.5">
                    Summary & Key Points
                  </span>
                  <p className="text-xs sm:text-sm text-slate-800 leading-relaxed font-sans">
                    {activeJudgment.excerpt}
                  </p>
                </blockquote>
              )}

              {/* Full Text Reader with Normalized Paragraphs */}
              <div className="space-y-3 pt-2">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Full Judgment & News Text
                </span>

                <div
                  className={`judgment-body text-slate-800 space-y-3 leading-relaxed ${
                    fontSize === 'large' ? 'text-base sm:text-lg' : 'text-sm sm:text-base'
                  }`}
                >
                  {normalizedContent.split('\n\n').map((paragraph, idx) => (
                    <p key={idx} className="leading-relaxed font-sans">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </div>
            </>
          ) : (
            /* Similar Precedents Tab */
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Related Legal Precedents
                </h3>
                <p className="text-xs text-slate-500">
                  Related Indian court judgments on similar legal issues and topics
                </p>
              </div>

              {isLoadingSimilar ? (
                <div className="py-12 text-center text-slate-400 text-sm">
                  <span className="inline-block animate-spin mr-2">⏳</span>
                  Finding related court judgments...
                </div>
              ) : similarJudgments.length === 0 ? (
                <div className="py-8 text-center text-slate-500 text-sm bg-slate-50 rounded-xl">
                  No related judgments found for this case yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {similarJudgments.map((similar) => (
                    <div
                      key={similar.id}
                      onClick={() => {
                        setActiveTab('judgment');
                        onSelectSimilarJudgment(similar);
                      }}
                      className="p-4 bg-slate-50 hover:bg-amber-50/60 border border-slate-200 hover:border-amber-300 rounded-xl cursor-pointer transition flex items-start justify-between group"
                    >
                      <div className="space-y-1.5 flex-1 pr-4">
                        <div className="flex items-center space-x-2 text-xs">
                          <span className="font-semibold text-slate-700">
                            {similar.court_name}
                          </span>
                          <span className="text-slate-400">•</span>
                          <span className="text-slate-500">
                            {formatJudgmentDate(similar.judgment_date)}
                          </span>
                          <span className="text-amber-700 bg-amber-100 px-2 py-0.5 rounded text-[10px] font-semibold">
                            {similar.subject_category}
                          </span>
                        </div>
                        <h4 className="text-sm font-semibold text-slate-900 group-hover:text-amber-700 transition line-clamp-1">
                          {similar.title}
                        </h4>
                        <p className="text-xs text-slate-600 line-clamp-2">
                          {similar.excerpt}
                        </p>
                      </div>
                      <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-amber-600 transition self-center shrink-0" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sticky Bottom Action Bar */}
        <div className="sticky bottom-0 z-20 px-4 py-3 sm:px-6 sm:py-3.5 border-t border-slate-200 bg-white/95 backdrop-blur-sm flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center space-x-2">
            {/* Save/Bookmark Button */}
            <button
              type="button"
              onClick={() => {
                if (isBookmarked) {
                  onToggleBookmark(activeJudgment);
                } else {
                  setShowNotesModal(true);
                }
              }}
              className={`min-h-[44px] px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold flex items-center space-x-2 transition ${
                isBookmarked
                  ? 'bg-amber-100 text-amber-900 border border-amber-300'
                  : 'bg-slate-900 text-white hover:bg-slate-800'
              }`}
            >
              <BookmarkIcon
                className="h-4 w-4"
                fill={isBookmarked ? 'currentColor' : 'none'}
              />
              <span>{isBookmarked ? 'Saved' : 'Bookmark'}</span>
            </button>

            {/* Cite / Copy Citation Button */}
            <button
              type="button"
              onClick={handleCopyCitation}
              title="Copy Citation"
              className="min-h-[44px] px-3.5 py-2 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-100 transition text-xs font-semibold flex items-center space-x-1.5"
            >
              {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
              <span className="hidden sm:inline">{copied ? 'Copied' : 'Cite'}</span>
            </button>
          </div>

          <div className="flex items-center space-x-2">
            {/* Read Original Source Link */}
            {activeJudgment.url && (
              <a
                href={activeJudgment.url}
                target="_blank"
                rel="noopener noreferrer"
                title="Open canonical source page in new tab"
                className="min-h-[44px] px-3.5 sm:px-4 py-2 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300/80 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center space-x-1.5"
              >
                <span>Original Source</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}

            {/* Mobile Font Size Toggle */}
            <div className="flex sm:hidden items-center space-x-1 border border-slate-200 rounded-xl p-1 bg-slate-50 min-h-[44px]">
              <button
                type="button"
                onClick={() => setFontSize('normal')}
                className={`min-h-[36px] px-2 py-1 rounded-lg text-xs font-medium transition ${
                  fontSize === 'normal'
                    ? 'bg-white shadow-sm text-slate-900 font-bold'
                    : 'text-slate-500'
                }`}
              >
                A
              </button>
              <button
                type="button"
                onClick={() => setFontSize('large')}
                className={`min-h-[36px] px-2 py-1 rounded-lg text-xs font-medium transition ${
                  fontSize === 'large'
                    ? 'bg-white shadow-sm text-slate-900 font-bold'
                    : 'text-slate-500'
                }`}
              >
                A+
              </button>
            </div>
          </div>
        </div>

        {/* Save Bookmark with Notes Modal Overlay */}
        {showNotesModal && (
          <div
            onClick={() => setShowNotesModal(false)}
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-30"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4"
            >
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <BookmarkIcon className="h-4 w-4 text-amber-500" />
                <span>Bookmark Judgment</span>
              </h3>
              <p className="text-xs text-slate-500">
                Add private research notes or custom organizational tags.
              </p>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Research Notes (Optional)
                </label>
                <textarea
                  value={bookmarkNote}
                  onChange={(e) => setBookmarkNote(e.target.value)}
                  placeholder="e.g., Key precedent for Section 438 CrPC anticipatory bail guidelines..."
                  rows={3}
                  className="w-full text-sm p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Tags (Comma separated)
                </label>
                <input
                  type="text"
                  value={bookmarkTagsInput}
                  onChange={(e) => setBookmarkTagsInput(e.target.value)}
                  placeholder="e.g., bail, client-matter, high-priority"
                  className="w-full text-sm min-h-[44px] px-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>
              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNotesModal(false)}
                  className="px-4 py-2 min-h-[44px] text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveBookmark}
                  className="px-5 py-2 min-h-[44px] text-xs bg-amber-600 hover:bg-amber-700 text-white rounded-xl font-semibold shadow-sm"
                >
                  Save Bookmark
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
