/**
 * Vercel Serverless Function - Feishu Image Proxy
 * Proxies cover images from Feishu with proper authentication
 */

module.exports = async function handler(req, res) {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    if (req.method !== 'GET') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    const { token } = req.query;

    if (!token) {
        return res.status(400).json({ error: 'Missing token parameter' });
    }

    try {
        // Get Feishu access token
        const APP_ID = process.env.FEISHU_APP_ID;
        const APP_SECRET = process.env.FEISHU_APP_SECRET;

        if (!APP_ID || !APP_SECRET) {
            return res.status(500).json({ error: 'Missing Feishu configuration' });
        }

        const tokenResponse = await fetch(
            'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_id: APP_ID, app_secret: APP_SECRET })
            }
        );

        const tokenData = await tokenResponse.json();
        if (tokenData.code !== 0) {
            return res.status(500).json({ error: 'Failed to get access token' });
        }

        const accessToken = tokenData.tenant_access_token;

        // Download image from Feishu
        const imageUrl = `https://open.feishu.cn/open-apis/drive/v1/medias/${token}/download`;

        const imageResponse = await fetch(imageUrl, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });

        if (!imageResponse.ok) {
            return res.status(imageResponse.status).json({
                error: 'Failed to fetch image',
                status: imageResponse.status
            });
        }

        // Get content type and forward the image
        const contentType = imageResponse.headers.get('content-type') || 'image/jpeg';
        const buffer = await imageResponse.arrayBuffer();

        // Cache for 1 hour
        res.setHeader('Cache-Control', 'public, max-age=3600, s-maxage=3600');
        res.setHeader('Content-Type', contentType);

        return res.status(200).send(Buffer.from(buffer));

    } catch (error) {
        console.error('Image proxy error:', error);
        return res.status(500).json({ error: 'Internal server error', message: error.message });
    }
};
