import React from 'react';
import {
  Scale,
  Bookmark as BookmarkIcon,
  Bell,
  LogIn,
  LogOut,
  User as UserIcon,
  Search,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  onOpenAuth: () => void;
  onOpenDashboard: (tab?: 'bookmarks' | 'alerts' | 'matches' | 'topics') => void;
  bookmarkCount: number;
  alertMatchCount?: number;
  onScrollToSearch?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenAuth,
  onOpenDashboard,
  bookmarkCount,
  alertMatchCount = 0,
  onScrollToSearch,
}) => {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 bg-slate-900 border-b border-slate-800 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="h-10 w-10 rounded-lg bg-amber-500/20 border border-amber-400/30 flex items-center justify-center text-amber-400">
              <Scale className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">
                  India Legal Aggregator
                </span>
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-400/30">
                  v2.0 RRF
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Hybrid AI Legal Research & Judgment Feed
              </p>
            </div>
          </div>

          {/* Quick Actions & Navigation */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* Scroll to search button */}
            {onScrollToSearch && (
              <button
                type="button"
                onClick={onScrollToSearch}
                className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition"
              >
                <Search className="h-3.5 w-3.5" />
                <span>Search</span>
              </button>
            )}

            {/* Bookmarks / Saved Button */}
            <button
              type="button"
              onClick={() => onOpenDashboard('bookmarks')}
              aria-label="View saved bookmarks"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 hover:text-white bg-slate-800/80 hover:bg-slate-700 transition border border-slate-700 relative"
            >
              <BookmarkIcon className="h-4 w-4 text-amber-400" />
              <span className="hidden sm:inline">Bookmarks</span>
              {bookmarkCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-500 text-slate-950">
                  {bookmarkCount}
                </span>
              )}
            </button>

            {/* Alerts / Matches Button */}
            <button
              type="button"
              onClick={() => onOpenDashboard('matches')}
              aria-label="View personalized alerts and matches"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 hover:text-white bg-slate-800/80 hover:bg-slate-700 transition border border-slate-700 relative"
            >
              <Bell className="h-4 w-4 text-indigo-400" />
              <span className="hidden sm:inline">Alerts</span>
              {alertMatchCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-indigo-500 text-white animate-pulse">
                  {alertMatchCount}
                </span>
              )}
            </button>

            {/* Auth State Button */}
            {isAuthenticated && user ? (
              <div className="flex items-center space-x-2 pl-2 border-l border-slate-700">
                <button
                  type="button"
                  onClick={() => onOpenDashboard('topics')}
                  className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 hover:text-white bg-slate-800 hover:bg-slate-700 transition border border-slate-700"
                >
                  <UserIcon className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="max-w-[120px] truncate">
                    {user.full_name || user.email.split('@')[0]}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={logout}
                  title="Sign out"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800 transition"
                  aria-label="Log out"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={onOpenAuth}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-900 bg-amber-400 hover:bg-amber-300 transition shadow-sm"
              >
                <LogIn className="h-3.5 w-3.5" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
