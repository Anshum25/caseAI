import PdfUploader from "@/components/ui/PdfUploader";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-24">
      <div className="max-w-5xl w-full flex flex-col items-center gap-8 text-center">
        <h1 className="text-5xl font-extrabold tracking-tight text-gray-900">
          Nyaya<span className="text-blue-600">AI</span>
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl">
          AI Legal Case Analysis & Document Chat. Upload Supreme Court of India cases, High Court cases, District Court documents, and more.
        </p>
        
        <div className="w-full mt-8 flex flex-col items-center gap-6">
          <PdfUploader />
          
          <Link
            href="/history"
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            View Case History
          </Link>
        </div>
      </div>
    </main>
  );
}
