// src/static/js/components/main2.js
console.log("Loaded v2 main2.js");
import { apiPost } from '../api.js';

// DOM refs

const qEl =
  document.querySelector('#q') ||
  document.querySelector('input[name="q"]') ||
  document.querySelector('input[name="query"]') ||
  document.querySelector('input[type="search"]');
  // used by runV2Search
  // Counter badge for number of citations
const citationsCountEl =
document.getElementById('citationsCount') ||
document.querySelector('[data-citations-count]');

function updateCitationsCount(n) {
if (citationsCountEl) citationsCountEl.textContent = String(n);
}

function escapeHtml(str){
  return String(str)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;");
}

// --- Enhanced loading/skeleton helpers ---
function skeletonSummary() {
    return `
      <div class="skeleton-summary">
        <div class="skeleton-summary-line"></div>
        <div class="skeleton-summary-line"></div>
        <div class="skeleton-summary-line"></div>
        <div class="skeleton-summary-line"></div>
      </div>
    `;
  }
  
  function skeletonCitationCard() {
    return `
      <div class="skeleton-citation-card">
        <div class="skeleton-citation-title"></div>
        <div class="skeleton-citation-meta"></div>
        <div class="skeleton-citation-snippet"></div>
        <div class="skeleton-citation-snippet"></div>
        <div class="skeleton-citation-snippet"></div>
        <div class="skeleton-citation-footer">
          <div class="skeleton-citation-score"></div>
          <div class="skeleton-citation-link"></div>
        </div>
      </div>
    `;
  }
  
  function showLoading() {
    const sum = document.getElementById('summary');
    if (sum) sum.innerHTML = skeletonSummary();
  
    const grid = document.getElementById('citations');
    if (grid) {
      grid.innerHTML =
        skeletonCitationCard() +
        skeletonCitationCard() +
        skeletonCitationCard() +
        skeletonCitationCard();
    }
  }
  
  function stopLoading() {
    // placeholder for future; kept for symmetry
  }

// --- Streaming Text Effects ---
function typewriterEffect(element, text, speed = 30) {
    return new Promise((resolve) => {
        element.innerHTML = '';
        element.classList.add('typewriter-text');
        element.style.color = '#e5e7eb';
        element.style.opacity = '1';
        element.style.visibility = 'visible';
        
        let i = 0;
        const timer = setInterval(() => {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
            } else {
                clearInterval(timer);
                element.classList.remove('typewriter-text');
                element.classList.add('fade-in-text');
                resolve();
            }
        }, speed);
    });
}

function streamText(element, text, speed = 20) {
    return new Promise((resolve) => {
        element.innerHTML = '';
        element.classList.add('text-reveal');
        element.style.color = '#e5e7eb';
        element.style.opacity = '1';
        element.style.visibility = 'visible';
        
        let i = 0;
        const timer = setInterval(() => {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
            } else {
                clearInterval(timer);
                element.classList.add('revealed');
                resolve();
            }
        }, speed);
    });
}

function streamParagraphs(element, text, speed = 25) {
    return new Promise((resolve) => {
        element.innerHTML = '';
        element.classList.add('text-reveal');
        element.style.color = '#e5e7eb';
        element.style.opacity = '1';
        element.style.visibility = 'visible';
        
        // Split text into paragraphs
        const paragraphs = text.split('\n\n').filter(p => p.trim());
        let currentParagraph = 0;
        let currentChar = 0;
        
        const timer = setInterval(() => {
            if (currentParagraph < paragraphs.length) {
                const paragraph = paragraphs[currentParagraph];
                if (currentChar < paragraph.length) {
                    element.innerHTML += paragraph.charAt(currentChar);
                    currentChar++;
                } else {
                    element.innerHTML += '\n\n';
                    currentParagraph++;
                    currentChar = 0;
                }
            } else {
                clearInterval(timer);
                element.classList.add('revealed');
                resolve();
            }
        }, speed);
    });
}

