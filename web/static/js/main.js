"use strict";

// ── Sample enquiries ─────────────────────────────────────────
const SAMPLES = {
  "new-client": `Hi there, I'm looking to engage your services for a new strata scheme. We have a 42-unit residential apartment building in North Sydney that currently self-manages, and the owners corporation committee recently voted to bring in a professional management company. Could you please send me an information pack about your services, management fees, and what the onboarding process looks like? We're hoping to transition before the end of the financial year.`,

  "support": `Good morning. I'm the treasurer for the owners corporation at 88 Harbour View Drive (Lot 14). We passed a resolution at our AGM last month to update our by-laws regarding short-term rental accommodation. Could you please advise on the process for having the updated by-laws registered, what documentation we need to provide, the estimated timeline, and any associated costs?`,

  "complaint": `I am writing to formally complain about the complete lack of action on the maintenance issue I reported six weeks ago. The stairwell lighting on levels 3 and 4 has been broken since September, creating a genuine safety hazard. I have sent three emails to your office with no response whatsoever. If this matter is not resolved within five working days I will be escalating to NSW Fair Trading.`,

  "general": `Hello, I recently received my quarterly levy notice and I'm a bit confused. There are two separate line items listed — one for the administrative fund and one for the capital works fund. Could you please explain the difference between these two? I want to understand what each one is used for before I make payment.`,

  "vague": `Hi, can you help me with my strata issue? It's quite urgent.`,

  "nonsense": `purple forty seven banana sky orange umbrella cat twelve sixteen`,
};

// ── DOM references ───────────────────────────────────────────
const enquiryInput    = document.getElementById("enquiry-input");
const charCount       = document.getElementById("char-count");
const analyzeBtn      = document.getElementById("analyze-btn");
const clearBtn        = document.getElementById("clear-btn");
const loadingState    = document.getElementById("loading-state");
const errorBanner     = document.getElementById("error-banner");
const errorMessage    = document.getElementById("error-message");
const resultsSection  = document.getElementById("results-section");
const reviewBanner    = document.getElementById("human-review-banner");
const reviewReason    = document.getElementById("review-reason");
const classifBadge    = document.getElementById("classification-badge");
const confidenceFill  = document.getElementById("confidence-fill");
const confidenceValue = document.getElementById("confidence-value");
const urgencyBadge    = document.getElementById("urgency-badge");
const processingTime  = document.getElementById("processing-time");
const summaryText     = document.getElementById("summary-text");
const recommendedAct  = document.getElementById("recommended-action");
const reasonText      = document.getElementById("reason-text");
const suggestedResp   = document.getElementById("suggested-response");
const copyBtn         = document.getElementById("copy-btn");
const riskSignalsRow        = document.getElementById("risk-signals-row");
const riskSignalsTags       = document.getElementById("risk-signals-tags");
const secondaryClassifs     = document.getElementById("secondary-classifications");
const categoryScoresCard    = document.getElementById("category-scores-card");
const categoryScoresList    = document.getElementById("category-scores-list");

const MAX_LENGTH = 5000;

// ── Character counter ────────────────────────────────────────
enquiryInput.addEventListener("input", () => {
  const len = enquiryInput.value.length;
  charCount.textContent = `${len} / ${MAX_LENGTH}`;
  charCount.className = len > MAX_LENGTH * 0.95 ? "at-limit"
                      : len > MAX_LENGTH * 0.80 ? "near-limit"
                      : "";
});

// ── Sample buttons ───────────────────────────────────────────
document.querySelectorAll(".btn-sample").forEach((btn) => {
  btn.addEventListener("click", () => {
    const key = btn.dataset.sample;
    enquiryInput.value = SAMPLES[key] || "";
    enquiryInput.dispatchEvent(new Event("input"));
    enquiryInput.focus();
  });
});

// ── Clear button ─────────────────────────────────────────────
clearBtn.addEventListener("click", () => {
  enquiryInput.value = "";
  enquiryInput.dispatchEvent(new Event("input"));
  hideResults();
  hideError();
  enquiryInput.focus();
});

// ── Analyse button ───────────────────────────────────────────
analyzeBtn.addEventListener("click", handleAnalyze);

enquiryInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    handleAnalyze();
  }
});

async function handleAnalyze() {
  const text = enquiryInput.value.trim();
  if (!text) {
    showError("Please enter an enquiry before analysing.");
    return;
  }

  hideResults();
  hideError();
  showLoading(true);
  analyzeBtn.disabled = true;

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enquiry: text }),
    });

    const json = await response.json();

    if (!response.ok || json.status === "error") {
      showError(json.message || "An unexpected error occurred. Please try again.");
      return;
    }

    renderResults(json.data);
  } catch (err) {
    showError("Could not reach the server. Please check your connection and try again.");
    console.error("Fetch error:", err);
  } finally {
    showLoading(false);
    analyzeBtn.disabled = false;
  }
}

