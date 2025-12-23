const K = new Uint32Array([
  0x428a2f98,
  0x71374491,
  0xb5c0fbcf,
  0xe9b5dba5,
  0x3956c25b,
  0x59f111f1,
  0x923f82a4,
  0xab1c5ed5,
  0xd807aa98,
  0x12835b01,
  0x243185be,
  0x550c7dc3,
  0x72be5d74,
  0x80deb1fe,
  0x9bdc06a7,
  0xc19bf174,
  0xe49b69c1,
  0xefbe4786,
  0x0fc19dc6,
  0x240ca1cc,
  0x2de92c6f,
  0x4a7484aa,
  0x5cb0a9dc,
  0x76f988da,
  0x983e5152,
  0xa831c66d,
  0xb00327c8,
  0xbf597fc7,
  0xc6e00bf3,
  0xd5a79147,
  0x06ca6351,
  0x14292967,
  0x27b70a85,
  0x2e1b2138,
  0x4d2c6dfc,
  0x53380d13,
  0x650a7354,
  0x766a0abb,
  0x81c2c92e,
  0x92722c85,
  0xa2bfe8a1,
  0xa81a664b,
  0xc24b8b70,
  0xc76c51a3,
  0xd192e819,
  0xd6990624,
  0xf40e3585,
  0x106aa070,
  0x19a4c116,
  0x1e376c08,
  0x2748774c,
  0x34b0bcb5,
  0x391c0cb3,
  0x4ed8aa4a,
  0x5b9cca4f,
  0x682e6ff3,
  0x748f82ee,
  0x78a5636f,
  0x84c87814,
  0x8cc70208,
  0x90befffa,
  0xa4506ceb,
  0xbef9a3f7,
  0xc67178f2,
]);

const INITIAL_HASH = new Uint32Array([
  0x6a09e667,
  0xbb67ae85,
  0x3c6ef372,
  0xa54ff53a,
  0x510e527f,
  0x9b05688c,
  0x1f83d9ab,
  0x5be0cd19,
]);

const rotr = (value: number, shift: number) => (value >>> shift) | (value << (32 - shift));
const ch = (x: number, y: number, z: number) => (x & y) ^ (~x & z);
const maj = (x: number, y: number, z: number) => (x & y) ^ (x & z) ^ (y & z);
const sigma0 = (x: number) => rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22);
const sigma1 = (x: number) => rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25);
const gamma0 = (x: number) => rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3);
const gamma1 = (x: number) => rotr(x, 17) ^ rotr(x, 19) ^ (x >>> 10);

class Sha256 {
  private readonly hash = new Uint32Array(INITIAL_HASH);
  private readonly buffer = new Uint8Array(64);
  private readonly words = new Uint32Array(64);
  private bufferLength = 0;
  private bytesHashed = 0;
  private finished = false;

  update(data: Uint8Array): void {
    if (this.finished) {
      throw new Error("SHA256: cannot update because digest was already computed.");
    }
    let position = 0;
    this.bytesHashed += data.length;
    if (this.bufferLength > 0) {
      const take = Math.min(64 - this.bufferLength, data.length);
      this.buffer.set(data.subarray(0, take), this.bufferLength);
      this.bufferLength += take;
      position += take;
      if (this.bufferLength === 64) {
        this.processBlock(this.buffer);
        this.bufferLength = 0;
      }
    }
    while (position + 64 <= data.length) {
      this.processBlock(data.subarray(position, position + 64));
      position += 64;
    }
    if (position < data.length) {
      this.buffer.set(data.subarray(position), 0);
      this.bufferLength = data.length - position;
    }
  }

  digest(): Uint8Array {
    if (!this.finished) {
      this.finish();
      this.finished = true;
    }
    const output = new Uint8Array(32);
    for (let i = 0; i < 8; i += 1) {
      const value = this.hash[i];
      output[i * 4] = (value >>> 24) & 0xff;
      output[i * 4 + 1] = (value >>> 16) & 0xff;
      output[i * 4 + 2] = (value >>> 8) & 0xff;
      output[i * 4 + 3] = value & 0xff;
    }
    return output;
  }