function animateCitations(citations, container, speed = 100) {
    return new Promise((resolve) => {
        container.innerHTML = "";
        let currentIndex = 0;
        
        const addCitation = () => {
            if (currentIndex < citations.length) {
                const citation = citations[currentIndex];
                const citationHTML = citationCard(citation);
                
                // Create a temporary container to parse the HTML
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = citationHTML;
                
                // Get the actual citation card element
                const citationCardElement = tempDiv.querySelector(".citation-card");
                if (citationCardElement) {
                    citationCardElement.classList.add("citation-stream");
                    container.appendChild(citationCardElement);
                    
                    // Trigger animation after a brief delay
                    setTimeout(() => {
                        citationCardElement.classList.add("streamed");
                    }, 50);
                } else {
                    // Fallback: create a simple div
                    const fallbackDiv = document.createElement("div");
                    fallbackDiv.innerHTML = citationHTML;
                    fallbackDiv.classList.add("citation-stream");
                    container.appendChild(fallbackDiv);
                    
                    setTimeout(() => {
                        fallbackDiv.classList.add("streamed");
                    }, 50);
                }
                
                currentIndex++;
                setTimeout(addCitation, speed);
            } else {
                resolve();
            }
        };
        
        addCitation();
    });
}function citationCard(c) {
  const score = c.score != null ? Number(c.score).toFixed(2) : "";
  const pmid = c.pmid ? String(c.pmid) : "";
  const meta = [c.journal, c.year, pmid && `PMID ${pmid}`].filter(Boolean).join(" • ");
  const pubmed = pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : "#";
  const snippet = c.snippet || c.abstract || "";

  return `
    <div class="citation-card">
      <div class="citation-content">
        <div class="citation-header">
          <h3 class="citation-title">
            ${escapeHtml(c.title || "Untitled")}
          </h3>
          <p class="citation-meta">${escapeHtml(meta)}</p>
          ${snippet ? `<p class="citation-snippet">${escapeHtml(snippet)}</p>` : ""}
        </div>
        <div class="citation-footer">
          ${score ? `<span class="citation-score">${score}</span>` : ""}
          ${pmid ? `<a class="citation-link" target="_blank" href="${pubmed}">PubMed ↗</a>` : ""}
        </div>
      </div>
    </div>
  `;
}
function formatAnswer(a, retrievalLatency = 0) {
  const refs = (a.used_pmids || []).map(p =>
    `<span class="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-200">PMID ${escapeHtml(String(p))}</span>`
  ).join(" ");
  const totalLatency = retrievalLatency + (a.gen_latency_ms || 0);
  
  return `
    <div class="prose prose-invert max-w-none">
      <p class="whitespace-pre-wrap leading-relaxed">${escapeHtml(a.answer || "")}</p>
      <div class="mt-4 flex flex-wrap items-center gap-2 text-xs text-neutral-400">
        <span>References:</span> ${refs}
      </div>
      <div class="mt-3 text-xs text-neutral-500 border-t border-neutral-700 pt-2">
        <span class="inline-flex items-center gap-1">
          <span class="w-2 h-2 bg-green-400 rounded-full"></span>
          Retrieved: ${Math.round(retrievalLatency)}ms
        </span>
        <span class="mx-2 text-neutral-600">•</span>
        <span class="inline-flex items-center gap-1">
          <span class="w-2 h-2 bg-purple-400 rounded-full"></span>
          Generated: ${Math.round(a.gen_latency_ms || 0)}ms
        </span>
        <span class="mx-2 text-neutral-600">•</span>
        <span class="inline-flex items-center gap-1">
          <span class="w-2 h-2 bg-cyan-400 rounded-full"></span>
          Total: ${Math.round(totalLatency)}ms
        </span>
      </div>
    </div>
  `;
}

function normalizeRow(raw) {
  const r = raw && raw._source ? raw._source : raw || {};
  let pmid = r.pmid ?? r.PMID ?? r.pubmed_id ?? r.id ?? "";
  if (!pmid && typeof r.url === "string") {
    const m = r.url.match(/pubmed\.ncbi\.nlm\.nih\.gov\/(\d+)/);
    if (m) pmid = m[1];
  }
  let year = r.year ?? r.pubyear ?? r.publication_year;
  if (!year && r.datePublished) {
    const m = String(r.datePublished).match(/\d{4}/);
    if (m) year = Number(m[0]);
  }
  return {
    pmid: String(pmid || ""),
    title: r.title ?? r.paper_title ?? r.name ?? "Untitled",
    journal: r.journal ?? r.journal_name ?? r.source ?? "",
    year: typeof year === "number" ? year : (year ? Number(year) : undefined),
    snippet: r.snippet ?? r.excerpt ?? r.abstractSnippet ?? r.abstract ?? "",
    score: typeof r.score === "number" ? r.score
         : (typeof r.relevance === "number" ? r.relevance : undefined),
    url: r.url ?? (pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : undefined),
  };
}

// Global state for citations
let allCitations = [];
let visibleCitations = 4; // Show 2x2 grid initially

