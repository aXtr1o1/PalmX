'use client';

import Link from "next/link";

export default function SignInPage() {
  return (
    <main className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="w-full max-w-lg bg-[#FAFAFA] border border-[#E9E9E9] rounded-2xl p-8">
        <h1 className="font-serif text-2xl text-[#0B0B0B]">Sign-in disabled</h1>
        <p className="mt-3 text-sm text-[#5A5A5A]">
          This app is currently running with auth UI turned off.
        </p>
        <div className="mt-6">
          <Link
            href="/"
            className="inline-flex items-center justify-center px-6 py-3 bg-[#0B0B0B] text-white rounded-full text-xs font-bold tracking-widest uppercase hover:bg-[#D22048] transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </main>
  );
}
