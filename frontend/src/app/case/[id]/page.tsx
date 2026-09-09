import CaseDashboard from "@/components/dashboard/CaseDashboard";

export default async function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="min-h-screen bg-white">
      <CaseDashboard documentId={id} />
    </main>
  );
}
