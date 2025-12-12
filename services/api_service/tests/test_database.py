"""
Tests for database connection and models.

These tests verify:
1. We can connect to the database
2. All tables were created by migrations
3. Basic CRUD operations work on models
"""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.db import Base

# Import ALL models so SQLAlchemy can resolve relationships between them
from app.models.user import User
from app.models.project import Project
from app.models.api_key import ApiKey
from app.models.event import Event
from app.models.alert import Alert
from app.models.alert_rule import AlertRule


# =============================================================================
# FIXTURES
# =============================================================================
# Fixtures provide reusable test setup. They run before each test that uses them.


@pytest.fixture
async def db_session():
    """
    Provide a database session for testing.
    
    This creates a fresh session for each test.
    Changes are rolled back after the test (not committed to DB).
    """
    # Create an engine connected to the test database
    engine = create_async_engine(settings.database_url)
    
    # Create a session factory
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create a session and yield it to the test
    async with async_session() as session:
        yield session
        # Rollback any changes made during the test
        await session.rollback()
    
    # Clean up
    await engine.dispose()


# =============================================================================
# CONNECTION TESTS
# =============================================================================


class TestDatabaseConnection:
    """Test that we can connect to the database."""

    @pytest.mark.asyncio
    async def test_can_connect(self, db_session: AsyncSession):
        """Verify basic database connectivity."""
        # Execute a simple query
        result = await db_session.execute(text("SELECT 1"))
        value = result.scalar()
        
        assert value == 1, "Should be able to execute simple query"

    @pytest.mark.asyncio
    async def test_database_is_postgresql(self, db_session: AsyncSession):
        """Verify we're connected to PostgreSQL (not SQLite or other)."""
        result = await db_session.execute(text("SELECT version()"))
        version = result.scalar()
        
        assert "PostgreSQL" in version, f"Expected PostgreSQL, got: {version}"


# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestDatabaseSchema:
    """Test that all expected tables exist."""

    @pytest.mark.asyncio
    async def test_users_table_exists(self, db_session: AsyncSession):
        """The 'users' table should exist."""
        result = await db_session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')")
        )
        exists = result.scalar()
        
        assert exists is True, "Table 'users' should exist"

    @pytest.mark.asyncio
    async def test_projects_table_exists(self, db_session: AsyncSession):
        """The 'projects' table should exist."""
        result = await db_session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'projects')")
        )
        exists = result.scalar()
        
        assert exists is True, "Table 'projects' should exist"

    @pytest.mark.asyncio
    async def test_api_keys_table_exists(self, db_session: AsyncSession):
        """The 'api_keys' table should exist."""
        result = await db_session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'api_keys')")
        )
        exists = result.scalar()
        
        assert exists is True, "Table 'api_keys' should exist"

    @pytest.mark.asyncio
    async def test_events_table_exists(self, db_session: AsyncSession):
        """The 'events' table should exist."""
        result = await db_session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events')")
        )
        exists = result.scalar()
        
        assert exists is True, "Table 'events' should exist"

    @pytest.mark.asyncio
    async def test_alerts_table_exists(self, db_session: AsyncSession):
        """The 'alerts' table should exist."""
        result = await db_session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alerts')")
        )
        exists = result.scalar()
        
        assert exists is True, "Table 'alerts' should exist"

    @pytest.mark.asyncio
    async def test_alert_rules_table_exists(self, db_session: AsyncSession):
        """The 'alert_rules' table should exist."""
        result = await db_session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alert_rules')")
        )
        exists = result.scalar()
        
        assert exists is True, "Table 'alert_rules' should exist"

    @pytest.mark.asyncio
    async def test_all_tables_count(self, db_session: AsyncSession):
        """We should have exactly 7 tables (6 models + alembic_version)."""
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
        )
        count = result.scalar()
        
        # 6 model tables + 1 alembic_version table = 7
        assert count == 7, f"Expected 7 tables, found {count}"


# =============================================================================
# MODEL CRUD TESTS
# =============================================================================


