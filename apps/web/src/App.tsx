import { ApiProblem } from '@jarvis/api-client'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Outlet } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import {
  EXAMPLE_ROUTE_PATH,
  isTrustedNavigation,
  trustedPath,
} from './moduleRegistry'
import { WorkspaceContext } from './workspaceContext'

export function App() {
  const queryClient = useQueryClient()
  const session = useQuery({
    queryKey: ['session'],
    queryFn: () => api.session(),
    retry: false,
  })
  const currentUser = useQuery({
    queryKey: ['me'],
    queryFn: () => api.me(),
    enabled: session.isSuccess,
    retry: false,
  })
  const [workspaceId, setWorkspaceId] = useState<string>('')

  useEffect(() => {
    if (!workspaceId && currentUser.data?.memberships[0]) {
      setWorkspaceId(currentUser.data.memberships[0].workspaceId)
    }
  }, [currentUser.data, workspaceId])

  const navigation = useQuery({
    queryKey: ['navigation', workspaceId],
    queryFn: () => api.navigation(workspaceId),
    enabled: Boolean(workspaceId),
  })
  const trustedNodes = useMemo(
    () => (navigation.data ?? []).filter(isTrustedNavigation),
    [navigation.data],
  )
  const rejectedNodeCount = (navigation.data?.length ?? 0) - trustedNodes.length

  if (session.isLoading) {
    return <main className="center-state">Opening JARVIS…</main>
  }
  if (
    session.error instanceof ApiProblem &&
    session.error.problem.status === 401
  ) {
    return (
      <main className="center-state">
        <div>
          <p className="brand-mark">JARVIS</p>
          <h1>Research platform foundation</h1>
          <p>Authentication is required to open a private workspace.</p>
          <a
            className="primary-action"
            href={api.loginUrl(
              window.location.pathname === EXAMPLE_ROUTE_PATH
                ? EXAMPLE_ROUTE_PATH
                : '/',
            )}
          >
            Sign in
          </a>
        </div>
      </main>
    )
  }
  if (session.isError) {
    return <main className="center-state">JARVIS could not start.</main>
  }
  if (!session.data) {
    return <main className="center-state">Opening JARVIS…</main>
  }
  const authenticatedSession = session.data

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-glyph" aria-hidden="true">
            J
          </span>
          <div>
            <strong>JARVIS</strong>
            <span>Foundation</span>
          </div>
        </div>
        <label className="workspace-picker">
          <span>Workspace</span>
          <select
            value={workspaceId}
            onChange={(event) => setWorkspaceId(event.target.value)}
          >
            {(currentUser.data?.memberships ?? []).map((membership) => (
              <option key={membership.workspaceId} value={membership.workspaceId}>
                {membership.roleKey} · {membership.workspaceId.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        <nav aria-label="Workspace navigation">
          <Link to="/" activeProps={{ 'aria-current': 'page' }}>
            Platform
          </Link>
          {trustedNodes
            .filter((node) => !node.hidden)
            .map((node) => (
              <Link
                key={node.key}
                to={trustedPath(node)}
                activeProps={{ 'aria-current': 'page' }}
              >
                {node.label}
              </Link>
            ))}
        </nav>
        {rejectedNodeCount > 0 && (
          <p className="configuration-warning" role="status">
            {rejectedNodeCount} untrusted component key rejected.
          </p>
        )}
        <p className="sidebar-footnote">Finance modules are not enabled.</p>
      </aside>
      <div className="work-area">
        <header className="topbar">
          <div>
            <span className="context-label">Current user</span>
            <strong>{authenticatedSession.user.displayName}</strong>
          </div>
          <div className="topbar-actions">
            <span className="phase-badge">Phase 1</span>
            <button
              className="text-action"
              type="button"
              onClick={async () => {
                await api.logout()
                queryClient.clear()
                window.location.assign('/')
              }}
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="content">
          <WorkspaceContext.Provider value={workspaceId}>
            <Outlet />
          </WorkspaceContext.Provider>
        </main>
      </div>
    </div>
  )
}

export function FoundationHome() {
  return (
    <section className="workspace-page" aria-labelledby="platform-heading">
      <p className="eyebrow">Platform status</p>
      <h1 id="platform-heading">Foundation is connected</h1>
      <p className="page-lede">
        Identity, workspaces, row security, resource and module registries,
        configuration portability, audit, outbox, and generated API contracts
        form this release boundary.
      </p>
      <div className="status-grid" aria-label="Foundation capabilities">
        {[
          ['Identity', 'Server-side session'],
          ['Isolation', 'Workspace + PostgreSQL RLS'],
          ['Modules', 'Trusted manifest registry'],
          ['Contracts', 'OpenAPI-generated client'],
        ].map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}

export default App
