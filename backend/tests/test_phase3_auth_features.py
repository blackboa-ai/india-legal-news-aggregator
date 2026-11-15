"""
Phase 3 Unit & Integration Tests: User Authentication, Google OAuth, Bookmarks & Personalized Legal Alerts
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Covers:
1. Password Hashing (bcrypt) & 72-Byte Boundary Safety
2. JWT Access and Refresh Token Creation, Decoding, Expiration, and Tampering
3. FastAPI Dependencies (get_current_user, get_optional_user, get_current_active_superuser)
4. Auth API Endpoints (Register, Login, Me, Refresh)
5. Google OAuth ID Token Verification & User Provisioning (Mocked)
6. Bookmarks CRUD & Duplicate Prevention (with notes/tags)
7. Topic & Statute Alerts CRUD & Keyword/Section Matching Logic
8. Upstash Redis / In-Memory Rate Limiting
9. OpenAPI Route & Documentation Registration (/docs)
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from app.api.v1.auth import (
    get_current_user_profile,
    login,
    login_with_google,
    refresh_access_token,
    register,
    verify_google_id_token,
)
from app.api.v1.bookmarks import (
    create_alert,
    create_bookmark_by_id,
    delete_alert,
    delete_bookmark,
    get_alert_matches,
    list_alerts,
    list_bookmarks,
)
from app.auth import RateLimiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_superuser,
    get_current_user,
    get_optional_user,
    get_password_hash,
    verify_password,
)
from app.main import app
from app.models.alert import Alert
from app.models.bookmark import Bookmark
from app.models.judgment import Judgment
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.user_features import (
    AlertCreateRequest,
    AlertListResponse,
    AlertMatchesResponse,
    AlertResponse,
    BookmarkCreateRequest,
    BookmarkListResponse,
    BookmarkResponse,
)
from app.services.alert_service import alert_service
from fastapi import HTTPException
from starlette.requests import Request

# ==============================================================================
# Helpers & Fixtures
# ==============================================================================


def create_mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


def create_mock_user(
    id: UUID | None = None,
    email: str = "advocate.sharma@example.com",
    full_name: str = "Advocate Sharma",
    is_active: bool = True,
    is_superuser: bool = False,
    hashed_password: str | None = None,
    google_id: str | None = None,
) -> User:
    uid = id or uuid4()
    pwd = hashed_password or get_password_hash("ValidPass123!")
    user = User(
        id=uid,
        email=email,
        full_name=full_name,
        hashed_password=pwd,
        google_id=google_id,
        is_active=is_active,
        is_superuser=is_superuser,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return user


def create_mock_judgment(
    id: UUID | None = None,
    title: str = "Arnesh Kumar v. State of Bihar",
    court_code: str = "sc",
    court_name: str = "Supreme Court of India",
    subject_category: str = "Criminal",
    judgment_date: date | None = None,
    tags: list[str] | None = None,
    excerpt: str = "Guidelines for arrest under Section 498A IPC and Section 41 CrPC.",
) -> Judgment:
    jid = id or uuid4()
    return Judgment(
        id=jid,
        external_id=f"ext_{jid.hex[:12]}",
        title=title,
        short_title=title.split(" v. ")[0],
        court_code=court_code,
        court_name=court_name,
        court_level=1,
        judgment_date=judgment_date or date(2014, 7, 2),
        subject_category=subject_category,
        excerpt=excerpt,
        full_text=f"Full judgment content for {title}...",
        url=f"https://indiankanoon.org/doc/{jid.hex[:8]}/",
        parties=[{"role": "petitioner", "name": "Arnesh Kumar"}],
        tags=tags or ["Section 498A IPC", "Section 41 CrPC", "Arrest Guidelines"],
        source="indiankanoon",
        is_archived=True,
        classification_confidence=0.96,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ==============================================================================
# 1. Password Hashing & Bcrypt 72-Byte Boundary Safety Tests
# ==============================================================================
class TestPasswordSecurity:
    """Verifies salted hashing, verification, and length handling."""

    def test_hash_password_generates_valid_bcrypt_hash(self):
        password = "SecurePassword2026!"
        hashed = get_password_hash(password)
        assert hashed.startswith("$2b$")
        assert hashed != password

    def test_verify_correct_password(self):
        password = "MyLegalPassword@123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        password = "MyLegalPassword@123"
        hashed = get_password_hash(password)
        assert verify_password("WrongPassword!", hashed) is False

    def test_long_password_boundary_safety(self):
        """Bcrypt has a 72-byte limit; ensure longer inputs don't crash the server."""
        long_pass = "A" * 150
        hashed = get_password_hash(long_pass)
        assert verify_password(long_pass, hashed) is True
        assert verify_password("Wrong" + "A" * 145, hashed) is False

    def test_empty_or_none_password_handling(self):
        assert verify_password("", "some_hash") is False
        assert verify_password("pass", "") is False


