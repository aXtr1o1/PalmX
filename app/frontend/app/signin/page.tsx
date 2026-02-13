'use client';

import { SignIn } from '@clerk/nextjs';
import Image from 'next/image';

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-r from-indigo-600 to-purple-600 font-sans">
      <div className="bg-white shadow-xl rounded-2xl p-8 w-full max-w-md">
        <div className="flex justify-center mb-6">
          <Image 
            src="/logo.svg" 
            alt="PalmX Logo" 
            width={200} 
            height={52}
            className="h-auto"
            priority
          />
        </div>
        <SignIn
          path="/sign-in"
          routing="path"
          signUpUrl="/sign-up"
          appearance={{
            elements: {
              card: "rounded-xl shadow-md",
              headerTitle: "text-xl font-semibold text-center text-gray-700 font-sans",
              formButtonPrimary: "bg-black text-white hover:bg-primary rounded-full font-sans transition-all",
              formFieldLabel: "font-sans",
              formFieldInput: "font-sans",
              footerActionLink: "font-sans",
            },
          }}
        />
      </div>
    </div>
  );
}
