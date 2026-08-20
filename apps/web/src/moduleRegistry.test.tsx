import { render, screen } from '@testing-library/react'
import { Suspense } from 'react'
import { describe, expect, it } from 'vitest'
import {
  hasTrustedComponent,
  isTrustedNavigation,
  moduleComponentRegistry,
} from './moduleRegistry'

describe('trusted module component registry', () => {
  it('resolves the statically shipped example module', async () => {
    const Component = moduleComponentRegistry['jarvis.example.page']
    expect(Component).toBeDefined()
    render(
      <Suspense fallback={<p>Loading</p>}>
        <Component workspaceId="workspace-test" />
      </Suspense>,
    )
    expect(await screen.findByText('Platform foundation')).toBeInTheDocument()
    expect(screen.getByText('workspace-test')).toBeInTheDocument()
  })

  it('fails closed for a database-supplied unknown component key', () => {
    expect(hasTrustedComponent('attacker.remote.import')).toBe(false)
    expect(
      isTrustedNavigation({
        key: 'jarvis.example.nav',
        parentKey: null,
        routeKey: 'jarvis.example.home',
        path: 'https://attacker.example',
        componentKey: 'jarvis.example.page',
        label: 'Unsafe',
        iconKey: 'blocks',
        order: 1,
        hidden: false,
        requiredPermission: 'jarvis.example.read',
      }),
    ).toBe(false)
  })
})

