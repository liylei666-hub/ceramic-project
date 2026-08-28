const axios = require('axios')
const cloud = require('wx-server-sdk')
const crypto = require('crypto')
const FormData = require('form-data')
const https = require('https')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV,
})

const MAX_IMAGE_BYTES = 50 * 1024 * 1024
const MD5_PATTERN = /^[0-9a-f]{32}$/
const STABLE_DEMO_HOST = '8-138-42-34.sslip.io'
const STABLE_DEMO_IP = '8.138.42.34'
const EXPECTED_DECODER_MODEL = 'trustmark-q-57bit-real18-step113100-locator5-perspective-rotation'
const EXPECTED_CHECKPOINT_SHA256 = '834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef'
const CONFIG_TIMEOUT_MS = 5000
const RETRYABLE_NETWORK_ERRORS = new Set([
  'ECONNRESET',
  'ENOTFOUND',
  'EAI_AGAIN',
  'ETIMEDOUT',
  'ECONNREFUSED',
])

function digest(buffer, algorithm) {
  return crypto.createHash(algorithm).update(buffer).digest('hex')
}

function safeEqual(left, right) {
  const leftBuffer = Buffer.from(String(left))
  const rightBuffer = Buffer.from(String(right))
  return leftBuffer.length === rightBuffer.length
    && crypto.timingSafeEqual(leftBuffer, rightBuffer)
}

async function deleteCloudFile(fileID) {
  try {
    await cloud.deleteFile({ fileList: [fileID] })
  } catch (error) {
    console.error('Failed to delete temporary cloud file', error)
  }
}

function createDecodeForm(imageBuffer) {
  const form = new FormData()
  form.append('image', imageBuffer, {
    filename: 'ceramic-capture.png',
    contentType: 'image/png',
    knownLength: imageBuffer.length,
  })
  form.append('payload_bits', '57')
  return form
}

function isRetryableNetworkError(error) {
  return Boolean(error && !error.response && RETRYABLE_NETWORK_ERRORS.has(error.code))
}

function validateDecoderUrl(value) {
  const url = new URL(String(value))
  if (url.protocol !== 'https:') {
    throw new Error('decoder URL must use HTTPS')
  }
  const host = url.hostname.toLowerCase()
  const allowed = host === STABLE_DEMO_HOST || host.endsWith('.trycloudflare.com')
  if (!allowed || url.pathname !== '/decode' || url.search || url.hash) {
    throw new Error('decoder URL is outside the approved Cloudflare endpoint contract')
  }
  return url.toString()
}

function validateDecoderState(state) {
  if (!state || typeof state !== 'object') {
    throw new Error('decoder config is not an object')
  }
  if (state.model !== EXPECTED_DECODER_MODEL) {
    throw new Error('decoder config model contract mismatch')
  }
  if (state.checkpoint_sha256 !== EXPECTED_CHECKPOINT_SHA256) {
    throw new Error('decoder config checkpoint contract mismatch')
  }
  if (state.device !== 'cuda:0') {
    throw new Error('decoder config device contract mismatch')
  }
  return validateDecoderUrl(state.decode_url)
}

async function resolveDecoderUrl() {
  const configUrl = String(process.env.DECODER_CONFIG_URL || '').trim()
  if (!configUrl) {
    const directUrl = String(process.env.DECODER_URL || '').trim()
    if (!/^https:\/\//i.test(directUrl)) {
      throw new Error('decoder endpoint is not configured')
    }
    return validateDecoderUrl(directUrl)
  }

  let parsedConfigUrl
  try {
    parsedConfigUrl = new URL(configUrl)
  } catch (error) {
    throw new Error('DECODER_CONFIG_URL is invalid')
  }
  if (parsedConfigUrl.protocol !== 'https:') {
    throw new Error('DECODER_CONFIG_URL must use HTTPS')
  }

  const response = await axios.get(parsedConfigUrl.toString(), {
    timeout: CONFIG_TIMEOUT_MS,
    proxy: false,
    validateStatus: (status) => status >= 200 && status < 300,
  })
  return validateDecoderState(response.data)
}

