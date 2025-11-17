import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MAGMA - Market Advisor',
  description: 'Your personal consultant for stock trades',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

