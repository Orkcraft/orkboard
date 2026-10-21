// A merged task leaves the field once (docs/specs/48-map-ideas.md §4.7): when a refresh shows an item gone that the field had a moment
// ago and it left because it was merged, its card is drawn once more, moving up and fading (`.map-leaving`, ≤1.1 s). None under
// `prefers-reduced-motion`, none on the first read (a component that has just been drawn has seen nothing leave), at most three at
// once: the rest leave without it.
import { useEffect, useRef, useState } from "preact/hooks";

export const LEAVING = 3;
const MS = 1100;
const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** `items` now (each with a stable `key(item)`); `merged(item)` is true for an item that was last seen and is merged now.
 *  Returns the items that are leaving, to be drawn at their old place with `.map-leaving`. */
export function useLeaving(items, key, merged) {
  const was = useRef(items);
  const [ghosts, setGhosts] = useState([]);
  const sig = items.map(key).join("|");
  useEffect(() => {
    const now = new Set(items.map(key));
    const gone = was.current.filter((x) => !now.has(key(x)) && merged(x));
    was.current = items;
    if (!gone.length || reducedMotion()) { setGhosts([]); return undefined; }
    setGhosts(gone.slice(0, LEAVING));
    const timer = setTimeout(() => setGhosts([]), MS);
    return () => clearTimeout(timer);
  }, [sig]);
  return ghosts;
}
