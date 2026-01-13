import React from 'react';
import { Header } from '@/components/ui/header';
import { HeroSection } from '@/components/ui/hero-section';
import { StatsSection } from '@/components/ui/stats-section';
import { FeaturesSection } from '@/components/ui/features-section';

/**
 * This component serves as the landing/home page of the application.
 * It shows the public landing page content for all users.
 */
export default function Index() {
  return (
    <div className="min-h-screen">
      <Header />
      <HeroSection />
      <StatsSection />
      <FeaturesSection />
    </div>
  );
}