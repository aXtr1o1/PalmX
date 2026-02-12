import ChatInterface from "@/components/chat-interface";

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      {/* Force Rebuild Trigger: v10.9 */}
      <ChatInterface key="force-refresh-v4" />
    </main>
  );
}
