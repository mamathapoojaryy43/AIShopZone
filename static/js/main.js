// AIShopzone — global client-side helpers (motion, skeletons, AJAX grid).

// ---- Toast ----
function showToast(message) {
    var container = document.getElementById("toastContainer");
    if (!container) return;
    var toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 3200);
}

// ---- Never show a broken image ----
// `error` events don't bubble, so we listen in the capture phase. Any <img>
// that fails to load is swapped to the placeholder (including images injected
// by the AJAX product grid). The guard prevents an infinite loop.
(function () {
    var placeholder = window.PLACEHOLDER_IMG;
    if (!placeholder) return;
    document.addEventListener("error", function (e) {
        var el = e.target;
        if (!el || el.tagName !== "IMG") return;
        if (el.src && el.src.endsWith(placeholder)) return;
        el.src = placeholder;
    }, true);
})();

/* ============================================================
   Reveal on scroll — lightweight fade + slide via one shared
   IntersectionObserver. Elements are tagged by JS only, so the
   site stays fully usable without JavaScript.
   ============================================================ */
var REVEAL_SELECTOR = ".hero-text, .section-head, .trust-card, .category-card, " +
    ".product-card, .order-card, .wishlist-card, .review, .empty-state";

function setupReveal() {
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Tag elements that should animate in.
    var taggables = document.querySelectorAll(REVEAL_SELECTOR);
    Array.prototype.forEach.call(taggables, function (el) {
        if (!el.classList.contains("reveal")) el.classList.add("reveal", "reveal--up");
    });

    if (reduce) {
        var all = document.querySelectorAll(".reveal");
        Array.prototype.forEach.call(all, function (el) { el.classList.add("is-visible"); });
        return;
    }

    // Stagger cards within their grid containers for a gentle cascade.
    var grids = document.querySelectorAll(
        ".product-grid, .category-row, .wishlist-grid, .trust, .order-grid, .review-list"
    );
    Array.prototype.forEach.call(grids, function (grid) {
        var kids = grid.children;
        for (var i = 0; i < kids.length && i < 12; i++) {
            kids[i].style.animationDelay = Math.min(i * 55, 480) + "ms";
        }
    });

    if (!window.__revealObserver) {
        window.__revealObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
                if (en.isIntersecting) {
                    en.target.classList.add("is-visible");
                    window.__revealObserver.unobserve(en.target);
                }
            });
        }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    }

    var unseen = document.querySelectorAll(".reveal:not(.is-visible)");
    Array.prototype.forEach.call(unseen, function (el) { window.__revealObserver.observe(el); });
}

/* ============================================================
   Loading skeletons — shimmer placeholders shown while the
   product grid is fetched.
   ============================================================ */
function skeletonGridHTML(n) {
    n = n || 9;
    var card =
        '<article class="skeleton-card">' +
            '<div class="skeleton sk-media"></div>' +
            '<div class="sk-body">' +
                '<div class="skeleton sk-line w70"></div>' +
                '<div class="skeleton sk-line w45"></div>' +
                '<div class="sk-row">' +
                    '<div class="skeleton sk-line price"></div>' +
                    '<div class="skeleton sk-line rating"></div>' +
                '</div>' +
            '</div>' +
        '</article>';
    var html = "";
    for (var i = 0; i < n; i++) html += card;
    return '<div class="product-grid">' + html + "</div>";
}

/* ============================================================
   AJAX product grid — fetch the partial fragment, swap it in
   while showing skeletons. Falls back to a full navigation if
   the request fails or the page lacks the grid container.
   ============================================================ */
function buildProductsUrl() {
    var form = document.getElementById("filterForm");
    if (!form) return window.location.pathname + window.location.search;
    var params = new URLSearchParams(new FormData(form)).toString();
    var base = form.getAttribute("action") || window.location.pathname;
    return base + (params ? "?" + params : "");
}

