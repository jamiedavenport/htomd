import data from "./entities.json" with { type: "json" };

const named = new Map(Object.entries(data));
const legacyDecoder = new TextDecoder("windows-1252");

function numericReference(digits: string): string {
  const value = /^x/i.test(digits) ? Number.parseInt(digits.slice(1), 16) : Number(digits);
  if (!value || value > 0x10ffff || (value >= 0xd800 && value <= 0xdfff)) {
    return "\ufffd";
  }
  if (value >= 0x80 && value <= 0x9f) {
    return legacyDecoder.decode(Uint8Array.of(value));
  }
  if (
    (value >= 1 && value <= 8) ||
    value === 11 ||
    (value >= 14 && value <= 31) ||
    value === 127 ||
    (value >= 0xfdd0 && value <= 0xfdef) ||
    (value & 0xffff) >= 0xfffe
  ) {
    return "";
  }
  return String.fromCodePoint(value);
}

export function decodeEntities(value: string, attribute = false): string {
  return value.replace(
    /&(?:#(x[\da-f]+|\d+);?|([a-z][a-z\d]*;?))/gi,
    (original: string, digits: string | undefined, name: string | undefined, offset: number) => {
      if (digits !== undefined) {
        return numericReference(digits);
      }
      if (name === undefined) {
        return original;
      }
      for (let length = name.length; length > 0; length--) {
        const prefix = name.slice(0, length);
        const decoded = named.get(prefix);
        if (decoded === undefined) {
          continue;
        }
        const following = value[offset + length + 1] ?? "";
        if (attribute && !prefix.endsWith(";") && /[a-z\d=]/i.test(following)) {
          return original;
        }
        return decoded + name.slice(length);
      }
      return original;
    },
  );
}
