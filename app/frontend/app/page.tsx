import ChatInterface from "@/components/chat-interface";

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      {/* Force Rebuild Trigger: v10.7 */}
      <ChatInterface key="force-refresh-v2" />
    </main>
  );
}
