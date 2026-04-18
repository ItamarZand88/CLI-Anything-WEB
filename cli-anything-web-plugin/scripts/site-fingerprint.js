// Site fingerprint script for playwright-cli run-code
// Usage: npx @playwright/cli@latest -s=<app> run-code "$(cat site-fingerprint.js)"
async page => {
  const mainResult = await page.evaluate(() => {
    const body = document.body ? document.body.textContent.toLowerCase() : "";
    const html = document.documentElement.outerHTML;
    const title = (document.title || "").toLowerCase();
    const scripts = Array.from(document.querySelectorAll("script[src]")).map(s => s.src);
    const scriptsLower = scripts.map(s => s.toLowerCase());
    const cookie = document.cookie || "";

    // Cloudflare "managed challenge" (interstitial) — a site with cf_clearance
    // is still protected but reachable; a site SHOWING the challenge now cannot
    // be captured headless and requires camoufox.
    const cloudflareManagedChallenge = (
      title.includes("just a moment") ||
      body.includes("checking if the site connection is secure") ||
      body.includes("verifying you are human") ||
      !!document.querySelector("#challenge-stage, #challenge-running, .cf-browser-verification")
    );

    // AWS WAF — sites like Booking.com return a 202 JS-challenge page to raw
    // HTTP clients. Signals (when browser-rendered): aws-waf-token cookie,
    // CAPTCHA script, or "automated access" body text.
    const awsWafChallenge = (
      cookie.includes("aws-waf-token") ||
      scriptsLower.some(s => s.includes("captcha.prod.us-west-2.amazonaws.com") ||
                             s.includes("tokenapi") ||
                             s.includes("awswaf")) ||
      html.includes("aws-waf-token") ||
      body.includes("automated access")
    );

    // Akamai Bot Manager — multiple fingerprint signals beyond the script URL.
    const akamaiBotManager = (
      scriptsLower.some(s => s.includes("akamai") ||
                             s.includes("akstat") ||
                             s.endsWith("/_bm/sensor") ||
                             s.includes("_bm.js") ||
                             s.includes("/akam/")) ||
      cookie.includes("_abck") ||
      cookie.includes("bm_sz") ||
      cookie.includes("bm_sv")
    );

    // DataDome — check for both scripts and its interstitial page.
    const datadomeActive = (
      scriptsLower.some(s => s.includes("datadome")) ||
      cookie.includes("datadome") ||
      body.includes("datadome") ||
      !!document.querySelector("#dd-captcha-container, [data-cf-origin=datadome]")
    );

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
        cloudflare: html.includes("cf-ray") || html.includes("__cf_bm") || !!cookie.match(/__cf_bm|cf_clearance/),
        cloudflareManagedChallenge: cloudflareManagedChallenge,
        captcha: !!(document.querySelector(".g-recaptcha") || document.querySelector("#px-captcha") || document.querySelector(".h-captcha")),
        akamai: akamaiBotManager,
        datadome: datadomeActive,
        perimeterx: scriptsLower.some(s => s.includes("perimeterx") || s.includes("/px/")) || cookie.includes("_px"),
        awsWaf: awsWafChallenge,
        rateLimit: title.includes("429") || title.includes("too many requests"),
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
