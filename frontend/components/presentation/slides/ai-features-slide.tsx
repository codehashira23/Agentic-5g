"use client";
import { AI_FEATURES } from "@/lib/presentation/config";
import { Eyebrow, FeatureCard, SlideHeading, SlideLayout } from "../primitives";

export default function AiFeaturesSlide() {
  return (
    <SlideLayout>
      <Eyebrow>{AI_FEATURES.eyebrow}</Eyebrow>
      <SlideHeading gradient className="mb-9 max-w-4xl">
        {AI_FEATURES.title}
      </SlideHeading>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {AI_FEATURES.items.map((f, i) => (
          <FeatureCard
            key={f.title}
            icon={f.icon}
            title={f.title}
            desc={f.desc}
            tone={i % 2 === 0 ? "ai" : "cyan"}
          />
        ))}
      </div>
    </SlideLayout>
  );
}
