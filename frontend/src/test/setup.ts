import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement matchMedia / IntersectionObserver. Stub them so
// components that touch them don't blow up during tests.
if (typeof window !== "undefined") {
  if (!window.matchMedia) {
    window.matchMedia = (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    });
  }
  if (!window.IntersectionObserver) {
    // @ts-expect-error -- minimal stub
    window.IntersectionObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() {
        return [];
      }
    };
  }
}

// Reset localStorage between tests so the auth store starts clean.
beforeEach(() => {
  localStorage.clear();
});
