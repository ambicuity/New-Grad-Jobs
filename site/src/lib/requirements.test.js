import { describe, expect, it } from 'vitest';
import { REQUIREMENTS_CACHE_SIZE, extractRequirements } from './requirements.js';

describe('extractRequirements', () => {
  it('returns [] for empty input', () => {
    expect(extractRequirements('')).toEqual([]);
    expect(extractRequirements(null)).toEqual([]);
  });

  it('pulls bullet items from a requirements section, stopping at the next header', () => {
    const desc = 'We build things. Requirements: - BS in Computer Science or related field '
      + '- Proficiency in Python or Go - Strong communication skills Benefits: - free lunch every day';
    expect(extractRequirements(desc)).toEqual([
      'BS in Computer Science or related field',
      'Proficiency in Python or Go',
      'Strong communication skills',
    ]);
  });

  it('splits numbered items and drops too-short fragments', () => {
    const desc = 'Qualifications 1. Experience with distributed systems 2. Familiar with SQL databases 3. ok';
    expect(extractRequirements(desc)).toEqual([
      'Experience with distributed systems',
      'Familiar with SQL databases',
    ]);
  });

  it('caps the list at 8 items', () => {
    const items = Array.from({ length: 12 }, (_, i) => `- requirement number ${i} is here`).join(' ');
    expect(extractRequirements(`Requirements: ${items}`)).toHaveLength(8);
  });

  it('falls back to <li> items when there is no usable header section', () => {
    const html = '<p>Join us.</p><ul><li>Build reliable backend services</li>'
      + '<li>Write&nbsp;well-tested code daily</li><li>Collaborate with product teams</li></ul>';
    expect(extractRequirements(html)).toEqual([
      'Build reliable backend services',
      'Write well-tested code daily',
      'Collaborate with product teams',
    ]);
  });

  it('needs at least three <li> items for the fallback', () => {
    expect(extractRequirements('<ul><li>Build reliable backend services</li><li>Another good item here</li></ul>')).toEqual([]);
  });

  it('returns [] for prose without structure', () => {
    expect(extractRequirements('A friendly team building useful tools for everyone.')).toEqual([]);
  });
});

describe('extractRequirements memoisation', () => {
  const desc = (n) => `Requirements: - Proficiency in language number ${n} - Strong communication skills for ${n}`;

  it('returns the cached result (same array) for a repeated description', () => {
    const first = extractRequirements(desc(1));
    expect(first).toHaveLength(2);
    expect(extractRequirements(desc(1))).toBe(first);
  });

  it('keeps a bounded number of descriptions, evicting the oldest', () => {
    const first = extractRequirements(desc('evict-me'));
    for (let i = 0; i < REQUIREMENTS_CACHE_SIZE; i++) extractRequirements(desc(`fill-${i}`));
    const again = extractRequirements(desc('evict-me'));
    expect(again).toEqual(first);
    expect(again).not.toBe(first);
  });
});

describe('extractRequirements tag stripping', () => {
  it('leaves no angle brackets when tags are nested to survive a single pass', () => {
    const desc = '<ul>' + ['Python <scr<b>ipt>x</scr<b>ipt>', 'Go and Rust experience', 'Distributed systems basics']
      .map((t) => `<li>${t}</li>`).join('') + '</ul>';
    const items = extractRequirements(desc);
    expect(items.length).toBeGreaterThan(0);
    for (const item of items) expect(item).not.toMatch(/[<>]/);
  });
});