async function streamCitations(citations, retrievalLatency = 0) {
  const citationsEl = document.getElementById("citations");
  const showMoreBtn = document.getElementById("showMoreBtn");
  
  if (citations.length === 0) {
    citationsEl.innerHTML = `<div class="col-span-2 text-neutral-400 text-center py-8">No citations found.</div>`;
    showMoreBtn.style.display = 'none';
    return;
  }
  
  const visibleItems = citations.slice(0, visibleCitations);
  
  // Stream citations with animation
  await animateCitations(visibleItems, citationsEl, 150);
  
  // Add retrieval timing
  const timingHTML = `
    <div class="col-span-2 text-xs text-neutral-500 text-center py-2 border-t border-neutral-700 mt-4 fade-in-text">
      <span class="inline-flex items-center gap-1">
        <span class="w-2 h-2 bg-green-400 rounded-full"></span>
        Retrieved ${citations.length} citations in ${Math.round(retrievalLatency)}ms
      </span>
    </div>
  `;
  
  citationsEl.insertAdjacentHTML('beforeend', timingHTML);
  
  if (citations.length > visibleCitations) {
    showMoreBtn.style.display = 'block';
  } else {
    showMoreBtn.style.display = 'none';
  }
}

function showMoreCitations() {
  visibleCitations = Math.min(visibleCitations + 4, allCitations.length); // Add 2 more rows
  streamCitations(allCitations, window.lastRetrievalLatency || 0);
}

// Accept an optional mode override: 'research' | 'auto' (defaults from URL)
async function runV2Search(nextMode) {
    const q = qEl.value.trim();
    // read mode from arg or URL (falls back to 'research')
    const mode = nextMode || getQueryFromURL().mode || 'research';
  
    showLoading();
  
    // keep the URL in sync so searches are shareable/bookmarkable
    setQueryInURL(q, mode);
  
    let result;
    try {
        const response = await fetch("https://api.facter.it.com/api/unified-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          query_type: mode,      // <— use selected mode
          want_summary: true
        })
      });
  
      // Parse JSON robustly
      try {
        result = await response.json();
      } catch (e) {
        streamSummary('', 0, 0);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      if (!response.ok) {
        streamSummary('', 0, 0);
        throw new Error(result?.error || `HTTP ${response.status}`);
      }
  
      // Normalize shapes (array = legacy; object = new)
      const isArray = Array.isArray(result);
      const citations = isArray ? result : (result.citations || []);
      const retrievalLatencyMs = isArray ? 0 : (result.retrieval_latency_ms ?? 0);
      const summaryText = isArray ? '' : (result.summary_text ?? result.summary ?? '');
      const answerText = isArray ? '' : (result.answer ?? result.summary_text ?? result.summary ?? '');
      
      const summaryLatencyMs = isArray ? 0 : (result.summary_latency_ms ?? 0);
      const answerLatencyMs = isArray ? 0 : (result.answer_latency_ms ?? 0);

      const detailedTextFromAPI = isArray ? '' : (result.detailed_answer ?? '');
      const detailedLatencyMs   = isArray ? 0 : (result.detailed_latency_ms ?? result.answer_latency_ms ?? 0);

  
      console.log("✅ unified-search result", {
        
        answerText,
        answerLatencyMs,
        citations,
        retrievalLatencyMs,
        summaryText,
        summaryLatencyMs,
        mode
      });
  
      // Update globals/UI (do NOT redeclare these elsewhere)
      window.lastRetrievalLatency = retrievalLatencyMs;
      allCitations = citations;
      visibleCitations = 4;
      if (typeof updateCitationsCount === 'function') {
        updateCitationsCount(citations.length);
      } else if (citationsCountEl) {
        citationsCountEl.textContent = String(citations.length);
      }
  
      // NEW ORDER: Citations first, then text
      await streamCitations(citations, retrievalLatencyMs);
      
      await streamSummary(summaryText, retrievalLatencyMs, summaryLatencyMs);
      const detailedText = (detailedTextFromAPI && detailedTextFromAPI.trim())
      ? detailedTextFromAPI
      : generateDetailedAnswer(summaryText);
      await streamAnswer(detailedText, retrievalLatencyMs, detailedLatencyMs);  

    } catch (err) {
      console.error('Search failed:', err);
      // (summary already cleared above on error paths)
      throw err;
    } finally {
      stopLoading();
    }
  }
  
// --- Enhanced Summary renderer with streaming ---
async function streamSummary(text, retrievedMs = 0, summaryMs = 0) {
    const box = document.getElementById('summary');
    if (!box) return; // no summary card in the DOM
  
    // Clear loading state
    box.classList.remove('text-neutral-400', 'text-center', 'py-6');
    box.style.color = '#e5e7eb';
    box.style.opacity = '1';
    box.style.visibility = 'visible';
    
    if (text && text.trim()) {
        // Stream the text with typewriter effect
        const formattedText = formatSummaryWithBullets(text);
        await streamParagraphs(box, formattedText, 2);
    } else {
        box.innerHTML = '<div class="text-neutral-400 text-center py-6">No summary available.</div>';
    }
  
    // Optional: update the tiny timing label if it exists
    const meter = document.querySelector('[data-summary-metrics]');
    if (meter) {
      meter.textContent = `Retrieved: ${retrievedMs}ms · Summary: ${summaryMs}ms`;
    }
  }
  
  // wire events (button + Enter + form submission + show more)
