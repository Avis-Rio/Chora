/**
 * Vercel Serverless Function - Feishu Bitable API Proxy
 * Securely fetches content from Feishu without exposing credentials
 */

export default async function handler(req, res) {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    if (req.method !== 'GET') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    try {
        // Get credentials from environment variables (set in Vercel dashboard)
        const APP_ID = process.env.FEISHU_APP_ID;
        const APP_SECRET = process.env.FEISHU_APP_SECRET;
        const BASE_ID = process.env.FEISHU_BASE_ID;
        const TABLE_ID = process.env.FEISHU_TABLE_ID;

        if (!APP_ID || !APP_SECRET || !BASE_ID || !TABLE_ID) {
            return res.status(500).json({ error: 'Missing Feishu configuration' });
        }

        // Step 1: Get access token
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
            return res.status(500).json({ error: 'Failed to get access token', details: tokenData });
        }

        const accessToken = tokenData.tenant_access_token;

        // Step 2: Fetch records from Bitable
        const recordsUrl = `https://open.feishu.cn/open-apis/bitable/v1/apps/${BASE_ID}/tables/${TABLE_ID}/records?page_size=100`;

        const recordsResponse = await fetch(recordsUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            }
        });

        const recordsData = await recordsResponse.json();
        if (recordsData.code !== 0) {
            return res.status(500).json({ error: 'Failed to fetch records', details: recordsData });
        }

        const items = recordsData.data?.items || [];

        // Step 3: Transform data for frontend
        const frontendData = items.map(record => {
            const fields = record.fields || {};

            // Extract cover URL from attachment field
            let coverUrl = null;
            if (fields['封面'] && Array.isArray(fields['封面']) && fields['封面'].length > 0) {
                coverUrl = fields['封面'][0].url || fields['封面'][0].tmp_url || null;
            }

            // Extract tags from multi-select field
            let tags = [];
            if (fields['标签']) {
                if (Array.isArray(fields['标签'])) {
                    tags = fields['标签'].map(t => typeof t === 'string' ? t : t.text || t);
                } else if (typeof fields['标签'] === 'string') {
                    tags = fields['标签'].split(',').map(t => t.trim());
                }
            }

            // Parse publish date
            let publishDate = '';
            if (fields['发布时间']) {
                const timestamp = fields['发布时间'];
                if (typeof timestamp === 'number') {
                    publishDate = new Date(timestamp).toISOString().split('T')[0];
                } else {
                    publishDate = timestamp;
                }
            }

            return {
                id: fields['记录ID'] || record.record_id,
                title: fields['标题'] || '',
                platform: fields['平台'] || '',
                channel: fields['频道'] || '',
                publish_date: publishDate,
                reading_time: fields['阅读时长'] || 10,
                cover_url: coverUrl,
                tags: tags,
                rewritten: fields['正文'] || '',
                quotes: parseQuotes(fields['金句'] || ''),
                guests: fields['嘉宾'] || '',
                url: fields['原始链接']?.link || fields['原始链接'] || '',
                score: fields['评分'] || 0
            };
        });

        // Sort by publish date (newest first)
        frontendData.sort((a, b) => (b.publish_date || '').localeCompare(a.publish_date || ''));

        // Cache for 5 minutes
        res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate');
        return res.status(200).json(frontendData);

    } catch (error) {
        console.error('API Error:', error);
        return res.status(500).json({ error: 'Internal server error', message: error.message });
    }
}

// Parse quotes from text field
function parseQuotes(quotesText) {
    if (!quotesText) return [];

    // Split by newlines and filter empty lines
    const lines = quotesText.split('\n').filter(line => line.trim());

    // Remove leading markers like "- " or "* " or numbers
    return lines.map(line => {
        return line.replace(/^[-*•]\s*/, '').replace(/^\d+\.\s*/, '').trim();
    }).filter(q => q.length > 0);
}
