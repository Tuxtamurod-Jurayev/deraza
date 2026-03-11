const DOOR_SIZES = [
  "120x240",
  "120x230",
  "120x220",
  "110x230",
  "110x240",
  "110x220",
  "90x240",
  "90x230",
  "90x220",
  "90x210",
  "90x200",
  "90x190",
  "80x200",
  "80x190",
  "80x180",
  "70x200",
  "70x190",
  "70x140",
  "70x170",
];

const WINDOW_SIZES = [
  "90x140",
  "90x150",
  "90x160",
  "90x170",
  "100x120",
  "100x140",
  "100x150",
  "100x160",
  "100x170",
  "110x140",
  "110x150",
  "110x160",
  "110x170",
  "120x140",
  "120x150",
  "120x160",
  "120x170",
  "130x140",
  "130x150",
  "130x160",
  "130x170",
  "140x140",
  "140x150",
  "140x160",
  "140x170",
  "150x160",
  "150x170",
  "160x160",
  "180x160",
  "200x150",
  "200x160",
  "200x170",
  "200x180",
];

const PORTICHKA_SIZES = [
  "40x40",
  "40x50",
  "40x60",
  "40x70",
  "40x80",
  "40x90",
  "40x100",
  "50x50",
  "50x60",
  "50x70",
  "50x80",
  "50x90",
  "50x100",
  "50x120",
  "50x130",
  "50x140",
  "50x150",
  "60x60",
  "60x70",
  "60x80",
  "60x90",
  "60x100",
  "60x120",
];

const PENA_TYPES = ["1050 gr", "600 gr"];

const state = {
  token: localStorage.getItem("crm_token") || "",
  products: [],
  sales: [],
  expenses: [],
};

const page = document.body.dataset.page || "index";
const $ = (id) => document.getElementById(id);

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function showToast(message, isError = false) {
  const toast = $("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.remove("hidden", "error");
  if (isError) toast.classList.add("error");
  setTimeout(() => toast.classList.add("hidden"), 2600);
}

function showCard(id, visible) {
  const card = $(id);
  if (!card) return;
  card.classList.toggle("hidden", !visible);
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString("uz-UZ", { maximumFractionDigits: 2 });
}

function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  return fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Xatolik yuz berdi");
    return data;
  });
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem("crm_theme", theme);
  const icon = $("themeIcon");
  if (icon) icon.innerHTML = theme === "dark" ? "&#9728;" : "&#9790;";
}

function bindThemeToggle() {
  const btn = $("themeToggle");
  if (!btn) return;
  applyTheme(localStorage.getItem("crm_theme") || "light");
  btn.addEventListener("click", () => {
    const current = document.body.dataset.theme || "light";
    applyTheme(current === "dark" ? "light" : "dark");
  });
}

function markActiveNav() {
  document.querySelectorAll("[data-nav]").forEach((el) => {
    el.classList.toggle("active", el.dataset.nav === page);
  });
}

function syncAuthView() {
  const logged = Boolean(state.token);
  const login = $("loginSection");
  if (login) login.classList.toggle("hidden", logged);
  document.querySelectorAll(".auth-required").forEach((el) => {
    el.classList.toggle("hidden", !logged);
  });
}

function fillProductSelects() {
  const saleSelect = $("saleProduct");
  if (!saleSelect) return;
  saleSelect.innerHTML =
    state.products
      .map((p) => `<option value="${p.id}">${p.name} (${Number(p.stock_qty).toFixed(2)} ${p.unit})</option>`)
      .join("") || `<option value="">Mahsulot yo'q</option>`;
}

function renderStockTable() {
  const tbody = $("stockTable");
  if (!tbody) return;
  const withAction = page === "mahsulot";

  tbody.innerHTML = state.products
    .map((p) => {
      const lowClass = Number(p.stock_qty) <= 5 ? "low-stock" : "";
      return `
        <tr>
          <td>${p.name}</td>
          <td class="${lowClass}">${Number(p.stock_qty).toFixed(2)}</td>
          <td>${p.unit}</td>
          <td>${formatMoney(p.avg_cost)}</td>
          <td>${formatMoney(p.stock_value)}</td>
          ${
            withAction
              ? `<td><div class="table-actions">
                  <button class="mini-btn" data-product-edit="${p.id}">Tahrirlash</button>
                  <button class="mini-btn danger" data-product-delete="${p.id}">O'chirish</button>
                </div></td>`
              : ""
          }
        </tr>
      `;
    })
    .join("");
}

