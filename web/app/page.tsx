'use client';

import Header from '@/components/Header';
import Hero from '@/components/Hero';
import TrustBadges from '@/components/TrustBadges';
import IntegrationLogos from '@/components/IntegrationLogos';
import Features from '@/components/Features';
import HowItWorks from '@/components/HowItWorks';
import Stats from '@/components/Stats';
import UseCases from '@/components/UseCases';
import SecuritySection from '@/components/SecuritySection';
import Testimonials from '@/components/Testimonials';
import ComparisonTable from '@/components/ComparisonTable';
import Pricing from '@/components/Pricing';
import FAQ from '@/components/FAQ';
import CTA from '@/components/CTA';
import Footer from '@/components/Footer';

export default function Home() {
  return (
    <main className="min-h-screen bg-premium-bg text-white">
      <Header />
      <Hero />
      <TrustBadges />
      <IntegrationLogos />
      <Features />
      <HowItWorks />
      <Stats />
      <UseCases />
      <SecuritySection />
      <Testimonials />
      <ComparisonTable />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
    </main>
  );
}
