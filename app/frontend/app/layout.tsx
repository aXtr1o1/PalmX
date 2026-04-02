import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import { ClerkProvider, SignedOut, SignInButton,SignedIn,UserButton } from '@clerk/nextjs'
import { AppProvider } from "@/contexts/app-context";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-serif" });

// ... imports

export const metadata: Metadata = {
  title: "PalmX | Palm Hills Property Concierge",
  description: "AI-powered property concierge for Palm Hills Developments",
  icons: {
    icon: "/favicon.ico",
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    
      <AppProvider>
        <html lang="en">
          <body className={`${inter.variable} ${playfair.variable} font-sans antialiased bg-white text-foreground selection:bg-primary selection:text-white`}>
            {children}
          </body>
        </html>
      </AppProvider>
  
  );
}
