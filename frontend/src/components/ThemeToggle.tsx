'use client';
import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
type Theme='light'|'dark';
const KEY='armstrong-theme';
export default function ThemeToggle(){
 const [theme,setTheme]=useState<Theme>('light');
 useEffect(()=>{const stored=window.localStorage.getItem(KEY);const current:Theme=stored==='light'||stored==='dark'?stored:window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';setTheme(current);document.documentElement.dataset.theme=current;},[]);
 function toggle(){const next:Theme=theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;window.localStorage.setItem(KEY,next);setTheme(next)}
 return <button type="button" className="theme-toggle" aria-label={theme==='dark'?'Switch to light mode':'Switch to dark mode'} title={theme==='dark'?'Light mode':'Dark mode'} aria-pressed={theme==='dark'} onClick={toggle}>{theme==='dark'?<Sun size={18}/>:<Moon size={18}/>}<span>{theme==='dark'?'Light':'Dark'}</span></button>
}
