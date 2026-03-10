👋 Welcome to New Grad Jobs, @justaishing! Thank you for this contribution to optimize our frontend performance.

As Gemini Code Assist noted, hardcoding a versioned direct link to a Google Fonts `.woff2` file (`/v19/...`) is brittle. Google frequently rotates these URLs, meaning this link will eventually return a 404 and create a **wasted, render-blocking network request** that actually hurts performance.

Since we are hosted on GitHub Pages with zero-cost architecture (no build step), the most robust way to eliminate render-blocking Google Font fetches without statically hosting the font files yourself is to use the `media="print"` async loading pattern.

Please update `docs/index.html` to replace the exact font file preload with the following async stylesheet preload pattern:

```html
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    
    <!-- Preload the stylesheet itself to initiate the fetch early -->
    <link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap">
    
    <!-- Load the CSS asynchronously by deferring until print, then switching to all -->
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap" media="print" onload="this.media='all'">
    
    <!-- Fallback for users with JavaScript disabled -->
    <noscript>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap">
    </noscript>
```

This ensures we don't block the first paint, fixes the brittle URL issue, and satisfies the `#112` requirement. Let me know if you need any help making this change!
