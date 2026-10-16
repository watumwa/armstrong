import type { Metadata, Viewport } from 'next';
import PwaInstaller from '../components/PwaInstaller';
import ThemeToggle from '../components/ThemeToggle';
import './globals.css';
export const metadata: Metadata = { title: 'Armstrong | Waste Operations', description: 'Armstrong Global Solutions waste management operations', applicationName: 'Armstrong Global Solutions', appleWebApp: { capable: true, statusBarStyle: 'default', title: 'Armstrong' }, formatDetection: { telephone: false } };
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#092c49' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en" suppressHydrationWarning><body>{children}<div className="global-theme-control"><ThemeToggle/></div><PwaInstaller/></body></html>; }