# ==============================================================================
# 2. JWT Access and Refresh Tokens Tests
# ==============================================================================
class TestJWTTokens:
    """Verifies JWT lifecycle: generation, claims, expiration, tampering."""

    def test_create_and_decode_access_token(self):
        uid = uuid4()
        token = create_access_token(subject=str(uid), claims={"role": "advocate"})
        claims = decode_token(token)

        assert claims["sub"] == str(uid)
        assert claims["type"] == "access"
        assert claims["role"] == "advocate"
        assert "exp" in claims
        assert "iat" in claims

    def test_create_and_decode_refresh_token(self):
        uid = uuid4()
        token = create_refresh_token(subject=str(uid))
        claims = decode_token(token)

        assert claims["sub"] == str(uid)
        assert claims["type"] == "refresh"

    def test_token_expiration_raises_401(self):
        uid = uuid4()
        # Create token already expired in the past
        token = create_access_token(subject=str(uid), expires_delta=timedelta(seconds=-10))
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_tampered_token_signature_raises_401(self):
        uid = uuid4()
        token = create_access_token(subject=str(uid))
        # Modify the signature part
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.badsignature"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered_token)
        assert exc_info.value.status_code == 401
        assert "could not validate" in exc_info.value.detail.lower()

    def test_invalid_token_format_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not-a-real-jwt-token")
        assert exc_info.value.status_code == 401


