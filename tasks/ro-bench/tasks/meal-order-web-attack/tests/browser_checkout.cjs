// Exercise the shipped page as a user would, with a deterministic HTTP stand-in.
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const { JSDOM } = require('jsdom');

const root = process.env.APP_ROOT || '/app';
const html = fs.readFileSync(path.join(root, 'public/index.html'), 'utf8');
const script = fs.readFileSync(path.join(root, 'public/assets/site.js'), 'utf8');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'menu/items.json'), 'utf8')).items;
const dom = new JSDOM(html, { url: 'http://ordering.local/', runScripts: 'outside-only' });
const { window } = dom;
const doc = window.document;
let available = 8;
let order = null;
const calls = [];
window.crypto.randomUUID = () => 'browser-review-key';
window.fetch = async (url, options = {}) => {
  const method = options.method || 'GET';
  const body = options.body ? JSON.parse(options.body) : null;
  calls.push({ url, method, body });
  let value;
  if (url === '/api/menu' && method === 'GET') {
    value = { items: catalog.map(item => ({ ...item, available: item.id === 'cheeseburger' ? available : 5 })) };
  } else if (url === '/api/quote' && method === 'POST') {
    assert.equal(body.items.length, 1);
    const line = body.items[0];
    assert.equal(line.id, 'cheeseburger');
    const subtotal = (1299 + (line.addons.includes('extra-cheese') ? 150 : 0)) * line.quantity;
    const discount = body.coupon === 'LUNCH10' ? Math.floor(subtotal / 10) : 0;
    const delivery = subtotal >= 2500 ? 0 : 399;
    value = { subtotal_cents: subtotal, discount_cents: discount,
      delivery_cents: delivery, total_cents: subtotal - discount + delivery };
  } else if (url === '/api/orders' && method === 'POST') {
    assert.equal(body.idempotency_key, 'browser-review-key');
    assert.deepEqual(body.items, [{ id: 'cheeseburger', quantity: 2, addons: ['extra-cheese'] }]);
    assert.equal(body.coupon, 'LUNCH10');
    order = { id: 'web-order-1', status: 'placed' };
    available -= 2;
    value = order;
  } else if (url === '/api/orders/web-order-1/cancel' && method === 'POST') {
    assert.ok(order);
    available += 2;
    value = { ...order, status: 'cancelled' };
  } else {
    throw new Error(`unexpected HTTP call: ${method} ${url}`);
  }
  return { ok: true, json: async () => value };
};

const tick = () => new Promise(resolve => setTimeout(resolve, 0));
const click = selector => {
  const element = doc.querySelector(selector);
  assert.ok(element, `missing control: ${selector}`);
  element.click();
};
async function main() {
  window.eval(script);
  await tick();
  assert.equal(doc.querySelectorAll('#menu-grid .menu-card').length, 12);
  click('[data-category="Mains"]');
  assert.ok(doc.querySelectorAll('#menu-grid .menu-card').length >= 3);
  click('[data-add="cheeseburger"]');
  await tick();
  click('[data-increase="0"]');
  await tick();
  const addon = doc.querySelector('[data-addon-line="0"]');
  assert.ok(addon, 'missing add-on control');
  addon.value = 'extra-cheese';
  addon.dispatchEvent(new window.Event('change', { bubbles: true }));
  await tick();
  const coupon = doc.getElementById('coupon');
  coupon.value = 'LUNCH10';
  coupon.dispatchEvent(new window.Event('input', { bubbles: true }));
  await tick();
  assert.match(doc.getElementById('quote').textContent, /\$26\.09/);
  click('#place-order');
  await tick();
  assert.match(doc.getElementById('order-message').textContent, /placed/);
  assert.equal(available, 6);
  click('#cancel-order');
  await tick();
  assert.match(doc.getElementById('order-message').textContent, /cancelled/);
  assert.equal(available, 8);
  assert.match(doc.getElementById('cart-lines').textContent, /empty/);
  for (const endpoint of ['/api/menu', '/api/quote', '/api/orders', '/api/orders/web-order-1/cancel']) {
    assert.ok(calls.some(call => call.url === endpoint), `missing flow: ${endpoint}`);
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
