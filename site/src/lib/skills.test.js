import { describe, expect, it } from 'vitest';
import { MAX_SKILLS, extractSkills } from './skills.js';

describe('extractSkills', () => {
  it('returns [] for empty input', () => {
    expect(extractSkills('')).toEqual([]);
    expect(extractSkills(null)).toEqual([]);
    expect(extractSkills(undefined)).toEqual([]);
  });

  it('finds named skills in plain prose, in order of first mention, once each', () => {
    const text = 'You will build services in Python and C++ on AWS, deploy them with Kubernetes, and write more Python.';
    expect(extractSkills(text)).toEqual(['Python', 'C++', 'AWS', 'Kubernetes']);
  });

  it('matches whole tokens only', () => {
    // Java inside JavaScript, SQL inside PostgreSQL/NoSQL, Git inside GitHub are not separate skills.
    expect(extractSkills('Experience with JavaScript, PostgreSQL, NoSQL stores and GitHub.')).toEqual([
      'JavaScript', 'PostgreSQL',
    ]);
  });

  it('does not read common English words as skills', () => {
    expect(extractSkills('You react to incidents, excel at teamwork and spark ideas swiftly.')).toEqual([]);
  });

  it('reads lowercase spellings of unambiguous names, but not of common words', () => {
    expect(extractSkills('experience with python, sql and kubernetes on aws; you excel and react quickly; tree sap.')).toEqual([
      'Python', 'SQL', 'Kubernetes', 'AWS',
    ]);
  });

  it('handles symbol-heavy names and aliases under one label', () => {
    const text = 'Stack: C#, ASP.NET, Node.js, CI/CD, K8s, Google Cloud, Power BI and scikit-learn.';
    expect(extractSkills(text)).toEqual(['C#', '.NET', 'Node.js', 'CI/CD', 'Kubernetes', 'GCP', 'Power BI', 'scikit-learn']);
  });

  it('ignores text inside HTML tags but reads the rendered text', () => {
    expect(extractSkills('<p class="Python">Ship features in <b>TypeScript</b> and React.</p>')).toEqual([
      'TypeScript', 'React',
    ]);
  });

  it(`caps the list at ${MAX_SKILLS}`, () => {
    const text = 'Python Java JavaScript TypeScript C++ C# Rust Kotlin Swift Scala SQL Docker Kubernetes AWS Azure';
    expect(extractSkills(text)).toHaveLength(MAX_SKILLS);
  });
});
