"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getGlossaryEntry } from "../lib/glossary";
import type { GlossaryTerm } from "../lib/glossary";

type TooltipPosition = {
  left: number;
  top: number;
  placement: "top" | "bottom";
};

export function TermInfo({ term }: { term: GlossaryTerm }) {
  const entry = getGlossaryEntry(term);
  const tooltipId = useId();
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const popoverRef = useRef<HTMLSpanElement | null>(null);
  const closeTimerRef = useRef<number | null>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<TooltipPosition>({
    left: 0,
    top: 0,
    placement: "bottom"
  });

  function clearCloseTimer() {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }

  function updatePosition() {
    const button = buttonRef.current;
    if (!button) return;

    const rect = button.getBoundingClientRect();
    const margin = 12;
    const estimatedWidth = 280;
    const estimatedHeight = 140;

    const centeredLeft = rect.left + rect.width / 2;
    const left = Math.min(
      Math.max(centeredLeft, margin + estimatedWidth / 2),
      window.innerWidth - margin - estimatedWidth / 2
    );

    const bottomTop = rect.bottom + 10;
    const wouldOverflowBottom = bottomTop + estimatedHeight > window.innerHeight - margin;

    setPosition({
      left,
      top: wouldOverflowBottom ? rect.top - 10 : bottomTop,
      placement: wouldOverflowBottom ? "top" : "bottom"
    });
  }

  function openTooltip() {
    clearCloseTimer();
    updatePosition();
    setOpen(true);
  }

  function closeTooltip() {
    clearCloseTimer();
    setOpen(false);
  }

  function scheduleClose() {
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => {
      setOpen(false);
    }, 120);
  }

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (buttonRef.current?.contains(target)) return;
      if (popoverRef.current?.contains(target)) return;
      closeTooltip();
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeTooltip();
      }
    }

    function handleViewportChange() {
      closeTooltip();
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("scroll", handleViewportChange, true);
    window.addEventListener("resize", handleViewportChange);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("scroll", handleViewportChange, true);
      window.removeEventListener("resize", handleViewportChange);
    };
  }, [open]);

  return (
    <span className="term-info-wrap">
      <button
        ref={buttonRef}
        type="button"
        className="term-info"
        aria-label={`${entry.term}: ${entry.shortDefinition}`}
        aria-describedby={open ? tooltipId : undefined}
        aria-expanded={open}
        onBlur={scheduleClose}
        onClick={(event) => {
          event.stopPropagation();
          if (open) {
            closeTooltip();
          } else {
            openTooltip();
          }
        }}
        onFocus={openTooltip}
        onMouseEnter={openTooltip}
        onMouseLeave={scheduleClose}
      >
        i
      </button>

      {open && typeof document !== "undefined"
        ? createPortal(
            <span
              ref={popoverRef}
              id={tooltipId}
              className="term-info-popover"
              role="tooltip"
              onBlur={scheduleClose}
              onFocus={clearCloseTimer}
              onMouseEnter={clearCloseTimer}
              onMouseLeave={scheduleClose}
              style={{
                left: position.left,
                top: position.top,
                transform:
                  position.placement === "top"
                    ? "translate(-50%, -100%)"
                    : "translateX(-50%)"
              }}
            >
              <strong>{entry.term}</strong>
              <span>{entry.shortDefinition}</span>
              {entry.links?.[0] ? <Link href={entry.links[0].href}>{entry.links[0].label} →</Link> : null}
              <Link href={`/glossary#${entry.slug}`}>Glossary →</Link>
            </span>,
            document.body
          )
        : null}
    </span>
  );
}
