import { createContext, useContext } from "react";
import type { Lang } from "./i18n";
import { PALETTES, type Mode, type Palette } from "./theme";

export interface UIContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  currency: string;
  setCurrency: (c: string) => void;
  mode: Mode;
  setMode: (m: Mode) => void;
  palette: Palette;
}

export const UIContext = createContext<UIContextValue>({
  lang: "en",
  setLang: () => {},
  currency: "INR",
  setCurrency: () => {},
  mode: "light",
  setMode: () => {},
  palette: PALETTES.light,
});

export const useUI = () => useContext(UIContext);
