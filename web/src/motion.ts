/** Shared Framer Motion presets — purposeful, fast (150-300ms). */
import type { Variants } from "framer-motion";
import { MOTION } from "./theme";

export const fadeIn: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: MOTION.base, ease: MOTION.ease } },
  exit: { opacity: 0, y: 8, transition: { duration: MOTION.fast } },
};

export const slideUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: MOTION.slow, ease: MOTION.ease } },
  exit: { opacity: 0, y: 24, transition: { duration: MOTION.fast } },
};

// Container that staggers its children's entrance (e.g. activity cards loading in).
export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};

export const stepSwap: Variants = {
  hidden: { opacity: 0, x: 32 },
  show: { opacity: 1, x: 0, transition: { duration: MOTION.base, ease: MOTION.ease } },
  exit: { opacity: 0, x: -32, transition: { duration: MOTION.fast } },
};

// A soft glow highlight used when a card is newly added/changed via chat.
export const glowHighlight = (accent: string) => ({
  boxShadow: [`0 0 0px ${accent}00`, `0 0 22px ${accent}aa`, `0 0 0px ${accent}00`],
  transition: { duration: 1.2, ease: "easeInOut" },
});