function loadProducts(url, push) {
    var main = document.getElementById("shopMain");
    if (!main) { window.location.href = url; return; }

    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) main.innerHTML = skeletonGridHTML(9);

    fetch(url, { headers: { "X-Requested-With": "fetch-partial" }, credentials: "same-origin" })
        .then(function (r) { if (!r.ok) throw new Error("bad response"); return r.text(); })
        .then(function (html) {
            main.innerHTML = html;
            if (push) history.pushState({}, "", url);
            else history.replaceState({}, "", url);
            setupReveal();
        })
        .catch(function () { window.location.href = url; });
}

/* ============================================================
   General UI (toast, nav, search, newsletter) + cart/wishlist.
   Card interactions use event delegation so they keep working
   after the grid is swapped by AJAX.
   ============================================================ */
function updateCartBadge(count) {
    var badge = document.getElementById("cartBadge");
    if (badge) badge.textContent = count;
}
function updateWishlistBadge(count) {
    var badge = document.getElementById("wishlistBadge");
    if (badge) badge.textContent = count;
}

function addToCart(productId, qty, onDone) {
    fetch(window.cartUrl.replace(/\/$/, "") + "/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, quantity: qty }),
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.ok) { updateCartBadge(data.count); if (onDone) onDone(true); }
            else if (onDone) { onDone(false); }
        })
        .catch(function () { if (onDone) onDone(false); });
}

function toggleWishlist(btn) {
    var id = btn.getAttribute("data-product");
    fetch(window.toggleWishlistUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: id }),
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.ok) {
                btn.classList.toggle("active", data.in_wishlist);
                updateWishlistBadge(data.count);
                showToast(data.in_wishlist ? "Added to wishlist" : "Removed from wishlist");
            } else { showToast("Could not update wishlist"); }
        })
        .catch(function () { showToast("Could not update wishlist"); });
}

document.addEventListener("DOMContentLoaded", function () {
    // ---- Mobile navigation ----
    var navToggle = document.getElementById("navToggle");
    var navMenu = document.getElementById("primaryNav");
    if (navToggle && navMenu) {
        navToggle.addEventListener("click", function () {
            var open = navMenu.classList.toggle("open");
            navToggle.setAttribute("aria-expanded", open ? "true" : "false");
        });
    }
    document.querySelectorAll(".nav-menu a").forEach(function (link) {
        link.addEventListener("click", function () {
            var menu = document.querySelector(".nav-menu");
            if (menu) menu.classList.remove("open");
            if (navToggle) navToggle.setAttribute("aria-expanded", "false");
        });
    });

    // ---- Search overlay ----
    var overlay = document.getElementById("searchOverlay");
    var toggle = document.getElementById("searchToggle");
    var closeBtn = document.getElementById("searchClose");
    if (toggle && overlay) {
        toggle.addEventListener("click", function () {
            overlay.classList.add("open");
            var input = overlay.querySelector("input");
            if (input) setTimeout(function () { input.focus(); }, 50);
        });
    }
    if (closeBtn && overlay) {
        closeBtn.addEventListener("click", function () { overlay.classList.remove("open"); });
    }
    if (overlay) {
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) overlay.classList.remove("open");
        });
    }
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && overlay) overlay.classList.remove("open");
    });

    // ---- Guest gate: only signed-in users can buy / wishlist ----
    function requireAuth(e) {
        if (window.isAuthed) return true;
        e.preventDefault();
        var next = "?next=" + encodeURIComponent(window.location.pathname);
        window.location.href = window.loginUrl + next;
        return false;
    }

    // ---- Google button (demo) ----
    var gbtn = document.getElementById("googleBtn");
    if (gbtn) gbtn.addEventListener("click", function () { showToast("Google sign-in is coming soon"); });

    // ---- Newsletter ----
    var nl = document.getElementById("newsletterForm");
    if (nl) {
        nl.addEventListener("submit", function (e) {
            e.preventDefault();
            nl.reset();
            showToast("Thanks for subscribing!");
        });
    }

    // ---- Delegated card interactions (survive AJAX swaps) ----
    document.addEventListener("click", function (e) {
        var qa = e.target.closest(".quick-add-btn");
        if (qa) {
            e.preventDefault();
            if (!requireAuth(e)) return;
            addToCart(qa.getAttribute("data-product"), 1, function (ok) {
                showToast(ok ? "Added to cart" : "Could not add to cart");
            });
            return;
        }
        var wl = e.target.closest(".wishlist-btn");
        if (wl) {
            e.preventDefault();
            if (!requireAuth(e)) return;
            toggleWishlist(wl);
        }
    });

    // ---- PDP: Add to cart / Buy now (static page, direct binds) ----
    document.querySelectorAll(".add-cart").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            if (!requireAuth(e)) return;
            var qty = document.getElementById("qtyInput");
            var n = qty ? parseInt(qty.value, 10) || 1 : 1;
            addToCart(btn.getAttribute("data-product"), n, function (ok) {
                showToast(ok ? "Added " + n + " to cart" : "Could not add to cart");
            });
        });
    });
    document.querySelectorAll(".buy-now").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            if (!requireAuth(e)) return;
            var qty = document.getElementById("qtyInput");
            var n = qty ? parseInt(qty.value, 10) || 1 : 1;
            addToCart(btn.getAttribute("data-product"), n, function () {
                window.location.href = window.cartUrl;
            });
        });
    });

    // ---- Entrance animations ----
    setupReveal();
});

