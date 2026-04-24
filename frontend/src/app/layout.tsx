import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Ssij. - Downloader Wideo',
  description: 'Pobieraj materiały wideo i audio z ponad 1000 platform.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl">
      <body className="antialiased min-h-screen bg-neutral-950">
        {children}
      </body>
    </html>
  );
}
