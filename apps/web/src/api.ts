import { JarvisApiClient } from '@jarvis/api-client'

export const api = new JarvisApiClient(
  import.meta.env.VITE_API_ORIGIN ?? '',
)