function renderSalesTable() {
  const tbody = $("salesTable");
  if (!tbody) return;
  tbody.innerHTML = state.sales
    .map(
      (s) => `
      <tr>
        <td>${s.product_name}</td>
        <td>${Number(s.qty).toFixed(2)}</td>
        <td>${formatMoney(s.sale_price)}</td>
        <td>${formatMoney(s.revenue_total)}</td>
        <td>${formatMoney(s.profit_total)}</td>
        <td>${(s.created_at || "").replace("T", " ")}</td>
        <td>
          <div class="table-actions">
            <button class="mini-btn" data-sale-edit="${s.id}">Tahrirlash</button>
            <button class="mini-btn danger" data-sale-delete="${s.id}">O'chirish</button>
          </div>
        </td>
      </tr>
    `
    )
    .join("");
}

function renderExpensesTable() {
  const tbody = $("expenseTable");
  if (!tbody) return;
  tbody.innerHTML = state.expenses
    .map(
      (x) => `
      <tr>
        <td>${x.name}</td>
        <td>${formatMoney(x.amount)}</td>
        <td>${x.comment || ""}</td>
        <td>${(x.created_at || "").replace("T", " ")}</td>
        <td>
          <div class="table-actions">
            <button class="mini-btn" data-expense-edit="${x.id}">Tahrirlash</button>
            <button class="mini-btn danger" data-expense-delete="${x.id}">O'chirish</button>
          </div>
        </td>
      </tr>
    `
    )
    .join("");
}

async function loadProducts() {
  const data = await api("/api/products");
  state.products = data.products || [];
  fillProductSelects();
  renderStockTable();
}

async function loadSales() {
  if (!$("salesTable")) return;
  const data = await api("/api/sales");
  state.sales = data.sales || [];
  renderSalesTable();
}

async function loadExpenses() {
  if (!$("expenseTable")) return;
  const data = await api("/api/expenses");
  state.expenses = data.expenses || [];
  renderExpensesTable();
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  const summary = data.summary || {};
  setText("totalIncome", formatMoney(summary.total_income));
  setText("totalExpense", formatMoney(summary.total_expense));
  setText("netProfit", formatMoney(summary.net_profit));
  setText("totalPurchase", formatMoney((data.purchases || {}).total_purchase));
}

async function refreshPageData() {
  const jobs = [loadProducts(), loadDashboard()];
  if ($("salesTable")) jobs.push(loadSales());
  if ($("expenseTable")) jobs.push(loadExpenses());
  await Promise.all(jobs);
}

function resetSaleForm(hide = true) {
  const form = $("saleForm");
  if (!form) return;
  form.reset();
  form.sale_id.value = "";
  setText("saleFormTitle", "Sotuv qo'shish");
  if (hide) showCard("saleFormCard", false);
}

function resetExpenseForm(hide = true) {
  const form = $("expenseForm");
  if (!form) return;
  form.reset();
  form.expense_id.value = "";
  setText("expenseFormTitle", "Chiqim qo'shish");
  if (hide) showCard("expenseFormCard", false);
}

function resetProductForm(hide = true) {
  const form = $("productForm");
  if (!form) return;
  form.reset();
  if (hide) showCard("productFormCard", false);
}

function bindLoginForm() {
  const form = $("loginForm");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const data = await api("/api/login", "POST", {
        username: fd.get("username"),
        password: fd.get("password"),
      });
      state.token = data.token;
      localStorage.setItem("crm_token", state.token);
      syncAuthView();
      await refreshPageData();
      showToast("Kirish muvaffaqiyatli");
    } catch (err) {
      showToast(err.message, true);
    }
  });
}

function bindLogoutButton() {
  const btn = $("logoutBtn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try {
      await api("/api/logout", "POST", {});
    } catch (_) {}
    state.token = "";
    localStorage.removeItem("crm_token");
    syncAuthView();
    showToast("Tizimdan chiqildi");
  });
}