class TestUserModel:
    """Test basic CRUD operations on the User model."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Can create a new user."""
        user = User(
            email="test@example.com",
            password_hash="fake_hash_for_testing",
            role="USER",
        )
        
        db_session.add(user)
        await db_session.flush()  # Flush to get the ID without committing
        
        assert user.id is not None, "User should have an ID after flush"
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_user_default_role(self, db_session: AsyncSession):
        """User role should default to 'USER' if not specified."""
        # Note: server_default is set in DB, so we need to insert and refresh
        result = await db_session.execute(
            text("""
                INSERT INTO users (email, password_hash) 
                VALUES ('default_role@example.com', 'fake_hash')
                RETURNING role
            """)
        )
        role = result.scalar()
        
        assert role == "USER", f"Default role should be 'USER', got '{role}'"

    @pytest.mark.asyncio
    async def test_user_email_unique(self, db_session: AsyncSession):
        """Cannot create two users with the same email."""
        from sqlalchemy.exc import IntegrityError
        
        # Insert first user
        await db_session.execute(
            text("""
                INSERT INTO users (email, password_hash) 
                VALUES ('unique@example.com', 'hash1')
            """)
        )
        
        # Try to insert second user with same email
        with pytest.raises(IntegrityError):
            await db_session.execute(
                text("""
                    INSERT INTO users (email, password_hash) 
                    VALUES ('unique@example.com', 'hash2')
                """)
            )
            await db_session.flush()


class TestAlertRuleModel:
    """Test CRUD operations on the AlertRule model."""

    @pytest.mark.asyncio
    async def test_create_global_rule(self, db_session: AsyncSession):
        """Can create a global alert rule (project_id = NULL)."""
        result = await db_session.execute(
            text("""
                INSERT INTO alert_rules (name, field, operator, value, alert_level, message_template)
                VALUES ('test_rule', 'severity', '==', 'CRITICAL', 'HIGH', 'Test message')
                RETURNING id, project_id
            """)
        )
        row = result.fetchone()
        
        assert row[0] is not None, "Rule should have an ID"
        assert row[1] is None, "Global rule should have NULL project_id"

    @pytest.mark.asyncio
    async def test_global_rule_name_unique(self, db_session: AsyncSession):
        """Cannot create two global rules with the same name."""
        from sqlalchemy.exc import IntegrityError
        
        # Insert first global rule
        await db_session.execute(
            text("""
                INSERT INTO alert_rules (name, field, operator, value, alert_level, message_template)
                VALUES ('unique_rule', 'severity', '==', 'CRITICAL', 'HIGH', 'Message 1')
            """)
        )
        
        # Try to insert second global rule with same name
        with pytest.raises(IntegrityError):
            await db_session.execute(
                text("""
                    INSERT INTO alert_rules (name, field, operator, value, alert_level, message_template)
                    VALUES ('unique_rule', 'severity', '==', 'ERROR', 'MEDIUM', 'Message 2')
                """)
            )
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_seeded_rules_exist(self, db_session: AsyncSession):
        """The migration should have seeded 3 default global rules."""
        result = await db_session.execute(
            text("""
                SELECT name FROM alert_rules 
                WHERE project_id IS NULL 
                ORDER BY name
            """)
        )
        rules = [row[0] for row in result.fetchall()]
        
        assert "critical_event" in rules, "Should have critical_event rule"
        assert "error_event" in rules, "Should have error_event rule"
        assert "high_latency" in rules, "Should have high_latency rule"

    @pytest.mark.asyncio
    async def test_rule_enabled_default(self, db_session: AsyncSession):
        """Rule should be enabled by default."""
        result = await db_session.execute(
            text("""
                INSERT INTO alert_rules (name, field, operator, value, alert_level, message_template)
                VALUES ('default_enabled', 'severity', '==', 'CRITICAL', 'HIGH', 'Test')
                RETURNING enabled
            """)
        )
        enabled = result.scalar()
        
        assert enabled is True, "Rule should be enabled by default"

