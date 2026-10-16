// Reading paths on the /guides/ index: "pick your situation" → an ordered
// list of guides. They mirror the situations in content/guides/start-here.md
// step for step (a test keeps the two in sync), so the index and the guide
// never recommend different sequences.

export const READING_PATHS = Object.freeze([
  {
    id: 'graduating-soon',
    label: 'Graduating in 0–3 months',
    explain: 'Check current employer and campus deadlines, and prepare while you apply.',
    steps: ['how-to-search-for-new-grad-jobs', 'build-a-target-company-list', 'ats-friendly-resume', 'resume-bullet-points', 'tailoring-your-resume', 'linkedin-for-new-grads', 'github-profile-for-new-grads', 'new-grad-hiring-timeline'],
  },
  {
    id: 'first-job',
    label: 'Looking for my first job',
    explain: 'Line up your target list, résumé and projects before you send volume.',
    steps: ['what-counts-as-a-new-grad-job', 'are-you-qualified', 'build-a-target-company-list', 'application-strategy', 'behavioral-interviews'],
  },
  {
    id: 'no-interviews',
    label: 'Applying, no interviews',
    explain: 'Review eligibility, targeting, résumé evidence and timing. Silence alone does not identify a résumé problem.',
    steps: ['why-applications-get-rejected', 'ats-friendly-resume', 'tailoring-your-resume', 'rejection-diagnosis', 'no-interviews-after-100-applications', 'how-to-ask-for-a-referral'],
  },
  {
    id: 'no-offers',
    label: 'Interviews, no offers',
    explain: 'Review feedback and preparation alongside eligibility, competition and headcount.',
    steps: ['diagnose-your-job-search-funnel', 'getting-interviews-but-no-offers', 'recruiter-screen', 'behavioral-interviews', 'behavioral-story-bank-builder', 'how-to-prepare-for-a-multi-round-interview-loop', 'interview-postmortem'],
  },
  {
    id: 'technical-interviews',
    label: 'Technical interviews',
    explain: 'Treat preparation like a project: scope, plan, execute.',
    steps: ['interview-process', 'coding-interviews', 'leetcode-roadmap-for-new-grads', 'coding-assessments', 'system-design', 'sql-interview-preparation', 'ml-ai-interview-preparation', 'cloud-interview-preparation', 'role-specific-technical-preparation'],
  },
  {
    id: 'ai-interviews',
    label: 'AI interviews and assessments',
    explain: 'Check your invitation rather than assuming what is used or what you may use.',
    steps: ['ai-assisted-interviews', 'ai-coding-assessments', 'interview-tool-policies', 'take-home-assessments', 'ai-job-search-framework', 'interview-accessibility-and-accommodations'],
  },
  {
    id: 'international',
    label: 'F-1, OPT or STEM OPT',
    explain: 'Your search has an extra axis: work authorisation. Read the basics, then confirm with official sources and your DSO.',
    steps: ['international-student-job-search-center', 'opt-and-stem-opt', 'sponsorship-language', 'visa-sponsorship-and-citizenship', 'citizenship-and-clearance', 'background-checks-and-pre-employment-verification', 'opt-unemployment-days', 'cap-exempt-h1b-and-other-visas'],
  },
  {
    id: 'graduated',
    label: 'Already graduated',
    explain: 'Keep a routine, widen where you look, and explain the gap plainly.',
    steps: ['searching-after-graduation', 'job-search-without-an-internship', 'finding-hidden-new-grad-roles', 'rotational-and-development-programs', 'location-strategy'],
  },
  {
    id: 'career-switch',
    label: 'Switching careers',
    explain: 'Your past work is a transferable record, not a liability.',
    steps: ['career-switchers-and-non-cs-majors', 'are-you-qualified', 'build-a-target-company-list', 'new-grad-projects', 'what-makes-a-github-repo-impressive', 'startup-vs-enterprise'],
  },
  {
    id: 'have-offer',
    label: 'I have an offer',
    explain: 'Understand the package, check the market, then decide and prepare to start.',
    steps: ['evaluating-an-offer', 'understanding-compensation', 'compensation-research', 'comparing-offers', 'negotiation', 'questions-before-accepting', 'reading-your-employment-agreement', 'after-accepting-a-new-grad-offer', 'background-checks-and-pre-employment-verification', 'first-90-days'],
  },
].map((p) => Object.freeze({ ...p, steps: Object.freeze([...p.steps]) })));
