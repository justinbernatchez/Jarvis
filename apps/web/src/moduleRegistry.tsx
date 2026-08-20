import type { NavigationNodeRead } from '@jarvis/api-client'
import type { ComponentType } from 'react'
import { LazyFoundationExamplePage } from './LazyFoundationExamplePage'

export interface ModulePageProps {
  workspaceId: string
}

export const EXAMPLE_ROUTE_PATH = '/example' as const

export const moduleComponentRegistry: Readonly<
  Record<string, ComponentType<ModulePageProps>>
> = Object.freeze({
  'jarvis.example.page': LazyFoundationExamplePage,
})

export const moduleRouteRegistry = Object.freeze({
  'jarvis.example.home': {
    path: EXAMPLE_ROUTE_PATH,
    componentKey: 'jarvis.example.page',
  },
})

export function hasTrustedComponent(componentKey: string): boolean {
  return Object.hasOwn(moduleComponentRegistry, componentKey)
}

export function isTrustedNavigation(node: NavigationNodeRead): boolean {
  const route =
    moduleRouteRegistry[node.routeKey as keyof typeof moduleRouteRegistry]
  return Boolean(
    route &&
      route.path === node.path &&
      route.componentKey === node.componentKey &&
      hasTrustedComponent(node.componentKey),
  )
}

export function trustedPath(node: NavigationNodeRead): string {
  const route =
    moduleRouteRegistry[node.routeKey as keyof typeof moduleRouteRegistry]
  if (!route || !isTrustedNavigation(node)) {
    throw new Error(`Untrusted navigation route: ${node.routeKey}`)
  }
  return route.path
}

