const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const COLLECTION = 'decoder_config'
const DOCUMENT_ID = 'current'
const MODEL = 'trustmark-q-57bit-real18-step113100-locator5-perspective-rotation'
const CHECKPOINT = '834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef'

function response(statusCode, body) {
  return {
    statusCode,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
    body: JSON.stringify(body),
  }
}

function header(event, name) {
  const headers = (event && (event.headers || event.header)) || {}
  return headers[name] || headers[name.toLowerCase()] || headers[name.toUpperCase()] || ''
}

function parseBody(event) {
  if (!event) return null
  if (typeof event.body === 'object' && event.body !== null) return event.body
  try { return JSON.parse(String(event.body || '')) } catch (_) { return null }
}

function validate(state) {
  if (!state || typeof state !== 'object') throw new Error('invalid JSON body')
  if (!/^https:\/\/[^/]+\.trycloudflare\.com\/decode$/.test(String(state.decode_url || ''))) throw new Error('invalid decode_url')
  if (!/^https:\/\/[^/]+\.trycloudflare\.com\/healthz$/.test(String(state.health_url || ''))) throw new Error('invalid health_url')
  if (state.model !== MODEL || state.checkpoint_sha256 !== CHECKPOINT || state.device !== 'cuda:0') throw new Error('decoder contract mismatch')
  if (!state.updated_at || Number.isNaN(Date.parse(state.updated_at))) throw new Error('invalid updated_at')
  return {
    updated_at: String(state.updated_at),
    base_url: String(state.base_url || state.decode_url).replace(/\/decode$/, ''),
    decode_url: String(state.decode_url),
    health_url: String(state.health_url),
    model: MODEL,
    checkpoint_sha256: CHECKPOINT,
    device: 'cuda:0',
  }
}

exports.main = async (event) => {
  const expectedKey = String(process.env.DECODER_CONFIG_UPDATE_KEY || '')
  const suppliedKey = String(header(event, 'X-Decoder-Config-Key') || '')
  if (!expectedKey || !suppliedKey || suppliedKey !== expectedKey) return response(401, { ok: false, message: 'unauthorized' })
  try {
    const state = validate(parseBody(event))
    await cloud.database().collection(COLLECTION).doc(DOCUMENT_ID).set({ data: state })
    return response(200, { ok: true, updated_at: state.updated_at })
  } catch (error) {
    console.error('updateDecoderConfig failed', { message: error && error.message })
    return response(400, { ok: false, message: error && error.message ? error.message : 'invalid configuration' })
  }
}
