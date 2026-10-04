const state = { items: [], cart: [], category: 'All', order: null, pendingKey: null };
const money = cents => `$${(cents / 100).toFixed(2)}`;
const grid = document.getElementById('menu-grid');
const tabs = document.getElementById('category-tabs');
const cartLines = document.getElementById('cart-lines');
const quoteBox = document.getElementById('quote');
const message = document.getElementById('order-message');

async function api(path, method = 'GET', body) {
  const response = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Request failed');
  return value;
}

async function loadMenu() {
  state.items = (await api('/api/menu')).items;
  renderMenu();
}

function renderMenu() {
  const categories = ['All', ...new Set(state.items.map(item => item.category))];
  tabs.innerHTML = categories.map(category => `<button type="button" data-category="${category}" class="${category === state.category ? 'active' : ''}">${category}</button>`).join('');
  grid.innerHTML = state.items.filter(item => state.category === 'All' || item.category === state.category).map(item => `
    <article class="menu-card" data-id="${item.id}"><img src="${item.image}" alt="${item.name}">
      <div class="details"><small>${item.category}</small><h3>${item.name}</h3>
        <p>${item.available} available</p>
        <div class="card-bottom"><strong>${money(item.price_cents)}</strong><button type="button" data-add="${item.id}" ${item.available ? '' : 'disabled'}>Add +</button></div>
      </div></article>`).join('');
}

function payload() {
  return { items: state.cart.map(line => ({ id: line.id, quantity: line.quantity, addons: line.addons })),
           coupon: document.getElementById('coupon').value.trim() };
}

async function renderCart() {
  cartLines.innerHTML = state.cart.length ? state.cart.map((line, index) => {
    const item = state.items.find(product => product.id === line.id);
    const options = Object.keys(item.addons || {});
    return `<div class="cart-line"><div><span>${item.name} x ${line.quantity}</span>
      ${options.length ? `<label>Add-ons <select data-addon-line="${index}"><option value="">None</option>${options.map(option => `<option value="${option}" ${line.addons.includes(option) ? 'selected' : ''}>${option} (+${money(item.addons[option])})</option>`).join('')}</select></label>` : ''}</div>
      <span><button type="button" data-decrease="${index}">-</button> <button type="button" data-increase="${index}">+</button></span></div>`;
  }).join('') : 'Your cart is empty.';
  if (!state.cart.length) { quoteBox.innerHTML = ''; return; }
  try {
    const quote = await api('/api/quote', 'POST', payload());
    quoteBox.innerHTML = `<div class="quote-line">Food <span>${money(quote.subtotal_cents)}</span></div><div class="quote-line">Discount <span>-${money(quote.discount_cents)}</span></div><div class="quote-line">Delivery <span>${money(quote.delivery_cents)}</span></div><div class="quote-line total">Total <span>${money(quote.total_cents)}</span></div>`;
  } catch (error) { quoteBox.textContent = error.message; }
}

tabs.addEventListener('click', event => {
  if (!event.target.dataset.category) return;
  state.category = event.target.dataset.category;
  renderMenu();
});

grid.addEventListener('click', event => {
  const id = event.target.dataset.add;
  if (!id) return;
  const line = state.cart.find(entry => entry.id === id && !entry.addons.length);
  if (line) line.quantity += 1;
  else state.cart.push({ id, quantity: 1, addons: [] });
  state.pendingKey = null;
  renderCart();
});

cartLines.addEventListener('click', event => {
  const index = Number(event.target.dataset.increase ?? event.target.dataset.decrease);
  if (!Number.isInteger(index) || !state.cart[index]) return;
  state.cart[index].quantity += event.target.dataset.increase === undefined ? -1 : 1;
  state.cart = state.cart.filter(entry => entry.quantity > 0);
  state.pendingKey = null;
  renderCart();
});

cartLines.addEventListener('change', event => {
  const index = Number(event.target.dataset.addonLine);
  if (!Number.isInteger(index) || !state.cart[index]) return;
  state.cart[index].addons = event.target.value ? [event.target.value] : [];
  state.pendingKey = null;
  renderCart();
});

document.getElementById('coupon').addEventListener('input', () => { state.pendingKey = null; renderCart(); });
document.getElementById('place-order').addEventListener('click', async () => {
  if (!state.cart.length) { message.textContent = 'Add something first.'; return; }
  const button = document.getElementById('place-order');
  button.disabled = true;
  try {
    state.pendingKey ||= crypto.randomUUID();
    const order = await api('/api/orders', 'POST', { ...payload(), idempotency_key: state.pendingKey });
    state.order = order;
    message.innerHTML = `Order ${order.id} placed. <button type="button" id="cancel-order">Cancel order</button>`;
    document.getElementById('cancel-order').addEventListener('click', async () => {
      const cancelled = await api(`/api/orders/${state.order.id}/cancel`, 'POST');
      message.textContent = `Order ${cancelled.id} cancelled.`;
      state.cart = [];
      state.pendingKey = null;
      await loadMenu();
      renderCart();
    });
    await loadMenu();
  } catch (error) { message.textContent = error.message; }
  finally { button.disabled = false; }
});

loadMenu().catch(error => { grid.textContent = `Menu unavailable: ${error.message}`; });
