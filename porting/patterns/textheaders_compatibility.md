# TextHeaders Encoding Compatibility: Python ↔ Zig

To ensure compatibility between Python and Zig implementations of the **tofu** protocol, the following rules must be followed for `TextHeaders`:

## 1. Character Encoding
- **UTF-8 Only:** All strings must be encoded/decoded using UTF-8 at the application boundaries.
- **Raw Bytes on Wire:** Internally, `TextHeaders` must be stored and transmitted as `bytes`.

## 2. Header Names
- **US-ASCII Recommended:** For maximum interoperability and performance, header names should be restricted to US-ASCII (subset of UTF-8).
- **Format:** `name: value
`

## 3. Header Values
- **Full UTF-8:** Header values can contain any Unicode character, encoded as UTF-8 bytes.

## 4. Python Implementation Strategy
- Store headers as `bytearray` internally.
- Use `.encode('utf-8')` when adding headers from Python strings.
- Use `.decode('utf-8', errors='replace')` when exposing headers to the Python application.
- Use the `bytes.find()` and slicing methods for efficient parsing of the wire format.
