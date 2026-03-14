// main script
(function () {
  "use strict";

  const initTocFlyout = () => {
    const tocFlyout = document.querySelector("[data-toc-flyout]");
    if (!tocFlyout) return;

    const storageKey = "toc_flyout_pinned";
    const setPinned = (pinned) => {
      tocFlyout.setAttribute("data-toc-pinned", pinned ? "1" : "0");
      try {
        window.localStorage.setItem(storageKey, pinned ? "1" : "0");
      } catch (e) {}
    };

    try {
      const pinned = window.localStorage.getItem(storageKey) === "1";
      tocFlyout.setAttribute("data-toc-pinned", pinned ? "1" : "0");
    } catch (e) {}

    const pinButton = tocFlyout.querySelector("[data-toc-pin]");
    if (pinButton) {
      pinButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const isPinned = tocFlyout.getAttribute("data-toc-pinned") === "1";
        setPinned(!isPinned);
      });
    }

    tocFlyout.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("[data-toc-pin]")) return;
      setPinned(true);
    });
  };

  // Testimonial Slider
  // ----------------------------------------
  new Swiper(".testimonial-slider", {
    spaceBetween: 24,
    loop: true,
    pagination: {
      el: ".testimonial-slider-pagination",
      type: "bullets",
      clickable: true,
    },
    breakpoints: {
      768: {
        slidesPerView: 2,
      },
      992: {
        slidesPerView: 3,
      },
    },
  });

  initTocFlyout();
})();
