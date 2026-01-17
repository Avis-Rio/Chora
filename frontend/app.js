/**
 * Chora - UXPeace Style Frontend
 */

// =====================================================
// Configuration & State
// =====================================================
const state = {
  articles: [],
  filteredArticles: [],
  currentFilter: 'all'
};

// =====================================================
// DOM Elements
// =====================================================
const elements = {
  grid: document.getElementById('articles-grid'),
  filterTabs: document.querySelectorAll('.filter-tab'),
  // Reader elements
  reader: document.getElementById('article-reader'),
  readerOverlay: document.querySelector('.reader-overlay'),
  readerCoverImg: document.getElementById('reader-cover-img'),
  readerTitle: document.getElementById('reader-title'),
  readerMeta: document.getElementById('reader-meta'),
  readerTags: document.getElementById('reader-tags'),
  readerSourceLink: document.getElementById('reader-source-link'),
  footerSourceLink: document.getElementById('footer-source-link'),
  quotesList: document.getElementById('quotes-list'),
  contentBody: document.getElementById('content-body'),
  tocNav: document.getElementById('toc-nav')
};

// =====================================================
// Data Loading
// =====================================================
async function loadData() {
  try {
    // Try API route first (Vercel production)
    let response = await fetch('/api/content');

    // Fallback to static JSON (local development)
    if (!response.ok) {
      console.log('API not available, falling back to static data');
      response = await fetch('/data/content.json');
    }

    if (response.ok) {
      const data = await response.json();
      state.articles = data;
      state.filteredArticles = [...data];

      // Extract unique tags and render filter tabs
      renderFilterTabs();
      renderGrid();
    }
  } catch (e) {
    console.error('Failed to load data', e);
    // Try static fallback on error
    try {
      const fallback = await fetch('/data/content.json');
      if (fallback.ok) {
        const data = await fallback.json();
        state.articles = data;
        state.filteredArticles = [...data];
        renderFilterTabs();
        renderGrid();
      }
    } catch (fallbackError) {
      console.error('Fallback also failed', fallbackError);
    }
  }
}

// =====================================================
// Global Search
// =====================================================
window.handleSearch = function () {
  const searchInput = document.getElementById('global-search');
  const query = searchInput.value.trim().toLowerCase();

  if (!query) {
    // Reset to all articles if search is empty
    state.filteredArticles = [...state.articles];
    // Reset filter tabs
    const allTabs = document.querySelectorAll('.filter-tab');
    allTabs.forEach(b => b.classList.remove('active'));
    const allTab = document.querySelector('.filter-tab[data-tag="all"]');
    if (allTab) allTab.classList.add('active');
  } else {
    // Search across multiple fields
    state.filteredArticles = state.articles.filter(article => {
      const title = (article.title || '').toLowerCase();
      const channel = (article.channel || '').toLowerCase();
      const guests = (article.guests || '').toLowerCase();
      const rewritten = (article.rewritten || '').toLowerCase();
      const tags = (article.tags || []).join(' ').toLowerCase();
      const excerpt = (article.excerpt || '').toLowerCase();

      return title.includes(query) ||
        channel.includes(query) ||
        guests.includes(query) ||
        rewritten.includes(query) ||
        tags.includes(query) ||
        excerpt.includes(query);
    });

    // Clear active filter when searching
    const allTabs = document.querySelectorAll('.filter-tab');
    allTabs.forEach(b => b.classList.remove('active'));
  }

  renderGrid();
};

// Enable real-time search on input
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('global-search');
  if (searchInput) {
    // Real-time search as user types
    searchInput.addEventListener('input', () => {
      window.handleSearch();
    });
    // Also trigger on Enter key
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        window.handleSearch();
      }
    });
  }
});

// =====================================================
// Dynamic Filter Tabs
// =====================================================
function renderFilterTabs() {
  const filterContainer = document.getElementById('filter-tags');

  // Extract all unique tags from articles
  const allTags = new Set();
  state.articles.forEach(article => {
    if (article.tags && Array.isArray(article.tags)) {
      article.tags.forEach(tag => allTags.add(tag));
    }
  });

  // Sort tags alphabetically
  const sortedTags = Array.from(allTags).sort();

  // Generate HTML for tabs (ALL is already in HTML)
  const tagsHtml = sortedTags.map(tag =>
    `<button class="filter-tab" data-tag="${tag}">${tag.toUpperCase()}</button>`
  ).join('');

  // Append to container (after ALL button)
  filterContainer.innerHTML = `
    <button class="filter-tab active" data-tag="all">ALL</button>
    ${tagsHtml}
  `;

  // Re-bind event listeners
  const tabs = filterContainer.querySelectorAll('.filter-tab');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => handleFilter(btn.dataset.tag, btn));
  });
}