# ==============================================================================
# 3. FastAPI Authentication Dependencies Tests
# ==============================================================================
class TestAuthDependencies:
    """Tests get_current_user and get_optional_user dependency behavior."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        user = create_mock_user()
        token = create_access_token(subject=str(user.id))

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        resolved_user = await get_current_user(token=token, db=mock_db)
        assert resolved_user.id == user.id
        assert resolved_user.email == user.email

    @pytest.mark.asyncio
    async def test_get_current_user_missing_token_raises_401(self):
        mock_db = create_mock_db()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=None, db=mock_db)
        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_refresh_token_rejected_raises_401(self):
        user = create_mock_user()
        refresh_tok = create_refresh_token(subject=str(user.id))
        mock_db = create_mock_db()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=refresh_tok, db=mock_db)
        assert exc_info.value.status_code == 401
        assert "claims" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_not_found_raises_401(self):
        user_id = uuid4()
        token = create_access_token(subject=str(user_id))

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db)
        assert exc_info.value.status_code == 401
        assert "user not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_raises_400(self):
        user = create_mock_user(is_active=False)
        token = create_access_token(subject=str(user.id))

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "inactive" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_optional_user_with_token(self):
        user = create_mock_user()
        token = create_access_token(subject=str(user.id))

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        opt_user = await get_optional_user(token=token, db=mock_db)
        assert opt_user is not None
        assert opt_user.id == user.id

    @pytest.mark.asyncio
    async def test_get_optional_user_without_token_returns_none(self):
        mock_db = create_mock_db()
        opt_user = await get_optional_user(token=None, db=mock_db)
        assert opt_user is None

    @pytest.mark.asyncio
    async def test_get_optional_user_with_invalid_token_returns_none(self):
        mock_db = create_mock_db()
        opt_user = await get_optional_user(token="invalid.bad.token", db=mock_db)
        assert opt_user is None

    @pytest.mark.asyncio
    async def test_get_current_active_superuser_checks(self):
        admin_user = create_mock_user(is_superuser=True)
        res = await get_current_active_superuser(current_user=admin_user)
        assert res.id == admin_user.id

        regular_user = create_mock_user(is_superuser=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_superuser(current_user=regular_user)
        assert exc_info.value.status_code == 403


# ==============================================================================
# 4. User Registration, Login & Profile Endpoints Tests
# ==============================================================================
class TestAuthEndpoints:
    """Tests POST /register, POST /login, GET /me, and POST /refresh."""

    @pytest.mark.asyncio
    async def test_register_new_user_success(self):
        mock_db = create_mock_db()
        # Email lookup returns None (no duplicate)
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        payload = UserRegisterRequest(
            email="newlawyer@barcouncil.in",
            password="StrongPassword123!",
            full_name="Advocate A. Verma",
        )

        resp = await register(payload=payload, db=mock_db)
        assert isinstance(resp, TokenResponse)
        assert resp.access_token is not None
        assert resp.refresh_token is not None
        assert resp.user.email == "newlawyer@barcouncil.in"
        assert resp.user.full_name == "Advocate A. Verma"
        assert resp.token_type == "bearer"
        assert resp.expires_in > 0

        # Verify DB add was called with hashed password
        assert mock_db.add.called
        added_user = mock_db.add.call_args[0][0]
        assert added_user.email == "newlawyer@barcouncil.in"
        assert added_user.hashed_password != "StrongPassword123!"
        assert verify_password("StrongPassword123!", added_user.hashed_password) is True

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self):
        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = create_mock_user(email="existing@example.com")
        mock_db.execute.return_value = mock_res

        payload = UserRegisterRequest(
            email="existing@example.com",
            password="StrongPassword123!",
            full_name="Duplicate Advocate",
        )

        with pytest.raises(HTTPException) as exc_info:
            await register(payload=payload, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_login_success(self):
        password = "CorrectPassword123!"
        user = create_mock_user(
            email="registered@legal.in",
            hashed_password=get_password_hash(password),
        )

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        payload = UserLoginRequest(email="registered@legal.in", password=password)
        resp = await login(payload=payload, db=mock_db)

        assert isinstance(resp, TokenResponse)
        assert resp.user.email == user.email
        claims = decode_token(resp.access_token)
        assert claims["sub"] == str(user.id)

    @pytest.mark.asyncio
    async def test_login_invalid_password_fails(self):
        user = create_mock_user(hashed_password=get_password_hash("Correct123!"))
        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        payload = UserLoginRequest(email=user.email, password="WrongPassword!")
        with pytest.raises(HTTPException) as exc_info:
            await login(payload=payload, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "incorrect email or password" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_fails(self):
        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        payload = UserLoginRequest(email="unknown@legal.in", password="AnyPassword123!")
        with pytest.raises(HTTPException) as exc_info:
            await login(payload=payload, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user_fails(self):
        pwd = "InactiveUserPass!"
        user = create_mock_user(hashed_password=get_password_hash(pwd), is_active=False)
        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        payload = UserLoginRequest(email=user.email, password=pwd)
        with pytest.raises(HTTPException) as exc_info:
            await login(payload=payload, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "inactive" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_profile_me(self):
        user = create_mock_user(email="me@law.in", full_name="Senior Counsel")
        resp = await get_current_user_profile(current_user=user)

        assert isinstance(resp, UserResponse)
        assert resp.id == user.id
        assert resp.email == "me@law.in"
        assert resp.full_name == "Senior Counsel"

    @pytest.mark.asyncio
    async def test_refresh_token_flow(self):
        user = create_mock_user()
        refresh_tok = create_refresh_token(subject=str(user.id))

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        payload = RefreshTokenRequest(refresh_token=refresh_tok)
        resp = await refresh_access_token(payload=payload, db=mock_db)

        assert isinstance(resp, TokenResponse)
        claims = decode_token(resp.access_token)
        assert claims["sub"] == str(user.id)
        assert claims["type"] == "access"


# ==============================================================================
# 5. Mocked Google OAuth SSO Verification Tests
# ==============================================================================
class TestGoogleOAuth:
    """Verifies Google ID-token decoding, mocking, and auto user provisioning."""

    @pytest.mark.asyncio
    async def test_verify_google_token_empty_raises(self):
        with pytest.raises(ValueError):
            await verify_google_id_token("")

    @pytest.mark.asyncio
    async def test_google_oauth_new_user_provisioning(self):
        mock_google_profile = {
            "sub": "google_sub_1098234710293",
            "email": "google.lawyer@gmail.com",
            "name": "Advocate G. Rao",
            "email_verified": True,
        }

        mock_db = create_mock_db()
        # No existing user
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        with patch("app.api.v1.auth.verify_google_id_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_google_profile

            payload = GoogleAuthRequest(id_token="valid_mock_google_id_token")
            resp = await login_with_google(payload=payload, db=mock_db)

            assert isinstance(resp, TokenResponse)
            assert resp.user.email == "google.lawyer@gmail.com"
            assert resp.user.full_name == "Advocate G. Rao"

            # Verify user was created in db with google_id and no local password
            assert mock_db.add.called
            added = mock_db.add.call_args[0][0]
            assert added.google_id == "google_sub_1098234710293"
            assert added.hashed_password is None

    @pytest.mark.asyncio
    async def test_google_oauth_existing_user_login(self):
        existing_user = create_mock_user(
            email="google.existing@gmail.com",
            google_id="google_existing_id_999",
        )

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_res

        with patch("app.api.v1.auth.verify_google_id_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {
                "sub": "google_existing_id_999",
                "email": "google.existing@gmail.com",
                "name": "Existing User",
            }

            payload = GoogleAuthRequest(id_token="valid_existing_google_token")
            resp = await login_with_google(payload=payload, db=mock_db)

            assert isinstance(resp, TokenResponse)
            assert resp.user.email == existing_user.email
            assert not mock_db.add.called  # Reuses existing account

    @pytest.mark.asyncio
    async def test_google_oauth_invalid_token_fails_400(self):
        mock_db = create_mock_db()

        with patch("app.api.v1.auth.verify_google_id_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = ValueError("Invalid signature on Google ID token")

            payload = GoogleAuthRequest(id_token="bad_google_token")
            with pytest.raises(HTTPException) as exc_info:
                await login_with_google(payload=payload, db=mock_db)

            assert exc_info.value.status_code == 400
            assert "verification failed" in exc_info.value.detail.lower()


# ==============================================================================
# 6. Bookmarks CRUD & Duplicate Prevention Tests
# ==============================================================================
class TestBookmarksCRUD:
    """Verifies bookmark creation, listing, duplicate constraint, and deletion."""

    @pytest.mark.asyncio
    async def test_create_bookmark_success_with_notes_and_tags(self):
        user = create_mock_user()
        judgment = create_mock_judgment()

        mock_db = create_mock_db()
        # 1st query: check judgment exists -> returns judgment
        # 2nd query: duplicate check -> returns None
        mock_j_res = MagicMock()
        mock_j_res.scalar_one_or_none.return_value = judgment
        mock_dup_res = MagicMock()
        mock_dup_res.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [mock_j_res, mock_dup_res]

        payload = BookmarkCreateRequest(
            notes="Crucial precedent on anticipatory bail scope.",
            tags=["anticipatory-bail", "client-defense"],
        )

        resp = await create_bookmark_by_id(
            judgment_id=judgment.id,
            payload=payload,
            current_user=user,
            db=mock_db,
        )

        assert isinstance(resp, BookmarkResponse)
        assert resp.judgment_id == judgment.id
        assert resp.notes == "Crucial precedent on anticipatory bail scope."
        assert resp.tags == ["anticipatory-bail", "client-defense"]
        assert resp.judgment is not None
        assert resp.judgment.title == judgment.title
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_create_bookmark_duplicate_prevention(self):
        """Duplicate bookmark attempt must return HTTP 409 Conflict."""
        user = create_mock_user()
        judgment = create_mock_judgment()
        existing_bookmark = Bookmark(
            id=uuid4(),
            user_id=str(user.id),
            judgment_id=judgment.id,
            notes=None,
            tags=[],
        )

        mock_db = create_mock_db()
        mock_j_res = MagicMock()
        mock_j_res.scalar_one_or_none.return_value = judgment
        mock_dup_res = MagicMock()
        mock_dup_res.scalar_one_or_none.return_value = existing_bookmark
        mock_db.execute.side_effect = [mock_j_res, mock_dup_res]

        with pytest.raises(HTTPException) as exc_info:
            await create_bookmark_by_id(
                judgment_id=judgment.id,
                payload=None,
                current_user=user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 409
        assert "already bookmarked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_bookmark_nonexistent_judgment_raises_404(self):
        user = create_mock_user()
        mock_db = create_mock_db()
        mock_j_res = MagicMock()
        mock_j_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_j_res

        with pytest.raises(HTTPException) as exc_info:
            await create_bookmark_by_id(
                judgment_id=uuid4(),
                payload=None,
                current_user=user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_bookmarks_returns_user_items(self):
        user = create_mock_user()
        judgment = create_mock_judgment()
        b1 = Bookmark(
            id=uuid4(),
            user_id=str(user.id),
            judgment_id=judgment.id,
            notes="Important reference",
            tags=["crpc"],
            created_at=datetime.now(UTC),
        )
        b1.judgment = judgment

        mock_db = create_mock_db()
        mock_count_res = MagicMock()
        mock_count_res.scalar.return_value = 1
        mock_items_res = MagicMock()
        mock_items_res.scalars.return_value.all.return_value = [b1]
        mock_db.execute.side_effect = [mock_count_res, mock_items_res]

        resp = await list_bookmarks(limit=10, offset=0, current_user=user, db=mock_db)
        assert isinstance(resp, BookmarkListResponse)
        assert resp.total == 1
        assert len(resp.data) == 1
        assert resp.data[0].notes == "Important reference"
        assert resp.data[0].judgment is not None
        assert resp.data[0].judgment.id == judgment.id

    @pytest.mark.asyncio
    async def test_delete_bookmark_success(self):
        user = create_mock_user()
        jid = uuid4()
        b = Bookmark(id=uuid4(), user_id=str(user.id), judgment_id=jid)

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = b
        mock_db.execute.return_value = mock_res

        resp = await delete_bookmark(judgment_id=jid, current_user=user, db=mock_db)
        assert resp["status"] == "deleted"
        assert resp["judgment_id"] == str(jid)
        assert mock_db.delete.called

    @pytest.mark.asyncio
    async def test_delete_nonexistent_bookmark_raises_404(self):
        user = create_mock_user()
        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        with pytest.raises(HTTPException) as exc_info:
            await delete_bookmark(judgment_id=uuid4(), current_user=user, db=mock_db)

        assert exc_info.value.status_code == 404


# ==============================================================================
# 7. Topic & Statute Alerts & Matching Service Tests
# ==============================================================================
class TestAlertsAndMatching:
    """Verifies alert subscriptions and deterministic legal criteria matching."""

    @pytest.mark.asyncio
    async def test_create_alert_success(self):
        user = create_mock_user()
        mock_db = create_mock_db()

        payload = AlertCreateRequest(
            title="Anticipatory Bail & Section 438",
            category="Criminal",
            court_code="sc",
            keywords=["Section 438", "Section 482", "Bail"],
            query="quashing FIR",
        )

        resp = await create_alert(payload=payload, current_user=user, db=mock_db)
        assert isinstance(resp, AlertResponse)
        assert resp.title == "Anticipatory Bail & Section 438"
        assert resp.category == "Criminal"
        assert resp.court_code == "sc"
        assert "Section 438" in resp.keywords
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_list_alerts(self):
        user = create_mock_user()
        a1 = Alert(
            id=uuid4(),
            user_id=str(user.id),
            title="Insolvency Alerts",
            category="Corporate",
            court_code="nclat",
            keywords=["IBC", "Section 7"],
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [a1]
        mock_db.execute.return_value = mock_res

        resp = await list_alerts(current_user=user, db=mock_db)
        assert isinstance(resp, AlertListResponse)
        assert resp.total == 1
        assert resp.data[0].title == "Insolvency Alerts"

    @pytest.mark.asyncio
    async def test_delete_alert_success(self):
        user = create_mock_user()
        aid = uuid4()
        a = Alert(id=aid, user_id=str(user.id), title="Test Alert", keywords=[])

        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = a
        mock_db.execute.return_value = mock_res

        resp = await delete_alert(alert_id=aid, current_user=user, db=mock_db)
        assert resp["status"] == "deleted"
        assert resp["alert_id"] == str(aid)
        assert mock_db.delete.called

    @pytest.mark.asyncio
    async def test_delete_alert_not_found_raises_404(self):
        user = create_mock_user()
        mock_db = create_mock_db()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        with pytest.raises(HTTPException) as exc_info:
            await delete_alert(alert_id=uuid4(), current_user=user, db=mock_db)

        assert exc_info.value.status_code == 404

    def test_alert_service_statute_keyword_matching(self):
        """Verifies statute matching in title, tags, or excerpt."""
        judgment = create_mock_judgment(
            title="Sundeep Kumar Bafna v. State of Maharashtra",
            subject_category="Criminal",
            court_code="sc",
            tags=["Section 438 CrPC", "Anticipatory Bail", "Article 21"],
            excerpt="Scope of Section 438 CrPC for pre-arrest bail when accused is in custody.",
        )

        # 1. Matching alert on keyword
        alert_match = Alert(
            id=uuid4(),
            user_id="user_1",
            title="Bail Watch",
            category="Criminal",
            court_code="sc",
            keywords=["Section 438", "IBC"],
            is_active=True,
        )
        matches = alert_service.match_judgment_to_alert(judgment, alert_match)
        assert "Section 438" in matches

        # 2. Category mismatch blocks alert
        alert_mismatch_cat = Alert(
            id=uuid4(),
            user_id="user_1",
            title="Corporate Watch",
            category="Corporate",
            court_code="sc",
            keywords=["Section 438"],
            is_active=True,
        )
        assert alert_service.match_judgment_to_alert(judgment, alert_mismatch_cat) == []

        # 3. Court mismatch blocks alert
        alert_mismatch_court = Alert(
            id=uuid4(),
            user_id="user_1",
            title="Delhi HC Watch",
            category="Criminal",
            court_code="delhi-hc",
            keywords=["Section 438"],
            is_active=True,
        )
        assert alert_service.match_judgment_to_alert(judgment, alert_mismatch_court) == []

        # 4. Inactive alert returns no matches
        alert_inactive = Alert(
            id=uuid4(),
            user_id="user_1",
            title="Inactive Alert",
            category="Criminal",
            court_code="sc",
            keywords=["Section 438"],
            is_active=False,
        )
        assert alert_service.match_judgment_to_alert(judgment, alert_inactive) == []

    @pytest.mark.asyncio
    async def test_get_alert_matches_endpoint(self):
        user = create_mock_user()
        judgment = create_mock_judgment(
            subject_category="Criminal",
            court_code="sc",
            tags=["Section 438 CrPC"],
        )
        alert = Alert(
            id=uuid4(),
            user_id=str(user.id),
            title="Criminal SC Alerts",
            category="Criminal",
            court_code="sc",
            keywords=["Section 438"],
            is_active=True,
            created_at=datetime.now(UTC),
        )

        mock_db = create_mock_db()
        # Query 1: user alerts
        mock_alerts_res = MagicMock()
        mock_alerts_res.scalars.return_value.all.return_value = [alert]
        # Query 2: recent judgments
        mock_j_res = MagicMock()
        mock_j_res.scalars.return_value.all.return_value = [judgment]
        mock_db.execute.side_effect = [mock_alerts_res, mock_j_res]

        resp = await get_alert_matches(current_user=user, db=mock_db)
        assert isinstance(resp, AlertMatchesResponse)
        assert resp.total >= 1
        assert resp.matches[0].alert_id == alert.id
        assert resp.matches[0].judgment.id == judgment.id
        assert "Section 438" in resp.matches[0].matched_keywords


# ==============================================================================
# 8. Rate Limiter Tests (Upstash Redis + In-Memory Fallback)
# ==============================================================================
class TestRateLimiter:
    """Verifies request rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_below_threshold(self):
        limiter = RateLimiter(requests_per_minute=5)
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"

        for _ in range(4):
            allowed = await limiter(mock_request)
            assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_threshold_exceeded(self):
        limiter = RateLimiter(requests_per_minute=2)
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.200"

        # 2 allowed
        assert await limiter(mock_request) is True
        assert await limiter(mock_request) is True

        # 3rd should raise 429
        with pytest.raises(HTTPException) as exc_info:
            await limiter(mock_request)
        assert exc_info.value.status_code == 429
        assert "too many requests" in exc_info.value.detail.lower()


