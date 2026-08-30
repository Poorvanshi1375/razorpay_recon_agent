import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "on-primary": "#ffffff",
        "tertiary-fixed": "#bfebe7",
        "on-primary-fixed": "#191c22",
        "tertiary": "#000404",
        "surface-dim": "#dcdad3",
        "error-container": "#ffdad6",
        "on-secondary": "#ffffff",
        "outline-variant": "#c6c6cb",
        "background": "#fcf9f2",
        "secondary": "#725b2f",
        "on-primary-fixed-variant": "#44474d",
        "inverse-surface": "#31312c",
        "primary-container": "#1a1d23",
        "secondary-fixed-dim": "#e1c28e",
        "on-error-container": "#93000a",
        "on-tertiary-fixed-variant": "#244d4b",
        "on-error": "#ffffff",
        "inverse-primary": "#c4c6ce",
        "on-secondary-container": "#796135",
        "outline": "#76777b",
        "primary": "#010306",
        "primary-fixed-dim": "#c4c6ce",
        "surface-container-high": "#ebe8e1",
        "on-tertiary": "#ffffff",
        "primary-fixed": "#e1e2ea",
        "on-secondary-fixed-variant": "#58431a",
        "on-tertiary-fixed": "#00201e",
        "tertiary-container": "#002220",
        "surface-variant": "#e5e2db",
        "surface-container-highest": "#e5e2db",
        "error": "#ba1a1a",
        "surface-container-low": "#f6f3ec",
        "surface-container-lowest": "#ffffff",
        "surface": "#fcf9f2",
        "secondary-container": "#ffdea7",
        "surface-container": "#f1eee7",
        "surface-tint": "#5c5e65",
        "surface-bright": "#fcf9f2",
        "on-primary-container": "#82858c",
        "on-background": "#1c1c18",
        "on-secondary-fixed": "#271900",
        "on-surface-variant": "#45474b",
        "on-tertiary-container": "#638d8a",
        "tertiary-fixed-dim": "#a4cfcb",
        "on-surface": "#1c1c18",
        "secondary-fixed": "#ffdea7",
        "inverse-on-surface": "#f3f0e9"
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px"
      },
      spacing: {
        "column-gutter": "24px",
        "rail-width": "64px",
        "container-padding": "48px",
        "unit": "4px",
        "row-gap": "12px"
      },
      fontFamily: {
        serif: ["var(--font-eb-garamond)", "serif"],
        sans: ["var(--font-public-sans)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"]
      }
    }
  }
};

export default config;
