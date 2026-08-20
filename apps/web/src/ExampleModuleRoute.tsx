import { Suspense } from 'react'
import { moduleComponentRegistry } from './moduleRegistry'
import { useWorkspaceId } from './workspaceContext'

export function ExampleModuleRoute() {
  const workspaceId = useWorkspaceId()
  const Component = moduleComponentRegistry['jarvis.example.page']
  if (!Component) {
    return <p role="alert">Trusted module component is unavailable.</p>
  }
  return (
    <Suspense fallback={<p>Loading trusted module…</p>}>
      <Component workspaceId={workspaceId} />
    </Suspense>
  )
}

