// Static pages layout - allows static generation for better SEO
export default function StaticLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Simple pass-through layout - html/body provided by root layout
  return <>{children}</>;
}