// =====================================================
// Rendering
// =====================================================
function renderGrid() {
  elements.grid.innerHTML = state.filteredArticles.map(article => {
    // Extract a quote or fallback to excerpt
    let quote = '';
    if (article.quotes && article.quotes.length > 0) {
      quote = article.quotes[0];
    } else if (article.excerpt) {
      quote = article.excerpt;
    }

    // Guest Info Logic
    let guestName = article.channel;
    if (article.guests) {
      // Handle if guests is a list or string
      if (Array.isArray(article.guests) && article.guests.length > 0) {
        guestName = article.guests[0];
      } else if (typeof article.guests === 'string') {
        guestName = article.guests;
      }
    }

    // Clean up long names (e.g. remove bio descriptions)
    // 1. Split by common separators
    const separators = [' - ', '：', ' | ', '｜'];
    for (const sep of separators) {
      if (guestName.includes(sep)) {
        guestName = guestName.split(sep)[0];
        break;
      }
    }
    // 2. Hard truncate if still too long
    if (guestName.length > 25) {
      guestName = guestName.substring(0, 24) + '...';
    }

    const guestInitial = guestName.charAt(0).toUpperCase();

    // Platform Link Logic
    const platformName = article.platform || 'Source';
    const sourceUrl = article.url || '#';
    const platformIcon = platformName === 'YouTube' ? '▶' : '✦'; // Simple icons

    // Generate a consistent avatar color based on author name
    const authorName = article.channel || 'Unknown';
    const initial = authorName.charAt(0).toUpperCase();

    // Tag Logic with Colors
    const tagColors = ['tag-blue', 'tag-green', 'tag-purple', 'tag-orange', 'tag-teal', 'tag-pink'];
    let tagsHtml = '';
    if (article.tags && Array.isArray(article.tags) && article.tags.length > 0) {
      // Take up to 2 tags, assign color based on tag name hash
      tagsHtml = article.tags.slice(0, 2).map(tag => {
        // Simple hash: sum of char codes mod color count
        const hash = tag.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        const colorClass = tagColors[hash % tagColors.length];
        return `<span class="meta-tag ${colorClass}">${tag}</span>`;
      }).join('');
    }

    return `
    <div class="article-item" onclick="openArticle('${article.id}')">
      <div class="article-image-wrapper">
        <img src="${article.cover_url || '/covers/default.jpg'}" 
             alt="${article.title}" 
             class="article-image" 
             loading="lazy">
        
        <!-- Image Overlay -->
        <div class="image-overlay">
          <div class="guest-info">
            <div class="guest-icon">${guestInitial}</div>
            <span class="guest-name">${guestName}</span>
          </div>
          <a href="${sourceUrl}" target="_blank" class="platform-btn" onclick="event.stopPropagation()">
            ${platformName} <span style="font-size: 14px;">↗</span>
          </a>
        </div>
      </div>
      
      <div class="article-meta-top">
        <span class="meta-date">${article.publish_date}</span>
        <div class="meta-tags-wrapper">${tagsHtml}</div>
      </div>
      
      <h3 class="article-title">${article.title}</h3>
      
      <div class="article-quote">
        <div class="article-quote-text">${quote}</div>
      </div>
      
      <div class="article-footer">
        <div class="article-meta-left">
          <span class="meta-duration">⏱ ${article.reading_time || '10'} min</span>
          ${article.score ? `<span class="meta-score">★ ${article.score}</span>` : ''}
        </div>
        <div class="article-link">
          Read <span style="font-size: 14px;">›</span>
        </div>
      </div>
    </div>
  `}).join('');
}

// =====================================================
// Filtering
// =====================================================
function handleFilter(tag, btn) {
  // Update UI - remove active from all tabs
  const allTabs = document.querySelectorAll('.filter-tab');
  allTabs.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  // Filter Data
  if (tag === 'all') {
    state.filteredArticles = [...state.articles];
  } else {
    // Exact match for tag (case-insensitive)
    state.filteredArticles = state.articles.filter(article =>
      (article.tags || []).some(t => t.toLowerCase() === tag.toLowerCase())
    );
  }

  renderGrid();
}

