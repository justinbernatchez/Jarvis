import type { ModulePageProps } from './moduleRegistry'

export function FoundationExamplePage({ workspaceId }: ModulePageProps) {
  return (
    <section className="workspace-page" aria-labelledby="foundation-heading">
      <p className="eyebrow">Trusted module proof</p>
      <h1 id="foundation-heading">Platform foundation</h1>
      <p className="page-lede">
        This page is resolved from the statically shipped component registry.
        Database navigation can select this key, but it cannot import code.
      </p>
      <dl className="facts">
        <div>
          <dt>Component key</dt>
          <dd>jarvis.example.page</dd>
        </div>
        <div>
          <dt>Workspace</dt>
          <dd>{workspaceId}</dd>
        </div>
        <div>
          <dt>Phase</dt>
          <dd>Foundation</dd>
        </div>
      </dl>
    </section>
  )
}

