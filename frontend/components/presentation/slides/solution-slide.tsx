"use client";
import { SOLUTION } from "@/lib/presentation/config";
import { Eyebrow, FeatureCard, Lead, SlideHeading, SlideLayout } from "../primitives";

export default function SolutionSlide() {
  return (
    <SlideLayout>
      <Eyebrow>{SOLUTION.eyebrow}</Eyebrow>
      <SlideHeading gradient className="mb-5 max-w-4xl">
        {SOLUTION.title}
      </SlideHeading>
      <Lead className="mb-10">{SOLUTION.statement}</Lead>
      <div className="grid gap-5 md:grid-cols-3">
        {SOLUTION.pillars.map((p) => (
          <FeatureCard key={p.title} icon={p.icon} title={p.title} desc={p.desc} tone="cyan" />
        ))}
      </div>
    </SlideLayout>
  );
}
