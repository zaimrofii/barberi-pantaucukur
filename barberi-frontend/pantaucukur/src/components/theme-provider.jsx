// components/theme-provider.jsx
"use client"

import * as React from 'react'
import { ThemeProvider as NextThemesProvider } from 'next-themes'

// Tambahkan kurung kurawal { children }
export function ThemeProvider({ children, ...props }) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}