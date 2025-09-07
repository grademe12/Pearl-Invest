// src/app/layout.tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'; // 👈 1. Header 컴포넌트 import

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Pearl Invest',
  description: 'Portfolio Management Service',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Header /> {/* 👈 2. <body> 태그 바로 아래에 Header 추가 */}
        <main>{children}</main> {/* 👈 3. 기존 children을 main 태그로 감싸주면 좋음 */}
      </body>
    </html>
  )
}