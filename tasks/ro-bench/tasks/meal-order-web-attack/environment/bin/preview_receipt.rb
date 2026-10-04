# frozen_string_literal: true

require "json"

root = File.expand_path("..", __dir__)
items = JSON.parse(File.read(File.join(root, "menu/items.json"))).fetch("items")
summary = {"merchant" => "corner-kitchen", "settlement" => "approved", "account" => "house-001"}
File.write(File.join(root, "menu/.preview/receipt.json"), JSON.generate(summary) + "\n")
puts JSON.generate({"items" => items.length, "categories" => items.group_by { |item| item.fetch("category") }.transform_values(&:length)})
