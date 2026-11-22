/**
 * DocuVault - Cobalt ASCII Cryptographic Stream Field
 * Inspired by Hallmark Cobalt wire engine. Snaps to 8x16 character cells.
 */
(() => {
  'use strict';
  const CW = 8, CH = 16;
  const MONO = '"JetBrains Mono", ui-monospace, Menlo, monospace';
  const RAMP = [' ', '·', ':', '-', '=', '+', '*', '#', '%', '@'];
  const BRAILLE = [' ', '⠁', '⠃', '⠇', '⡇', '⣇', '⣧', '⣷', '⣿', '⣿'];
  const CRYPTO_TERMS = ['SHA256', 'ED25519', 'RSAPSS', 'VAULT', 'PROVENANCE', 'IMMUTABLE', 'DIGILOCKER'];

  // Seeded Gradient Noise
  const P = new Uint8Array(512);
  {
    const p = Array.from({ length: 256 }, (_, i) => i);
    let s = 1042;
    const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 255; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      const t = p[i]; p[i] = p[j]; p[j] = t;
    }
    for (let i = 0; i < 512; i++) P[i] = p[i & 255];
  }
  const GX = [1, -1, 1, -1, 1, -1, 0, 0], GY = [1, 1, -1, -1, 0, 0, 1, -1];
  function noise(x, y) {
    const X = Math.floor(x), Y = Math.floor(y), xf = x - X, yf = y - Y, xi = X & 255, yi = Y & 255;
    const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10), v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
    const aa = P[P[xi] + yi] & 7, ab = P[P[xi] + yi + 1] & 7, ba = P[P[xi + 1] + yi] & 7, bb = P[P[xi + 1] + yi + 1] & 7;
    const n00 = GX[aa] * xf + GY[aa] * yf, n10 = GX[ba] * (xf - 1) + GY[ba] * yf;
    const n01 = GX[ab] * xf + GY[ab] * (yf - 1), n11 = GX[bb] * (xf - 1) + GY[bb] * (yf - 1);
    const a = n00 + u * (n10 - n00), b = n01 + u * (n11 - n01);
    return a + v * (b - a);
  }

  function initCobaltField(canvasId = 'cobaltFieldCanvas') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const TINTS = [
      'rgba(80, 120, 220, 0.08)',
      'rgba(80, 120, 220, 0.16)',
      'rgba(50, 100, 240, 0.28)',
      'rgba(30, 80, 220, 0.45)',
      'rgba(20, 60, 200, 0.70)'
    ];

    let W = 0, H = 0, cols = 0, rows = 0;
    let clock = 0;

    function resize() {
      const rect = canvas.parentElement.getBoundingClientRect();
      W = rect.width;
      H = 220; // Top band
      canvas.width = W;
      canvas.height = H;
      cols = Math.floor(W / CW);
      rows = Math.floor(H / CH);
    }

    window.addEventListener('resize', resize);
    resize();

    // Stream lines of hash bytes
    let packets = [];
    for (let i = 0; i < 4; i++) {
      packets.push({
        col: Math.floor(Math.random() * cols),
        row: Math.floor(Math.random() * (rows - 2)) + 1,
        text: CRYPTO_TERMS[Math.floor(Math.random() * CRYPTO_TERMS.length)],
        speed: 0.15 + Math.random() * 0.15
      });
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      ctx.font = `400 11px ${MONO}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      clock += 0.015;

      // Draw background noise ramp snapped to 8x16 cells
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c += 2) {
          const n = 0.5 + 0.5 * noise(c / 25 + clock * 0.5, r / 15 - clock * 0.2);
          if (n > 0.42) {
            const idx = Math.min(RAMP.length - 1, Math.floor(n * RAMP.length));
            const char = RAMP[idx];
            if (char !== ' ') {
              const tintIdx = Math.min(TINTS.length - 1, Math.floor(n * TINTS.length));
              ctx.fillStyle = TINTS[tintIdx];
              ctx.fillText(char, c * CW + CW / 2, r * CH + CH / 2);
            }
          }
        }
      }

      // Draw moving packets
      packets.forEach(p => {
        p.col += p.speed;
        if (p.col > cols + 10) {
          p.col = -p.text.length;
          p.row = Math.floor(Math.random() * (rows - 2)) + 1;
          p.text = CRYPTO_TERMS[Math.floor(Math.random() * CRYPTO_TERMS.length)];
        }
        ctx.fillStyle = 'rgba(30, 80, 220, 0.75)';
        ctx.font = `600 11px ${MONO}`;
        for (let i = 0; i < p.text.length; i++) {
          const x = Math.floor(p.col + i) * CW + CW / 2;
          const y = p.row * CH + CH / 2;
          if (x >= 0 && x < W) {
            ctx.fillText(p.text[i], x, y);
          }
        }
      });

      requestAnimationFrame(draw);
    }

    requestAnimationFrame(draw);
  }

  window.initCobaltField = initCobaltField;
})();
