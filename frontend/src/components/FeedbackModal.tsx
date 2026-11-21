import React, { useEffect, useState } from 'react';
import {
  Star,
  MessageSquareHeart,
  X,
  Send,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultTab?: 'form' | 'reviews';
}

const RATING_LABELS: Record<number, string> = {
  1: 'Poor — Needs significant improvement',
  2: 'Fair — Has potential but needs work',
  3: 'Good — Useful for legal research',
  4: 'Very Good — Smooth and helpful experience',
  5: 'Excellent — Outstanding legal research tool!',
};

const CATEGORIES = [
  { id: 'general', label: 'General' },
  { id: 'feature', label: 'Feature Request' },
  { id: 'bug', label: 'Bug Report' },
  { id: 'content', label: 'Legal Accuracy' },
];

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { user } = useAuth();

  // Form states
  const [rating, setRating] = useState<number>(5);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [category, setCategory] = useState<string>('general');
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitSuccess, setSubmitSuccess] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Auto-fill user email if authenticated
  useEffect(() => {
    if (user?.email) {
      setEmail((prev) => prev || user.email);
    }
  }, [user?.email]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const currentDisplayRating = hoverRating !== null ? hoverRating : rating;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!rating || rating < 1 || rating > 5) {
      setErrorMessage('Please select a star rating between 1 and 5.');
      return;
    }

    if (!feedbackText.trim() || feedbackText.trim().length < 2) {
      setErrorMessage('Please share a few words in your feedback.');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.feedback.submit({
        rating,
        feedback_text: feedbackText.trim(),
        email: email.trim() || undefined,
        category,
      });

      setSubmitSuccess(true);
      // Reset form
      setFeedbackText('');
      setRating(5);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Failed to submit feedback. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetForAnother = () => {
    setSubmitSuccess(false);
    setErrorMessage(null);
    setFeedbackText('');
    setRating(5);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="feedback-modal-title"
    >
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-amber-500/20 border border-amber-400/30 flex items-center justify-center text-amber-400">
              <Star className="h-5 w-5 fill-amber-400/40" />
            </div>
            <div>
              <h2
                id="feedback-modal-title"
                className="text-base sm:text-lg font-bold text-white tracking-tight"
              >
                Feedback & Reviews
              </h2>
              <p className="text-xs text-slate-400">
                Help improve India Legal Aggregator
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body - Strictly Private Submission Form */}
        <div className="overflow-y-auto px-5 sm:px-6 py-5 space-y-4">
          {submitSuccess ? (
            /* Success Screen */
            <div className="py-8 text-center space-y-4 animate-fade-in">
              <div className="h-16 w-16 mx-auto rounded-full bg-emerald-500/20 border border-emerald-400/30 flex items-center justify-center text-emerald-400">
                <CheckCircle2 className="h-10 w-10" />
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-white">Thank You!</h3>
                <p className="text-xs sm:text-sm text-slate-300 max-w-sm mx-auto leading-relaxed">
                  Your feedback has been successfully recorded in the database. We read every review to continuously improve the platform.
                </p>
              </div>
              <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={handleResetForAnother}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 text-xs font-semibold transition"
                >
                  Submit Another Review
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-slate-950 text-xs font-bold transition shadow"
                >
                  Close
                </button>
              </div>
            </div>
          ) : (
            /* Form */
            <form onSubmit={handleSubmit} className="space-y-4">
              {errorMessage && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center space-x-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Star Rating Section */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300">
                  How was your experience? <span className="text-amber-400">*</span>
                </label>
                <div className="flex items-center space-x-1.5 sm:space-x-2">
                  {[1, 2, 3, 4, 5].map((starVal) => {
                    const isFilled = starVal <= currentDisplayRating;
                    return (
                      <button
                        key={starVal}
                        type="button"
                        onClick={() => setRating(starVal)}
                        onMouseEnter={() => setHoverRating(starVal)}
                        onMouseLeave={() => setHoverRating(null)}
                        className="p-1 rounded-lg text-slate-500 hover:text-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-400/50 transition transform hover:scale-110 active:scale-95"
                        aria-label={`Rate ${starVal} out of 5 stars`}
                      >
                        <Star
                          className={`h-7 w-7 sm:h-8 sm:w-8 transition ${
                            isFilled
                              ? 'text-amber-400 fill-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.5)]'
                              : 'text-slate-600 hover:text-amber-300/50'
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>
                <p className="text-[11px] font-medium text-amber-300/90 h-4">
                  {RATING_LABELS[currentDisplayRating] || ''}
                </p>
              </div>

              {/* Category Selection */}
              <div className="space-y-1.5 pt-1">
                <label className="block text-xs font-semibold text-slate-300">
                  Feedback Category
                </label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map((cat) => {
                    const isSelected = category === cat.id;
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => setCategory(cat.id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                          isSelected
                            ? 'bg-amber-500/20 border-amber-400/50 text-amber-300'
                            : 'bg-slate-800/60 border-slate-700/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                        }`}
                      >
                        {cat.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Feedback Textarea */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="feedback-text"
                    className="block text-xs font-semibold text-slate-300"
                  >
                    Your Feedback / Review <span className="text-amber-400">*</span>
                  </label>
                  <span className="text-[10px] text-slate-500">
                    {feedbackText.length} / 2000
                  </span>
                </div>
                <textarea
                  id="feedback-text"
                  rows={4}
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  maxLength={2000}
                  placeholder="Tell us what you like, report an issue, or suggest features..."
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-100 placeholder-slate-500 text-xs sm:text-sm focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition resize-none"
                />
              </div>

              {/* Optional Email */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="feedback-email"
                    className="block text-xs font-semibold text-slate-300"
                  >
                    Email Address <span className="text-slate-500 font-normal">(Optional)</span>
                  </label>
                  {user && (
                    <span className="text-[10px] text-emerald-400">
                      Logged in as {user.email}
                    </span>
                  )}
                </div>
                <input
                  id="feedback-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com (if you'd like a response)"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-100 placeholder-slate-500 text-xs sm:text-sm focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition"
                />
                <p className="text-[10px] text-slate-500">
                  We will never share your email. Used only if we need clarification or to follow up.
                </p>
              </div>

              {/* Submit Action */}
              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 text-xs font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !feedbackText.trim()}
                  className="px-5 py-2.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs transition shadow flex items-center space-x-2 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <Send className="h-3.5 w-3.5" />
                      <span>Send Feedback</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

interface FloatingFeedbackButtonProps {
  onClick: () => void;
}

export const FloatingFeedbackButton: React.FC<FloatingFeedbackButtonProps> = ({
  onClick,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Give feedback"
      className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-40 flex items-center space-x-2 px-3.5 py-2.5 bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-400 hover:to-amber-300 text-slate-950 font-bold text-xs rounded-full shadow-lg hover:shadow-amber-500/20 hover:scale-105 active:scale-95 transition duration-200 border border-amber-300/40 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-900 group"
    >
      <div className="relative">
        <MessageSquareHeart className="h-4 w-4 text-slate-950" />
        <span className="absolute -top-1 -right-1 flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-900 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-950"></span>
        </span>
      </div>
      <span className="tracking-wide">Feedback</span>
    </button>
  );
};
