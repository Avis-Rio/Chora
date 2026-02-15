/**
 * Vercel Serverless Function - Feishu Bitable API Proxy
 * Securely fetches content from Feishu without exposing credentials
 */

module.exports = async function handler(req, res) {
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
            return res.status(500).json({
                error: 'Missing Feishu configuration',
                missing: {
                    APP_ID: !APP_ID,
                    APP_SECRET: !APP_SECRET,
                    BASE_ID: !BASE_ID,
                    TABLE_ID: !TABLE_ID
                }
            });
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

        // Step 2: Fetch records from Bitable with pagination
        let allItems = [];
        let pageToken = null;
        let hasMore = true;

        while (hasMore) {
            // Build URL with pagination
            let recordsUrl = `https://open.feishu.cn/open-apis/bitable/v1/apps/${BASE_ID}/tables/${TABLE_ID}/records?page_size=500`;

            // Add page token if exists
            if (pageToken) {
                recordsUrl += `&page_token=${pageToken}`;
            }

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
            allItems = allItems.concat(items);

            // Check if there are more pages
            hasMore = recordsData.data?.has_more || false;
            pageToken = recordsData.data?.page_token || null;
        }

        console.log(`Fetched ${allItems.length} total records from Feishu`);
        const items = allItems;

        // Filter: only include records where '是否发布' is true
        const publishedItems = items.filter(record => {
            const isPublished = record.fields?.['是否发布'];
            return isPublished === true;
        });

        console.log(`Filtered to ${publishedItems.length} published records`);

        // Step 3: Transform data for frontend
        const frontendData = publishedItems.map(record => {
            const fields = record.fields || {};

            // Extract cover URL from attachment field - use proxy for Feishu images
            let coverUrl = null;
            if (fields['封面'] && Array.isArray(fields['封面']) && fields['封面'].length > 0) {
                const originalUrl = fields['封面'][0].url || fields['封面'][0].tmp_url || null;
                if (originalUrl) {
                    // Extract file token from Feishu URL and use our proxy
                    const tokenMatch = originalUrl.match(/medias\/([^\/]+)/);
                    if (tokenMatch) {
                        coverUrl = `/api/image?token=${tokenMatch[1]}`;
                    } else {
                        coverUrl = originalUrl; // Fallback to original if pattern doesn't match
                    }
                }
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
                quotes: parseQuotes(fields['金句渲染'] || fields['金句'] || ''),
                guests: fields['嘉宾'] || '',
                url: fields['原始链接']?.link || fields['原始链接'] || '',
                score: fields['评分'] || 0
            };
        });

        // Sort by publish date (newest first)
        frontendData.sort((a, b) => (b.publish_date || '').localeCompare(a.publish_date || ''));

        // Cache for 30 seconds (balance between performance and freshness)
        res.setHeader('Cache-Control', 's-maxage=30, stale-while-revalidate=15');
        return res.status(200).json(frontendData);

    } catch (error) {
        console.error('API Error:', error);
        return res.status(500).json({ error: 'Internal server error', message: error.message });
    }
};

// Parse quotes from text field or array
function parseQuotes(quotesText) {
    if (!quotesText) return [];

    // Handle array type (Feishu might return array)
    if (Array.isArray(quotesText)) {
        return quotesText.map(item => {
            // If array item is object, try to get text property
            const text = typeof item === 'string' ? item : (item.text || item.content || String(item));
            return text.replace(/^[\s>＞]+/, '').replace(/^[-*•]\s*/, '').replace(/^\d+\.\s*/, '').trim();
        }).filter(q => q.length > 0);
    }

    // Handle string type
    if (typeof quotesText === 'string') {
        // Split by newlines and filter empty lines
        const lines = quotesText.split('\n').filter(line => line.trim());

        // Remove leading markers like "- " or "* " or numbers
        return lines.map(line => {
            // Remove leading markers: > (half/full), -, *, digits
            return line.replace(/^[\s>＞]+/, '').replace(/^[-*•]\s*/, '').replace(/^\d+\.\s*/, '').trim();
        }).filter(q => q.length > 0);
    }

    // Handle other types - try to convert to string
    try {
        const text = String(quotesText);
        return text ? [text.trim()] : [];
    } catch (e) {
        console.error('Failed to parse quotes:', e);
        return [];
    }
}
