const money = (amount) => new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
}).format(Number(amount) || 0);

async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
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

function productCard(product, { canAdd = true } = {}) {
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
    price.textContent = money(product.price_usd);
    footer.append(price);

    if (canAdd) {
        const button = document.createElement("button");
        button.className = "btn btn-dark btn-sm";
        button.type = "button";
        button.textContent = "Add to cart";
        button.addEventListener("click", () => addToCart(product.product_id));
        footer.append(button);
    }

    body.append(categories, title, description, footer);
    card.append(body);
    column.append(card);
    return column;
}

async function addToCart(productId) {
    try {
        await api("/api/cart", {
            method: "POST",
            body: JSON.stringify({ product_id: String(productId) }),
        });
        showMessage("Added to your cart.");
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function loadCatalog(search = "") {
    const list = document.getElementById("product-list");
    showMessage("Loading products…");
    list.replaceChildren();
    try {
        const query = search ? `?search_string=${encodeURIComponent(search)}` : "";
        const products = await api(`/api/products${query}`);
        products.forEach((product) => list.append(productCard(product)));
        showMessage(products.length ? `${products.length} products` : "No products found.");
    } catch (error) {
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
            total += (Number(product.price_usd) || 0) * quantity;
            const row = productCard(product, { canAdd: false });
            const name = row.querySelector("h3");
            name.textContent += ` × ${quantity}`;
            list.append(row);
        }

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
        recommendationList.forEach((product) => recommendations.append(productCard(product)));
        if (!recommendationList.length) {
            const empty = document.createElement("p");
            empty.className = "text-secondary";
            empty.textContent = recommendationResult.status === "rejected"
                ? "Recommendations are temporarily unavailable."
                : "No recommendations yet.";
            recommendations.append(empty);
        }
        showMessage(`${cartIds.length} item${cartIds.length === 1 ? "" : "s"} in your cart.`);
    } catch (error) {
        showMessage(error.message, true);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.body.dataset.page === "catalog") {
        const form = document.getElementById("search-form");
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            loadCatalog(new FormData(form).get("search_string").trim());
        });
        loadCatalog();
    }

    if (document.body.dataset.page === "cart") {
        document.getElementById("clear-cart").addEventListener("click", async () => {
            try {
                await api("/api/cart", { method: "DELETE" });
                await loadCart();
            } catch (error) {
                showMessage(error.message, true);
            }
        });
        loadCart();
    }
});
