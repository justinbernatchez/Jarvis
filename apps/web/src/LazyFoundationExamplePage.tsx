import { lazy } from 'react'

export const LazyFoundationExamplePage = lazy(async () => {
  const module = await import('./FoundationExamplePage')
  return { default: module.FoundationExamplePage }
})

