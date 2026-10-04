# frozen_string_literal: true

require "socket"
require "json"
require "cgi"
require_relative "lib/order_book"

ROOT = File.expand_path(__dir__)
BOOK = OrderBook.new
PORT = Integer(ENV.fetch("PORT", "9292"))

def response(code, body, type = "application/json")
  text = body.is_a?(String) ? body : JSON.generate(body)
  ["HTTP/1.1 #{code}\r\nContent-Type: #{type}\r\nContent-Length: #{text.bytesize}\r\nConnection: close\r\n\r\n", text]
end

def route(method, path, payload)
  case [method, path]
  when ["GET", "/"]
    response("200 OK", File.binread(File.join(ROOT, "public/index.html")), "text/html; charset=utf-8")
  when ["GET", "/api/menu"]
    response("200 OK", {"items" => BOOK.catalog})
  when ["POST", "/api/quote"]
    response("200 OK", BOOK.quote(payload))
  when ["POST", "/api/orders"]
    response("201 Created", BOOK.place(payload))
  else
    if method == "GET" && path.start_with?("/assets/")
      name = path.delete_prefix("/assets/")
      raise OrderBook::OrderError, "invalid asset" unless name.match?(/\A[a-z0-9_-]+\.(?:png|css|js)\z/)
      file = File.join(ROOT, "public/assets", name)
      raise OrderBook::OrderError, "missing asset" unless File.file?(file)
      type = {".png" => "image/png", ".css" => "text/css", ".js" => "application/javascript"}.fetch(File.extname(file))
      response("200 OK", File.binread(file), type)
    elsif method == "GET" && path.start_with?("/api/orders/")
      response("200 OK", BOOK.find(path.split("/").last))
    elsif method == "POST" && path.match?(%r{\A/api/orders/[^/]+/cancel\z})
      response("200 OK", BOOK.cancel(path.split("/")[-2]))
    else
      response("404 Not Found", {"error" => "not found"})
    end
  end
rescue OrderBook::OrderError, JSON::ParserError => error
  response("400 Bad Request", {"error" => error.message})
end

server = TCPServer.new("0.0.0.0", PORT)
loop do
  socket = server.accept
  begin
    request = socket.gets
    next unless request
    method, target = request.split(" ", 3)
    headers = {}
    while (line = socket.gets) && line != "\r\n"
      key, value = line.split(":", 2)
      headers[key.downcase] = value.to_s.strip
    end
    bytes = Integer(headers.fetch("content-length", "0"))
    raise OrderBook::OrderError, "request too large" if bytes > 65_536
    raw = bytes.zero? ? "{}" : socket.read(bytes)
    payload = JSON.parse(raw)
    status, body = route(method, target.split("?", 2).first, payload)
    socket.write(status)
    socket.write(body)
  rescue StandardError => error
    status, body = response("400 Bad Request", {"error" => error.message})
    socket.write(status)
    socket.write(body)
  ensure
    socket.close
  end
end
