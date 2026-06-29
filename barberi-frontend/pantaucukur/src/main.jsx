import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ThemeProvider } from './components/theme-provider' // Sesuaikan path-nya

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider 
      attribute="class" 
      defaultTheme="dark" 
      enableSystem={false} // Set ke false dulu untuk memastikan manual toggle berhasil
    >
      <App />
    </ThemeProvider>
  </StrictMode>,
)