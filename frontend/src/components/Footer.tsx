import React from 'react';
import { Scale, ExternalLink, ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 text-xs py-10 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand Col */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center space-x-2 text-white font-bold text-base">
              <div className="h-8 w-8 rounded bg-amber-500/20 border border-amber-400/30 flex items-center justify-center text-amber-400">
                <Scale className="h-5 w-5" />
              </div>
              <span>India Legal News Aggregator</span>
            </div>
            <p className="text-slate-400 text-xs leading-relaxed max-w-md">
              Comprehensive Indian legal news and court judgment aggregator. Providing daily updates,
              headnotes, and smart search across the Supreme Court of India, High Courts, and Tribunals.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-400">
              <span>Supreme Court & High Courts</span>
              <span>•</span>
              <span>Daily Precedents</span>
              <span>•</span>
              <span>Verified Sources</span>
            </div>
          </div>

          {/* Sources Attribution */}
          <div className="space-y-2">
            <h4 className="text-white font-semibold text-xs uppercase tracking-wider">
              Legal Content Sources
            </h4>
            <ul className="space-y-1.5 text-slate-400">
              <li>
                <a
                  href="https://indiankanoon.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-amber-400 transition flex items-center space-x-1"
                >
                  <span>Indian Kanoon</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://main.sci.gov.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-amber-400 transition flex items-center space-x-1"
                >
                  <span>Supreme Court of India</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.livelaw.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-amber-400 transition flex items-center space-x-1"
                >
                  <span>LiveLaw News & Feeds</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.barandbench.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-amber-400 transition flex items-center space-x-1"
                >
                  <span>Bar & Bench</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Disclaimer & Transparency */}
          <div className="space-y-2">
            <h4 className="text-white font-semibold text-xs uppercase tracking-wider">
              Legal Disclaimer
            </h4>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              This platform indexes publicly available legal news and judgments for academic,
              professional research, and informational purposes. It does not constitute formal legal
              advice.
            </p>
            <div className="pt-2 flex items-center space-x-1 text-[11px] text-amber-400/80">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Updated Daily • Free & Open Access</span>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 gap-2">
          <p>© {new Date().getFullYear()} India Legal News Aggregator. Built with precision for the Indian Bar & Judiciary.</p>
          <div className="flex items-center space-x-4">
            <span>v2.0 Master Execution Plan</span>
            <button
              type="button"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="text-slate-400 hover:text-white transition"
            >
              Back to Top ↑
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
};