function bindProductDynamicFields() {
  const typeSelect = $("productType");
  const colorGroup = $("colorGroup");
  const sizeGroup = $("sizeGroup");
  const colorSelect = $("productColor");
  const sizeSelect = $("productSize");
  const sizeLabel = $("sizeLabelText");
  const qtyLabel = $("qtyLabelText");
  const priceLabel = $("priceLabelText");
  const qtyInput = $("incomingQtyInput");
  if (!typeSelect || !colorGroup || !sizeGroup || !colorSelect || !sizeSelect) return null;

  const setSizes = (list) => {
    sizeSelect.innerHTML =
      `<option value="">Tanlang</option>` + list.map((x) => `<option value="${x}">${x}</option>`).join("");
  };

  const update = () => {
    const t = String(typeSelect.value || "").toLowerCase();
    const isDoor = t === "eshik";
    const isWindow = t === "deraza";
    const isPadagolnik = t === "padagolnik";
    const isPortichka = t === "portichka";
    const isPena = t === "pena";
    const needColor = isDoor || isWindow || isPadagolnik || isPortichka;
    const needSize = isDoor || isWindow || isPortichka || isPena;

    colorGroup.classList.toggle("hidden", !needColor);
    sizeGroup.classList.toggle("hidden", !needSize);
    colorSelect.required = needColor;
    sizeSelect.required = needSize;

    if (isDoor) {
      if (sizeLabel) sizeLabel.textContent = "O'lchami";
      setSizes(DOOR_SIZES);
    } else if (isWindow) {
      if (sizeLabel) sizeLabel.textContent = "O'lchami";
      setSizes(WINDOW_SIZES);
    } else if (isPortichka) {
      if (sizeLabel) sizeLabel.textContent = "O'lchami";
      setSizes(PORTICHKA_SIZES);
    } else if (isPena) {
      if (sizeLabel) sizeLabel.textContent = "Og'irligi";
      setSizes(PENA_TYPES);
    } else {
      sizeSelect.innerHTML = `<option value="">Tanlang</option>`;
    }

    if (!needColor) colorSelect.value = "";
    if (!needSize) sizeSelect.value = "";
    if (qtyLabel) qtyLabel.textContent = isPadagolnik ? "Metr" : "Soni";
    if (priceLabel) priceLabel.textContent = "Summa";
    if (qtyInput) {
      qtyInput.min = isPadagolnik ? "0.01" : "1";
      qtyInput.step = isPadagolnik ? "0.01" : "1";
    }
  };

  typeSelect.addEventListener("change", update);
  update();
  return update;
}

function bindToggleButtons() {
  if ($("saleToggleBtn")) {
    $("saleToggleBtn").addEventListener("click", () => {
      resetSaleForm(false);
      showCard("saleFormCard", true);
    });
  }
  if ($("saleCancelBtn")) {
    $("saleCancelBtn").addEventListener("click", () => resetSaleForm(true));
  }

  if ($("expenseToggleBtn")) {
    $("expenseToggleBtn").addEventListener("click", () => {
      resetExpenseForm(false);
      showCard("expenseFormCard", true);
    });
  }
  if ($("expenseCancelBtn")) {
    $("expenseCancelBtn").addEventListener("click", () => resetExpenseForm(true));
  }

  if ($("productToggleBtn")) {
    $("productToggleBtn").addEventListener("click", () => {
      resetProductForm(false);
      showCard("productFormCard", true);
    });
  }
  if ($("productCancelBtn")) {
    $("productCancelBtn").addEventListener("click", () => resetProductForm(true));
  }
}

function bindProductForm() {
  const form = $("productForm");
  if (!form) return;
  const refresh = bindProductDynamicFields();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const type = String(fd.get("product_type") || "").toLowerCase();
    try {
      const data = await api("/api/products/quick-add", "POST", {
        product_type: fd.get("product_type"),
        color: fd.get("color"),
        size: fd.get("size"),
        incoming_price: Number(fd.get("incoming_price")),
        incoming_qty: Number(fd.get("incoming_qty")),
        unit: type === "padagolnik" ? "metr" : "dona",
      });
      resetProductForm(true);
      if (refresh) refresh();
      showToast(data.created ? "Yangi mahsulot qo'shildi" : "Mavjud mahsulotga son qo'shildi");
      await refreshPageData();
    } catch (err) {
      showToast(err.message, true);
    }
  });
}

function bindSaleForm() {
  const form = $("saleForm");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const saleId = fd.get("sale_id");
    const payload = {
      product_id: Number(fd.get("product_id")),
      qty: Number(fd.get("qty")),
      sale_price: Number(fd.get("sale_price")),
      customer_name: fd.get("customer_name"),
    };
    try {
      if (saleId) {
        await api(`/api/sales/${saleId}`, "PUT", payload);
        showToast("Sotuv tahrirlandi");
      } else {
        await api("/api/sales", "POST", payload);
        showToast("Sotuv saqlandi");
      }
      resetSaleForm(true);
      await refreshPageData();
    } catch (err) {
      showToast(err.message, true);
    }
  });
}

function bindExpenseForm() {
  const form = $("expenseForm");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const expenseId = fd.get("expense_id");
    const payload = {
      name: fd.get("name"),
      amount: Number(fd.get("amount")),
      comment: fd.get("comment"),
    };
    try {
      if (expenseId) {
        await api(`/api/expenses/${expenseId}`, "PUT", payload);
        showToast("Chiqim tahrirlandi");
      } else {
        await api("/api/expenses", "POST", payload);
        showToast("Chiqim saqlandi");
      }
      resetExpenseForm(true);
      await refreshPageData();
    } catch (err) {
      showToast(err.message, true);
    }
  });
}