window.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("searchForm");
  const btn = document.getElementById("btn-search");
  const q = document.getElementById("q");
  const showMoreBtn = document.getElementById("showMoreBtn");
  
  // Handle form submission to prevent page reload
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault(); // Prevent form submission
      runV2Search();
    });
  }
  
  // Handle button click
  if (btn) {
    btn.addEventListener("click", (e) => {
      e.preventDefault(); // Prevent any default behavior
      runV2Search();
    });
  }
  
  // Handle Enter key
  if (false && q) {
    q.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault(); // Prevent form submission
        runV2Search();
      }
    });
  }
  
  // Handle show more citations
  if (showMoreBtn) {
    showMoreBtn.addEventListener("click", showMoreCitations);
  }
});
function getQueryFromURL() {
    const params = new URLSearchParams(window.location.search);
    return {
      q: params.get('q') || '',
      mode: params.get('mode') || 'research'
    };
  }
  
function setQueryInURL(q, mode) {
    const url = new URL(window.location.href);
    if (q) url.searchParams.set('q', q); else url.searchParams.delete('q');
    if (mode) url.searchParams.set('mode', mode); else url.searchParams.delete('mode');
    history.replaceState(null, '', url);
  }
window.addEventListener('DOMContentLoaded', () => {
    const { q, mode } = getQueryFromURL();
    if (false && q) {
      qEl.value = q;
      runV2Search(mode).catch(err => console.error('Auto search failed:', err));
    }
  });

// Format summary text with proper bullet points
function formatSummaryWithBullets(text) {
    if (!text || !text.trim()) return text;
    
    // Split by common dash patterns and convert to bullet points
    const lines = text.split(/\n|\r\n/).filter(line => line.trim());
    const formattedLines = lines.map(line => {
        const trimmed = line.trim();
        // If line starts with dash, convert to bullet point
        if (trimmed.startsWith("-") || trimmed.startsWith("•")) {
            return trimmed.replace(/^[-•]\s*/, "");
        }
        return trimmed;
    });
    
    // Join with proper spacing for bullet points
    return formattedLines.join("\n\n");
}


async function streamAnswer(answerText, retrievedMs = 0, answerMs = 0) {
    const answerEl = document.getElementById("answer");
    if (!answerEl) return; // no answer card in the DOM

    // Clear loading state
    answerEl.classList.remove('text-neutral-400', 'text-center', 'py-8');
    answerEl.style.color = '#e5e7eb';
    answerEl.style.opacity = '1';
    answerEl.style.visibility = 'visible';

    if (answerText && answerText.trim()) {
        // Check if this is the same as summary and expand it
        const summaryEl = document.getElementById("summary");
        const summaryText = summaryEl ? summaryEl.textContent : "";
        if (answerText === summaryText || answerText.includes(summaryText)) {
            // Generate a more detailed, paragraph-style response
            answerText = generateDetailedAnswer(answerText);
        }
        // Stream the text with typewriter effect
        await streamParagraphs(answerEl, answerText, 2);
    } else {
        answerEl.innerHTML = '<div class="text-neutral-400 text-center py-8">No detailed answer available.</div>';
    }

    // Optional: update the tiny timing label if it exists
    const meter = document.querySelector('[data-answer-metrics]');
    if (meter) {
      meter.textContent = `Retrieved: ${retrievedMs}ms · Answer: ${answerMs}ms`;
    }
}


// Generate a more detailed, paragraph-style answer from summary
function generateDetailedAnswer(summaryText) {
    if (!summaryText || summaryText.trim() === "") {
        return "No detailed information available.";
    }
    
    // Convert bullet points to paragraph format
    const lines = summaryText.split('\n').filter(line => line.trim());
    const paragraphs = [];
    
    // Group related points into paragraphs
    let currentParagraph = [];
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('-') || trimmed.startsWith('•')) {
            // Remove bullet point and add to current paragraph
            const content = trimmed.replace(/^[-•]\s*/, '');
            currentParagraph.push(content);
        } else if (trimmed.length > 0) {
            // If we have accumulated points, create a paragraph
            if (currentParagraph.length > 0) {
                paragraphs.push(currentParagraph.join('. ') + '.');
                currentParagraph = [];
            }
            // Add standalone content
            paragraphs.push(trimmed);
        }
    }
    
    // Add any remaining points as a paragraph
    if (currentParagraph.length > 0) {
        paragraphs.push(currentParagraph.join('. ') + '.');
    }
    
    // If no paragraphs were created, return the original text
    if (paragraphs.length === 0) {
        return summaryText;
    }
    
    // Join paragraphs with proper spacing
    return paragraphs.join('\n\n');
}


