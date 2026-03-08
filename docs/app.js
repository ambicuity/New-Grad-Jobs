function countUp(el, target, duration = 1200, suffix = '') {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    el.textContent = target.toLocaleString() + suffix;
    return;
  }
  const start = performance.now();
  function frame(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    el.textContent = Math.floor(eased * target).toLocaleString() + (progress === 1 ? suffix : '');
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

async function updateStats() {
  const response = await fetch('jobs.json');
  const data = await response.json();
  const count = data.length;
  
  const jobCountEl = document.getElementById('job-count-hero');
  if (jobCountEl) countUp(jobCountEl, count);

  const companyCountEl = document.getElementById('company-count-hero');
  if (companyCountEl) countUp(companyCountEl, 150, 1200, '+');
}

document.addEventListener('DOMContentLoaded', updateStats);