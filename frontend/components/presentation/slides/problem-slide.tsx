"use client";
import { PROBLEM } from "@/lib/presentation/config";
import { Eyebrow, FeatureCard, SlideHeading, SlideLayout } from "../primitives";

export default function ProblemSlide() {
  return (
    <SlideLayout>
      <Eyebrow>{PROBLEM.eyebrow}</Eyebrow>
      <SlideHeading className="mb-10 max-w-4xl">{PROBLEM.title}</SlideHeading>
      <div className="grid gap-5 sm:grid-cols-2">
        {PROBLEM.points.map((p) => (
          <FeatureCard key={p.title} icon={p.icon} title={p.title} desc={p.desc} />
        ))}
      </div>
    </SlideLayout>
  );
}