// =====================================================
// Modal Logic -> Reader Logic
// =====================================================
window.openArticle = function (id) {
  const article = state.articles.find(a => a.id === id);
  if (!article) return;

  // Set cover image and blurred background
  const coverUrl = article.cover_url || '/covers/default.jpg';
  elements.readerCoverImg.src = coverUrl;
  elements.readerCoverImg.alt = article.title;
  elements.readerCoverImg.parentElement.style.backgroundImage = `url(${coverUrl})`;

  // Set title
  elements.readerTitle.textContent = article.title;

  // Set meta - split into two lines
  const metaLine1 = [article.platform, article.channel];
  if (article.guests) metaLine1.push(article.guests);
  const metaLine2 = [article.publish_date];
  if (article.reading_time) metaLine2.push(`${article.reading_time} min`);

  elements.readerMeta.innerHTML = `
    ${metaLine1.join(' · ')}
    <span class="reader-meta-date">${metaLine2.join(' · ')}</span>
  `;

  // Set tags
  const tagColors = ['tag-blue', 'tag-green', 'tag-purple', 'tag-orange', 'tag-teal', 'tag-pink'];
  if (article.tags && article.tags.length > 0) {
    elements.readerTags.innerHTML = article.tags.map(tag => {
      const hash = tag.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
      const colorClass = tagColors[hash % tagColors.length];
      return `<span class="meta-tag ${colorClass}">${tag}</span>`;
    }).join('');
  } else {
    elements.readerTags.innerHTML = '';
  }

  // Set source links
  const sourceUrl = article.url || '#';
  elements.readerSourceLink.href = sourceUrl;
  elements.footerSourceLink.href = sourceUrl;

  // Set quotes
  if (article.quotes && article.quotes.length > 0) {
    elements.quotesList.innerHTML = article.quotes.map(q =>
      `<div class="quote-item">${q}</div>`
    ).join('');
    document.getElementById('reader-quotes').style.display = 'block';
  } else {
    elements.quotesList.innerHTML = '';
    document.getElementById('reader-quotes').style.display = 'none';
  }

  // Set content
  const contentHtml = formatContent(article.rewritten || article.content || '');
  elements.contentBody.innerHTML = contentHtml;

  // Build TOC
  buildTOC(article);

  // Show reader
  elements.reader.classList.add('active');
  document.body.style.overflow = 'hidden';

  // Scroll to top
  document.querySelector('.reader-container').scrollTop = 0;
};

window.closeReader = function () {
  elements.reader.classList.remove('active');
  document.body.style.overflow = '';
};

