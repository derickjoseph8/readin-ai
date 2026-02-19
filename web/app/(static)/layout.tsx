// Force dynamic rendering
export const dynamic = 'force-dynamic';

export default function StaticLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Simple pass-through layout - html/body provided by root layout
  return <>{children}</>;
}
