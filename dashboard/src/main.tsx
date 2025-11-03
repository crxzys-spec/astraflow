import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import './lib/setupAxios'
import './index.css'
import App from './App.tsx'
import { queryClient } from './lib/queryClient.ts'
import { sseClient } from './lib/sseClient'

sseClient.enableKeepAlive()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
)

