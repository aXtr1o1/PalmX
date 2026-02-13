'use client';

import ChatInterface from "@/components/chat-interface";
import { SignedIn, SignedOut, SignIn, SignUp } from "@clerk/nextjs";
import { useState } from "react";
import Image from 'next/image';

export default function Home() {
  const [showSignUp, setShowSignUp] = useState(false);

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4 font-serif">

      {/* If user is logged in → Show Chat */}
      <SignedIn>
        <ChatInterface />
      </SignedIn>

      {/* If user is logged out → Show Auth UI */}
      <SignedOut>
        <div className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl overflow-hidden grid md:grid-cols-2">

          {/* Left Side – Branding */}
          <div className="hidden md:flex flex-col justify-center bg-gradient-to-br  p-10">
            <div className="mb-6 flex justify-center">
              <Image 
                src="/brand/palmHills-BlockLogo.png" 
                alt="PalmX Logo" 
                width={100} 
                height={50}
                className="h-auto"
                priority
              />
            </div>
            <h1 className="text-4xl font-bold mb-4 font-serif text-center text-black">
              <span className="font-serif">PalmX</span> <span className="text-[#D22048]">Concierge</span>
            </h1>
            <p className="text-lg opacity-90 font-serif text-center text-black">
              AI-powered property assistant for Palm Hills Developments.
            </p>
          </div>

          {/* Right Side – Auth */}
          <div className="p-8 flex flex-col justify-center">
            <div className="flex justify-center mb-6 md:hidden">
              <Image 
                src="/logo.svg" 
                alt="PalmX Logo" 
                width={200} 
                height={52}
                className="h-auto"
                priority
              />
            </div>
            <h2 className="text-2xl font-semibold mb-6 text-center font-serif">
              {showSignUp ? "Create an Account" : "Welcome Back"}
            </h2>

            {showSignUp ? (
              <SignUp
                routing="hash"
                appearance={{
                  elements: {
                    formButtonPrimary:
                      "bg-black text-white hover:bg-primary rounded-full font-serif transition-all",
                    formFieldLabel: "font-serif",
                    formFieldInput: "font-serif",
                    footerActionLink: "font-serif",
                  },
                }}
              />
            ) : (
              <SignIn
                routing="hash"
                appearance={{
                  elements: {
                    formButtonPrimary:
                      "bg-black text-white hover:bg-primary rounded-full font-serif transition-all",
                    formFieldLabel: "font-serif",
                    formFieldInput: "font-serif",
                    footerActionLink: "font-serif",
                  },
                }}
              />
            )}

            {/* Toggle Button */}
            <button
              onClick={() => setShowSignUp(!showSignUp)}
              className="mt-6 text-sm text-center"
            >
              {showSignUp ? (
                <>Already have an account? <span className="text-[#D22048] hover:underline">Sign In</span></>
              ) : (
                <>Don't have an account? <span className="text-[#D22048] hover:underline">Sign Up</span></>
              )}
            </button>
          </div>
        </div>
      </SignedOut>
    </main>
  );
}
