import { NextResponse } from "next/server";

// No-op middleware to avoid auth/proxy interference in deployment.
export default function middleware() {
  return NextResponse.next();
}

export const config = {
  // Keep the same matcher shape but do nothing with the request.
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};