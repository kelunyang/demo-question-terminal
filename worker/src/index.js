// DeepSeek 代理：金鑰只存在 Worker 的 secret（env.DEEPSEEK_API_KEY），前端直連本 Worker，
// 不再經過 GAS 的 UrlFetchApp（那裡有無法穩定繞過的逾時天花板）。
// 模型「等級（tier）」由前端設定視窗選擇（flash / pro），但實際 model ID 仍鎖死在這份白名單裡：
// 前端只能送 tier 字串，不能直接指定任意 model，避免代理被拿去呼叫預期外的（更貴的）模型。

const DEEPSEEK_ENDPOINT = 'https://api.deepseek.com/chat/completions';

// tier → 實際 model ID 對照（白名單）。model ID 已於 2026-07 對 DeepSeek 官方文件核實。
// 兩者 API 參數完全相同（reasoning_effort / thinking / tools / stream / max_tokens 通用），
// 皆為 1M context、最大輸出 384K；差別在能力、費率與併發：
//   flash：輸出 $0.28 / 1M，併發上限 2500
//   pro  ：輸出 $0.87 / 1M（約 3×），併發上限 500，1.6T MoE（49B 活躍）
const MODEL_TIERS = {
  flash: 'deepseek-v4-flash',
  pro: 'deepseek-v4-pro',
};
const DEFAULT_TIER = 'flash';
const DEEPSEEK_REASONING_EFFORT = 'high';

function resolveModel(tier) {
  return MODEL_TIERS[tier] || MODEL_TIERS[DEFAULT_TIER];
}

// ── 濫用防護 ────────────────────────────────────────────────────────────────
// 前端 token 寫在公開的 GAS 網頁裡、可被 view-source 取得，因此無法當真正的機密。
// 防線改為兩道：(1) Origin 白名單擋掉爬蟲／腳本／別站 JS；(2) 每 IP rate limit 鎖住傷害上限。
// ENFORCE_ORIGIN=false 時 Origin 只記錄不阻擋（用來先觀察 GAS 沙箱真實 Origin，確認後再開啟）。
const ENFORCE_ORIGIN = true;
// 允許的 Origin「字尾」白名單（GAS HtmlService 沙箱 iframe 的子網域會浮動，故用 endsWith 比對）。
const ALLOWED_ORIGIN_SUFFIXES = ['.googleusercontent.com', 'script.google.com'];

function isAllowedOrigin(origin) {
  if (!origin) return false;
  return ALLOWED_ORIGIN_SUFFIXES.some(function (s) { return origin === s || origin.endsWith(s); });
}

// 限流器沒設定或呼叫失敗時一律放行（fail-open），避免限流本身把正常流量擋死。
async function underRateLimit(env, key) {
  if (!env.RATE_LIMITER || typeof env.RATE_LIMITER.limit !== 'function') return true;
  try {
    const { success } = await env.RATE_LIMITER.limit({ key: key });
    return success;
  } catch (e) {
    return true;
  }
}

// CORS 從 `*` 收成「只回白名單 Origin」：允許的來源就把它原樣 echo 回去，其餘不帶 ACAO
// （瀏覽器端就讀不到回應）。GAS 沙箱子網域會浮動，所以是動態 echo 而非寫死單一值，需搭配 Vary。
function corsHeaders(origin) {
  const h = {
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-App-Token',
    'Vary': 'Origin',
  };
  if (isAllowedOrigin(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

function jsonResponse(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' },
  });
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin');

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders(origin) });
    }
    if (request.method !== 'POST') {
      return jsonResponse({ error: 'Method Not Allowed' }, 405, origin);
    }

    // Origin 白名單。ENFORCE_ORIGIN=false 時只記錄不阻擋（觀察真實 Origin 用）。
    if (!isAllowedOrigin(origin)) {
      console.log('[origin] 非白名單來源 origin=' + JSON.stringify(origin) +
        ' referer=' + JSON.stringify(request.headers.get('Referer')) +
        ' enforce=' + ENFORCE_ORIGIN);
      if (ENFORCE_ORIGIN) return jsonResponse({ error: 'Forbidden origin' }, 403, origin);
    }

    if (env.APP_SHARED_TOKEN) {
      const token = request.headers.get('X-App-Token');
      if (token !== env.APP_SHARED_TOKEN) {
        return jsonResponse({ error: 'Unauthorized' }, 401, origin);
      }
    }

    // 每來源 IP 限流（fail-open）。放在 token 檢查之後，連「拿到 token 想狂打」也一起擋。
    const clientIp = request.headers.get('CF-Connecting-IP') || 'unknown';
    if (!(await underRateLimit(env, clientIp))) {
      return jsonResponse({ error: '請求過於頻繁，請稍後再試（rate limited）' }, 429, origin);
    }

    let payload;
    try {
      payload = await request.json();
    } catch (e) {
      return jsonResponse({ error: 'Invalid JSON body' }, 400, origin);
    }
    if (!Array.isArray(payload.messages)) {
      return jsonResponse({ error: 'messages array is required' }, 400, origin);
    }

    const body = {
      model: resolveModel(payload.tier),
      messages: payload.messages,
      reasoning_effort: DEEPSEEK_REASONING_EFFORT,
      thinking: { type: 'enabled' },
    };
    if (payload.tools) body.tools = payload.tools;
    if (payload.max_tokens) body.max_tokens = payload.max_tokens;
    if (payload.stream) body.stream = true;

    let upstream;
    try {
      upstream = await fetch(DEEPSEEK_ENDPOINT, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.DEEPSEEK_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
    } catch (e) {
      return jsonResponse({ error: 'DeepSeek 連線失敗：' + e }, 502, origin);
    }

    if (payload.stream) {
      const headers = new Headers(corsHeaders(origin));
      headers.set('Content-Type', 'text/event-stream');
      headers.set('Cache-Control', 'no-cache');
      // 直接把 DeepSeek 的 SSE stream 原樣轉發回前端，做到真正 token 級別的串流
      return new Response(upstream.body, { status: upstream.status, headers });
    }

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' },
    });
  },
};
