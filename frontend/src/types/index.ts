/**
 * TypeScript Interfaces for India Legal News Aggregator
 * Aligned with FastAPI backend schemas (v2.0)
 */

export type ContentType = 'judgment' | 'news' | 'unknown';

export interface Party {
  role: string;
  name: string;
}

export interface Judgment {
  id: string;
  external_id: string;
  title: string;
  short_title: string | null;
  court_code: string;
  court_name: string;
  court_level: number; // 1 = Supreme Court, 2 = High Court, 3 = Tribunal
  judgment_date: string; // YYYY-MM-DD
  subject_category: string;
  excerpt: string;
  summary?: string;
  full_text: string | null;
  url: string;
  parties: Party[] | Record<string, unknown>[];
  tags: string[];
  source: string;
  is_archived: boolean;
  classification_confidence: number;
  content_type?: ContentType;
  content_type_confidence?: number;
  created_at: string;
  updated_at: string;
}

export type JudgmentItem = Judgment;

export interface SearchResultItem extends Judgment {
  score: number;
  keyword_rank: number | null;
  semantic_rank: number | null;
  content_type?: ContentType;
  content_type_confidence?: number;
}

export interface SearchResponse {
  results: SearchResultItem[];
  query_type: 'hybrid' | 'keyword' | 'semantic';
  matched_terms: string[];
  total: number;
}

export interface JudgmentListResponse {
  data: Judgment[];
  items?: Judgment[];
  total: number;
  limit: number;
  offset: number;
}

export interface LegalCategoryItem {
  id: string;
  name: string;
  description: string;
}

export interface CourtItem {
  code: string;
  name: string;
  level: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Bookmark {
  id: string;
  user_id: string;
  judgment_id: string;
  notes?: string | null;
  tags: string[];
  created_at: string;
  judgment?: Judgment | null;
}

export interface BookmarkListResponse {
  data: Bookmark[];
  total: number;
  limit: number;
  offset: number;
}

export interface Alert {
  id: string;
  user_id: string;
  title: string;
  category?: string | null;
  court_code?: string | null;
  keywords: string[];
  query?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertMatchItem {
  alert_id: string;
  alert_title: string;
  matched_keywords: string[];
  judgment: Judgment;
}

export interface AlertMatchesResponse {
  matches: AlertMatchItem[];
  total: number;
}

export interface Topic {
  id: string;
  user_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  judgment_count: number;
}

export type SearchMode = 'hybrid' | 'keyword' | 'semantic';

export interface JudgmentQueryParams {
  category?: string;
  court?: string;
  content_type?: ContentType | 'all';
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface SearchQueryParams {
  q: string;
  mode?: SearchMode;
  category?: string;
  court?: string;
  content_type?: ContentType | 'all';
  limit?: number;
  offset?: number;
}

export interface FilterState {
  q: string;
  mode: SearchMode;
  category: string;
  court: string;
  content_type?: ContentType;
  date_from: string;
  date_to: string;
  page: number;
  limit: number;
}

export interface Feedback {
  id: string;
  rating: number;
  feedback_text: string;
  email?: string | null;
  category: string;
  user_id?: string | null;
  created_at: string;
}

export interface FeedbackCreate {
  rating: number;
  feedback_text: string;
  email?: string;
  category?: string;
}

export interface FeedbackStats {
  total_count: number;
  average_rating: number;
  rating_distribution: Record<string, number>;
}

export interface FeedbackListResponse {
  data: Feedback[];
  total: number;
  stats: FeedbackStats;
}