async function postToDecoder({ decoderUrl, decoderToken, imageBuffer, sha256 }) {
  const configuredUrl = new URL(decoderUrl)
  const attempts = [{ url: configuredUrl.toString() }]
  if (configuredUrl.hostname === STABLE_DEMO_HOST) {
    const directUrl = new URL(configuredUrl.toString())
    directUrl.hostname = STABLE_DEMO_IP
    attempts.push({
      url: directUrl.toString(),
      hostHeader: STABLE_DEMO_HOST,
      httpsAgent: new https.Agent({
        keepAlive: false,
        rejectUnauthorized: true,
        servername: STABLE_DEMO_HOST,
      }),
    })
  }

  let lastError
  for (let index = 0; index < attempts.length; index += 1) {
    const attempt = attempts[index]
    const form = createDecodeForm(imageBuffer)
    try {
      return await axios.post(attempt.url, form, {
        headers: {
          ...form.getHeaders(),
          ...(attempt.hostHeader ? { Host: attempt.hostHeader } : {}),
          'X-Ceramic-Token': decoderToken,
          'X-Image-SHA256': sha256,
        },
        httpsAgent: attempt.httpsAgent,
        proxy: false,
        timeout: 20000,
        maxBodyLength: MAX_IMAGE_BYTES,
        maxContentLength: MAX_IMAGE_BYTES,
        validateStatus: (status) => status >= 200 && status < 300,
      })
    } catch (error) {
      lastError = error
      const retryable = !error.response && RETRYABLE_NETWORK_ERRORS.has(error.code)
      if (!retryable || index === attempts.length - 1) {
        throw error
      }
      console.warn('Decoder hostname connection failed; retrying pinned IP', {
        code: error.code,
      })
    }
  }
  throw lastError || new Error('解码服务器连接失败')
}

exports.main = async (event) => {
  const fileID = String(event && event.fileID ? event.fileID : '')
  const clientMd5 = String(event && event.clientMd5 ? event.clientMd5 : '').toLowerCase()
  const clientBytes = Number(event && event.clientBytes)
  const decoderToken = String(process.env.DECODER_TOKEN || '')

  if (!fileID) {
    return { ok: false, message: '缺少云存储文件ID' }
  }
  if (!MD5_PATTERN.test(clientMd5) || !Number.isSafeInteger(clientBytes) || clientBytes <= 0) {
    return { ok: false, message: '客户端文件校验信息无效' }
  }
  if ((!process.env.DECODER_CONFIG_URL && !process.env.DECODER_URL) || !decoderToken) {
    return { ok: false, message: '云函数尚未配置解码服务' }
  }

  try {
    const downloaded = await cloud.downloadFile({ fileID })
    const imageBuffer = downloaded && downloaded.fileContent
    if (!Buffer.isBuffer(imageBuffer) || imageBuffer.length === 0) {
      throw new Error('云存储中的照片为空')
    }
    if (imageBuffer.length > MAX_IMAGE_BYTES) {
      throw new Error('照片超过50 MB限制')
    }

    const cloudMd5 = digest(imageBuffer, 'md5')
    if (imageBuffer.length !== clientBytes || !safeEqual(cloudMd5, clientMd5)) {
      throw new Error('照片上传后的字节完整性校验失败')
    }

    const sha256 = digest(imageBuffer, 'sha256')
    let decoderUrl = await resolveDecoderUrl()
    let response
    try {
      response = await postToDecoder({ decoderUrl, decoderToken, imageBuffer, sha256 })
    } catch (error) {
      // A Quick Tunnel can rotate between config reads. Refresh once on a
      // transport failure; never retry application-level HTTP failures.
      if (!process.env.DECODER_CONFIG_URL || !isRetryableNetworkError(error)) {
        throw error
      }
      decoderUrl = await resolveDecoderUrl()
      response = await postToDecoder({ decoderUrl, decoderToken, imageBuffer, sha256 })
    }
    const serverSha256 = String(
      response && response.data && response.data.input_sha256
        ? response.data.input_sha256
        : '',
    ).toLowerCase()
    if (!safeEqual(serverSha256, sha256)) {
      throw new Error('解码服务器收到的照片校验值不一致')
    }

    return {
      ok: true,
      integrity: {
        verified: true,
        byteLength: imageBuffer.length,
        md5: cloudMd5,
        sha256,
        serverVerified: true,
      },
      decode: response.data,
    }
  } catch (error) {
    console.error('decodeCeramic failed', {
      message: error && error.message,
      status: error && error.response && error.response.status,
    })
    const serverDetail = error
      && error.response
      && error.response.data
      && error.response.data.detail
    return {
      ok: false,
      message: serverDetail || (error && error.message) || '解码失败',
    }
  } finally {
    await deleteCloudFile(fileID)
  }
}
