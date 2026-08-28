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

exports.main = async () => {
  try {
    const result = await cloud.database().collection(COLLECTION).doc(DOCUMENT_ID).get()
    const state = result && result.data
    if (!state || state.model !== MODEL || state.checkpoint_sha256 !== CHECKPOINT || state.device !== 'cuda:0') {
      return response(503, { ok: false, message: 'decoder configuration is unavailable or invalid' })
    }
    return response(200, {
      updated_at: state.updated_at,
      base_url: state.base_url,
      decode_url: state.decode_url,
      health_url: state.health_url,
      model: state.model,
      checkpoint_sha256: state.checkpoint_sha256,
      device: state.device,
    })
  } catch (error) {
    console.error('getDecoderConfig failed', { message: error && error.message })
    return response(503, { ok: false, message: 'decoder configuration is unavailable' })
  }
}
