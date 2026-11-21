import React from 'react';
import {
  Scale,
  Bookmark as BookmarkIcon,
  Bell,
  LogIn,
  LogOut,
  User as UserIcon,
  Search,
  Star,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  onOpenAuth: () => void;
  onOpenDashboard: (tab?: 'bookmarks' | 'alerts' | 'matches' | 'topics') => void;
  onOpenFeedback?: () => void;
  bookmarkCount: number;
  alertMatchCount?: number;
  onScrollToSearch?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenAuth,
  onOpenDashboard,
  onOpenFeedback,
  bookmarkCount,
  alertMatchCount = 0,
  onScrollToSearch,
}) => {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 bg-slate-900 border-b border-slate-800 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-2">
          {/* Logo & Brand Title */}
          <div
            className="flex items-center space-x-2 sm:space-x-3 cursor-pointer min-w-0"
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }
            }}
          >
            <div className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-amber-500/20 border border-amber-400/30 flex items-center justify-center text-amber-400 shrink-0">
              <Scale className="h-5 w-5 sm:h-6 sm:w-6" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-1.5 sm:space-x-2">
                <span className="font-bold text-sm sm:text-base md:text-lg tracking-tight text-white truncate">
                  India Legal Aggregator
                </span>
                <span className="hidden md:inline-flex text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-400/30 shrink-0">
                  Live Feed
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden lg:block truncate">
                Smart Legal Research & Daily Court Updates
              </p>
            </div>
          </div>

          {/* Quick Actions & Navigation Buttons (Single-row, no wrapping on mobile) */}
          <div className="flex items-center space-x-1 sm:space-x-2 shrink-0">
            {/* Scroll to Search Button (Desktop) */}
            {onScrollToSearch && (
              <button
                type="button"
                onClick={onScrollToSearch}
                className="hidden md:flex items-center space-x-1.5 px-3 py-2 min-h-[44px] rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition"
              >
                <Search className="h-3.5 w-3.5" />
                <span>Search</span>
              </button>
            )}

            {/* Bookmarks Button */}
            <button
              type="button"
              onClick={() => onOpenDashboard('bookmarks')}
              aria-label="View saved bookmarks"
              className="flex items-center justify-center space-x-1 sm:space-x-1.5 px-2.5 sm:px-3 py-2 min-h-[44px] min-w-[44px] rounded-xl text-xs font-medium text-slate-200 hover:text-white bg-slate-800/80 hover:bg-slate-700 transition border border-slate-700 relative"
            >
              <BookmarkIcon className="h-4 w-4 text-amber-400" />
              <span className="hidden sm:inline">Bookmarks</span>
              {bookmarkCount > 0 && (
                <span className="ml-0.5 sm:ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-500 text-slate-950">
                  {bookmarkCount}
                </span>
              )}
            </button>

            {/* Alerts Button */}
            <button
              type="button"
              onClick={() => onOpenDashboard('matches')}
              aria-label="View personalized alerts and matches"
              className="flex items-center justify-center space-x-1 sm:space-x-1.5 px-2.5 sm:px-3 py-2 min-h-[44px] min-w-[44px] rounded-xl text-xs font-medium text-slate-200 hover:text-white bg-slate-800/80 hover:bg-slate-700 transition border border-slate-700 relative"
            >
              <Bell className="h-4 w-4 text-indigo-400" />
              <span className="hidden sm:inline">Alerts</span>
              {alertMatchCount > 0 && (
                <span className="ml-0.5 sm:ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-indigo-500 text-white animate-pulse">
                  {alertMatchCount}
                </span>
              )}
            </button>

            {/* Feedback Trigger Button */}
            {onOpenFeedback && (
              <button
                type="button"
                onClick={onOpenFeedback}
                aria-label="Submit feedback or review"
                className="hidden lg:flex items-center space-x-1.5 px-3 py-2 min-h-[44px] rounded-xl text-xs font-semibold text-amber-300 hover:text-amber-200 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-400/30 transition shadow-sm"
              >
                <Star className="h-3.5 w-3.5 fill-amber-400/40 text-amber-400" />
                <span>Feedback</span>
              </button>
            )}

            {/* Auth State Button */}
            {isAuthenticated && user ? (
              <div className="flex items-center space-x-1 sm:space-x-1.5 pl-1 sm:pl-2 border-l border-slate-700">
                <button
                  type="button"
                  onClick={() => onOpenDashboard('topics')}
                  className="flex items-center space-x-1.5 px-2.5 sm:px-3 py-2 min-h-[44px] rounded-xl text-xs font-medium text-slate-200 hover:text-white bg-slate-800 hover:bg-slate-700 transition border border-slate-700"
                  title="Open user workspace"
                >
                  <UserIcon className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span className="max-w-[70px] sm:max-w-[120px] truncate hidden sm:inline">
                    {user.full_name || user.email.split('@')[0]}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={logout}
                  title="Sign out"
                  className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl text-slate-400 hover:text-red-400 hover:bg-slate-800 transition"
                  aria-label="Log out"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={onOpenAuth}
                className="flex items-center space-x-1.5 px-3 sm:px-3.5 py-2 min-h-[44px] rounded-xl text-xs font-semibold text-slate-900 bg-amber-400 hover:bg-amber-300 transition shadow-sm"
              >
                <LogIn className="h-4 w-4" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
