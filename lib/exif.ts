// Strips photo metadata (EXIF, XMP, text chunks) before a report photo is sent to the model, so GPS position,
// camera serial and timestamps never leave the server. Only the location the reporter picked on the map is sent.
// Unknown or malformed files are returned unchanged rather than rejected.

function stripJpeg(b: Buffer): Buffer {
  const out: Buffer[] = [b.subarray(0, 2)];
  let i = 2;
  while (i + 4 <= b.length && b[i] === 0xff) {
    const marker = b[i + 1];
    // start of scan: the rest is image data
    if (marker === 0xda) break;
    const len = b.readUInt16BE(i + 2);
    // APP1 (EXIF, XMP), APP13 (IPTC) and COM segments carry metadata
    if (marker !== 0xe1 && marker !== 0xed && marker !== 0xfe) out.push(b.subarray(i, i + 2 + len));
    i += 2 + len;
  }
  out.push(b.subarray(i));
  return Buffer.concat(out);
}

function stripPng(b: Buffer): Buffer {
  const drop = new Set(["eXIf", "tEXt", "zTXt", "iTXt", "tIME"]);
  const out: Buffer[] = [b.subarray(0, 8)];
  let i = 8;
  while (i + 12 <= b.length) {
    const len = b.readUInt32BE(i);
    const type = b.toString("latin1", i + 4, i + 8);
    const end = i + 12 + len;
    if (!drop.has(type)) out.push(b.subarray(i, end));
    i = end;
  }
  return Buffer.concat(out);
}

function stripWebp(b: Buffer): Buffer {
  const out: Buffer[] = [];
  let i = 12;
  while (i + 8 <= b.length) {
    const type = b.toString("latin1", i, i + 4);
    const len = b.readUInt32LE(i + 4);
    const end = i + 8 + len + (len % 2);
    if (type === "VP8X") {
      const c = Buffer.from(b.subarray(i, end));
      c[8] &= ~0x0c; // clear the EXIF and XMP flags
      out.push(c);
    } else if (type !== "EXIF" && type !== "XMP ") {
      out.push(b.subarray(i, end));
    }
    i = end;
  }
  const body = Buffer.concat(out);
  const head = Buffer.from(b.subarray(0, 12));
  head.writeUInt32LE(body.length + 4, 4);
  return Buffer.concat([head, body]);
}

export function hapusMetadata(b: Buffer, type: string): Buffer {
  try {
    if (type === "image/jpeg" && b[0] === 0xff && b[1] === 0xd8) return stripJpeg(b);
    if (type === "image/png" && b.toString("latin1", 1, 4) === "PNG") return stripPng(b);
    if (type === "image/webp" && b.toString("latin1", 0, 4) === "RIFF" && b.toString("latin1", 8, 12) === "WEBP") return stripWebp(b);
  } catch {
    // fall through: a file we cannot parse is sent as it is
  }
  return b;
}
