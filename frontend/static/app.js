const money = (amount) => new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
}).format(Number(amount) || 0);

let catalogRequestId = 0;

async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            "correlation_id": crypto.randomUUID(),
            ...(options.headers || {}),
        },
    });
    if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${response.status})`);
    }
    return response.json();
}

function showMessage(text, isError = false) {
    const message = document.getElementById("page-message");
    if (!message) return;
    message.textContent = text;
    message.classList.toggle("text-danger", isError);
    message.classList.toggle("text-secondary", !isError);
}

function productCard(product, { canAdd = true, signedIn = false } = {}) {
    const column = document.createElement("div");
    column.className = "col-12 col-sm-6 col-lg-4";

    const card = document.createElement("article");
    card.className = "card h-100 border-0 shadow-sm product-card";

    const body = document.createElement("div");
    body.className = "card-body d-flex flex-column p-4";

    const categories = document.createElement("p");
    categories.className = "eyebrow mb-2";
    categories.textContent = Array.isArray(product.categories) ? product.categories.join(" · ") : "PRODUCT";

    const title = document.createElement("h3");
    title.className = "h5";
    title.textContent = product.name || "Product";

    const description = document.createElement("p");
    description.className = "text-secondary small flex-grow-1";
    description.textContent = product.description || "";

    const footer = document.createElement("div");
    footer.className = "d-flex justify-content-between align-items-center gap-2 mt-3";
    const price = document.createElement("strong");
    price.textContent = money(product.price);
    footer.append(price);

    if (canAdd) {
        const button = document.createElement("button");
        button.className = "btn btn-dark btn-sm";
        button.type = "button";
        button.textContent = signedIn ? "Add to cart" : "Sign in first";
        button.disabled = !signedIn;
        if (signedIn) button.addEventListener("click", () => addToCart(product));
        footer.append(button);
    }

    body.append(categories, title, description, footer);
    card.append(body);
    column.append(card);
    return column;
}

async function addToCart(product) {
    try {
        await api("/api/cart", {
            method: "POST",
            body: JSON.stringify(product),
        });
        if (document.body.dataset.page === "cart" && !(await loadCart())) return;
        showMessage("Added to your cart.");
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function loadCatalog(search = "") {
    const list = document.getElementById("product-list");
    const currentRequestId = ++catalogRequestId;
    showMessage("Loading products…");
    list.replaceChildren();
    try {
        const query = search ? `?search_string=${encodeURIComponent(search)}` : "";
        const products = await api(`/api/products${query}`);
        if (currentRequestId !== catalogRequestId) return;
        const signedIn = Boolean(document.body.dataset.userId);
        products.forEach((product) => list.append(productCard(product, { signedIn })));
        showMessage(products.length ? `${products.length} products` : "No products found.");
    } catch (error) {
        if (currentRequestId !== catalogRequestId) return;
        showMessage(error.message, true);
    }
}

function getCartItems(cart) {
    if (Array.isArray(cart)) return cart;
    if (Array.isArray(cart?.cart)) return cart.cart;
    if (Array.isArray(cart?.items)) return cart.items;
    return [];
}

function getProductId(item) {
    const id = typeof item === "object" && item !== null
        ? (item.product_id ?? item.id)
        : item;
    return id == null ? "" : String(id).replace(/^product-/, "");
}

async function loadCart() {
    const list = document.getElementById("cart-list");
    const recommendations = document.getElementById("recommendation-list");
    const checkoutSection = document.getElementById("checkout-section");
    const checkoutAmount = document.getElementById("checkout-amount");
    const checkoutButton = document.getElementById("checkout-button");
    showMessage("Loading your cart…");
    list.replaceChildren();
    recommendations.replaceChildren();
    try {
        const [cartResult, productsResult, recommendationResult] = await Promise.allSettled([
            api("/api/cart"),
            api("/api/products"),
            api("/api/recommendations"),
        ]);
        if (cartResult.status === "rejected") throw cartResult.reason;
        if (productsResult.status === "rejected") throw productsResult.reason;

        const cart = cartResult.value;
        const products = productsResult.value;
        const items = getCartItems(cart);
        const productById = new Map(products.map((product) => [String(product.product_id), product]));
        const cartIds = items.map(getProductId).filter(Boolean);
        const counts = new Map();
        cartIds.forEach((id) => counts.set(id, (counts.get(id) || 0) + 1));

        let total = 0;
        for (const [id, quantity] of counts) {
            const product = productById.get(id);
            if (!product) continue;
            total += (Number(product.price) || 0) * quantity;
            const row = productCard(product, { canAdd: false });
            const name = row.querySelector("h3");
            name.textContent += ` × ${quantity}`;
            list.append(row);
        }

        checkoutAmount.textContent = `Cart subtotal: ${money(total)}`;
        checkoutSection.hidden = counts.size === 0;
        checkoutButton.disabled = counts.size === 0;

        if (!list.children.length) {
            const empty = document.createElement("p");
            empty.className = "text-secondary";
            empty.textContent = "Your cart is empty. Browse the catalog to add something.";
            list.append(empty);
        } else {
            const totalRow = document.createElement("p");
            totalRow.className = "col-12 text-end fw-semibold mb-0";
            totalRow.textContent = `Cart total: ${money(total)}`;
            list.append(totalRow);
        }

        const recommendationList = recommendationResult.status === "fulfilled" && Array.isArray(recommendationResult.value)
            ? recommendationResult.value.slice(0, 5)
            : [];
        recommendationList.forEach((product) => recommendations.append(productCard(product, { signedIn: true })));
        if (!recommendationList.length) {
            const empty = document.createElement("p");
            empty.className = "text-secondary";
            empty.textContent = recommendationResult.status === "rejected"
                ? "Recommendations are temporarily unavailable."
                : "No recommendations yet.";
            recommendations.append(empty);
        }
        showMessage(`${cartIds.length} item${cartIds.length === 1 ? "" : "s"} in your cart.`);
        return true;
    } catch (error) {
        showMessage(error.message, true);
        return false;
    }
}

function initializeCheckout() {
    const form = document.getElementById("checkout-form");
    const button = document.getElementById("checkout-button");
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        form.classList.add("was-validated");
        if (!form.checkValidity()) return;

        button.disabled = true;
        button.textContent = "Placing order…";
        const values = new FormData(form);
        try {
            const result = await api("/api/checkout", {
                method: "POST",
                body: JSON.stringify({
                    shipping_address: {
                        name: values.get("shipping_name").trim(),
                        street: values.get("street").trim(),
                        city: values.get("city").trim(),
                        state: values.get("state").trim().toUpperCase(),
                        zip: Number(values.get("zip")),
                        country: values.get("country").trim(),
                    },
                    card_number: values.get("card_number"),
                    expiration_date: values.get("expiration_date"),
                    svn: values.get("svn"),
                }),
            });
            form.reset();
            form.classList.remove("was-validated");
            const orderSummary = document.getElementById("order-summary");
            document.getElementById("shipping-estimate").textContent = money(result.shipping_estimate);
            document.getElementById("order-total").textContent = money(result.total);
            orderSummary.hidden = false;
            await loadCart();
            const paymentStatus = result.payment?.status;
            const transactionId = result.payment?.transaction_id;
            showMessage(
                `Order placed${paymentStatus ? ` (${paymentStatus})` : ""}`
                + `${transactionId ? `. Transaction ID: ${transactionId}` : ""}.`,
            );
        } catch (error) {
            showMessage(error.message, true);
            button.disabled = false;
        } finally {
            button.textContent = "Place order";
        }
    });
}

async function initializeSession() {
    const form = document.getElementById("sign-in-form");
    const userIdInput = document.getElementById("user-id");
    const button = document.getElementById("sign-in-button");
    const openButton = document.getElementById("open-signin");
    const sessionStatus = document.getElementById("session-status");
    const modalElement = document.getElementById("sign-in-modal");
    if (!form || !userIdInput || !button || !openButton || !sessionStatus || !modalElement) {
        showMessage("The sign-in form did not load. Refresh the page or rebuild the frontend container.", true);
        return false;
    }

    const session = await api("/api/session");
    const userId = session.user_id || "";
    document.body.dataset.userId = userId;
    userIdInput.value = "";
    button.textContent = "Continue";
    openButton.textContent = "Sign in";
    sessionStatus.textContent = userId ? `Signed in as ${userId}` : "";

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        button.disabled = true;
        try {
            await api("/api/session", {
                method: "POST",
                body: JSON.stringify({ user_id: userIdInput.value }),
            });
            window.location.reload();
        } catch (error) {
            showMessage(error.message, true);
            button.disabled = false;
        }
    });

    if (!userId && document.body.dataset.page === "cart" && window.bootstrap?.Modal) {
        bootstrap.Modal.getOrCreateInstance(modalElement, {
            backdrop: "static",
            keyboard: false,
        }).show();
        modalElement.querySelector(".btn-close").hidden = true;
        userIdInput.focus();
    }

    return Boolean(userId);
}

document.addEventListener("DOMContentLoaded", () => {
    initializeSession().then((signedIn) => {
        if (document.body.dataset.page === "catalog") {
            const input = document.getElementById("search-input");
            input.addEventListener("input", () => loadCatalog(input.value.trim()));
            loadCatalog();
        }

        if (document.body.dataset.page === "cart") {
            const clearButton = document.getElementById("clear-cart");
            clearButton.disabled = !signedIn;
            if (signedIn) {
                initializeCheckout();
                clearButton.addEventListener("click", async () => {
                    try {
                        await api("/api/cart", { method: "DELETE" });
                        await loadCart();
                    } catch (error) {
                        showMessage(error.message, true);
                    }
                });
                loadCart();
            } else {
                showMessage("Enter your user ID above to view your cart and recommendations.");
            }
        }
    }).catch((error) => showMessage(error.message, true));
});