// ── Render results ───────────────────────────────────────────
function renderResults(data) {
  // Human review banner
  if (data.needs_human_review) {
    reviewReason.textContent = data.reason || "This enquiry has been flagged for staff review.";
    reviewBanner.classList.remove("hidden");
  } else {
    reviewBanner.classList.add("hidden");
  }

  // Classification badge (primary)
  classifBadge.textContent = data.classification;
  classifBadge.className = "classification-badge " + classificationClass(data.classification);

  // Secondary classification badges — shown when the enquiry spans multiple categories
  const others = (data.classifications || []).filter((c) => c !== data.classification);
  if (others.length > 0) {
    secondaryClassifs.innerHTML =
      '<span class="also-label">Also:</span>' +
      others.map((c) => `<span class="badge-secondary">${c}</span>`).join("");
    secondaryClassifs.classList.remove("hidden");
  } else {
    secondaryClassifs.innerHTML = "";
    secondaryClassifs.classList.add("hidden");
  }

  // Confidence bar
  const pct = Math.round((data.confidence || 0) * 100);
  confidenceFill.style.width = `${pct}%`;
  confidenceFill.className = "confidence-fill " + confidenceLevel(pct);
  confidenceValue.textContent = `${pct}%`;

  // Urgency badge
  const urg = (data.urgency || "Unknown").toLowerCase();
  urgencyBadge.textContent = data.urgency || "Unknown";
  urgencyBadge.className = `urgency-badge urgency-${urg}`;

  // Risk signals from preprocessing
  const signals = data.preprocessing?.risk_signals ?? [];
  if (signals.length > 0) {
    riskSignalsTags.innerHTML = signals
      .map((s) => `<span class="risk-tag">${s}</span>`)
      .join("");
    riskSignalsRow.classList.remove("hidden");
  } else {
    riskSignalsTags.innerHTML = "";
    riskSignalsRow.classList.add("hidden");
  }

  // Category confidence breakdown
  const CATEGORY_ORDER = [
    "New Client",
    "Support Request",
    "Complaint",
    "General Question",
    "Unknown / Needs Human Review",
  ];
  const scores = data.category_scores || {};
  if (Object.keys(scores).length > 0) {
    categoryScoresList.innerHTML = CATEGORY_ORDER.map((cat) => {
      const pct = Math.round((scores[cat] || 0) * 100);
      const isPrimary = cat === data.classification;
      const fillClass = pct >= 70 ? "" : pct >= 40 ? " medium" : " low";
      return `<div class="cscore-row${isPrimary ? " cscore-primary" : ""}">
        <span class="cscore-label">${cat}</span>
        <div class="cscore-bar"><div class="cscore-fill${fillClass}" style="width:${pct}%"></div></div>
        <span class="cscore-pct">${pct}%</span>
      </div>`;
    }).join("");
    categoryScoresCard.classList.remove("hidden");
  } else {
    categoryScoresList.innerHTML = "";
    categoryScoresCard.classList.add("hidden");
  }

  // Processing time
  processingTime.textContent = data.processing_time_ms != null
    ? `${data.processing_time_ms} ms`
    : "—";

  // Text fields
  summaryText.textContent     = data.summary || "—";
  recommendedAct.textContent  = data.recommended_action || "—";
  reasonText.textContent      = data.reason || "—";
  suggestedResp.value         = data.suggested_response || "";

  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Copy button ──────────────────────────────────────────────
copyBtn.addEventListener("click", async () => {
  const text = suggestedResp.value;
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
    copyBtn.textContent = "Copied!";
    copyBtn.classList.add("copied");
    setTimeout(() => {
      copyBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
          <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
        </svg>
        Copy`;
      copyBtn.classList.remove("copied");
    }, 2000);
  } catch {
    // Fallback for browsers without clipboard API
    suggestedResp.select();
    document.execCommand("copy");
  }
});

// ── Helpers ──────────────────────────────────────────────────
function showLoading(visible) {
  loadingState.classList.toggle("hidden", !visible);
}

function showError(msg) {
  errorMessage.textContent = msg;
  errorBanner.classList.remove("hidden");
}

function hideError() {
  errorBanner.classList.add("hidden");
}

function hideResults() {
  resultsSection.classList.add("hidden");
}

function classificationClass(value) {
  const map = {
    "New Client":                "badge-new-client",
    "Support Request":           "badge-support",
    "Complaint":                 "badge-complaint",
    "General Question":          "badge-general",
    "Unknown / Needs Human Review": "badge-unknown",
  };
  return map[value] || "badge-unknown";
}

function confidenceLevel(pct) {
  if (pct >= 70) return "";       // green (default)
  if (pct >= 40) return "medium"; // amber
  return "low";                    // red
}