# ==============================================================================
# 9. OpenAPI Routes Registration & Documentation Tests
# ==============================================================================
class TestOpenAPIRouteRegistration:
    """Verifies all Phase 3 endpoints and OpenAPI documentation are mounted."""

    def test_openapi_contains_phase3_endpoints(self):
        root_routes = [route.path for route in app.routes if hasattr(route, "path")]

        # Verify documentation endpoints
        assert "/docs" in root_routes
        assert "/openapi.json" in root_routes
        assert "/health" in root_routes

        # Verify openapi schema paths contain all Phase 3 endpoints
        schema = app.openapi()
        paths = schema["paths"]

        # Core Auth
        assert "/api/v1/auth/register" in paths
        assert "/api/v1/auth/login" in paths
        assert "/api/v1/auth/google" in paths
        assert "/api/v1/auth/me" in paths
        assert "/api/v1/auth/refresh" in paths

        # Bookmarks & Alerts
        assert "/api/v1/bookmarks" in paths
        assert "/api/v1/bookmarks/{judgment_id}" in paths
        assert "/api/v1/alerts" in paths
        assert "/api/v1/alerts/{alert_id}" in paths
        assert "/api/v1/alerts/matches" in paths

        # Topics & Admin
        assert "/api/v1/topics" in paths
        assert "/api/v1/admin/refresh" in paths
