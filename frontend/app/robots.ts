import type { MetadataRoute } from "next";

/**
 * Keeps the hidden Presentation Mode route out of search engines. Combined with
 * the per-page `noindex, nofollow` metadata, crawlers won't index or follow it.
 * There is no sitemap in this project, so the route can't leak through one.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/__present", "/__present/"],
    },
  };
}
