import './marketing.css';
import MarketingNav from './components/MarketingNav';
import HeroSection from './components/HeroSection';
import StatsSection from './components/StatsSection';
import ProblemSection from './components/ProblemSection';
import PersonasSection from './components/PersonasSection';
import CapabilitiesSection from './components/CapabilitiesSection';
import HowItWorksSection from './components/HowItWorksSection';
import ComparisonSection from './components/ComparisonSection';
import PricingSection from './components/PricingSection';
import TestimonialsSection from './components/TestimonialsSection';
import TrustSection from './components/TrustSection';
import CTASection from './components/CTASection';
import Footer from './components/Footer';

export default function MarketingPage() {
  return (
    <div className="mkt-page">
      <MarketingNav />
      <HeroSection />
      <StatsSection />
      <ProblemSection />
      <PersonasSection />
      <CapabilitiesSection />
      <HowItWorksSection />
      <ComparisonSection />
      <PricingSection />
      <TestimonialsSection />
      <TrustSection />
      <CTASection />
      <Footer />
    </div>
  );
}
