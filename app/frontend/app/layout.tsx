import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-serif" });

// ... imports

export const metadata: Metadata = {
  title: "PalmX | Palm Hills Property Concierge",
  description: "AI-powered property concierge for Palm Hills Developments",
  icons: {
    icon: "/logo.svg", // Fallback to logo or standard icon
    // In a real app we'd map this to a specific ico/png. 
    // For now I'm ensuring the title is branded.
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${playfair.variable} font-sans antialiased bg-white text-foreground selection:bg-primary selection:text-white`}>
        {children}
      </body>
    </html>
  );
}