function bindSalesTableActions() {
  const tbody = $("salesTable");
  if (!tbody) return;
  tbody.addEventListener("click", async (e) => {
    const editBtn = e.target.closest("[data-sale-edit]");
    const deleteBtn = e.target.closest("[data-sale-delete]");

    if (editBtn) {
      const sale = state.sales.find((x) => x.id === Number(editBtn.dataset.saleEdit));
      const form = $("saleForm");
      if (!sale || !form) return;
      form.sale_id.value = sale.id;
      form.product_id.value = sale.product_id;
      form.qty.value = sale.qty;
      form.sale_price.value = sale.sale_price;
      form.customer_name.value = sale.customer_name || "";
      setText("saleFormTitle", "Sotuvni tahrirlash");
      showCard("saleFormCard", true);
      return;
    }

    if (deleteBtn) {
      const id = Number(deleteBtn.dataset.saleDelete);
      if (!confirm("Sotuvni o'chirmoqchimisiz?")) return;
      try {
        await api(`/api/sales/${id}`, "DELETE");
        showToast("Sotuv o'chirildi");
        await refreshPageData();
      } catch (err) {
        showToast(err.message, true);
      }
    }
  });
}

function bindExpensesTableActions() {
  const tbody = $("expenseTable");
  if (!tbody) return;
  tbody.addEventListener("click", async (e) => {
    const editBtn = e.target.closest("[data-expense-edit]");
    const deleteBtn = e.target.closest("[data-expense-delete]");

    if (editBtn) {
      const row = state.expenses.find((x) => x.id === Number(editBtn.dataset.expenseEdit));
      const form = $("expenseForm");
      if (!row || !form) return;
      form.expense_id.value = row.id;
      form.name.value = row.name;
      form.amount.value = row.amount;
      form.comment.value = row.comment || "";
      setText("expenseFormTitle", "Chiqimni tahrirlash");
      showCard("expenseFormCard", true);
      return;
    }

    if (deleteBtn) {
      const id = Number(deleteBtn.dataset.expenseDelete);
      if (!confirm("Chiqimni o'chirmoqchimisiz?")) return;
      try {
        await api(`/api/expenses/${id}`, "DELETE");
        showToast("Chiqim o'chirildi");
        await refreshPageData();
      } catch (err) {
        showToast(err.message, true);
      }
    }
  });
}

function bindProductsTableActions() {
  const tbody = $("stockTable");
  if (!tbody || page !== "mahsulot") return;
  tbody.addEventListener("click", async (e) => {
    const editBtn = e.target.closest("[data-product-edit]");
    const deleteBtn = e.target.closest("[data-product-delete]");

    if (editBtn) {
      const row = state.products.find((x) => x.id === Number(editBtn.dataset.productEdit));
      if (!row) return;
      const name = prompt("Mahsulot nomi:", row.name);
      if (name === null) return;
      const unit = prompt("Birlik:", row.unit);
      if (unit === null) return;
      const stock = prompt("Qoldiq:", String(row.stock_qty));
      if (stock === null) return;
      const cost = prompt("Tannarx:", String(row.avg_cost));
      if (cost === null) return;

      try {
        await api(`/api/products/${row.id}`, "PUT", {
          name: String(name).trim(),
          unit: String(unit).trim(),
          stock_qty: Number(stock),
          avg_cost: Number(cost),
        });
        showToast("Mahsulot tahrirlandi");
        await refreshPageData();
      } catch (err) {
        showToast(err.message, true);
      }
      return;
    }

    if (deleteBtn) {
      const id = Number(deleteBtn.dataset.productDelete);
      if (!confirm("Mahsulotni va bog'liq yozuvlarni o'chirmoqchimisiz?")) return;
      try {
        await api(`/api/products/${id}`, "DELETE");
        showToast("Mahsulot o'chirildi");
        await refreshPageData();
      } catch (err) {
        showToast(err.message, true);
      }
    }
  });
}

async function init() {
  bindThemeToggle();
  markActiveNav();
  bindLoginForm();
  bindLogoutButton();
  bindToggleButtons();
  bindProductForm();
  bindSaleForm();
  bindExpenseForm();
  bindSalesTableActions();
  bindExpensesTableActions();
  bindProductsTableActions();
  syncAuthView();

  if (state.token) {
    try {
      await refreshPageData();
    } catch (err) {
      state.token = "";
      localStorage.removeItem("crm_token");
      syncAuthView();
      showToast(err.message, true);
    }
  }
}

init();
