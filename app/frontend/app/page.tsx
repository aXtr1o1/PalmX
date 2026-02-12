import ChatInterface from "@/components/chat-interface";

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      {/* Force Rebuild Trigger: v11.2 */}
      <ChatInterface key="force-refresh-v7" />
    </main>
  );
}
