import {
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { App, FoundationHome } from './App'
import { ExampleModuleRoute } from './ExampleModuleRoute'
import { EXAMPLE_ROUTE_PATH } from './moduleRegistry'

const rootRoute = createRootRoute({
  component: App,
  notFoundComponent: () => (
    <section className="workspace-page">
      <p className="eyebrow">Not found</p>
      <h1>This platform route is not registered.</h1>
    </section>
  ),
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: FoundationHome,
})

const exampleRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: EXAMPLE_ROUTE_PATH,
  component: ExampleModuleRoute,
})

const routeTree = rootRoute.addChildren([indexRoute, exampleRoute])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

