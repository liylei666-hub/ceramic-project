// Deploy this logic in the existing cloud function. The fixed CONFIG_URL must
// be hosted outside the temporary Quick Tunnel (CloudBase, the company's HTTPS
// domain, or a Cloudflare Named Tunnel). Do not put the decoder token in the
// Mini Program source.
const FIXED_CONFIG_URL = process.env.DECODER_CONFIG_URL;
const EXPECTED_MODEL = 'trustmark-q-57bit-real18-step113100-locator5-perspective-rotation';

async function readCurrentDecoderUrl() {
  if (!FIXED_CONFIG_URL) throw new Error('DECODER_CONFIG_URL is not configured');
  const response = await fetch(FIXED_CONFIG_URL, { signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`decoder config HTTP ${response.status}`);
  const state = await response.json();
  if (state.model !== EXPECTED_MODEL || state.device !== 'cuda:0') {
    throw new Error('decoder config model/device contract mismatch');
  }
  if (!/^https:\/\/[^/]+\.trycloudflare\.com\/decode$/.test(state.decode_url)) {
    throw new Error('decoder config URL is invalid');
  }
  return state.decode_url;
}

async function callDecoder(formData) {
  const decoderUrl = await readCurrentDecoderUrl();
  const response = await fetch(decoderUrl, {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.DECODER_TOKEN}` },
    body: formData,
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`decoder HTTP ${response.status}`);
  return response.json();
}

module.exports = { readCurrentDecoderUrl, callDecoder };
