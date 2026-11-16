import React, { useEffect, useState } from 'react';
import {
  X,
  Bookmark as BookmarkIcon,
  Bell,
  Plus,
  Trash2,
  BookOpen,
  Tag,
  Sparkles,
  Layers,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Alert,
  AlertMatchItem,
  Bookmark,
  CourtItem,
  Judgment,
  LegalCategoryItem,
  Topic,
} from '../types';
import { CANONICAL_CATEGORIES } from './SearchAndFilters';
import { formatJudgmentDate } from './JudgmentCard';

interface BookmarksAndAlertsModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultTab?: 'bookmarks' | 'alerts' | 'matches' | 'topics';
  onSelectJudgment: (judgment: Judgment) => void;
  courts: CourtItem[];
  categories: LegalCategoryItem[];
  onOpenAuth: () => void;
}

export const BookmarksAndAlertsModal: React.FC<BookmarksAndAlertsModalProps> = ({
  isOpen,
  onClose,
  defaultTab = 'bookmarks',
  onSelectJudgment,
  courts,
  onOpenAuth,
}) => {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<'bookmarks' | 'alerts' | 'matches' | 'topics'>(defaultTab);

  // Bookmarks State
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [isLoadingBookmarks, setIsLoadingBookmarks] = useState(false);

  // Alerts State
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);
  const [showNewAlertForm, setShowNewAlertForm] = useState(false);
  const [newAlertTitle, setNewAlertTitle] = useState('');
  const [newAlertCategory, setNewAlertCategory] = useState('');
  const [newAlertCourt, setNewAlertCourt] = useState('');
  const [newAlertKeywords, setNewAlertKeywords] = useState('');
  const [newAlertQuery, setNewAlertQuery] = useState('');
  const [isSubmittingAlert, setIsSubmittingAlert] = useState(false);

  // Alert Matches State
  const [matches, setMatches] = useState<AlertMatchItem[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);

  // Topics State
  const [topics, setTopics] = useState<Topic[]>([]);
  const [isLoadingTopics, setIsLoadingTopics] = useState(false);
  const [showNewTopicForm, setShowNewTopicForm] = useState(false);
  const [newTopicName, setNewTopicName] = useState('');
  const [newTopicDesc, setNewTopicDesc] = useState('');
  const [isSubmittingTopic, setIsSubmittingTopic] = useState(false);

  // Synchronize defaultTab when modal opens
  useEffect(() => {
    if (isOpen && defaultTab) {
      setActiveTab(defaultTab);
    }
  }, [isOpen, defaultTab]);

  // Load data based on active tab and authentication
  useEffect(() => {
    if (!isOpen || !isAuthenticated) return;

    if (activeTab === 'bookmarks') {
      loadBookmarks();
    } else if (activeTab === 'alerts') {
      loadAlerts();
    } else if (activeTab === 'matches') {
      loadMatches();
    } else if (activeTab === 'topics') {
      loadTopics();
    }
  }, [isOpen, activeTab, isAuthenticated]);

  const loadBookmarks = async () => {
    setIsLoadingBookmarks(true);
    try {
      const res = await api.bookmarks.list({ limit: 50 });
      setBookmarks(res.data);
    } catch (err) {
      console.warn('Failed to load bookmarks:', err);
    } finally {
      setIsLoadingBookmarks(false);
    }
  };

  const loadAlerts = async () => {
    setIsLoadingAlerts(true);
    try {
      const res = await api.alerts.list();
      setAlerts(res.data);
    } catch (err) {
      console.warn('Failed to load alerts:', err);
    } finally {
      setIsLoadingAlerts(false);
    }
  };

  const loadMatches = async () => {
    setIsLoadingMatches(true);
    try {
      const res = await api.alerts.matches({ limit: 50 });
      setMatches(res.matches);
    } catch (err) {
      console.warn('Failed to load alert matches:', err);
    } finally {
      setIsLoadingMatches(false);
    }
  };

  const loadTopics = async () => {
    setIsLoadingTopics(true);
    try {
      const res = await api.topics.list();
      setTopics(res.data);
    } catch (err) {
      console.warn('Failed to load topics:', err);
    } finally {
      setIsLoadingTopics(false);
    }
  };

  const handleDeleteBookmark = async (judgmentId: string) => {
    try {
      await api.bookmarks.remove(judgmentId);
      setBookmarks((prev) => prev.filter((b) => b.judgment_id !== judgmentId));
    } catch (err) {
      console.error('Failed to remove bookmark:', err);
    }
  };

  const handleCreateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAlertTitle.trim()) return;

    setIsSubmittingAlert(true);
    try {
      const kwList = newAlertKeywords
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean);

      const created = await api.alerts.create({
        title: newAlertTitle.trim(),
        category: newAlertCategory || undefined,
        court_code: newAlertCourt || undefined,
        keywords: kwList,
        query: newAlertQuery.trim() || undefined,
        is_active: true,
      });

      setAlerts((prev) => [created, ...prev]);
      setShowNewAlertForm(false);
      setNewAlertTitle('');
      setNewAlertCategory('');
      setNewAlertCourt('');
      setNewAlertKeywords('');
      setNewAlertQuery('');
    } catch (err) {
      console.error('Failed to create alert:', err);
    } finally {
      setIsSubmittingAlert(false);
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    try {
      await api.alerts.delete(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (err) {
      console.error('Failed to delete alert:', err);
    }
  };

  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopicName.trim()) return;

    setIsSubmittingTopic(true);
    try {
      const created = await api.topics.create({
        name: newTopicName.trim(),
        description: newTopicDesc.trim() || undefined,
      });

      setTopics((prev) => [created, ...prev]);
      setShowNewTopicForm(false);
      setNewTopicName('');
      setNewTopicDesc('');
    } catch (err) {
      console.error('Failed to create topic:', err);
    } finally {
      setIsSubmittingTopic(false);
    }
  };

  const handleDeleteTopic = async (topicId: string) => {
    try {
      await api.topics.delete(topicId);
      setTopics((prev) => prev.filter((t) => t.id !== topicId));
    } catch (err) {
      console.error('Failed to delete topic:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-fadeIn">
      <div
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden relative"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dashboard-title"
      >
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <h2 id="dashboard-title" className="text-lg font-bold text-slate-900">
              My Saved Cases & Alerts
            </h2>
            <p className="text-xs text-slate-500">
              Manage saved judgments, custom topic alerts, and research folders
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-white px-6 text-xs font-semibold overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('bookmarks')}
            className={`py-3 flex items-center space-x-1.5 border-b-2 transition mr-4 whitespace-nowrap shrink-0 ${
              activeTab === 'bookmarks'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <BookmarkIcon className="h-4 w-4 text-amber-500" />
            <span>Bookmarks ({bookmarks.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('matches')}
            className={`py-3 flex items-center space-x-1.5 border-b-2 transition mr-4 whitespace-nowrap shrink-0 ${
              activeTab === 'matches'
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Sparkles className="h-4 w-4 text-indigo-500" />
            <span>Alert Updates ({matches.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('alerts')}
            className={`py-3 flex items-center space-x-1.5 border-b-2 transition mr-4 whitespace-nowrap shrink-0 ${
              activeTab === 'alerts'
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Bell className="h-4 w-4 text-indigo-500" />
            <span>Custom Alerts ({alerts.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('topics')}
            className={`py-3 flex items-center space-x-1.5 border-b-2 transition whitespace-nowrap shrink-0 ${
              activeTab === 'topics'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Layers className="h-4 w-4 text-emerald-500" />
            <span>Research Folders ({topics.length})</span>
          </button>
        </div>

        {/* Content Area */}
        <div className="overflow-y-auto p-6 flex-1">
          {!isAuthenticated ? (
            <div className="text-center py-12 space-y-4">
              <div className="h-12 w-12 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto">
                <BookmarkIcon className="h-6 w-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Sign in to Access Your Legal Workspace
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Save legal precedents with custom notes, configure automated statutory alerts,
                and organize cases into research folders.
              </p>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onOpenAuth();
                }}
                className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition"
              >
                Sign In / Register
              </button>
            </div>
          ) : (
            <>
              {/* TAB 1: BOOKMARKS */}
              {activeTab === 'bookmarks' && (
                <div className="space-y-4">
                  {isLoadingBookmarks ? (
                    <div className="text-center py-10 text-xs text-slate-400">
                      Loading saved bookmarks...
                    </div>
                  ) : bookmarks.length === 0 ? (
                    <div className="text-center py-12 text-slate-500 space-y-2">
                      <BookmarkIcon className="h-8 w-8 text-slate-300 mx-auto" />
                      <p className="text-sm font-medium">No saved bookmarks yet.</p>
                      <p className="text-xs text-slate-400">
                        Click the bookmark icon on any judgment to save it for quick reference.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {bookmarks.map((b) => (
                        <div
                          key={b.id}
                          className="p-4 bg-slate-50 hover:bg-amber-50/50 border border-slate-200 rounded-xl transition flex flex-col justify-between"
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div>
                              <div className="flex items-center space-x-2 text-xs mb-1">
                                <span className="font-semibold text-slate-700">
                                  {b.judgment?.court_name || 'Court'}
                                </span>
                                <span className="text-slate-400">•</span>
                                <span className="text-slate-500">
                                  {b.judgment
                                    ? formatJudgmentDate(b.judgment.judgment_date)
                                    : ''}
                                </span>
                                {b.judgment?.subject_category && (
                                  <span className="bg-amber-100 text-amber-800 px-2 py-0.2 rounded text-[10px] font-semibold">
                                    {b.judgment.subject_category}
                                  </span>
                                )}
                              </div>
                              <h4
                                onClick={() => b.judgment && onSelectJudgment(b.judgment)}
                                className="text-sm font-bold text-slate-900 hover:text-amber-700 transition cursor-pointer"
                              >
                                {b.judgment?.title || 'Saved Legal Record'}
                              </h4>
                            </div>

                            <button
                              type="button"
                              onClick={() => handleDeleteBookmark(b.judgment_id)}
                              title="Delete bookmark"
                              className="p-1.5 text-slate-400 hover:text-rose-600 transition"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>

                          {/* Notes if any */}
                          {b.notes && (
                            <p className="text-xs text-slate-600 bg-white p-2 rounded-lg border border-slate-200 my-2 italic">
                              <strong>Note:</strong> {b.notes}
                            </p>
                          )}

                          {/* Tags if any */}
                          {b.tags && b.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {b.tags.map((tag, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center text-[10px] bg-slate-200/80 text-slate-700 px-2 py-0.5 rounded"
                                >
                                  <Tag className="h-2.5 w-2.5 mr-1" />
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="flex items-center justify-between pt-2 border-t border-slate-200 text-xs mt-2">
                            <span className="text-[11px] text-slate-400">
                              Saved on {formatJudgmentDate(b.created_at)}
                            </span>
                            {b.judgment && (
                              <button
                                type="button"
                                onClick={() => onSelectJudgment(b.judgment!)}
                                className="font-semibold text-amber-700 hover:underline flex items-center space-x-1"
                              >
                                <BookOpen className="h-3.5 w-3.5" />
                                <span>Open Reader</span>
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: STATUTE ALERTS */}
              {activeTab === 'alerts' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-500">
                      Receive notifications when fresh judgments match your statutory sections or domains.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowNewAlertForm(!showNewAlertForm)}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition flex items-center space-x-1"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>{showNewAlertForm ? 'Cancel' : 'New Alert'}</span>
                    </button>
                  </div>

                  {/* Create New Alert Form */}
                  {showNewAlertForm && (
                    <form
                      onSubmit={handleCreateAlert}
                      className="bg-indigo-50/50 border border-indigo-200 rounded-xl p-4 space-y-3"
                    >
                      <h4 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">
                        Create New Alert
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-slate-700 mb-1">
                            Alert Title *
                          </label>
                          <input
                            type="text"
                            required
                            value={newAlertTitle}
                            onChange={(e) => setNewAlertTitle(e.target.value)}
                            placeholder="e.g., Anticipatory Bail Tracker"
                            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white min-h-[40px]"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-slate-700 mb-1">
                            Legal Category
                          </label>
                          <select
                            value={newAlertCategory}
                            onChange={(e) => setNewAlertCategory(e.target.value)}
                            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white min-h-[40px]"
                          >
                            <option value="">Any Legal Category</option>
                            {CANONICAL_CATEGORIES.map((cat) => (
                              <option key={cat} value={cat}>
                                {cat}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-slate-700 mb-1">
                            Court
                          </label>
                          <select
                            value={newAlertCourt}
                            onChange={(e) => setNewAlertCourt(e.target.value)}
                            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white min-h-[40px]"
                          >
                            <option value="">All Indian Courts</option>
                            {courts.map((court) => (
                              <option key={court.code} value={court.code}>
                                {court.name}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-slate-700 mb-1">
                            Key Terms or Sections (Comma separated)
                          </label>
                          <input
                            type="text"
                            value={newAlertKeywords}
                            onChange={(e) => setNewAlertKeywords(e.target.value)}
                            placeholder="e.g., Section 438 CrPC, Article 21, IBC Section 9"
                            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white min-h-[40px]"
                          />
                        </div>
                      </div>

                      <div className="flex justify-end pt-2">
                        <button
                          type="submit"
                          disabled={isSubmittingAlert}
                          className="px-4 py-2 min-h-[40px] bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition"
                        >
                          {isSubmittingAlert ? 'Saving...' : 'Save Alert'}
                        </button>
                      </div>
                    </form>
                  )}

                  {/* List of active alerts */}
                  {isLoadingAlerts ? (
                    <div className="text-center py-8 text-xs text-slate-400">Loading alerts...</div>
                  ) : alerts.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs bg-slate-50 rounded-xl">
                      No active alerts. Create an alert above to receive notifications when new judgments match your interests.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {alerts.map((alt) => (
                        <div
                          key={alt.id}
                          className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between"
                        >
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-bold text-slate-900">{alt.title}</span>
                              {alt.category && (
                                <span className="bg-amber-100 text-amber-800 text-[10px] px-1.5 py-0.2 rounded font-medium">
                                  {alt.category}
                                </span>
                              )}
                              {alt.court_code && (
                                <span className="bg-blue-100 text-blue-800 text-[10px] px-1.5 py-0.2 rounded font-medium uppercase">
                                  {alt.court_code}
                                </span>
                              )}
                            </div>
                            {alt.keywords && alt.keywords.length > 0 && (
                              <p className="text-[11px] text-slate-500 mt-0.5">
                                Keywords: {alt.keywords.join(', ')}
                              </p>
                            )}
                          </div>

                          <button
                            type="button"
                            onClick={() => handleDeleteAlert(alt.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 transition"
                            title="Delete alert"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: ALERT MATCHES FEED */}
              {activeTab === 'matches' && (
                <div className="space-y-4">
                  <p className="text-xs text-slate-500">
                    Recent judgments matching your active statutory sections and research alerts.
                  </p>

                  {isLoadingMatches ? (
                    <div className="text-center py-8 text-xs text-slate-400">
                      Scanning recent judgments against your alerts...
                    </div>
                  ) : matches.length === 0 ? (
                    <div className="text-center py-10 text-slate-500 text-xs bg-slate-50 rounded-xl space-y-1">
                      <Sparkles className="h-6 w-6 text-slate-300 mx-auto mb-2" />
                      <p className="font-semibold text-slate-700">No recent alert matches found.</p>
                      <p className="text-slate-400">
                        Ensure you have created active alerts under the Statute Alerts tab.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {matches.map((item, idx) => (
                        <div
                          key={idx}
                          className="p-4 bg-slate-50 hover:bg-indigo-50/40 border border-slate-200 rounded-xl transition"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full flex items-center space-x-1">
                              <Bell className="h-3 w-3" />
                              <span>Matched: {item.alert_title}</span>
                            </span>
                            <span className="text-[11px] text-slate-500">
                              {formatJudgmentDate(item.judgment.judgment_date)}
                            </span>
                          </div>

                          <h4
                            onClick={() => onSelectJudgment(item.judgment)}
                            className="text-sm font-bold text-slate-900 hover:text-indigo-700 transition cursor-pointer mb-1"
                          >
                            {item.judgment.title}
                          </h4>

                          <p className="text-xs text-slate-600 line-clamp-2 mb-2">
                            {item.judgment.excerpt}
                          </p>

                          {/* Matched Keywords Badges */}
                          {item.matched_keywords && item.matched_keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-2">
                              {item.matched_keywords.map((kw, kIdx) => (
                                <span
                                  key={kIdx}
                                  className="text-[10px] font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-300"
                                >
                                  ✓ {kw}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="flex justify-end">
                            <button
                              type="button"
                              onClick={() => onSelectJudgment(item.judgment)}
                              className="text-xs font-semibold text-indigo-700 hover:underline flex items-center space-x-1"
                            >
                              <BookOpen className="h-3.5 w-3.5" />
                              <span>Read Judgment</span>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: RESEARCH FOLDERS */}
              {activeTab === 'topics' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-500">
                      Organize judgments into dedicated case folders and legal research lists.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowNewTopicForm(!showNewTopicForm)}
                      className="px-3 py-2 min-h-[40px] bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition flex items-center space-x-1"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>{showNewTopicForm ? 'Cancel' : 'New Folder'}</span>
                    </button>
                  </div>

                  {showNewTopicForm && (
                    <form
                      onSubmit={handleCreateTopic}
                      className="bg-emerald-50/50 border border-emerald-200 rounded-xl p-4 space-y-3"
                    >
                      <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wider">
                        Create New Research Folder
                      </h4>
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">
                          Folder Name *
                        </label>
                        <input
                          type="text"
                          required
                          value={newTopicName}
                          onChange={(e) => setNewTopicName(e.target.value)}
                          placeholder="e.g., Anticipatory Bail Precedents"
                          className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white min-h-[40px]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">
                          Description (Optional)
                        </label>
                        <textarea
                          rows={2}
                          value={newTopicDesc}
                          onChange={(e) => setNewTopicDesc(e.target.value)}
                          placeholder="e.g., Precedents concerning Section 438 CrPC conditions on international travel"
                          className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white"
                        />
                      </div>
                      <div className="flex justify-end pt-1">
                        <button
                          type="submit"
                          disabled={isSubmittingTopic}
                          className="px-4 py-2 min-h-[40px] bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition"
                        >
                          {isSubmittingTopic ? 'Saving...' : 'Save Folder'}
                        </button>
                      </div>
                    </form>
                  )}

                  {isLoadingTopics ? (
                    <div className="text-center py-8 text-xs text-slate-400">Loading folders...</div>
                  ) : topics.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs bg-slate-50 rounded-xl">
                      No research folders yet. Create one to organize related judgments.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {topics.map((t) => (
                        <div
                          key={t.id}
                          className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col justify-between"
                        >
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <h4 className="text-sm font-bold text-slate-900">{t.name}</h4>
                              <button
                                type="button"
                                onClick={() => handleDeleteTopic(t.id)}
                                className="text-slate-400 hover:text-rose-600 transition"
                                title="Delete folder"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                            {t.description && (
                              <p className="text-xs text-slate-600 line-clamp-2 mb-2">
                                {t.description}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-200 mt-2">
                            <span>{t.judgment_count} judgments linked</span>
                            <span>{formatJudgmentDate(t.created_at)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
