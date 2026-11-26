// The only script on the site: loads the Calendly scheduler when the visitor
// approaches the booking section, so Calendly is not contacted on page load.
// If Calendly is blocked (privacy extensions often do), a direct link stays visible.
(function () {
  var el = document.getElementById("calendly");
  if (!el) return;
  var url = el.getAttribute("data-url");
  var started = false;

  function failed() {
    var msg = el.querySelector(".book-fallback-text");
    if (msg) msg.textContent = el.getAttribute("data-error") || "";
  }

  function load() {
    if (started) return;
    started = true;
    var s = document.createElement("script");
    s.src = "https://assets.calendly.com/assets/external/widget.js";
    s.async = true;
    s.onload = function () {
      if (!window.Calendly) return failed();
      var fallback = el.querySelector(".book-fallback");
      window.Calendly.initInlineWidget({ url: url, parentElement: el });
      if (fallback) fallback.remove();
    };
    s.onerror = failed;
    document.head.appendChild(s);
  }

  if (location.hash === "#book" || !("IntersectionObserver" in window)) {
    load();
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    for (var i = 0; i < entries.length; i++) {
      if (entries[i].isIntersecting) { io.disconnect(); load(); return; }
    }
  }, { rootMargin: "600px 0px" });
  io.observe(el);
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href$="#book"]');
    if (a) load();
  });
})();
