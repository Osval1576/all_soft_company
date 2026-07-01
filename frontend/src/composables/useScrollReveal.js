import { onMounted, onBeforeUnmount } from "vue";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function useScrollReveal(getEl) {
  const reduced = typeof window !== "undefined"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let st;

  onMounted(() => {
    if (reduced) return;
    const el = typeof getEl === "function" ? getEl() : getEl;
    if (!el) return;
    gsap.from(el, {
      opacity: 0,
      y: 24,
      duration: 0.6,
      ease: "power2.out",
      scrollTrigger: { trigger: el, start: "top 85%" },
    });
  });

  onBeforeUnmount(() => st && st.kill());
}
