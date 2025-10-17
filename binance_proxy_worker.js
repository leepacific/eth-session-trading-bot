
// Cloudflare Worker - 바이낸스 API 프록시
export default {
  async fetch(request, env, ctx) {
    // CORS 헤더 설정
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-MBX-APIKEY, X-API-Key, Authorization',
    };

    // OPTIONS 요청 처리 (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, { 
        status: 200,
        headers: corsHeaders 
      });
    }

    try {
      const url = new URL(request.url);
      
      // 바이낸스 API URL 구성
      const binanceBaseUrl = 'https://api.binance.com';
      const targetUrl = binanceBaseUrl + url.pathname + url.search;
      
      console.log(`Proxying request to: ${targetUrl}`);
      
      // 원본 요청 헤더 복사
      const headers = new Headers();
      
      // 중요한 헤더들만 복사
      const allowedHeaders = [
        'x-mbx-apikey',
        'content-type',
        'user-agent'
      ];
      
      for (const [key, value] of request.headers) {
        const lowerKey = key.toLowerCase();
        if (allowedHeaders.includes(lowerKey)) {
          headers.set(key, value);
        }
      }
      
      // User-Agent 설정 (바이낸스 요구사항)
      if (!headers.has('User-Agent')) {
        headers.set('User-Agent', 'Cloudflare-Worker-Binance-Proxy/1.0');
      }
      
      // 요청 생성
      const proxyRequest = new Request(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
      });

      // 바이낸스 API 호출
      const response = await fetch(proxyRequest);
      
      // 응답 헤더 설정
      const responseHeaders = new Headers(response.headers);
      
      // CORS 헤더 추가
      Object.entries(corsHeaders).forEach(([key, value]) => {
        responseHeaders.set(key, value);
      });
      
      // 프록시 정보 헤더 추가
      responseHeaders.set('X-Proxy-By', 'Cloudflare-Workers');
      responseHeaders.set('X-Proxy-Timestamp', new Date().toISOString());
      responseHeaders.set('X-Proxy-Target', targetUrl);
      
      // 응답 반환
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
      
    } catch (error) {
      console.error('Proxy error:', error);
      
      return new Response(JSON.stringify({
        error: 'Proxy Error',
        message: error.message,
        timestamp: new Date().toISOString(),
        worker: 'binance-api-proxy'
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }
  },
};
