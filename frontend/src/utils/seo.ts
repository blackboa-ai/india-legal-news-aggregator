export interface SEOConfig {
  title?: string;
  description?: string;
  canonicalUrl?: string;
  ogType?: 'website' | 'article';
  ogImage?: string;
  schema?: Record<string, unknown> | Array<Record<string, unknown>>;
  keywords?: string[];
}

export const DEFAULT_SITE_TITLE = 'India Legal News Aggregator | Real-Time Court Judgments & Legal Updates';
export const DEFAULT_SITE_DESCRIPTION =
  'Fast, intelligent legal aggregator and hybrid search across Supreme Court of India, High Courts, and Tribunals. Live court orders, case law citations, and breaking legal journalism.';
export const SITE_ORIGIN = 'https://india-legal-news.vercel.app';
export const DEFAULT_OG_IMAGE = `${SITE_ORIGIN}/og-image.png`;

/**
 * Updates DOM title, meta description, OpenGraph, Twitter, and Schema.org JSON-LD tags dynamically.
 */
export function updateSEOMetadata(config: SEOConfig = {}): void {
  if (typeof document === 'undefined') return;

  const rawTitle = config.title;
  const fullTitle = rawTitle
    ? rawTitle.includes('India Legal News')
      ? rawTitle
      : `${rawTitle} | India Legal News`
    : DEFAULT_SITE_TITLE;

  const description = config.description || DEFAULT_SITE_DESCRIPTION;
  const canonicalUrl = config.canonicalUrl || `${SITE_ORIGIN}/`;
  const ogType = config.ogType || 'website';
  const ogImage = config.ogImage || DEFAULT_OG_IMAGE;

  // Title tags
  document.title = fullTitle;
  setMetaTag('name', 'title', fullTitle);
  setMetaTag('property', 'og:title', fullTitle);
  setMetaTag('name', 'twitter:title', fullTitle);

  // Description tags
  setMetaTag('name', 'description', description);
  setMetaTag('property', 'og:description', description);
  setMetaTag('name', 'twitter:description', description);

  // Canonical & URLs
  setMetaTag('property', 'og:url', canonicalUrl);
  setMetaTag('name', 'twitter:url', canonicalUrl);
  let canonicalEl = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;
  if (!canonicalEl) {
    canonicalEl = document.createElement('link');
    canonicalEl.setAttribute('rel', 'canonical');
    document.head.appendChild(canonicalEl);
  }
  canonicalEl.setAttribute('href', canonicalUrl);

  // Media & Social Preview tags
  setMetaTag('property', 'og:type', ogType);
  setMetaTag('property', 'og:image', ogImage);
  setMetaTag('name', 'twitter:image', ogImage);
  setMetaTag('name', 'twitter:card', 'summary_large_image');

  // Keywords if provided
  if (config.keywords && config.keywords.length > 0) {
    setMetaTag('name', 'keywords', config.keywords.join(', '));
  }

  // Schema.org structured data
  updateJsonLd(config.schema);
}

function setMetaTag(attrName: 'name' | 'property', attrValue: string, content: string): void {
  let el = document.querySelector(`meta[${attrName}="${attrValue}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(attrName, attrValue);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

function updateJsonLd(schema?: Record<string, unknown> | Array<Record<string, unknown>>): void {
  const SCRIPT_ID = 'seo-structured-data';
  let scriptEl = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;

  const payload = schema || {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'India Legal News Aggregator',
    url: `${SITE_ORIGIN}/`,
    description: DEFAULT_SITE_DESCRIPTION,
    potentialAction: {
      '@type': 'SearchAction',
      target: `${SITE_ORIGIN}/?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  };

  if (!scriptEl) {
    scriptEl = document.createElement('script');
    scriptEl.id = SCRIPT_ID;
    scriptEl.type = 'application/ld+json';
    document.head.appendChild(scriptEl);
  }

  scriptEl.textContent = JSON.stringify(payload);
}

/**
 * Builds Google NewsArticle / Article Schema.org structured data for a court judgment or legal news item.
 */
export function buildJudgmentSchema(
  judgment: {
    id: string;
    title: string;
    short_title?: string | null;
    excerpt?: string;
    summary?: string;
    court_name?: string;
    court_code?: string;
    judgment_date?: string;
    updated_at?: string;
    subject_category?: string;
    tags?: string[];
    content_type?: string;
  },
  canonicalUrl: string
): Record<string, unknown> {
  const isNews = judgment.content_type === 'news';
  const courtName = judgment.court_name || 'Supreme Court of India';
  const caseTitle = judgment.short_title || judgment.title;
  const holdingText = judgment.excerpt || judgment.summary || judgment.title;

  return {
    '@context': 'https://schema.org',
    '@type': isNews ? 'NewsArticle' : 'Article',
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': canonicalUrl,
    },
    headline: judgment.title,
    description: holdingText,
    datePublished: judgment.judgment_date || new Date().toISOString().split('T')[0],
    dateModified: judgment.updated_at || judgment.judgment_date || new Date().toISOString(),
    author: {
      '@type': 'Organization',
      name: courtName,
    },
    publisher: {
      '@type': 'NewsMediaOrganization',
      name: 'India Legal News Aggregator',
      url: SITE_ORIGIN,
      logo: {
        '@type': 'ImageObject',
        url: DEFAULT_OG_IMAGE,
      },
    },
    articleSection: judgment.subject_category || 'Legal News',
    keywords: (judgment.tags || []).join(', ') || judgment.subject_category || 'Indian Law',
    image: DEFAULT_OG_IMAGE,
    // Google AI Overviews & Perplexity Direct Answer Extracts (FAQ / Q&A Holding Schema)
    hasPart: [
      {
        '@type': 'Question',
        name: `What did the ${courtName} rule in ${caseTitle}?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: holdingText,
        },
      },
      ...(judgment.tags && judgment.tags.length > 0
        ? [
            {
              '@type': 'Question',
              name: `Which statutory provisions and legal sections are involved in ${caseTitle}?`,
              acceptedAnswer: {
                '@type': 'Answer',
                text: `Key provisions and statutory citations applied: ${judgment.tags.join(', ')}.`,
              },
            },
          ]
        : []),
    ],
  };
}

/**
 * Builds Schema.org BreadcrumbList structured data for search engine result snippets.
 */
export function buildBreadcrumbSchema(items: { name: string; url: string }[]): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, idx) => ({
      '@type': 'ListItem',
      position: idx + 1,
      name: item.name,
      item: item.url,
    })),
  };
}
