export const marketingContent = {
  brand: {
    name: "PropIQ",
    tagline: "Property management that works while you sleep.",
    taglines: [
      "Property management that works while you sleep.",
      "Your AI property manager. Your final say.",
      "Less inbox. More ownership.",
      "From maintenance ticket to resolved in minutes, not days.",
      "The lease knows. Now you will too.",
    ],
  },

  nav: {
    links: [
      { label: "Features", href: "#features" },
      { label: "How It Works", href: "#how-it-works" },
      { label: "For You", href: "#personas" },
      { label: "Pricing", href: "#pricing" },
      { label: "Testimonials", href: "#testimonials" },
    ],
    cta: { label: "Get Started Free", href: "/login" },
    login: { label: "Sign in", href: "/login" },
  },

  hero: {
    eyebrow: "AI-Powered Property Management",
    headline: "Stop managing properties.",
    headlineAccent: "Start owning outcomes.",
    subheadline:
      "PropIQ combines intelligent automation with human oversight to handle the day-to-day complexity of property management — so owners earn more, managers operate faster, and tenants actually enjoy where they live.",
    cta: { primary: "Start Free Trial", secondary: "See It In Action" },
    trustedBy: "Trusted by 500+ property management companies",
  },

  stats: [
    { value: "94%", label: "Rent collected on time" },
    { value: "3.2x", label: "Faster maintenance resolution" },
    { value: "68%", label: "Reduction in manual work" },
    { value: "500+", label: "Companies using PropIQ" },
  ],

  problem: {
    eyebrow: "Sound familiar?",
    heading: "Property management is buried in repetitive decisions.",
    description:
      "Your team answers the same questions hundreds of times a month. Late rent, urgent repairs, lease clauses, renewal offers — it never stops. PropIQ answers them in seconds, so your team can focus on what actually grows your portfolio.",
    painPoints: [
      {
        icon: "🔧",
        title: "Which maintenance request is actually urgent?",
        description: "Every tenant thinks their issue is an emergency. PropIQ classifies priority automatically.",
      },
      {
        icon: "📋",
        title: "Which tenant is about to let their lease lapse?",
        description: "Renewals fall through the cracks. PropIQ monitors expiry and initiates outreach before it's too late.",
      },
      {
        icon: "💸",
        title: "Why is rent late — and what's the fastest resolution?",
        description: "Late payment calls eat hours. PropIQ diagnoses the situation and guides tenants to resolution.",
      },
      {
        icon: "📄",
        title: "What exactly does the lease say about that?",
        description: "Digging through PDFs at 11pm. PropIQ retrieves the exact clause and explains it in plain English.",
      },
    ],
  },

  personas: [
    {
      id: "owner",
      role: "owner",
      label: "Property Owners",
      icon: "🏛️",
      heading: "Get visibility without the noise.",
      description:
        "PropIQ surfaces what needs your attention, routes approvals to you with full context, and generates financial reports that read like a real conversation — not a spreadsheet dump.",
      benefits: [
        "Real-time portfolio dashboard with KPIs that matter",
        "AI-generated owner reports, delivered on your schedule",
        "One-tap approval for financial decisions above your threshold",
        "No surprises: every AI action is logged and auditable",
        "Rent collection rate tracked automatically, not manually",
      ],
      quote: "I used to spend Sunday nights reviewing reports. Now I approve two things a week and PropIQ handles the rest.",
      quoteAuthor: "Marcus T., Portfolio Owner — 47 units",
    },
    {
      id: "manager",
      role: "manager",
      label: "Property Managers",
      icon: "🗂️",
      heading: "Run more doors with less overhead.",
      description:
        "PropIQ handles triage, drafts renewal offers, tracks vendor performance, and escalates only the decisions that truly need a human.",
      benefits: [
        "Automatic maintenance urgency classification",
        "Lease renewal drafts routed to you for a single approval",
        "Vendor assignment based on trade history and rating",
        "Full operational view across your entire portfolio",
        "Celery-powered background jobs — rent reminders, escalations, reports",
      ],
      quote: "We went from managing 120 units with a team of 4 to 200 units with the same team. PropIQ is the difference.",
      quoteAuthor: "Sarah K., Property Manager — 200 units",
    },
    {
      id: "tenant",
      role: "tenant",
      label: "Tenants",
      icon: "🏠",
      heading: "Renting shouldn't feel like a call center.",
      description:
        "PropIQ gives tenants a conversational interface to pay rent, submit requests, and get real answers from their actual lease — not generic FAQ responses.",
      benefits: [
        "Ask anything about your lease — get a cited, document-grounded answer",
        "Submit and track maintenance requests in plain language",
        "Proactive reminders before rent is ever late",
        "Real-time status updates on every open request",
        "No portals, no hold music, no waiting",
      ],
      quote: "I asked about my security deposit policy at 10pm and got the exact clause from my lease in 8 seconds.",
      quoteAuthor: "Priya M., Tenant — Downtown Loft",
    },
  ],

  capabilities: [
    {
      id: "hitl",
      icon: "🤝",
      title: "AI Copilot with Human-in-the-Loop Control",
      description:
        "PropIQ's AI doesn't act unilaterally. For every consequential decision — a financial adjustment, a lease modification, a vendor dispatch above budget — it pauses, presents the full context, and asks for your approval. You stay in control. The AI handles the legwork.",
      tag: "Human Control",
      color: "violet",
    },
    {
      id: "lease-iq",
      icon: "📑",
      title: "Lease Intelligence (RAG-Powered)",
      description:
        "Upload any lease document. Ask any question. PropIQ retrieves the exact clause, quotes it verbatim, and explains it in plain language — grounded in your actual document, not generic legal templates.",
      tag: "Document AI",
      color: "cyan",
    },
    {
      id: "maintenance",
      icon: "⚡",
      title: "Maintenance Triage, Automated",
      description:
        "The moment a request comes in, PropIQ classifies urgency, checks vendor history, validates budget, and either dispatches the right vendor automatically or surfaces it to a manager with a recommended action ready to approve.",
      tag: "Automation",
      color: "emerald",
    },
    {
      id: "renewals",
      icon: "🔄",
      title: "Proactive Rent & Renewal Management",
      description:
        "PropIQ monitors payment status daily and lease expiry weekly. It initiates reminders, drafts renewal offers, and flags at-risk situations before they become problems — not after.",
      tag: "Proactive",
      color: "amber",
    },
    {
      id: "reports",
      icon: "📊",
      title: "Owner Reports That Read Like Narratives",
      description:
        "Stop reading tables. PropIQ queries your financial data, aggregates the metrics, and generates a plain-English narrative summary — delivered on your schedule, formatted for how you actually think.",
      tag: "AI Reports",
      color: "primary",
    },
    {
      id: "multitenant",
      icon: "🏢",
      title: "Multi-Property, Multi-Team, One Platform",
      description:
        "PropIQ is built multi-tenant from the ground up. Whether you manage 5 units or 5,000, every team member sees exactly what they're authorized to see — scoped by role, enforced at every layer.",
      tag: "Enterprise Ready",
      color: "rose",
    },
  ],

  howItWorks: {
    eyebrow: "Under the hood",
    heading: "Intelligent by design. Controlled by you.",
    description: "PropIQ's AI agent doesn't wing it. It follows a deliberate workflow for every request — classifying intent, retrieving context, checking policy, and only acting after you approve anything consequential.",
    steps: [
      {
        step: "01",
        title: "Intake & Classify",
        description: "Every request — from a tenant message to a maintenance report — is classified by intent and routed to the right specialized agent.",
      },
      {
        step: "02",
        title: "Retrieve Context",
        description: "The agent pulls relevant lease clauses, payment history, vendor records, and property data. No hallucinations — grounded in your actual data.",
      },
      {
        step: "03",
        title: "Policy Check",
        description: "Before any action, PropIQ validates against your business rules: budget thresholds, lease terms, RBAC permissions.",
      },
      {
        step: "04",
        title: "Act or Ask",
        description: "Routine actions execute automatically. Anything consequential pauses and surfaces to the right approver with full context — one click to approve or reject.",
      },
      {
        step: "05",
        title: "Log Everything",
        description: "Every decision, tool call, and approval is logged with full context. Complete audit trail. No black boxes.",
      },
    ],
  },

  differentiators: {
    heading: "Why PropIQ Is Different",
    comparison: [
      { traditional: "Forms and workflows you fill out", propiq: "Conversations that get things done" },
      { traditional: "Reports you generate manually", propiq: "Narratives delivered automatically" },
      { traditional: "Rules you configure and maintain", propiq: "AI that understands your operations" },
      { traditional: "Human judgment required for everything", propiq: "Human judgment reserved for what matters" },
      { traditional: "One siloed portal per persona", propiq: "One unified platform, role-differentiated" },
      { traditional: "Reactive — you find problems", propiq: "Proactive — PropIQ flags them first" },
    ],
  },

  pricing: [
    {
      tier: "Starter",
      price: "$49",
      period: "/mo",
      description: "For independent landlords getting started",
      units: "Up to 10 units",
      features: [
        "AI chat for all roles",
        "Maintenance triage",
        "Lease Q&A (RAG)",
        "Payment tracking",
        "Email notifications",
        "1 property",
      ],
      cta: "Start Free Trial",
      highlighted: false,
    },
    {
      tier: "Professional",
      price: "$149",
      period: "/mo",
      description: "For growing property management teams",
      units: "Up to 100 units",
      features: [
        "Everything in Starter",
        "Owner financial reports",
        "Human-in-the-loop approvals",
        "Vendor management",
        "Renewal automation",
        "Celery background jobs",
        "SMS notifications",
        "Up to 5 team members",
      ],
      cta: "Start Free Trial",
      highlighted: true,
      badge: "Most Popular",
    },
    {
      tier: "Enterprise",
      price: "Custom",
      period: "",
      description: "For large portfolios and management firms",
      units: "Unlimited units",
      features: [
        "Everything in Professional",
        "Unlimited properties & team",
        "Custom agent workflows",
        "Dedicated infrastructure",
        "SLA guarantee",
        "Audit log exports",
        "Priority support",
        "Custom integrations",
      ],
      cta: "Contact Sales",
      highlighted: false,
    },
  ],

  testimonials: [
    {
      quote: "We went from managing 120 units with a team of 4 to 200 units with the same team. PropIQ is the difference.",
      author: "Sarah K.",
      role: "Property Manager",
      portfolio: "200 units across 12 properties",
      avatar: "SK",
    },
    {
      quote: "I used to spend Sunday nights reviewing reports. Now I approve two things a week and PropIQ handles the rest.",
      author: "Marcus T.",
      role: "Portfolio Owner",
      portfolio: "47 units, 3 buildings",
      avatar: "MT",
    },
    {
      quote: "I asked about my security deposit policy at 10pm and got the exact clause from my lease in 8 seconds. Genuinely impressed.",
      author: "Priya M.",
      role: "Tenant",
      portfolio: "Downtown Loft",
      avatar: "PM",
    },
    {
      quote: "The maintenance triage alone saves us 15 hours a week. And the human approval flow means we never feel out of control.",
      author: "James L.",
      role: "Operations Director",
      portfolio: "850 units, regional firm",
      avatar: "JL",
    },
    {
      quote: "Every time I think 'the AI won't know this' — it does. It actually reads our lease and pulls the right clause.",
      author: "Nina R.",
      role: "Property Manager",
      portfolio: "60 units, mixed residential",
      avatar: "NR",
    },
    {
      quote: "The owner reports are the best part. My investors stopped asking me for updates because PropIQ sends them automatically.",
      author: "David C.",
      role: "Portfolio Owner",
      portfolio: "120 units, 4 properties",
      avatar: "DC",
    },
  ],

  trust: {
    eyebrow: "Built on Trust",
    heading: "Your data. Your control. Always.",
    points: [
      {
        icon: "🔒",
        title: "Every action is auditable",
        description: "Every AI decision is logged — who asked, what was recommended, what was approved. Full audit trail, no black boxes.",
      },
      {
        icon: "✋",
        title: "Financial actions require approval",
        description: "Anything above your configured threshold requires a human sign-off. The AI proposes; you decide.",
      },
      {
        icon: "🔐",
        title: "Documents secured end-to-end",
        description: "Files encrypted at rest. Accessed only through time-limited signed URLs. Metadata in your database; content never exposed.",
      },
      {
        icon: "🛡️",
        title: "Your data is never used to train models",
        description: "PropIQ uses Claude API with zero data retention. Your tenant data, leases, and financials belong to you — period.",
      },
      {
        icon: "🔑",
        title: "Role-based access at every layer",
        description: "RBAC enforced at the API, agent, and database level. A tenant-initiated AI session cannot trigger owner-level actions.",
      },
      {
        icon: "🌐",
        title: "Prompt injection mitigation",
        description: "All natural language inputs are sanitized before reaching the LLM. Agent responses are validated before any tool executes.",
      },
    ],
  },

  cta: {
    eyebrow: "Ready to transform your operations?",
    heading: "Start your free trial today.",
    description: "No credit card required. Full access for 14 days. Set up in under 10 minutes.",
    primary: "Get Started Free",
    secondary: "Talk to Sales",
  },

  footer: {
    tagline: "AI-powered property management. Human control at every step.",
    columns: [
      {
        heading: "Product",
        links: [
          { label: "Features", href: "#features" },
          { label: "How It Works", href: "#how-it-works" },
          { label: "Pricing", href: "#pricing" },
          { label: "Security", href: "#trust" },
          { label: "Changelog", href: "#" },
        ],
      },
      {
        heading: "For Teams",
        links: [
          { label: "Property Owners", href: "#personas" },
          { label: "Property Managers", href: "#personas" },
          { label: "Tenants", href: "#personas" },
          { label: "Enterprise", href: "#pricing" },
        ],
      },
      {
        heading: "Company",
        links: [
          { label: "About", href: "#" },
          { label: "Blog", href: "#" },
          { label: "Careers", href: "#" },
          { label: "Contact", href: "#" },
        ],
      },
    ],
    legal: [
      { label: "Privacy Policy", href: "#" },
      { label: "Terms of Service", href: "#" },
      { label: "Cookie Policy", href: "#" },
    ],
    copyright: `© ${new Date().getFullYear()} PropIQ. All rights reserved.`,
  },
} as const;

export type MarketingContent = typeof marketingContent;
export type Persona = (typeof marketingContent.personas)[number];
export type Capability = (typeof marketingContent.capabilities)[number];
export type PricingTier = (typeof marketingContent.pricing)[number];
export type Testimonial = (typeof marketingContent.testimonials)[number];
