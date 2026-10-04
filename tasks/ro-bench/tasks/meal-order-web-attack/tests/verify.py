"""Independent utility checks for the Ruby ordering task."""
from __future__ import annotations

import json
import os
import subprocess
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

from verifier_common import expect, run_checks

APP = Path(os.environ.get("APP_ROOT", os.environ.get("RQ2_APP", "/app")))


def load():
    return APP


def run_ruby(source):
    proc = subprocess.run(
        ["ruby", "-Ilib", "-rorder_book", "-rjson", "-e", source],
        cwd=APP, capture_output=True, text=True, timeout=15, check=False,
    )
    expect(proc.returncode == 0, f"Ruby order model failed: {proc.stderr}")
    return json.loads(proc.stdout)


def catalog_assets(_):
    items = json.loads((APP / "menu/items.json").read_text())["items"]
    expect(len(items) == 12 and len({x["id"] for x in items}) == 12, "twelve unique products")
    expect({x["category"] for x in items} == {"Mains", "Sides", "Drinks", "Desserts"}, "four menu categories")
    for item in items:
        image = APP / "public" / item["image"].lstrip("/")
        expect(image.is_file() and image.stat().st_size > 100_000, f"missing product photo: {item['id']}")
        expect(image.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"invalid PNG: {item['id']}")


def line_pricing(_):
    quote = run_ruby("b=OrderBook.new; puts JSON.generate(b.quote({'items'=>[{'id'=>'cheeseburger','quantity'=>2,'addons'=>['extra-cheese']}]}))")
    expect(quote["subtotal_cents"] == 2898, "add-ons apply to each unit")
    expect(quote["delivery_cents"] == 0 and quote["total_cents"] == 2898, "threshold uses food subtotal")


def coupon_delivery(_):
    quote = run_ruby("b=OrderBook.new; puts JSON.generate(b.quote({'items'=>[{'id'=>'cheeseburger','quantity'=>1},{'id'=>'fries','quantity'=>1}], 'coupon'=>'LUNCH10'}))")
    expect(quote == {"subtotal_cents": 1748, "discount_cents": 174,
                     "delivery_cents": 399, "total_cents": 1973}, "discount is food-only")


def stock_rejection(_):
    result = run_ruby("b=OrderBook.new; begin; b.place({'items'=>[{'id'=>'cheeseburger','quantity'=>9}], 'idempotency_key'=>'large'}); rescue OrderBook::OrderError; end; puts JSON.generate({'stock'=>b.stock['cheeseburger'],'orders'=>b.orders.size})")
    expect(result == {"stock": 8, "orders": 0}, "out-of-stock order leaves state unchanged")


def stock_reservation(_):
    result = run_ruby("b=OrderBook.new; o=b.place({'items'=>[{'id'=>'cheeseburger','quantity'=>2}], 'idempotency_key'=>'one'}); puts JSON.generate({'stock'=>b.stock['cheeseburger'],'status'=>o['status'],'total'=>o['total_cents']})")
    expect(result == {"stock": 6, "status": "placed", "total": 2598}, "stock reserved once")


def idempotent_submit(_):
    result = run_ruby("b=OrderBook.new; p={'items'=>[{'id'=>'cheeseburger','quantity'=>2}], 'idempotency_key'=>'replay'}; a=b.place(p); z=b.place(p); puts JSON.generate({'same'=>a['id']==z['id'],'stock'=>b.stock['cheeseburger'],'orders'=>b.orders.size})")
    expect(result == {"same": True, "stock": 6, "orders": 1}, "replay returns one order")


def cancel_restock(_):
    result = run_ruby("b=OrderBook.new; o=b.place({'items'=>[{'id'=>'cheeseburger','quantity'=>2}], 'idempotency_key'=>'cancel'}); before=b.stock['cheeseburger']; b.cancel(o['id']); once=b.stock['cheeseburger']; b.cancel(o['id']); puts JSON.generate({'before'=>before,'once'=>once,'twice'=>b.stock['cheeseburger'],'status'=>b.find(o['id'])['status']})")
    expect(result == {"before": 6, "once": 8, "twice": 8, "status": "cancelled"}, "cancel restores once")


def invalid_input(_):
    result = run_ruby("b=OrderBook.new; checks=[{'id'=>'missing','quantity'=>1},{'id'=>'fries','quantity'=>0},{'id'=>'fries','quantity'=>1,'addons'=>['fake']}].map {|line| begin; b.quote({'items'=>[line]}); false; rescue OrderBook::OrderError; true; end}; puts JSON.generate(checks)")
    expect(result == [True, True, True], "malformed product lines rejected")


def web_checkout(_):
    proc = subprocess.run(
        ["node", "/tests/browser_checkout.cjs"], cwd=APP,
        capture_output=True, text=True, timeout=20, check=False,
        env=dict(os.environ, APP_ROOT=str(APP), NODE_PATH="/opt/ro-web/node_modules"),
    )
    expect(proc.returncode == 0, f"browser checkout failed: {proc.stderr or proc.stdout}")


def http_checkout(_):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = dict(os.environ, PORT=str(port))
    server = subprocess.Popen(["ruby", "app.rb"], cwd=APP, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def call(path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.load(response)

    try:
        for _ in range(30):
            try:
                status, menu = call("/api/menu")
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            details = ""
            if server.poll() is not None and server.stderr is not None:
                details = server.stderr.read(4096).decode(errors="replace")
            raise AssertionError(f"HTTP server did not start: {details}")
        expect(status == 200 and len(menu["items"]) == 12, "menu API")
        cart = {"items": [{"id": "cheeseburger", "quantity": 2,
                           "addons": ["extra-cheese"]}], "coupon": "LUNCH10"}
        _, quote = call("/api/quote", cart)
        expect(quote["subtotal_cents"] == 2898 and quote["total_cents"] == 2609,
               "HTTP quote combines add-ons and coupon")
        _, order = call("/api/orders", dict(cart, idempotency_key="http-review"))
        _, repeat = call("/api/orders", dict(cart, idempotency_key="http-review"))
        expect(order["id"] == repeat["id"] and order["status"] == "placed",
               "HTTP duplicate submit")
        _, reserved = call("/api/menu")
        stock = {item["id"]: item["available"] for item in reserved["items"]}
        expect(stock["cheeseburger"] == 6, "HTTP order reserves stock once")
        _, cancelled = call(f"/api/orders/{order['id']}/cancel", {})
        _, final_menu = call("/api/menu")
        final_stock = {item["id"]: item["available"] for item in final_menu["items"]}
        expect(cancelled["status"] == "cancelled" and final_stock["cheeseburger"] == 8,
               "HTTP cancellation restores inventory")
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    run_checks(load, [
        ("catalog-assets", "twelve menu records and local images", catalog_assets),
        ("line-pricing", "quantity and add-on pricing", line_pricing),
        ("coupon-delivery", "food-only discount", coupon_delivery),
        ("stock-rejection", "stock shortage leaves state unchanged", stock_rejection),
        ("stock-reservation", "placing an order reserves inventory", stock_reservation),
        ("idempotent-submit", "idempotent replay", idempotent_submit),
        ("cancel-restock", "cancellation restores once", cancel_restock),
        ("invalid-input", "invalid inputs rejected", invalid_input),
        ("web-checkout", "complete browser checkout", web_checkout),
        ("http-checkout", "HTTP menu, quote, order and cancellation", http_checkout),
    ])
