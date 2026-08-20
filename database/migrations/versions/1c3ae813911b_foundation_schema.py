"""foundation schema

Revision ID: 1c3ae813911b
Revises: 
Create Date: 2026-08-19 08:24:10.711966
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '1c3ae813911b'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA identity")
    op.execute("CREATE SCHEMA platform")
    op.execute("CREATE SCHEMA knowledge")
    op.execute("CREATE SCHEMA governance")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'jarvis_app') THEN
                CREATE ROLE jarvis_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOINHERIT NOBYPASSRLS;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'jarvis_rls_definer'
            ) THEN
                CREATE ROLE jarvis_rls_definer NOLOGIN NOSUPERUSER NOCREATEDB
                    NOCREATEROLE NOINHERIT BYPASSRLS;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'jarvis_auth_definer'
            ) THEN
                CREATE ROLE jarvis_auth_definer NOLOGIN NOSUPERUSER NOCREATEDB
                    NOCREATEROLE NOINHERIT BYPASSRLS;
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT jarvis_rls_definer, jarvis_auth_definer TO CURRENT_USER")
    op.execute(
        """
        CREATE FUNCTION platform.semver_satisfies(
            candidate_version text,
            version_range text
        )
        RETURNS boolean
        LANGUAGE plpgsql
        IMMUTABLE
        STRICT
        SET search_path = pg_catalog
        AS $$
        DECLARE
            candidate_parts int[];
            target_parts int[];
            clause text;
            operator text;
            target_version text;
        BEGIN
            IF candidate_version !~ '^\\d+\\.\\d+\\.\\d+$' THEN
                RETURN false;
            END IF;
            candidate_parts := string_to_array(candidate_version, '.')::int[];
            FOREACH clause IN ARRAY string_to_array(version_range, ',') LOOP
                operator := substring(clause FROM '^(>=|<=|==|>|<)');
                target_version := regexp_replace(clause, '^(>=|<=|==|>|<)', '');
                IF operator IS NULL OR target_version !~ '^\\d+\\.\\d+\\.\\d+$' THEN
                    RETURN false;
                END IF;
                target_parts := string_to_array(target_version, '.')::int[];
                IF operator = '>=' AND NOT (candidate_parts >= target_parts) THEN
                    RETURN false;
                ELSIF operator = '<=' AND NOT (candidate_parts <= target_parts) THEN
                    RETURN false;
                ELSIF operator = '>' AND NOT (candidate_parts > target_parts) THEN
                    RETURN false;
                ELSIF operator = '<' AND NOT (candidate_parts < target_parts) THEN
                    RETURN false;
                ELSIF operator = '==' AND NOT (candidate_parts = target_parts) THEN
                    RETURN false;
                END IF;
            END LOOP;
            RETURN true;
        END
        $$;
        """
    )
    op.create_table('oidc_login_transactions',
    sa.Column('issuer', sa.String(length=500), nullable=False),
    sa.Column('state_digest', sa.String(length=64), nullable=False),
    sa.Column('binding_digest', sa.String(length=64), nullable=False),
    sa.Column('verifier_ciphertext', sa.String(), nullable=False),
    sa.Column('nonce_ciphertext', sa.String(), nullable=False),
    sa.Column('return_path', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oidc_login_transactions')),
    sa.UniqueConstraint('state_digest', name='state_digest'),
    schema='identity'
    )
    op.create_table('permissions',
    sa.Column('key', sa.String(length=150), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permissions')),
    sa.UniqueConstraint('key', name=op.f('uq_permissions_key')),
    schema='identity'
    )
    op.create_table('roles',
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
    sa.UniqueConstraint('key', name=op.f('uq_roles_key')),
    schema='identity'
    )
    op.create_table('users',
    sa.Column('display_name', sa.String(length=200), nullable=False),
    sa.Column('primary_email', sa.String(length=320), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'disabled')", name=op.f('ck_users_valid_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    schema='identity'
    )
    op.create_table('resource_types',
    sa.Column('key', sa.String(length=150), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('module_key', sa.String(length=150), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resource_types')),
    sa.UniqueConstraint('key', name=op.f('uq_resource_types_key')),
    schema='knowledge'
    )
    op.create_table('modules',
    sa.Column('key', sa.String(length=150), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=False),
    sa.Column('lifecycle_status', sa.String(length=30), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_modules')),
    sa.UniqueConstraint('key', name=op.f('uq_modules_key')),
    schema='platform'
    )
    op.create_table('auth_identities',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('issuer', sa.String(length=500), nullable=False),
    sa.Column('subject', sa.String(length=500), nullable=False),
    sa.Column('last_authenticated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['identity.users.id'], name=op.f('fk_auth_identities_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_identities')),
    sa.UniqueConstraint('issuer', 'subject', name='issuer_subject'),
    schema='identity'
    )
    op.create_index(op.f('ix_auth_identities_user_id'), 'auth_identities', ['user_id'], unique=False, schema='identity')
    op.create_table('role_permissions',
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('permission_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['identity.permissions.id'], name=op.f('fk_role_permissions_permission_id_permissions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['identity.roles.id'], name=op.f('fk_role_permissions_role_id_roles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('role_id', 'permission_id', name=op.f('pk_role_permissions')),
    schema='identity'
    )
    op.create_table('sessions',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_digest', sa.String(length=64), nullable=False),
    sa.Column('digest_key_version', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('auth_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('mfa_context', sa.String(length=200), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['identity.users.id'], name=op.f('fk_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sessions')),
    sa.UniqueConstraint('token_digest', name='token_digest'),
    schema='identity'
    )
    op.create_index('ix_sessions_active_expiry', 'sessions', ['expires_at'], unique=False, schema='identity', postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False, schema='identity')
    op.create_table('workspaces',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('lock_version', sa.Integer(), nullable=False),
    sa.Column('created_by_user_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('personal', 'team')", name=op.f('ck_workspaces_valid_kind')),
    sa.CheckConstraint("status IN ('active', 'archived')", name=op.f('ck_workspaces_valid_status')),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['identity.users.id'], name=op.f('fk_workspaces_created_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workspaces')),
    sa.UniqueConstraint('slug', name=op.f('uq_workspaces_slug')),
    schema='identity'
    )
    op.create_table('capabilities',
    sa.Column('module_id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("kind IN ('permission', 'route', 'component', 'provider', 'handler', 'ai_tool')", name=op.f('ck_capabilities_valid_kind')),
    sa.ForeignKeyConstraint(['module_id'], ['platform.modules.id'], name=op.f('fk_capabilities_module_id_modules'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_capabilities')),
    sa.UniqueConstraint('id', 'module_id', name='uq_capabilities_id_module'),
    sa.UniqueConstraint('key', name=op.f('uq_capabilities_key')),
    schema='platform'
    )
    op.create_table('module_releases',
    sa.Column('module_id', sa.UUID(), nullable=False),
    sa.Column('semantic_version', sa.String(length=50), nullable=False),
    sa.Column('manifest_version', sa.String(length=20), nullable=False),
    sa.Column('core_compatibility', sa.String(length=100), nullable=False),
    sa.Column('code_digest', sa.String(length=100), nullable=False),
    sa.Column('manifest_digest', sa.String(length=100), nullable=False),
    sa.Column('configuration_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['module_id'], ['platform.modules.id'], name=op.f('fk_module_releases_module_id_modules'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_module_releases')),
    sa.UniqueConstraint('id', 'module_id', name='uq_module_releases_id_module'),
    sa.UniqueConstraint('id', 'module_id', 'semantic_version', name='uq_module_releases_id_module_version'),
    sa.UniqueConstraint('module_id', 'semantic_version', name='module_version'),
    schema='platform'
    )
    op.create_table('audit_events',
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('actor_user_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=200), nullable=False),
    sa.Column('resource_type', sa.String(length=100), nullable=False),
    sa.Column('resource_id', sa.UUID(), nullable=True),
    sa.Column('request_id', sa.String(length=100), nullable=True),
    sa.Column('outcome', sa.String(length=30), nullable=False),
    sa.Column('before_hash', sa.String(length=64), nullable=True),
    sa.Column('after_hash', sa.String(length=64), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['identity.users.id'], name=op.f('fk_audit_events_actor_user_id_users')),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_audit_events_workspace_id_workspaces'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_events')),
    schema='governance'
    )
    op.create_index(op.f('ix_audit_events_workspace_id'), 'audit_events', ['workspace_id'], unique=False, schema='governance')
    op.create_table('outbox_events',
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('event_type', sa.String(length=200), nullable=False),
    sa.Column('aggregate_type', sa.String(length=100), nullable=False),
    sa.Column('aggregate_id', sa.UUID(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_outbox_events_workspace_id_workspaces'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outbox_events')),
    schema='governance'
    )
    op.create_index(op.f('ix_outbox_events_workspace_id'), 'outbox_events', ['workspace_id'], unique=False, schema='governance')
    op.create_table('workspace_memberships',
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('active', 'suspended')", name=op.f('ck_workspace_memberships_valid_status')),
    sa.ForeignKeyConstraint(['role_id'], ['identity.roles.id'], name=op.f('fk_workspace_memberships_role_id_roles')),
    sa.ForeignKeyConstraint(['user_id'], ['identity.users.id'], name=op.f('fk_workspace_memberships_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_workspace_memberships_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('workspace_id', 'user_id', name=op.f('pk_workspace_memberships')),
    schema='identity'
    )
    op.create_table('resource_namespaces',
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('key', sa.String(length=150), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('read_only', sa.Boolean(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(kind = 'system' AND workspace_id IS NULL) OR (kind = 'workspace' AND workspace_id IS NOT NULL)", name=op.f('ck_resource_namespaces_workspace_scope')),
    sa.CheckConstraint("kind IN ('system', 'workspace')", name=op.f('ck_resource_namespaces_valid_kind')),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_resource_namespaces_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resource_namespaces')),
    sa.UniqueConstraint('id', 'workspace_id', name='uq_resource_namespaces_id_workspace'),
    sa.UniqueConstraint('workspace_id', 'key', name='uq_resource_namespaces_workspace_key'),
    schema='knowledge'
    )
    op.create_index(op.f('ix_resource_namespaces_workspace_id'), 'resource_namespaces', ['workspace_id'], unique=False, schema='knowledge')
    op.create_table('module_dependencies',
    sa.Column('module_release_id', sa.UUID(), nullable=False),
    sa.Column('target_module_id', sa.UUID(), nullable=False),
    sa.Column('version_range', sa.String(length=100), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['module_release_id'], ['platform.module_releases.id'], name=op.f('fk_module_dependencies_module_release_id_module_releases'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['target_module_id'], ['platform.modules.id'], name=op.f('fk_module_dependencies_target_module_id_modules')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_module_dependencies')),
    sa.UniqueConstraint('id', 'target_module_id', name='uq_module_dependencies_id_target'),
    sa.UniqueConstraint('id', 'target_module_id', 'version_range', 'module_release_id', name='uq_module_dependencies_resolution_identity'),
    sa.UniqueConstraint('module_release_id', 'target_module_id', name='release_target_module'),
    schema='platform'
    )
    op.create_table('module_installations',
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('module_id', sa.UUID(), nullable=False),
    sa.Column('module_release_id', sa.UUID(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('lock_version', sa.Integer(), nullable=False),
    sa.Column('installed_by_user_id', sa.UUID(), nullable=False),
    sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('installed', 'removed')", name=op.f('ck_module_installations_valid_status')),
    sa.ForeignKeyConstraint(['installed_by_user_id'], ['identity.users.id'], name=op.f('fk_module_installations_installed_by_user_id_users')),
    sa.ForeignKeyConstraint(['module_id'], ['platform.modules.id'], name=op.f('fk_module_installations_module_id_modules')),
    sa.ForeignKeyConstraint(['module_release_id', 'module_id'], ['platform.module_releases.id', 'platform.module_releases.module_id'], name='fk_module_installations_release_module'),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_module_installations_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_module_installations')),
    sa.UniqueConstraint('id', 'module_release_id', name='uq_module_installations_id_release'),
    sa.UniqueConstraint('workspace_id', 'module_id', name='workspace_module'),
    schema='platform'
    )
    op.create_index(op.f('ix_module_installations_workspace_id'), 'module_installations', ['workspace_id'], unique=False, schema='platform')
    op.create_table('module_release_capabilities',
    sa.Column('module_release_id', sa.UUID(), nullable=False),
    sa.Column('capability_id', sa.UUID(), nullable=False),
    sa.Column('module_id', sa.UUID(), nullable=False),
    sa.Column('implementation_version', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['capability_id', 'module_id'], ['platform.capabilities.id', 'platform.capabilities.module_id'], name='fk_release_capability_same_module', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['module_release_id', 'module_id'], ['platform.module_releases.id', 'platform.module_releases.module_id'], name='fk_release_capability_release_module', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('module_release_id', 'capability_id', name=op.f('pk_module_release_capabilities')),
    schema='platform'
    )
    op.create_table('navigation_nodes',
    sa.Column('module_release_id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=200), nullable=False),
    sa.Column('parent_key', sa.String(length=200), nullable=True),
    sa.Column('route_key', sa.String(length=200), nullable=False),
    sa.Column('path', sa.String(length=300), nullable=False),
    sa.Column('component_key', sa.String(length=200), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('icon_key', sa.String(length=100), nullable=False),
    sa.Column('default_order', sa.Integer(), nullable=False),
    sa.Column('required_permission', sa.String(length=200), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['module_release_id'], ['platform.module_releases.id'], name=op.f('fk_navigation_nodes_module_release_id_module_releases'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_navigation_nodes')),
    sa.UniqueConstraint('module_release_id', 'key', name='release_key'),
    schema='platform'
    )
    op.create_table('navigation_overrides',
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('node_key', sa.String(length=200), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=True),
    sa.Column('order', sa.Integer(), nullable=True),
    sa.Column('hidden', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_navigation_overrides_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_navigation_overrides')),
    sa.UniqueConstraint('workspace_id', 'node_key', name='workspace_node'),
    schema='platform'
    )
    op.create_index(op.f('ix_navigation_overrides_workspace_id'), 'navigation_overrides', ['workspace_id'], unique=False, schema='platform')
    op.create_table('workspace_preferences',
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('values', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('workflow_defaults', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('personal_categories', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('lock_version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_workspace_preferences_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('workspace_id', name=op.f('pk_workspace_preferences')),
    schema='platform'
    )
    op.create_table('resources',
    sa.Column('resource_type_id', sa.UUID(), nullable=False),
    sa.Column('namespace_id', sa.UUID(), nullable=False),
    sa.Column('scope', sa.String(length=20), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('lifecycle_status', sa.String(length=20), nullable=False),
    sa.Column('lock_version', sa.Integer(), nullable=False),
    sa.Column('current_revision_id', sa.UUID(), nullable=True),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(scope = 'system' AND workspace_id IS NULL) OR (scope = 'workspace' AND workspace_id IS NOT NULL)", name=op.f('ck_resources_workspace_scope')),
    sa.CheckConstraint("lifecycle_status IN ('active', 'archived', 'deleted')", name=op.f('ck_resources_valid_lifecycle_status')),
    sa.CheckConstraint("scope IN ('system', 'workspace')", name=op.f('ck_resources_valid_scope')),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['identity.users.id'], name=op.f('fk_resources_created_by_user_id_users')),
    sa.ForeignKeyConstraint(['namespace_id', 'workspace_id'], ['knowledge.resource_namespaces.id', 'knowledge.resource_namespaces.workspace_id'], name='namespace_workspace'),
    sa.ForeignKeyConstraint(['namespace_id'], ['knowledge.resource_namespaces.id'], name=op.f('fk_resources_namespace_id_resource_namespaces')),
    sa.ForeignKeyConstraint(['resource_type_id'], ['knowledge.resource_types.id'], name=op.f('fk_resources_resource_type_id_resource_types')),
    sa.ForeignKeyConstraint(['workspace_id'], ['identity.workspaces.id'], name=op.f('fk_resources_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resources')),
    sa.UniqueConstraint('id', 'workspace_id', name='uq_resources_id_workspace'),
    sa.UniqueConstraint('namespace_id', 'slug', name='uq_resources_namespace_slug'),
    schema='knowledge'
    )
    op.create_index(op.f('ix_resources_resource_type_id'), 'resources', ['resource_type_id'], unique=False, schema='knowledge')
    op.create_index(op.f('ix_resources_workspace_id'), 'resources', ['workspace_id'], unique=False, schema='knowledge')
    op.create_table('module_dependency_resolutions',
    sa.Column('installation_id', sa.UUID(), nullable=False),
    sa.Column('dependency_id', sa.UUID(), nullable=False),
    sa.Column('resolved_release_id', sa.UUID(), nullable=False),
    sa.Column('target_module_id', sa.UUID(), nullable=False),
    sa.Column('dependent_release_id', sa.UUID(), nullable=False),
    sa.Column('version_range', sa.String(length=100), nullable=False),
    sa.Column('resolved_version', sa.String(length=50), nullable=False),
    sa.CheckConstraint('platform.semver_satisfies(resolved_version, version_range)', name=op.f('ck_module_dependency_resolutions_semver_range')),
    sa.ForeignKeyConstraint(['dependency_id', 'target_module_id', 'version_range', 'dependent_release_id'], ['platform.module_dependencies.id', 'platform.module_dependencies.target_module_id', 'platform.module_dependencies.version_range', 'platform.module_dependencies.module_release_id'], name='fk_dependency_resolution_declared_target', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['installation_id'], ['platform.module_installations.id'], name=op.f('fk_module_dependency_resolutions_installation_id_module_installations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['installation_id', 'dependent_release_id'], ['platform.module_installations.id', 'platform.module_installations.module_release_id'], name='fk_dependency_resolution_installation_release'),
    sa.ForeignKeyConstraint(['resolved_release_id', 'target_module_id', 'resolved_version'], ['platform.module_releases.id', 'platform.module_releases.module_id', 'platform.module_releases.semantic_version'], name='fk_dependency_resolution_target_release'),
    sa.PrimaryKeyConstraint('installation_id', 'dependency_id', name=op.f('pk_module_dependency_resolutions')),
    schema='platform'
    )
    op.create_table('resource_revisions',
    sa.Column('resource_id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('scope', sa.String(length=20), nullable=False),
    sa.Column('revision_number', sa.Integer(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('authority', sa.String(length=50), nullable=False),
    sa.Column('confidence', sa.Numeric(precision=6, scale=5), nullable=True),
    sa.Column('source_status', sa.String(length=50), nullable=False),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('supersedes_revision_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("(scope = 'system' AND workspace_id IS NULL) OR (scope = 'workspace' AND workspace_id IS NOT NULL)", name=op.f('ck_resource_revisions_workspace_scope')),
    sa.CheckConstraint("scope IN ('system', 'workspace')", name=op.f('ck_resource_revisions_valid_scope')),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['identity.users.id'], name=op.f('fk_resource_revisions_created_by_user_id_users')),
    sa.ForeignKeyConstraint(['resource_id', 'workspace_id'], ['knowledge.resources.id', 'knowledge.resources.workspace_id'], name='resource_workspace', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['resource_id'], ['knowledge.resources.id'], name=op.f('fk_resource_revisions_resource_id_resources'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['supersedes_revision_id'], ['knowledge.resource_revisions.id'], name=op.f('fk_resource_revisions_supersedes_revision_id_resource_revisions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resource_revisions')),
    sa.UniqueConstraint('id', 'resource_id', name='uq_resource_revisions_id_resource'),
    sa.UniqueConstraint('resource_id', 'revision_number', name='uq_resource_revisions_resource_number'),
    schema='knowledge'
    )
    op.create_index(op.f('ix_resource_revisions_workspace_id'), 'resource_revisions', ['workspace_id'], unique=False, schema='knowledge')
    op.create_table('resource_revision_lifecycle_events',
    sa.Column('resource_revision_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.String(length=30), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('actor_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("event_type IN ('superseded', 'deprecated', 'withdrawn', 'restored')", name=op.f('ck_resource_revision_lifecycle_events_valid_event_type')),
    sa.ForeignKeyConstraint(['actor_user_id'], ['identity.users.id'], name=op.f('fk_resource_revision_lifecycle_events_actor_user_id_users')),
    sa.ForeignKeyConstraint(['resource_revision_id'], ['knowledge.resource_revisions.id'], name=op.f('fk_resource_revision_lifecycle_events_resource_revision_id_resource_revisions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resource_revision_lifecycle_events')),
    schema='knowledge'
    )
    op.create_foreign_key(
        "fk_resources_current_revision",
        "resources",
        "resource_revisions",
        ["current_revision_id", "id"],
        ["id", "resource_id"],
        source_schema="knowledge",
        referent_schema="knowledge",
    )
    op.create_foreign_key(
        "fk_resource_revisions_supersedes_same_resource",
        "resource_revisions",
        "resource_revisions",
        ["supersedes_revision_id", "resource_id"],
        ["id", "resource_id"],
        source_schema="knowledge",
        referent_schema="knowledge",
    )
    op.create_index(
        "uq_resource_namespaces_system_key",
        "resource_namespaces",
        ["key"],
        unique=True,
        schema="knowledge",
        postgresql_where=sa.text("kind = 'system'"),
    )
    op.create_index(
        "uq_resource_namespaces_default_workspace",
        "resource_namespaces",
        ["workspace_id"],
        unique=True,
        schema="knowledge",
        postgresql_where=sa.text("kind = 'workspace' AND is_default"),
    )
    op.execute(
        """
        CREATE FUNCTION knowledge.enforce_resource_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = pg_catalog, knowledge
        AS $$
        DECLARE
            namespace_kind text;
            namespace_workspace_id uuid;
        BEGIN
            SELECT kind, workspace_id
            INTO namespace_kind, namespace_workspace_id
            FROM knowledge.resource_namespaces
            WHERE id = NEW.namespace_id;

            IF namespace_kind IS NULL THEN
                RAISE EXCEPTION 'Resource namespace does not exist'
                    USING ERRCODE = '23503';
            END IF;
            IF namespace_kind = 'system' AND (
                NEW.scope <> 'system' OR NEW.workspace_id IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'System namespace requires system resource scope'
                    USING ERRCODE = '23514';
            END IF;
            IF namespace_kind = 'workspace' AND (
                NEW.scope <> 'workspace'
                OR NEW.workspace_id IS DISTINCT FROM namespace_workspace_id
            ) THEN
                RAISE EXCEPTION 'Workspace resource scope must match its namespace'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE TRIGGER resources_scope_guard
        BEFORE INSERT OR UPDATE OF namespace_id, scope, workspace_id
        ON knowledge.resources
        FOR EACH ROW EXECUTE FUNCTION knowledge.enforce_resource_scope();

        CREATE FUNCTION knowledge.enforce_revision_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = pg_catalog, knowledge
        AS $$
        DECLARE
            parent_scope text;
            parent_workspace_id uuid;
        BEGIN
            SELECT scope, workspace_id
            INTO parent_scope, parent_workspace_id
            FROM knowledge.resources
            WHERE id = NEW.resource_id;

            IF parent_scope IS NULL THEN
                RAISE EXCEPTION 'Revision resource does not exist'
                    USING ERRCODE = '23503';
            END IF;
            IF NEW.scope IS DISTINCT FROM parent_scope
                OR NEW.workspace_id IS DISTINCT FROM parent_workspace_id THEN
                RAISE EXCEPTION 'Revision scope must match its resource'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE TRIGGER revisions_scope_guard
        BEFORE INSERT OR UPDATE OF resource_id, scope, workspace_id
        ON knowledge.resource_revisions
        FOR EACH ROW EXECUTE FUNCTION knowledge.enforce_revision_scope();
        """
    )

    op.execute(
        """
        CREATE FUNCTION identity.current_user_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
            SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
        $$;

        CREATE FUNCTION identity.current_workspace_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
            SELECT NULLIF(current_setting('app.workspace_id', true), '')::uuid
        $$;

        CREATE FUNCTION identity.has_workspace_membership(target_workspace_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, identity
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM identity.workspace_memberships membership
                JOIN identity.users app_user ON app_user.id = membership.user_id
                WHERE membership.workspace_id = target_workspace_id
                  AND membership.user_id =
                      NULLIF(current_setting('app.user_id', true), '')::uuid
                  AND membership.status = 'active'
                  AND app_user.status = 'active'
            )
        $$;

        CREATE FUNCTION identity.is_workspace_creator(target_workspace_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, identity
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM identity.workspaces workspace
                WHERE workspace.id = target_workspace_id
                  AND workspace.created_by_user_id =
                      NULLIF(current_setting('app.user_id', true), '')::uuid
            )
        $$;

        CREATE FUNCTION identity.resolve_session(p_token_digest text)
        RETURNS TABLE(session_id uuid, user_id uuid, auth_time timestamptz)
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, identity
        AS $$
            SELECT app_session.id, app_session.user_id, app_session.auth_time
            FROM identity.sessions app_session
            JOIN identity.users app_user ON app_user.id = app_session.user_id
            WHERE app_session.token_digest = p_token_digest
              AND app_session.revoked_at IS NULL
              AND app_session.expires_at > now()
              AND app_user.status = 'active'
            LIMIT 1
        $$;

        CREATE FUNCTION identity.provision_oidc_user(
            p_issuer text,
            p_subject text,
            p_email text,
            p_display_name text
        )
        RETURNS uuid
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, identity
        AS $$
        DECLARE
            resolved_user_id uuid;
        BEGIN
            SELECT auth_identity.user_id
            INTO resolved_user_id
            FROM identity.auth_identities auth_identity
            WHERE auth_identity.issuer = p_issuer
              AND auth_identity.subject = p_subject;

            IF resolved_user_id IS NOT NULL THEN
                UPDATE identity.auth_identities
                SET last_authenticated_at = now()
                WHERE issuer = p_issuer AND subject = p_subject;
                RETURN resolved_user_id;
            END IF;

            INSERT INTO identity.users (
                id, display_name, primary_email, status, created_at, updated_at
            )
            VALUES (
                gen_random_uuid(), p_display_name, p_email, 'active', now(), now()
            )
            RETURNING id INTO resolved_user_id;

            INSERT INTO identity.auth_identities (
                id, user_id, issuer, subject, last_authenticated_at
            )
            VALUES (
                gen_random_uuid(), resolved_user_id, p_issuer, p_subject, now()
            );
            RETURN resolved_user_id;
        END
        $$;

        REVOKE ALL ON FUNCTION identity.has_workspace_membership(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION identity.is_workspace_creator(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION identity.resolve_session(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION identity.provision_oidc_user(text, text, text, text)
            FROM PUBLIC;
        """
    )
    op.execute(
        """
        GRANT USAGE ON SCHEMA identity TO jarvis_rls_definer, jarvis_auth_definer;
        GRANT SELECT ON
            identity.users,
            identity.workspace_memberships,
            identity.workspaces,
            identity.sessions
            TO jarvis_rls_definer;
        GRANT SELECT, INSERT, UPDATE ON
            identity.users,
            identity.auth_identities
            TO jarvis_auth_definer;

        ALTER FUNCTION identity.has_workspace_membership(uuid)
            OWNER TO jarvis_rls_definer;
        ALTER FUNCTION identity.is_workspace_creator(uuid)
            OWNER TO jarvis_rls_definer;
        ALTER FUNCTION identity.resolve_session(text)
            OWNER TO jarvis_rls_definer;
        ALTER FUNCTION identity.provision_oidc_user(text, text, text, text)
            OWNER TO jarvis_auth_definer;
        """
    )

    for table in (
        "users",
        "auth_identities",
        "sessions",
        "workspaces",
        "workspace_memberships",
    ):
        op.execute(f"ALTER TABLE identity.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE identity.{table} FORCE ROW LEVEL SECURITY")

    for table in ("resource_namespaces", "resources", "resource_revisions"):
        op.execute(f"ALTER TABLE knowledge.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE knowledge.{table} FORCE ROW LEVEL SECURITY")

    op.execute(
        "ALTER TABLE knowledge.resource_revision_lifecycle_events ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE knowledge.resource_revision_lifecycle_events FORCE ROW LEVEL SECURITY"
    )

    for table in (
        "module_installations",
        "module_dependency_resolutions",
        "workspace_preferences",
        "navigation_overrides",
    ):
        op.execute(f"ALTER TABLE platform.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE platform.{table} FORCE ROW LEVEL SECURITY")

    for table in ("audit_events", "outbox_events"):
        op.execute(f"ALTER TABLE governance.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE governance.{table} FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY users_self ON identity.users
            USING (id = identity.current_user_id())
            WITH CHECK (id = identity.current_user_id());
        CREATE POLICY auth_identities_self ON identity.auth_identities
            USING (user_id = identity.current_user_id())
            WITH CHECK (user_id = identity.current_user_id());
        CREATE POLICY sessions_self ON identity.sessions
            USING (user_id = identity.current_user_id())
            WITH CHECK (user_id = identity.current_user_id());

        CREATE POLICY workspaces_select ON identity.workspaces FOR SELECT
            USING (identity.has_workspace_membership(id));
        CREATE POLICY workspaces_insert ON identity.workspaces FOR INSERT
            WITH CHECK (created_by_user_id = identity.current_user_id());
        CREATE POLICY workspaces_update ON identity.workspaces FOR UPDATE
            USING (identity.has_workspace_membership(id))
            WITH CHECK (identity.has_workspace_membership(id));

        CREATE POLICY memberships_select ON identity.workspace_memberships FOR SELECT
            USING (identity.has_workspace_membership(workspace_id));
        CREATE POLICY memberships_insert ON identity.workspace_memberships FOR INSERT
            WITH CHECK (
                identity.has_workspace_membership(workspace_id)
                OR (
                    user_id = identity.current_user_id()
                    AND identity.is_workspace_creator(workspace_id)
                )
            );
        CREATE POLICY memberships_update ON identity.workspace_memberships FOR UPDATE
            USING (identity.has_workspace_membership(workspace_id))
            WITH CHECK (identity.has_workspace_membership(workspace_id));

        CREATE POLICY namespaces_select ON knowledge.resource_namespaces FOR SELECT
            USING (kind = 'system' OR identity.has_workspace_membership(workspace_id));
        CREATE POLICY namespaces_insert ON knowledge.resource_namespaces FOR INSERT
            WITH CHECK (
                kind = 'workspace'
                AND workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );
        CREATE POLICY namespaces_update ON knowledge.resource_namespaces FOR UPDATE
            USING (
                kind = 'workspace'
                AND workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            )
            WITH CHECK (
                kind = 'workspace'
                AND workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );

        CREATE POLICY resources_select ON knowledge.resources FOR SELECT
            USING (
                scope = 'system'
                OR (
                    workspace_id = identity.current_workspace_id()
                    AND identity.has_workspace_membership(workspace_id)
                )
            );
        CREATE POLICY resources_insert ON knowledge.resources FOR INSERT
            WITH CHECK (
                scope = 'workspace'
                AND workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );
        CREATE POLICY resources_update ON knowledge.resources FOR UPDATE
            USING (
                scope = 'workspace'
                AND workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            )
            WITH CHECK (
                scope = 'workspace'
                AND workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );

        CREATE POLICY revisions_select ON knowledge.resource_revisions FOR SELECT
            USING (
                scope = 'system'
                OR (
                    workspace_id = identity.current_workspace_id()
                    AND identity.has_workspace_membership(workspace_id)
                )
            );
        CREATE POLICY revisions_insert ON knowledge.resource_revisions FOR INSERT
            WITH CHECK (
                scope = 'workspace'
                AND workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );

        CREATE POLICY revision_events_select
            ON knowledge.resource_revision_lifecycle_events FOR SELECT
            USING (
                EXISTS (
                    SELECT 1
                    FROM knowledge.resource_revisions revision
                    WHERE revision.id = resource_revision_id
                )
            );
        CREATE POLICY revision_events_insert
            ON knowledge.resource_revision_lifecycle_events FOR INSERT
            WITH CHECK (
                EXISTS (
                    SELECT 1
                    FROM knowledge.resource_revisions revision
                    WHERE revision.id = resource_revision_id
                      AND revision.scope = 'workspace'
                      AND revision.workspace_id = identity.current_workspace_id()
                      AND identity.has_workspace_membership(revision.workspace_id)
                )
            );

        CREATE POLICY installations_access ON platform.module_installations
            USING (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            )
            WITH CHECK (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );
        CREATE POLICY dependency_resolutions_access
            ON platform.module_dependency_resolutions
            USING (
                EXISTS (
                    SELECT 1
                    FROM platform.module_installations installation
                    WHERE installation.id = installation_id
                )
            )
            WITH CHECK (
                EXISTS (
                    SELECT 1
                    FROM platform.module_installations installation
                    WHERE installation.id = installation_id
                )
            );
        CREATE POLICY preferences_access ON platform.workspace_preferences
            USING (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            )
            WITH CHECK (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );
        CREATE POLICY navigation_overrides_access ON platform.navigation_overrides
            USING (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            )
            WITH CHECK (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );

        CREATE POLICY audit_access ON governance.audit_events
            USING (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            )
            WITH CHECK (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );
        CREATE POLICY outbox_access ON governance.outbox_events
            USING (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            )
            WITH CHECK (
                workspace_id = identity.current_workspace_id()
                AND identity.has_workspace_membership(workspace_id)
            );
        """
    )

    op.execute(
        """
        GRANT USAGE ON SCHEMA identity, platform, knowledge, governance TO jarvis_app;
        GRANT EXECUTE ON FUNCTION identity.current_user_id() TO jarvis_app;
        GRANT EXECUTE ON FUNCTION identity.current_workspace_id() TO jarvis_app;
        GRANT EXECUTE ON FUNCTION identity.has_workspace_membership(uuid) TO jarvis_app;
        GRANT EXECUTE ON FUNCTION identity.is_workspace_creator(uuid) TO jarvis_app;
        GRANT EXECUTE ON FUNCTION identity.resolve_session(text) TO jarvis_app;
        GRANT EXECUTE ON FUNCTION identity.provision_oidc_user(text, text, text, text)
            TO jarvis_app;

        GRANT SELECT ON
            identity.users,
            identity.auth_identities,
            identity.roles,
            identity.permissions,
            identity.role_permissions
            TO jarvis_app;
        GRANT SELECT, INSERT, UPDATE ON
            identity.sessions,
            identity.oidc_login_transactions,
            identity.workspaces,
            identity.workspace_memberships
            TO jarvis_app;
        GRANT DELETE ON identity.oidc_login_transactions TO jarvis_app;

        GRANT SELECT ON
            platform.modules,
            platform.module_releases,
            platform.capabilities,
            platform.module_release_capabilities,
            platform.module_dependencies,
            platform.navigation_nodes
            TO jarvis_app;
        GRANT SELECT, INSERT, UPDATE ON
            platform.module_installations,
            platform.module_dependency_resolutions,
            platform.workspace_preferences,
            platform.navigation_overrides
            TO jarvis_app;
        GRANT DELETE ON
            platform.module_dependency_resolutions,
            platform.navigation_overrides
            TO jarvis_app;

        GRANT SELECT ON knowledge.resource_types TO jarvis_app;
        GRANT SELECT, INSERT, UPDATE ON
            knowledge.resource_namespaces,
            knowledge.resources,
            knowledge.resource_revisions,
            knowledge.resource_revision_lifecycle_events
            TO jarvis_app;

        GRANT SELECT, INSERT ON governance.audit_events, governance.outbox_events
            TO jarvis_app;

        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'jarvis_runtime') THEN
                EXECUTE 'GRANT jarvis_app TO jarvis_runtime';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.semver_satisfies(text, text) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS knowledge.enforce_revision_scope() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS knowledge.enforce_resource_scope() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS identity.provision_oidc_user(text, text, text, text) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS identity.resolve_session(text) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS identity.is_workspace_creator(uuid) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS identity.has_workspace_membership(uuid) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS identity.current_workspace_id() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS identity.current_user_id() CASCADE")
    op.drop_constraint(
        "fk_resources_current_revision",
        "resources",
        schema="knowledge",
        type_="foreignkey",
    )
    op.drop_table('resource_revision_lifecycle_events', schema='knowledge')
    op.drop_index(op.f('ix_resource_revisions_workspace_id'), table_name='resource_revisions', schema='knowledge')
    op.drop_table('resource_revisions', schema='knowledge')
    op.drop_table('module_dependency_resolutions', schema='platform')
    op.drop_index(op.f('ix_resources_workspace_id'), table_name='resources', schema='knowledge')
    op.drop_index(op.f('ix_resources_resource_type_id'), table_name='resources', schema='knowledge')
    op.drop_table('resources', schema='knowledge')
    op.drop_table('workspace_preferences', schema='platform')
    op.drop_index(op.f('ix_navigation_overrides_workspace_id'), table_name='navigation_overrides', schema='platform')
    op.drop_table('navigation_overrides', schema='platform')
    op.drop_table('navigation_nodes', schema='platform')
    op.drop_table('module_release_capabilities', schema='platform')
    op.drop_index(op.f('ix_module_installations_workspace_id'), table_name='module_installations', schema='platform')
    op.drop_table('module_installations', schema='platform')
    op.drop_table('module_dependencies', schema='platform')
    op.drop_index(op.f('ix_resource_namespaces_workspace_id'), table_name='resource_namespaces', schema='knowledge')
    op.drop_index(
        "uq_resource_namespaces_default_workspace",
        table_name="resource_namespaces",
        schema="knowledge",
    )
    op.drop_index(
        "uq_resource_namespaces_system_key",
        table_name="resource_namespaces",
        schema="knowledge",
    )
    op.drop_table('resource_namespaces', schema='knowledge')
    op.drop_table('workspace_memberships', schema='identity')
    op.drop_index(op.f('ix_outbox_events_workspace_id'), table_name='outbox_events', schema='governance')
    op.drop_table('outbox_events', schema='governance')
    op.drop_index(op.f('ix_audit_events_workspace_id'), table_name='audit_events', schema='governance')
    op.drop_table('audit_events', schema='governance')
    op.drop_table('module_releases', schema='platform')
    op.drop_table('capabilities', schema='platform')
    op.drop_table('workspaces', schema='identity')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions', schema='identity')
    op.drop_index('ix_sessions_active_expiry', table_name='sessions', schema='identity')
    op.drop_table('sessions', schema='identity')
    op.drop_table('role_permissions', schema='identity')
    op.drop_index(op.f('ix_auth_identities_user_id'), table_name='auth_identities', schema='identity')
    op.drop_table('auth_identities', schema='identity')
    op.drop_table('modules', schema='platform')
    op.drop_table('resource_types', schema='knowledge')
    op.drop_table('users', schema='identity')
    op.drop_table('roles', schema='identity')
    op.drop_table('permissions', schema='identity')
    op.drop_table('oidc_login_transactions', schema='identity')
    op.execute("DROP SCHEMA governance")
    op.execute("DROP SCHEMA knowledge")
    op.execute("DROP SCHEMA platform")
    op.execute("DROP SCHEMA identity")

