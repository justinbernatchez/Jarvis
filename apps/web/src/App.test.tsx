import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FoundationHome } from './App'

describe('foundation shell content', () => {
  it('states the Phase 1 platform boundary without finance features', () => {
    render(<FoundationHome />)
    expect(
      screen.getByRole('heading', { name: 'Foundation is connected' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Workspace + PostgreSQL RLS')).toBeInTheDocument()
    expect(screen.queryByText('Equity Research')).not.toBeInTheDocument()
  })
})

