import type { MetadataRoute } from "next";

/**
 * Keeps the hidden routes out of search engines — the Presentation Mode deck
 * (/__present) and the internal docs walkthrough (/internal). Combined with
 * each page's `noindex, nofollow` metadata, crawlers won't index or follow them.
 * There is no sitemap in this project, so the routes can't leak through one.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/__present", "/__present/", "/internal", "/internal/"],
    },
  };
}
