"""
Unit and Integration Tests for User Feedback API
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from app.api.v1.feedback import forward_feedback_notification, list_feedback, submit_feedback
from app.main import app
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackListResponse, FeedbackResponse


def _run_coro(coro):
    """Executes a coroutine synchronously for isolated unit testing."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


def test_feedback_routes_registered():
    """Verify feedback endpoints are registered in OpenAPI spec."""
    openapi = app.openapi()
    assert "/api/v1/feedback" in openapi["paths"]
    assert "post" in openapi["paths"]["/api/v1/feedback"]
    assert "get" in openapi["paths"]["/api/v1/feedback"]


@pytest.mark.asyncio
async def test_submit_feedback_anonymous():
    """Verify anonymous user can submit valid feedback."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    bg_tasks = BackgroundTasks()

    payload = FeedbackCreate(
        rating=5,
        feedback_text="Outstanding search engine for Indian legal judgments!",
        email="lawyer@example.com",
        category="general",
    )

    result = await submit_feedback(
        payload=payload,
        background_tasks=bg_tasks,
        db=mock_db,
        current_user=None,
    )

    assert result.rating == 5
    assert result.feedback_text == "Outstanding search engine for Indian legal judgments!"
    assert result.email == "lawyer@example.com"
    assert result.category == "general"
    assert result.user_id is None

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_feedback_authenticated_user():
    """Verify authenticated user automatically attaches user_id and email if omitted."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    bg_tasks = BackgroundTasks()

    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="advocate@barcouncil.in",
        full_name="Advocate Sharma",
        is_active=True,
    )

    payload = FeedbackCreate(
        rating=4,
        feedback_text="Add more high court bail judgments please.",
        category="feature",
    )

    result = await submit_feedback(
        payload=payload,
        background_tasks=bg_tasks,
        db=mock_db,
        current_user=mock_user,
    )

    assert result.rating == 4
    assert result.feedback_text == "Add more high court bail judgments please."
    assert result.category == "feature"
    assert result.user_id == str(user_id)
    assert result.email == "advocate@barcouncil.in"


@pytest.mark.asyncio
async def test_list_feedback_with_stats():
    """Verify list_feedback returns records and correctly aggregated stats."""
    mock_db = AsyncMock()

    # Mock count
    count_res = MagicMock()
    count_res.scalar.return_value = 2

    # Mock avg
    avg_res = MagicMock()
    avg_res.scalar.return_value = 4.5

    # Mock distribution
    dist_res = MagicMock()
    dist_res.all.return_value = [(4, 1), (5, 1)]

    # Mock records
    rec1 = Feedback(
        id=uuid.uuid4(),
        rating=5,
        feedback_text="Great work",
        email="a@test.com",
        category="general",
        created_at=datetime.now(UTC),
    )
    rec2 = Feedback(
        id=uuid.uuid4(),
        rating=4,
        feedback_text="Very good",
        email=None,
        category="feature",
        created_at=datetime.now(UTC),
    )
    items_res = MagicMock()
    items_res.scalars.return_value.all.return_value = [rec1, rec2]

    mock_db.execute.side_effect = [count_res, avg_res, dist_res, items_res]

    admin_user = User(
        id=uuid.uuid4(),
        email="admin@barcouncil.in",
        full_name="Admin Counsel",
        is_active=True,
        is_superuser=True,
    )

    response = await list_feedback(
        limit=10,
        offset=0,
        category=None,
        current_user=admin_user,
        db=mock_db,
    )

    assert isinstance(response, FeedbackListResponse)
    assert response.total == 2
    assert response.stats.average_rating == 4.5
    assert response.stats.total_count == 2
    assert response.stats.rating_distribution["5"] == 1
    assert response.stats.rating_distribution["4"] == 1
    assert len(response.data) == 2


def test_forward_feedback_notification_logger():
    """Verify forward_feedback_notification runs without raising exceptions."""
    with patch("app.api.v1.feedback.logger.info") as mock_log:
        forward_feedback_notification(
            feedback_id="test-id",
            rating=5,
            feedback_text="Amazing app!",
            email="dev@example.com",
            category="general",
            user_id="user-123",
        )
        assert mock_log.called
