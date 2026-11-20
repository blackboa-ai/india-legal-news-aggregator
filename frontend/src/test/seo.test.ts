import { describe, it, expect, beforeEach } from 'vitest';
import {
  updateSEOMetadata,
  buildJudgmentSchema,
  buildBreadcrumbSchema,
  DEFAULT_SITE_TITLE,
  SITE_ORIGIN,
} from '../utils/seo';

describe('SEO Utilities', () => {
  beforeEach(() => {
    document.title = '';
    // Clean up meta tags
    document.querySelectorAll('meta, link[rel="canonical"], script[id="seo-structured-data"]').forEach((el) => {
      el.remove();
    });
  });

  it('updates title and meta tags with default values when called without arguments', () => {
    updateSEOMetadata();
    expect(document.title).toBe(DEFAULT_SITE_TITLE);
    expect(document.querySelector('meta[name="description"]')?.getAttribute('content')).toContain(
      'Fast, intelligent legal aggregator'
    );
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(`${SITE_ORIGIN}/`);
  });

  it('updates title, description, and canonical for a specific judgment', () => {
    const judgmentTitle = 'State of Maharashtra v. Union of India';
    const judgmentUrl = `${SITE_ORIGIN}/?judgment=test-id-123`;

    updateSEOMetadata({
      title: judgmentTitle,
      description: 'Landmark constitutional precedent on cooperative federalism.',
      canonicalUrl: judgmentUrl,
      ogType: 'article',
    });

    expect(document.title).toBe(`${judgmentTitle} | India Legal News`);
    expect(document.querySelector('meta[property="og:title"]')?.getAttribute('content')).toBe(
      `${judgmentTitle} | India Legal News`
    );
    expect(document.querySelector('meta[property="og:description"]')?.getAttribute('content')).toBe(
      'Landmark constitutional precedent on cooperative federalism.'
    );
    expect(document.querySelector('meta[property="og:type"]')?.getAttribute('content')).toBe('article');
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(judgmentUrl);
  });

  it('generates valid Schema.org NewsArticle / Article schema', () => {
    const schema = buildJudgmentSchema(
      {
        id: '123',
        title: 'Supreme Court Bail Order',
        excerpt: 'Anticipatory bail granted under Section 438 CrPC.',
        court_name: 'Supreme Court of India',
        judgment_date: '2026-11-20',
        subject_category: 'Criminal',
        tags: ['Bail', 'Section 438 CrPC'],
        content_type: 'judgment',
      },
      `${SITE_ORIGIN}/?judgment=123`
    );

    expect(schema['@context']).toBe('https://schema.org');
    expect(schema['@type']).toBe('Article');
    expect(schema['headline']).toBe('Supreme Court Bail Order');
    expect((schema['author'] as { name: string }).name).toBe('Supreme Court of India');
  });

  it('generates valid BreadcrumbList schema', () => {
    const breadcrumbs = buildBreadcrumbSchema([
      { name: 'Home', url: `${SITE_ORIGIN}/` },
      { name: 'Supreme Court', url: `${SITE_ORIGIN}/?court=sc` },
      { name: 'Case Order', url: `${SITE_ORIGIN}/?judgment=123` },
    ]);

    expect(breadcrumbs['@type']).toBe('BreadcrumbList');
    expect(breadcrumbs['itemListElement']).toHaveLength(3);
    expect((breadcrumbs['itemListElement'] as Array<{ position: number }>)[0].position).toBe(1);
  });
});