/* ============================================================
   Shop / Products page — AJAX filters, sort, pagination.
   ============================================================ */
document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("filterForm");
    if (!form) return;

    // Mobile filter toggle
    var ft = document.getElementById("filterToggle");
    var sb = document.getElementById("shopSidebar");
    if (ft && sb) ft.addEventListener("click", function () { sb.classList.toggle("open"); });

    // Dual-range price slider
    var minR = document.getElementById("priceMin");
    var maxR = document.getElementById("priceMax");
    var minH = document.getElementById("minPriceInput");
    var maxH = document.getElementById("maxPriceInput");
    var minL = document.getElementById("priceMinLabel");
    var maxL = document.getElementById("priceMaxLabel");
    var range = document.getElementById("sliderRange");

    function paintSlider() {
        var lo = parseInt(minR.value, 10);
        var hi = parseInt(maxR.value, 10);
        if (lo > hi) { lo = hi = Math.min(lo, hi); }
        var floor = parseInt(minR.min, 10);
        var ceil = parseInt(minR.max, 10);
        var span = (ceil - floor) || 1;
        range.style.left = ((lo - floor) / span * 100) + "%";
        range.style.width = ((hi - lo) / span * 100) + "%";
        minL.textContent = "₹" + lo.toLocaleString("en-IN");
        maxL.textContent = "₹" + hi.toLocaleString("en-IN");
        minH.value = lo;
        maxH.value = hi;
    }

    if (minR && maxR) {
        minR.addEventListener("input", function () {
            if (parseInt(minR.value, 10) > parseInt(maxR.value, 10)) minR.value = maxR.value;
            paintSlider();
        });
        maxR.addEventListener("input", function () {
            if (parseInt(maxR.value, 10) < parseInt(minR.value, 10)) maxR.value = minR.value;
            paintSlider();
        });
        // Reload grid on release (avoids querying on every tick).
        minR.addEventListener("change", function () { loadProducts(buildProductsUrl(), false); });
        maxR.addEventListener("change", function () { loadProducts(buildProductsUrl(), false); });
        paintSlider();
    }

    // Filter submit + live checkboxes/radios -> AJAX grid update.
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        loadProducts(buildProductsUrl(), false);
    });
    form.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function (el) {
        el.addEventListener("change", function () { loadProducts(buildProductsUrl(), false); });
    });

    // Sort dropdown (delegated so it works after AJAX swaps).
    document.addEventListener("change", function (e) {
        if (e.target && e.target.id === "sortSelect") {
            var si = document.getElementById("sortInput");
            if (si) si.value = e.target.value;
            loadProducts(buildProductsUrl(), true);
        }
    });

    // Pagination (delegated).
    document.addEventListener("click", function (e) {
        var link = e.target.closest(".page-link, .page-nav");
        if (link && link.getAttribute("href")) {
            e.preventDefault();
            loadProducts(link.getAttribute("href"), true);
        }
    });

    // Back/forward navigation re-fetches the matching grid.
    window.addEventListener("popstate", function () {
        if (document.getElementById("shopMain")) {
            loadProducts(window.location.pathname + window.location.search, false);
        }
    });
});
