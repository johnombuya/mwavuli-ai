'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Inter } from 'next/font/google';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { AppShell } from '@/components/layout/AppShell';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchInterval: 120000,
            staleTime: 120000,
            retry: 2,
            refetchOnWindowFocus: true,
          },
        },
      })
  );

  return (
    <html lang="en">
      <body className={`${inter.variable} ${inter.className}`}>
        <QueryClientProvider client={queryClient}>
          <LanguageProvider>
            <AppShell>{children}</AppShell>
          </LanguageProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
