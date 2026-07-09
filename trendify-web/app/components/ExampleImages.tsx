"use client";

import { useState } from "react";
import type { ExampleImage } from "@/app/types/trends";

function ChevronLeft() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M11 14L6 9L11 4" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M7 4L12 9L7 14" />
    </svg>
  );
}

interface ExampleImagesProps {
  images: ExampleImage[];
  /** Override the outer container class — useful when embedding in a modal */
  containerClassName?: string;
}

export default function ExampleImages({
  images,
  containerClassName = "relative aspect-[3/4] bg-zinc-900 group overflow-hidden",
}: ExampleImagesProps) {
  const [index, setIndex] = useState(0);
  const [failedSet, setFailedSet] = useState<Set<number>>(new Set());

  if (images.length === 0) return null;

  const current = images[index];
  const hasFailed = failedSet.has(index);
  const canPrev = index > 0;
  const canNext = index < images.length - 1;

  // stopPropagation so nav clicks don't bubble up to a parent card onClick
  const prev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIndex((i) => Math.max(0, i - 1));
  };
  const next = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIndex((i) => Math.min(images.length - 1, i + 1));
  };
  const markFailed = () =>
    setFailedSet((prev) => new Set([...prev, index]));

  return (
    <div className={containerClassName}>

      {/* Image or fallback placeholder */}
      {hasFailed ? (
        <div className="w-full h-full flex items-center justify-center">
          <span className="text-zinc-600 text-xs font-mono">@{current.username}</span>
        </div>
      ) : (
        <img
          key={index}
          src={current.image_url}
          alt={`Outfit by @${current.username}`}
          className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-[filter] duration-500"
          onError={markFailed}
          loading="lazy"
        />
      )}

      {/* Influencer badge — top left, visible on hover */}
      {!hasFailed && current.username && (
        <a
          href={`https://www.instagram.com/${current.username}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute top-2.5 left-2.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10"
          onClick={(e) => e.stopPropagation()}
        >
          <span className="text-[10px] font-mono text-white bg-black/70 px-2 py-1 backdrop-blur-sm">
            @{current.username}
          </span>
        </a>
      )}

      {/* Prev arrow */}
      {images.length > 1 && canPrev && (
        <button
          onClick={prev}
          className="absolute left-0 top-0 bottom-0 w-12 flex items-center justify-start pl-2 bg-gradient-to-r from-black/60 to-transparent text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          aria-label="Previous image"
        >
          <ChevronLeft />
        </button>
      )}

      {/* Next arrow */}
      {images.length > 1 && canNext && (
        <button
          onClick={next}
          className="absolute right-0 top-0 bottom-0 w-12 flex items-center justify-end pr-2 bg-gradient-to-l from-black/60 to-transparent text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          aria-label="Next image"
        >
          <ChevronRight />
        </button>
      )}

      {/* Dot indicators */}
      {images.length > 1 && (
        <div className="absolute bottom-2.5 left-0 right-0 flex justify-center gap-1.5 pointer-events-none">
          {images.map((_, i) => (
            <div
              key={i}
              className={`h-[3px] rounded-full transition-all duration-300 ${
                i === index ? "w-5 bg-white" : "w-[5px] bg-white/35"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
