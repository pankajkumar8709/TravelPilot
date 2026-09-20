/** Shared Framer Motion presets — response motion only.

  The guide's one orchestrated moment is the generation route-draw (in
  GeneratingState + DayView's initial draw). Everything here is fast response
  motion: opacity-only entrances (no uniform fade-slide-up), and a single
  highlight pulse for confirmed diffs.
 */
import type { Variants } from "framer-motion";
import { MOTION } from "./theme";

/** Opacity-only entrance — replaces the old fade+slide used on every card. */
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: MOTION.base, ease: MOTION.ease } },
  exit: { opacity: 0, transition: { duration: MOTION.fast } },
};

// Container that staggers its children's entrance in sequence order.
export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};

export const stepSwap: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: MOTION.base, ease: MOTION.ease } },
  exit: { opacity: 0, transition: { duration: MOTION.fast } },
};

/** Confirmed diff: ONE brief highlight pulse (~600ms), then settle. */
export const confirmPulse = (accent: string) => ({
  boxShadow: [`0 0 0px ${accent}00`, `0 0 18px ${accent}99`, `0 0 0px ${accent}00`],
  transition: { duration: 0.6, ease: "easeInOut" as const },
});
