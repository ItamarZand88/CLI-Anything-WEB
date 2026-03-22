// Site fingerprint script for playwright-cli run-code
// Usage: npx @playwright/cli@latest -s=<app> run-code "$(cat site-fingerprint.js)"
async page => {
  const mainResult = await page.evaluate(() => {
    const body = document.body ? document.body.textContent.toLowerCase() : "";
    const html = document.documentElement.outerHTML;
    const scripts = Array.from(document.querySelectorAll("script[src]")).map(s => s.src);
    return {
      framework: {
        nextPages: !!document.getElementById("__NEXT_DATA__"),
        nextApp: html.includes("self.__next_f.push"),
        nuxt: typeof window.__NUXT__ !== "undefined",
        remix: typeof window.__remixContext !== "undefined",
        gatsby: typeof window.___gatsby !== "undefined",
        sveltekit: typeof window.__sveltekit_data !== "undefined",
        googleBatch: typeof WIZ_global_data !== "undefined",
        angular: !!document.querySelector("[ng-version]"),
        react: !!document.querySelector("[data-reactroot]"),
        spaRoot: (document.querySelector("#app, #root, #__next, #__nuxt") || {}).id || null,
        preloadedState: typeof window.__INITIAL_STATE__ !== "undefined" || typeof window.__PRELOADED_STATE__ !== "undefined"
      },
      protection: {
        cloudflare: html.includes("cf-ray") || html.includes("__cf_bm") || !!document.cookie.match(/__cf_bm/),
        captcha: !!(document.querySelector(".g-recaptcha") || document.querySelector("#px-captcha") || document.querySelector(".h-captcha")),
        akamai: scripts.some(function(s) { return s.includes("akamai"); }),
        datadome: scripts.some(function(s) { return s.includes("datadome"); }),
        perimeterx: scripts.some(function(s) { return s.includes("perimeterx") || s.includes("/px/"); }),
        awsWaf: html.includes("aws-waf-token") || body.includes("automated access"),
        rateLimit: document.title.includes("429") || document.title.toLowerCase().includes("too many requests"),
        serviceWorker: !!(navigator.serviceWorker && navigator.serviceWorker.controller)
      },
      auth: {
        hasLoginButton: body.includes("sign in") || body.includes("log in") || body.includes("sign up"),
        hasUserMenu: !!document.querySelector("[aria-label*=account], [aria-label*=profile], .user-menu, .avatar, [data-testid*=avatar]"),
        hasAuthMeta: !!document.querySelector("meta[name=csrf-token], meta[name=_token]")
      },
      page: {
        title: document.title,
        url: location.href,
        lang: document.documentElement.lang || null,
        scripts: scripts.slice(0, 15)
      }
    };
  });

  var frames = page.frames();
  var iframes = [];
  for (var i = 1; i < frames.length; i++) {
    try {
      iframes.push({ index: i, url: frames[i].url(), name: frames[i].name() || null });
    } catch (e) {
      iframes.push({ index: i, url: "inaccessible", name: null });
    }
  }

  return Object.assign({}, mainResult, { iframes: iframes, iframeCount: iframes.length });
}
