// Apply the appearance preference before rendering; storage may be unavailable.
(() => {
  let theme = 'frost';
  try {
    if (globalThis.localStorage.getItem('clubops.theme') === 'afterdark') theme = 'afterdark';
  } catch {
    // Appearance must never prevent sign-in or page rendering.
  }
  globalThis.document.documentElement.dataset.theme = theme;
})();
