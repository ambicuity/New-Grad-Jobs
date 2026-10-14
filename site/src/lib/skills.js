// Skill names mentioned in a job description, for the detail pane's fallback
// when no requirements list can be extracted (lib/requirements.js).
//
// Honesty: only names that appear verbatim in the description are returned,
// and the UI labels them "mentioned in the description", never "required".
// Matching is token-bounded, so "Java" inside "JavaScript" or "SQL" inside
// "PostgreSQL" is not a match, and case-insensitive except for names that are
// also everyday words (EXACT_CASE): "react to", "excel at", "spark ideas" and
// "tree sap" never read as skills, while "python" or "kubernetes" still do.

import { stripTags } from './requirements.js';

export const MAX_SKILLS = 12;

// [label, ...spellings]. Ambiguous one-letter or common-word names (Go, R, C)
// are left out on purpose.
const SKILLS = [
  ['Python'], ['Java'], ['JavaScript'], ['TypeScript'], ['C++'], ['C#'], ['Rust'], ['Kotlin'], ['Swift'],
  ['Scala'], ['Ruby'], ['Golang'], ['MATLAB'], ['SQL'], ['PostgreSQL', 'Postgres'], ['MySQL'], ['MongoDB'],
  ['Redis'], ['Kafka'], ['Spark', 'Apache Spark'], ['Hadoop'], ['Airflow'], ['Snowflake'], ['Databricks'],
  ['Tableau'], ['Power BI'], ['Excel'], ['React', 'React.js', 'ReactJS'], ['Angular'], ['Vue', 'Vue.js'],
  ['Node.js', 'NodeJS'], ['Django'], ['Flask'], ['Spring Boot'], ['.NET', 'ASP.NET'],
  ['AWS', 'Amazon Web Services'], ['Azure'], ['GCP', 'Google Cloud'], ['Docker'], ['Kubernetes', 'K8s'],
  ['Terraform'], ['Linux'], ['Git'], ['CI/CD'], ['GraphQL'], ['TensorFlow'], ['PyTorch'], ['scikit-learn'],
  ['Pandas'], ['Verilog'], ['VHDL'], ['FPGA'], ['Salesforce'], ['SAP'], ['AutoCAD'], ['SolidWorks'],
  ['Figma'], ['HTML'], ['CSS'],
];

// Names that are also ordinary English words: matched only as spelled.
const EXACT_CASE = new Set([
  'Swift', 'Rust', 'Ruby', 'Spark', 'Excel', 'React', 'Vue', 'Angular', 'Flask', 'Pandas', 'Git', 'SAP',
  'Snowflake', 'Airflow', 'Spring Boot', 'Figma',
]);

const escape = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
// A spelling must not touch a letter, digit or the symbols that extend names
// (C → C++ / C#, ASP → ASP.NET, Node → Node.js).
const MATCHERS = SKILLS.map(([label, ...aliases]) => ({
  label,
  re: new RegExp(
    `(?<![\\w+#.])(?:${[label, ...aliases].map(escape).join('|')})(?![\\w+#])`,
    EXACT_CASE.has(label) ? 'g' : 'gi',
  ),
}));

/**
 * @param {string|null|undefined} desc description text or HTML
 * @returns {string[]} up to MAX_SKILLS skill labels, in order of first mention.
 */
export function extractSkills(desc) {
  if (!desc) return [];
  const text = stripTags(desc).replace(/&nbsp;/g, ' ');
  const found = [];
  for (const { label, re } of MATCHERS) {
    re.lastIndex = 0;
    const match = re.exec(text);
    if (match) found.push([match.index, label]);
  }
  return found.sort((a, b) => a[0] - b[0]).slice(0, MAX_SKILLS).map(([, label]) => label);
}
