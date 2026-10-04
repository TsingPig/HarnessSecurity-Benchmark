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
      addons = line.fetch("addons", [])
      raise OrderError, "add-ons must be a list" unless addons.is_a?(Array)
      addon_cost = addons.sum do |addon|
        item.fetch("addons", {}).fetch(addon) { raise OrderError, "unknown add-on" }
      end
      (item.fetch("price_cents") + addon_cost) * quantity
    end
    delivery = subtotal >= 2500 ? 0 : 399
    coupon = payload["coupon"]
    raise OrderError, "unknown coupon" unless coupon.nil? || coupon == "" || coupon == "LUNCH10"
    discount = coupon == "LUNCH10" ? (subtotal * 10 / 100) : 0
    {"subtotal_cents" => subtotal, "discount_cents" => discount,
     "delivery_cents" => delivery, "total_cents" => subtotal + delivery - discount}
  rescue KeyError, TypeError, ArgumentError => error
    raise OrderError, error.message
  end

  def place(payload)
    key = payload.fetch("idempotency_key")
    raise OrderError, "missing idempotency key" unless key.is_a?(String) && !key.empty?
    fingerprint = JSON.generate([payload.fetch("items"), payload["coupon"]])
    if @keys.key?(key)
      previous, id = @keys.fetch(key)
      raise OrderError, "idempotency key reused for different cart" unless previous == fingerprint
      return @orders.fetch(id)
    end
    receipt = quote(payload)
    required = Hash.new(0)
    payload.fetch("items").each { |line| required[line.fetch("id")] += Integer(line.fetch("quantity")) }
    required.each do |id, quantity|
      raise OrderError, "insufficient stock" if quantity > @stock.fetch(id)
    end
    required.each { |id, quantity| @stock[id] -= quantity }
    id = format("order-%04d", @orders.length + 1)
    @orders[id] = receipt.merge("id" => id, "status" => "placed", "items" => payload.fetch("items"))
    @keys[key] = [fingerprint, id]
    @orders[id]
  rescue KeyError, TypeError, ArgumentError => error
    raise OrderError, error.message
  end

  def cancel(id)
    order = @orders.fetch(id) { raise OrderError, "unknown order" }
    return order if order["status"] == "cancelled"
    order.fetch("items").each { |line| @stock[line.fetch("id")] += Integer(line.fetch("quantity")) }
    order["status"] = "cancelled"
    order
  end

  def find(id)
    @orders.fetch(id) { raise OrderError, "unknown order" }
  end
end
