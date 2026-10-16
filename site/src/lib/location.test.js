import { describe, expect, it } from 'vitest';
import { countryOf, metroOf } from './location.js';

describe('countryOf: Indian locations as employers write them', () => {
  // Every string here appeared in the live feed on 2026-10-15 without being tagged India.
  it.each([
    'IN: Bangalore Technology BTC Office',
    'IN: Lilly Bengaluru',
    'IN - Chennai',
    'IND - Telangana - Hyderabad (Hitec City Raidurg)',
    'IND-Pune-Equifax Analytics-PEC',
    'Gurgaon',
    'Bangalore',
    'Chennai, Tamil Nadu',
    'Hyderabad, Telangana, IN',
    'Noida, Uttar Pradesh',
  ])('%s → India', (loc) => {
    expect(countryOf(loc)).toBe('IN');
  });

  it.each([
    ['Indianapolis, IN', 'US'],
    ['Fort Wayne, Indiana', 'US'],
    ['Delhi, NY', 'US'],
    ['Remote Indiana', 'US'],
    ['Toronto, ON, CA', 'CA'],
  ])('%s stays %s', (loc, code) => {
    expect(countryOf(loc)).toBe(code);
  });

  it('never makes an Indian city a US metro', () => {
    expect(metroOf('Hyderabad, Telangana, IN')).toBe(null);
    expect(metroOf('IN - Chennai')).toBe(null);
    expect(metroOf('Indianapolis, IN')).toEqual({ locality: 'Indianapolis', code: 'IN', label: 'Indianapolis, IN' });
  });
});
