import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AXIOM | Digital Integrity',
  description: 'SOC Dashboard for deepfake and multi-modal digital integrity analysis.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
        <style>{`
          body {
            font-family: 'Inter', sans-serif;
          }
        `}</style>
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
