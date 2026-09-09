import PdfUploader from "@/components/ui/PdfUploader";

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
        
        <div className="w-full mt-8 flex justify-center">
          <PdfUploader />
        </div>
      </div>
    </main>
  );
}
