import { EB_Garamond, Public_Sans, JetBrains_Mono } from 'next/font/google';

export const ebGaramond = EB_Garamond({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-eb-garamond',
  display: 'swap',
});

export const publicSans = Public_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-public-sans',
  display: 'swap',
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});
