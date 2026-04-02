import Image from "next/image";

export default function Loading() {
    return (
        <div className="min-h-screen bg-white flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <Image
                src="/brand/palmHills-BlockLogo.png"
                alt="Palm Hills"
                width={80}
                height={80}
                className="opacity-60"
                />
                <div className="w-48 h-1 bg-[#E9E9E9] rounded-full overflow-hidden">
                    <div className="h-full bg=[#D22O48] rounded-full animate-pulse w-2/3"/>

                </div>
                <p className="text-xs text-[#5A5A5A] tracking-widest uppercase" >
                    Loading dashboard
                </p>
            </div>
        </div>
    )
}