  digestHex(): string {
    const digest = this.digest();
    let hex = "";
    for (let i = 0; i < digest.length; i += 1) {
      hex += digest[i].toString(16).padStart(2, "0");
    }
    return hex;
  }

  private finish(): void {
    const buffer = this.buffer;
    let i = this.bufferLength;
    buffer[i] = 0x80;
    i += 1;
    if (i > 56) {
      buffer.fill(0, i, 64);
      this.processBlock(buffer);
      i = 0;
    }
    buffer.fill(0, i, 56);
    const bitsHashed = this.bytesHashed * 8;
    const high = Math.floor(bitsHashed / 0x100000000);
    const low = bitsHashed >>> 0;
    buffer[56] = (high >>> 24) & 0xff;
    buffer[57] = (high >>> 16) & 0xff;
    buffer[58] = (high >>> 8) & 0xff;
    buffer[59] = high & 0xff;
    buffer[60] = (low >>> 24) & 0xff;
    buffer[61] = (low >>> 16) & 0xff;
    buffer[62] = (low >>> 8) & 0xff;
    buffer[63] = low & 0xff;
    this.processBlock(buffer);
  }

  private processBlock(chunk: Uint8Array): void {
    const words = this.words;
    for (let i = 0; i < 16; i += 1) {
      const offset = i * 4;
      words[i] =
        ((chunk[offset] << 24) | (chunk[offset + 1] << 16) | (chunk[offset + 2] << 8) | chunk[offset + 3]) >>> 0;
    }
    for (let i = 16; i < 64; i += 1) {
      const value = (gamma1(words[i - 2]) + words[i - 7] + gamma0(words[i - 15]) + words[i - 16]) >>> 0;
      words[i] = value;
    }
    let a = this.hash[0];
    let b = this.hash[1];
    let c = this.hash[2];
    let d = this.hash[3];
    let e = this.hash[4];
    let f = this.hash[5];
    let g = this.hash[6];
    let h = this.hash[7];
    for (let i = 0; i < 64; i += 1) {
      const t1 = (h + sigma1(e) + ch(e, f, g) + K[i] + words[i]) >>> 0;
      const t2 = (sigma0(a) + maj(a, b, c)) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + t1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (t1 + t2) >>> 0;
    }
    this.hash[0] = (this.hash[0] + a) >>> 0;
    this.hash[1] = (this.hash[1] + b) >>> 0;
    this.hash[2] = (this.hash[2] + c) >>> 0;
    this.hash[3] = (this.hash[3] + d) >>> 0;
    this.hash[4] = (this.hash[4] + e) >>> 0;
    this.hash[5] = (this.hash[5] + f) >>> 0;
    this.hash[6] = (this.hash[6] + g) >>> 0;
    this.hash[7] = (this.hash[7] + h) >>> 0;
  }
}

type Sha256FileOptions = {
  signal?: AbortSignal;
  onProgress?: (progress: number) => void;
};

const throwIfAborted = (signal?: AbortSignal) => {
  if (signal?.aborted) {
    throw new DOMException("SHA256 aborted", "AbortError");
  }
};

export const sha256File = async (file: File, options: Sha256FileOptions = {}): Promise<string> => {
  const hasher = new Sha256();
  if (file.size === 0) {
    return hasher.digestHex();
  }
  let processed = 0;
  if (typeof file.stream === "function") {
    const reader = file.stream().getReader();
    while (true) {
      throwIfAborted(options.signal);
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      if (value) {
        hasher.update(value);
        processed += value.length;
        if (options.onProgress) {
          options.onProgress(processed / file.size);
        }
      }
    }
  } else {
    const chunkSize = 4 * 1024 * 1024;
    for (let offset = 0; offset < file.size; offset += chunkSize) {
      throwIfAborted(options.signal);
      const chunk = await file.slice(offset, offset + chunkSize).arrayBuffer();
      const bytes = new Uint8Array(chunk);
      hasher.update(bytes);
      processed += bytes.length;
      if (options.onProgress) {
        options.onProgress(processed / file.size);
      }
    }
  }
  return hasher.digestHex();
};
