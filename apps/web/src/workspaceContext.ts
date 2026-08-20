import { createContext, useContext } from 'react'

export const WorkspaceContext = createContext<string>('')

export function useWorkspaceId(): string {
  return useContext(WorkspaceContext)
}

