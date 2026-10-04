import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Clause — Contract review', description: 'Evidence-backed contract review workspace' };
export default function Layout({children}: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
