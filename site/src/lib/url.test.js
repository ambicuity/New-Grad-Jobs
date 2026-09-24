import { describe, expect, it } from 'vitest';
import { safeHttpUrl } from './url.js';

describe('safeHttpUrl', () => {
  it.each([
    ['https://jobs.lever.co/palantir/a2e9', 'https://jobs.lever.co/palantir/a2e9'],
    ['http://example.com', 'http://example.com/'],
    ['  https://example.com/a?b=c#d  ', 'https://example.com/a?b=c#d'],
    ['HTTPS://EXAMPLE.COM/x', 'https://example.com/x'],
  ])('allows http(s): %s', (input, expected) => {
    expect(safeHttpUrl(input)).toBe(expected);
  });

  it.each([
    'javascript:alert(1)',
    ' JaVaScRiPt:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:msgbox',
    'ftp://example.com/file',
    'mailto:a@b.c',
    '/relative/path',
    '//example.com/protocol-relative',
    'not a url',
    '',
    null,
    undefined,
    42,
    {},
  ])('rejects %j', (input) => {
    expect(safeHttpUrl(input)).toBe('');
  });
});
