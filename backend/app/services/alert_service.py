"""
Personalized Legal Alert Service
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Matches incoming legal news and judgments against user topic & statute subscriptions.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.judgment import Judgment
from app.schemas.judgment import JudgmentResponse
from app.schemas.user_features import AlertMatchItem

logger = logging.getLogger("app.services.alert_service")


class AlertService:
    """
    Evaluates judgments against active topic, court, and statute alerts.
    Operates in-memory with sub-millisecond evaluation per judgment.
    """

    @staticmethod
    def match_judgment_to_alert(judgment: Judgment, alert: Alert) -> list[str]:
        """
        Determines whether a judgment fulfills an alert rule.
        Returns a list of matched keywords/sections, or an empty list if not matched.
        """
        if not alert.is_active:
            return []

        # 1. Subject Category Filter (e.g., 'Criminal', 'Corporate')
        if alert.category:
            if not judgment.subject_category:
                return []
            if alert.category.strip().lower() != judgment.subject_category.strip().lower():
                return []

        # 2. Court Code Filter (e.g., 'sc', 'delhi-hc')
        if alert.court_code:
            if not judgment.court_code:
                return []
            if alert.court_code.strip().lower() != judgment.court_code.strip().lower():
                return []

        matched_terms: list[str] = []

        # Prepare searchable text from judgment
        title_text = (judgment.title or "").lower()
        excerpt_text = (judgment.excerpt or "").lower()
        tags_lower = [t.lower() for t in (judgment.tags or [])]
        combined_text = f"{title_text} {excerpt_text} {' '.join(tags_lower)}"

        # 3. Keywords / Statute Sections Matching (e.g. 'Section 438', 'IBC')
        has_keyword_filter = bool(alert.keywords and len(alert.keywords) > 0)
        if has_keyword_filter:
            for kw in alert.keywords:
                kw_clean = kw.strip().lower()
                if not kw_clean:
                    continue
                # Check exact in tags or substring in title/excerpt
                if any(kw_clean in tag for tag in tags_lower) or kw_clean in combined_text:
                    matched_terms.append(kw.strip())

        # 4. Free-text Query Matching
        has_query_filter = bool(alert.query and alert.query.strip())
        if has_query_filter:
            q_clean = alert.query.strip().lower()
            if q_clean in combined_text:
                matched_terms.append(alert.query.strip())

        # If keyword or query was specified, at least one term must match
        if (has_keyword_filter or has_query_filter) and not matched_terms:
            return []

        # If no keywords or query were specified, category or court filter was the rule
        if not matched_terms:
            if alert.category:
                matched_terms.append(alert.category)
            elif alert.court_code:
                matched_terms.append(alert.court_code)
            else:
                matched_terms.append("General Match")

        return matched_terms

    async def find_matches_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        alert_id: UUID | None = None,
        limit: int = 50,
    ) -> list[AlertMatchItem]:
        """
        Queries recent judgments in the database and matches them against user alerts.
        """
        max_limit = limit if isinstance(limit, int) else 50
        # 1. Fetch user alerts
        stmt = select(Alert).where(Alert.user_id == user_id, Alert.is_active.is_(True))
        if alert_id:
            stmt = stmt.where(Alert.id == alert_id)
        stmt = stmt.order_by(Alert.created_at.desc())

        res = await db.execute(stmt)
        alerts = res.scalars().all()
        if not alerts:
            return []

        # 2. Fetch candidate judgments (recent 100)
        j_stmt = (
            select(Judgment)
            .order_by(Judgment.judgment_date.desc(), Judgment.created_at.desc())
            .limit(100)
        )
        j_res = await db.execute(j_stmt)
        judgments = j_res.scalars().all()

        matches: list[AlertMatchItem] = []
        for alert in alerts:
            for j in judgments:
                matched_terms = self.match_judgment_to_alert(j, alert)
                if matched_terms:
                    matches.append(
                        AlertMatchItem(
                            alert_id=alert.id,
                            alert_title=alert.title,
                            matched_keywords=matched_terms,
                            judgment=JudgmentResponse.model_validate(j),
                        )
                    )
                if len(matches) >= max_limit:
                    break
            if len(matches) >= max_limit:
                break

        return matches


# Global singleton instance
alert_service = AlertService()
