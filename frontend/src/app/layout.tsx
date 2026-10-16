import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Armstrong | Waste Operations', description: 'Armstrong Global Solutions waste management operations' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