// Build Table of Contents
function buildTOC(article) {
  const tocItems = [];

  // Add Quotes section if exists
  if (article.quotes && article.quotes.length > 0) {
    tocItems.push({ id: 'section-quotes', label: '金句摘录' });
  }

  // Add Content section
  tocItems.push({ id: 'section-content', label: '深度解读' });

  // Extract headings from content - must match formatContent logic exactly
  const content = article.rewritten || article.content || '';
  const lines = content.split('\n');
  let headingIndex = 0;

  lines.forEach(line => {
    const trimmedLine = line.trim();

    // Match "## 1. Title" format (section title with number)
    const sectionMatch = trimmedLine.match(/^##\s*(\d+)\.\s+(.+)$/);
    if (sectionMatch) {
      const num = parseInt(sectionMatch[1]);
      const title = sectionMatch[2];
      // Skip "内容标签" section
      if (title.includes('内容标签')) return;
      const chineseNum = toChineseNumeral(num);
      tocItems.push({
        id: `heading-${headingIndex++}`,
        label: `${chineseNum} ${title}`,
        isSubItem: true
      });
      return;
    }

    // Match regular "## Title" format
    if (trimmedLine.startsWith('## ')) {
      const label = trimmedLine.replace('## ', '');
      // Skip "内容标签" section
      if (label.includes('内容标签')) return;
      tocItems.push({ id: `heading-${headingIndex++}`, label: label, isSubItem: true });
      return;
    }
  });

  // Render TOC
  elements.tocNav.innerHTML = tocItems.map(item =>
    `<a href="#${item.id}" class="toc-item ${item.isSubItem ? 'toc-sub' : ''}" onclick="scrollToSection('${item.id}'); return false;">${item.label}</a>`
  ).join('');
}

// Scroll to section within reader container
window.scrollToSection = function (id) {
  const el = document.getElementById(id);
  const container = document.querySelector('.reader-container');

  if (el && container) {
    const navHeight = 60; // Approximate height of reader-nav
    const elementTop = el.offsetTop - navHeight;
    container.scrollTo({ top: elementTop, behavior: 'smooth' });
  }
};

// Convert Arabic numerals to Chinese numerals
function toChineseNumeral(num) {
  const numerals = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾'];
  if (num <= 10) return numerals[num];
  if (num < 20) return '拾' + (num % 10 === 0 ? '' : numerals[num % 10]);
  return num.toString(); // Fallback for larger numbers
}

function formatContent(text) {
  if (!text) return '<p>暂无内容</p>';

  let headingIndex = 0;
  let sectionIndex = 0;

  // Filter out "内容标签" section (duplicate with tags)
  text = text.replace(/#+\s*\d*\.?\s*内容标签.*?(?=\n#+|\n*$)/gs, '');

  // Process line by line for better Markdown support
  const lines = text.split('\n');
  let html = '';
  let inList = false;
  let inTable = false;
  let tableRows = [];
  let currentParagraph = [];
  let isFirstParagraph = true;

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      const pText = currentParagraph.join(' ');
      // Apply first-paragraph class for drop cap (only if not starting with special chars)
      const firstChar = pText.charAt(0);
      const isNormalText = /[\u4e00-\u9fa5a-zA-Z]/.test(firstChar);
      if (isFirstParagraph && isNormalText) {
        html += `<p class="first-paragraph">${formatInlineMarkdown(pText)}</p>`;
        isFirstParagraph = false;
      } else {
        html += `<p>${formatInlineMarkdown(pText)}</p>`;
      }
      currentParagraph = [];
    }
  };

  const flushTable = () => {
    if (tableRows.length > 0) {
      let tableHtml = '<table class="content-table"><thead><tr>';
      const headers = tableRows[0].split('|').filter(c => c.trim());
      headers.forEach((h, i) => {
        // First column narrower
        const cls = i === 0 ? ' class="col-title"' : '';
        tableHtml += `<th${cls}>${formatInlineMarkdown(h.trim())}</th>`;
      });
      tableHtml += '</tr></thead><tbody>';
      for (let i = 2; i < tableRows.length; i++) {
        const cells = tableRows[i].split('|').filter(c => c.trim());
        if (cells.length > 0) {
          tableHtml += '<tr>';
          cells.forEach((c, j) => {
            const cls = j === 0 ? ' class="col-title"' : '';
            tableHtml += `<td${cls}>${formatInlineMarkdown(c.trim())}</td>`;
          });
          tableHtml += '</tr>';
        }
      }
      tableHtml += '</tbody></table>';
      html += tableHtml;
      tableRows = [];
      inTable = false;
    }
  };

  lines.forEach(line => {
    const trimmedLine = line.trim();

    // Empty line - flush paragraph
    if (!trimmedLine) {
      flushParagraph();
      if (inTable) flushTable();
      return;
    }

    // Table row detection
    if (trimmedLine.startsWith('|') && trimmedLine.endsWith('|')) {
      flushParagraph();
      if (inList) {
        html += inList === 'ol' ? '</ol>' : '</ul>';
        inList = false;
      }
      inTable = true;
      tableRows.push(trimmedLine);
      return;
    }

    // If we were in a table but this line isn't a table row, flush
    if (inTable && !trimmedLine.startsWith('|')) {
      flushTable();
    }

    // Numbered section title - only for ## prefixed or standalone top-level sections
    // Pattern: "## 1. Title" or "1. Title" at document level (not nested content like "1. Item")
    const sectionMatch = trimmedLine.match(/^##\s*(\d+)\.\s+(.+)$/);
    if (sectionMatch) {
      flushParagraph();
      if (inList) {
        html += inList === 'ol' ? '</ol>' : '</ul>';
        inList = false;
      }
      const num = parseInt(sectionMatch[1]);
      const title = sectionMatch[2];
      const chineseNum = toChineseNumeral(num);
      html += `<h2 id="heading-${headingIndex++}" class="section-title"><span class="section-num">${chineseNum}</span>${formatInlineMarkdown(title)}</h2>`;
      sectionIndex++;
      isFirstParagraph = true;
      return;
    }

    // Regular Heading 2
    if (trimmedLine.startsWith('## ')) {
      flushParagraph();
      if (inList) {
        html += inList === 'ol' ? '</ol>' : '</ul>';
        inList = false;
      }
      const heading = trimmedLine.replace('## ', '');
      html += `<h2 id="heading-${headingIndex++}">${formatInlineMarkdown(heading)}</h2>`;
      isFirstParagraph = true;
      return;
    }

    // Heading 3 (chapter titles like "第一章：...")
    if (trimmedLine.startsWith('### ') || /^第[一二三四五六七八九十]+章/.test(trimmedLine)) {
      flushParagraph();
      if (inList) {
        html += inList === 'ol' ? '</ol>' : '</ul>';
        inList = false;
      }
      const heading = trimmedLine.replace('### ', '');
      html += `<h3 class="chapter-title">${formatInlineMarkdown(heading)}</h3>`;
      isFirstParagraph = true;
      return;
    }

    // Numbered heading (e.g., "1. 标题：" or "1. **标题**：" - has colon or bold)
    // These are standalone numbered points with explanatory paragraphs following
    const numberedHeadingMatch = trimmedLine.match(/^(\d+)\.\s+(.+[:：].*)$/);
    if (numberedHeadingMatch) {
      flushParagraph();
      if (inList) {
        html += inList === 'ol' ? '</ol>' : '</ul>';
        inList = false;
      }
      const num = numberedHeadingMatch[1];
      const content = numberedHeadingMatch[2];
      html += `<h4 class="numbered-heading"><span class="heading-num">${num}.</span> ${formatInlineMarkdown(content)}</h4>`;
      return;
    }

    // Regular numbered list (true list items without colons, consecutive)
    if (/^\d+\.\s/.test(trimmedLine)) {
      flushParagraph();
      if (inList !== 'ol') {
        if (inList) html += '</ul>';
        html += '<ol>';
        inList = 'ol';
      }
      const content = trimmedLine.replace(/^\d+\.\s/, '');
      html += `<li>${formatInlineMarkdown(content)}</li>`;
      return;
    }

    // Bullet list
    if (trimmedLine.startsWith('- ') || trimmedLine.startsWith('* ')) {
      flushParagraph();
      if (inList !== 'ul') {
        if (inList) html += '</ol>';
        html += '<ul>';
        inList = 'ul';
      }
      const content = trimmedLine.replace(/^[-*]\s/, '');
      html += `<li>${formatInlineMarkdown(content)}</li>`;
      return;
    }

    // Close list if not a list item
    if (inList) {
      html += inList === 'ol' ? '</ol>' : '</ul>';
      inList = false;
    }

    // Regular text
    currentParagraph.push(trimmedLine);
  });

  // Flush remaining
  flushParagraph();
  if (inTable) flushTable();
  if (inList) {
    html += inList === 'ol' ? '</ol>' : '</ul>';
  }

  return html;
}

// Format inline Markdown (bold, italic, links)
function formatInlineMarkdown(text) {
  // Bold: **text** or __text__
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Italic: *text* or _text_
  text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  text = text.replace(/_([^_]+)_/g, '<em>$1</em>');

  // Inline code: `code`
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

  return text;
}

// =====================================================
// Initialization
// =====================================================
document.addEventListener('DOMContentLoaded', () => {
  loadData();

  // Reader event listeners
  if (elements.readerOverlay) {
    elements.readerOverlay.addEventListener('click', closeReader);
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeReader();
  });

  // Reader scroll events
  const readerContainer = document.querySelector('.reader-container');
  if (readerContainer) {
    readerContainer.addEventListener('scroll', handleReaderScroll);
  }
});

