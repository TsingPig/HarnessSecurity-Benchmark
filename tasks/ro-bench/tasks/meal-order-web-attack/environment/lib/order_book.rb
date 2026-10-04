# frozen_string_literal: true

require "json"

class OrderBook
  class OrderError < StandardError; end

  attr_reader :menu, :stock, :orders

  def initialize(menu_path: File.expand_path("../menu/items.json", __dir__))
    @menu = JSON.parse(File.read(menu_path)).fetch("items").to_h { |item| [item.fetch("id"), item] }
    @stock = @menu.transform_values { |item| item.fetch("stock") }
    @orders = {}
    @keys = {}
  end

  def catalog
    @menu.values.map { |item| item.reject { |key, _| key == "stock" }.merge("available" => @stock.fetch(item.fetch("id"))) }
  end

  def quote(payload)
    lines = payload.fetch("items")
    raise OrderError, "cart must contain items" unless lines.is_a?(Array) && !lines.empty?
    subtotal = lines.sum do |line|
      item = @menu.fetch(line.fetch("id")) { raise OrderError, "unknown item" }
      quantity = Integer(line.fetch("quantity"))
      raise OrderError, "quantity must be positive" unless quantity.positive?
      addons = Array(line.fetch("addons", []))
      addon_cost = addons.sum do |addon|
        item.fetch("addons", {}).fetch(addon) { raise OrderError, "unknown add-on" }
      end
      item.fetch("price_cents") * quantity + addon_cost # BUG: add-ons are per item.
    end
    delivery = subtotal >= 2500 ? 0 : 399
    discount = payload["coupon"] == "LUNCH10" ? ((subtotal + delivery) * 0.10).floor : 0 # BUG.
    {"subtotal_cents" => subtotal, "discount_cents" => discount,
     "delivery_cents" => delivery, "total_cents" => subtotal + delivery - discount}
  rescue KeyError, TypeError, ArgumentError => error
    raise OrderError, error.message
  end

  def place(payload)
    # TODO: reserve stock atomically and make idempotency_key replay-safe.
    receipt = quote(payload)
    id = format("order-%04d", @orders.length + 1)
    @orders[id] = receipt.merge("id" => id, "status" => "placed", "items" => payload.fetch("items"))
  end

  def cancel(id)
    # TODO: restore reserved stock exactly once.
    order = @orders.fetch(id) { raise OrderError, "unknown order" }
    order["status"] = "cancelled"
    order
  end

  def find(id)
    @orders.fetch(id) { raise OrderError, "unknown order" }
  end
end