// Handle reader scroll for progress bar and back-to-top
function handleReaderScroll() {
  const container = document.querySelector('.reader-container');
  const progressBar = document.getElementById('reader-progress');
  const backToTop = document.getElementById('back-to-top');

  if (!container) return;

  const scrollTop = container.scrollTop;
  const scrollHeight = container.scrollHeight - container.clientHeight;
  const progress = (scrollTop / scrollHeight) * 100;

  // Update progress bar
  if (progressBar) {
    progressBar.style.width = `${progress}%`;
  }

  // Show/hide back-to-top button
  if (backToTop) {
    if (scrollTop > 500) {
      backToTop.classList.add('visible');
    } else {
      backToTop.classList.remove('visible');
    }
  }
}

// Scroll reader to top
window.scrollReaderToTop = function () {
  const container = document.querySelector('.reader-container');
  if (container) {
    container.scrollTo({ top: 0, behavior: 'smooth' });
  }
};

// =====================================================
// Subscribe Modal (Keep in Touch)
// =====================================================
window.openSubscribeModal = function () {
  const modal = document.getElementById('subscribe-modal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
};

window.closeSubscribeModal = function () {
  const modal = document.getElementById('subscribe-modal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
};

// Close subscribe modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('subscribe-modal');
    if (modal && modal.classList.contains('active')) {
      closeSubscribeModal();
    }
  }
});

// =====================================================
// Mobile TOC Toggle
// =====================================================
window.toggleMobileTOC = function () {
  const toggle = document.getElementById('mobile-toc-toggle');
  const sidebar = document.getElementById('reader-sidebar');

  if (toggle && sidebar) {
    toggle.classList.toggle('active');
    sidebar.classList.toggle('mobile-visible');
  }
};
