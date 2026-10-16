console.log("Nine-point uniformity UI loaded");


// ============================================================
// UI ELEMENTS
// ============================================================

const uniformitySheetIdInput = document.getElementById(
    "uniformity-sheet-id-input"
);
const uniformityStartButton = document.getElementById(
    "uniformity-start-button"
);
const uniformityEvaluateButton = document.getElementById(
    "uniformity-evaluate-button"
);
const uniformityResetButton = document.getElementById(
    "uniformity-reset-button"
);
const uniformityStatusText = document.getElementById(
    "uniformity-status-text"
);
const uniformityResultText = document.getElementById(
    "uniformity-result-text"
);
const uniformityResultDescription = document.getElementById(
    "uniformity-result-description"
);
const uniformityRegionTable = document.getElementById(
    "uniformity-region-table"
);

const maxPairDistanceValue = document.getElementById(
    "uniformity-max-pair-distance"
);
const worstPairValue = document.getElementById(
    "uniformity-worst-pair"
);
const repeatabilityValue = document.getElementById(
    "uniformity-repeatability"
);
const clearDeviationValue = document.getElementById(
    "uniformity-clear-deviation"
);
const colorThresholdValue = document.getElementById(
    "uniformity-color-threshold"
);
const repeatabilityThresholdValue = document.getElementById(
    "uniformity-repeatability-threshold"
);

const uniformityThresholdInput = document.getElementById(
    "uniformity-threshold-input"
);
const uniformityThresholdSaveButton = document.getElementById(
    "uniformity-threshold-save-button"
);
const uniformityThresholdSaveStatus = document.getElementById(
    "uniformity-threshold-save-status"
);

const uniformityExportButton = document.getElementById(
    "uniformity-export-button"
);
const uniformityHistoryRefreshButton = document.getElementById(
    "uniformity-history-refresh-button"
);
const uniformityHistoryCount = document.getElementById(
    "uniformity-history-count"
);
const uniformityHistoryTable = document.getElementById(
    "uniformity-history-table"
);
const uniformityHistoryEmpty = document.getElementById(
    "uniformity-history-empty"
);
const uniformityHistoryDetail = document.getElementById(
    "uniformity-history-detail"
);

const regionButtons = Array.from(
    document.querySelectorAll("[data-region-id]")
);


// ============================================================
// STATE
// ============================================================

let uniformityBusy = false;
let completedNinePointTestCount = 0;
let uniformityHistory = [];


// ============================================================
// BASIC HELPERS
// ============================================================

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatNumber(value, digits = 4) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "-";
    }

    return number.toFixed(digits);
}


function formatPercent(value, digits = 1) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "-";
    }

    return `${(number * 100).toFixed(digits)}%`;
}


function formatTimestamp(value) {
    if (!value) {
        return "-";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString();
}


function pointSortKey(point) {
    const match = String(point?.region_id ?? "")
        .match(/^(?:P|R)(\d+)$/i);

    return match ? Number(match[1]) : 999;
}


function resultBadge(status) {
    const normalized = String(status ?? "-").toUpperCase();
    const cssClass = (
        normalized === "PASS"
            ? "pass"
            : normalized === "FAIL"
                ? "fail"
                : "warn"
    );

    return (
        `<span class="uniformity-status-badge ${cssClass}">`
        + `${escapeHtml(normalized)}`
        + "</span>"
    );
}


// ============================================================
// API HELPERS
// ============================================================

async function uniformityRequest(path, options = {}) {
    const response = await fetch(path, options);

    let data = null;

    try {
        data = await response.json();
    }
    catch (error) {
        data = {};
    }

    if (!response.ok) {
        throw new Error(
            data.detail || `HTTP ${response.status}`
        );
    }

    return data;
}


function getDownloadFilename(response) {
    const contentDisposition = response.headers.get(
        "Content-Disposition"
    );

    if (!contentDisposition) {
        return "nine_point_uniformity_results.csv";
    }

    const match = contentDisposition.match(
        /filename="?([^";]+)"?/i
    );

    return (
        match
            ? match[1]
            : "nine_point_uniformity_results.csv"
    );
}


// ============================================================
// BUSY STATE
// ============================================================

function updateUniformityExportButton() {
    if (!uniformityExportButton) {
        return;
    }

    uniformityExportButton.disabled = (
        uniformityBusy
        || completedNinePointTestCount === 0
    );

    uniformityExportButton.textContent = (
        completedNinePointTestCount > 0
            ? `Export All Nine-Point CSV (${completedNinePointTestCount})`
            : "Export All Nine-Point CSV"
    );
}


function setUniformityBusy(isBusy) {
    uniformityBusy = isBusy;

    if (uniformityStartButton) {
        uniformityStartButton.disabled = isBusy;
    }

    if (uniformityEvaluateButton) {
        uniformityEvaluateButton.disabled = isBusy;
    }

    if (uniformityResetButton) {
        uniformityResetButton.disabled = isBusy;
    }

    if (uniformityThresholdSaveButton) {
        uniformityThresholdSaveButton.disabled = isBusy;
    }

    if (uniformityHistoryRefreshButton) {
        uniformityHistoryRefreshButton.disabled = isBusy;
    }

    regionButtons.forEach(button => {
        button.disabled = (
            isBusy
            || button.dataset.captured === "true"
        );
    });

    updateUniformityExportButton();
}


// ============================================================
// CURRENT TEST DISPLAY
// ============================================================

function resetUniformityDisplay() {
    uniformityStatusText.textContent = "Not started";
    uniformityResultText.textContent = "READY";
    uniformityResultText.className = "uniformity-result waiting";
    uniformityResultDescription.textContent =
        "Start a sheet test, measure P1 to P9, then evaluate.";

    maxPairDistanceValue.textContent = "-";
    worstPairValue.textContent = "-";
    repeatabilityValue.textContent = "-";
    clearDeviationValue.textContent = "-";

    uniformityRegionTable.innerHTML = "";

    regionButtons.forEach(button => {
        button.dataset.captured = "false";
        button.classList.remove("captured");
        button.disabled = true;
    });

    uniformityEvaluateButton.disabled = true;
    updateUniformityExportButton();
}


function updateRegionRow(region) {
    const existing = document.getElementById(
        `uniformity-row-${region.region_id}`
    );

    if (existing) {
        existing.remove();
    }

    const row = document.createElement("tr");
    row.id = `uniformity-row-${region.region_id}`;

    row.innerHTML = `
        <td><strong>${escapeHtml(region.region_id)}</strong></td>
        <td>${escapeHtml(region.r)}</td>
        <td>${escapeHtml(region.g)}</td>
        <td>${escapeHtml(region.b)}</td>
        <td>${escapeHtml(region.clear)}</td>
        <td>${formatNumber(region.normalized?.r)}</td>
        <td>${formatNumber(region.normalized?.g)}</td>
        <td>${formatNumber(region.normalized?.b)}</td>
        <td>${formatNumber(
            region.repeatability?.normalized_p95_distance
        )}</td>
    `;

    uniformityRegionTable.appendChild(row);
}


function updateCurrentResult(record) {
    const result = record.uniformity;

    uniformityResultText.textContent = result.status;
    uniformityResultText.className = (
        `uniformity-result ${
            result.status === "PASS"
                ? "pass"
                : "fail"
        }`
    );

    uniformityResultDescription.textContent =
        `Colour: ${result.color_status}; `
        + `repeatability: ${result.repeatability_status}; `
        + `Clear diagnostic: ${result.clear_status}.`;

    if (typeof window.showHardwareOutput === "function") {
        window.showHardwareOutput(result.status);
    }

    maxPairDistanceValue.textContent = formatNumber(
        result.max_pair_distance
    );

    worstPairValue.textContent = (
        result.worst_pair
            ? `${result.worst_pair.first}–${result.worst_pair.second}`
            : "-"
    );

    repeatabilityValue.textContent = formatNumber(
        result.max_repeatability_p95_distance
    );

    clearDeviationValue.textContent = formatPercent(
        result.max_clear_deviation
    );
}


// ============================================================
// THRESHOLD SETTINGS
// ============================================================

async function loadUniformitySettings() {
    try {
        const settings = await uniformityRequest(
            "/api/settings"
        );

        const colorThreshold = Number(
            settings.uniformity_color_threshold
        );

        const repeatabilityThreshold = Number(
            settings.uniformity_repeatability_threshold
        );

        if (Number.isFinite(colorThreshold)) {
            colorThresholdValue.textContent =
                colorThreshold.toFixed(3);

            uniformityThresholdInput.value =
                colorThreshold.toFixed(3);
        }

        if (Number.isFinite(repeatabilityThreshold)) {
            repeatabilityThresholdValue.textContent =
                repeatabilityThreshold.toFixed(3);
        }

        uniformityThresholdSaveStatus.textContent =
            "Loaded from config/settings.json.";
    }
    catch (error) {
        console.error(
            "Uniformity settings load error:",
            error
        );

        uniformityThresholdSaveStatus.textContent =
            `Could not load threshold: ${error.message}`;
    }
}


uniformityThresholdSaveButton.addEventListener(
    "click",
    async () => {
        const threshold = Number(
            uniformityThresholdInput.value
        );

        if (
            !Number.isFinite(threshold)
            || threshold <= 0
            || threshold > 1.5
        ) {
            uniformityThresholdSaveStatus.textContent =
                "Enter a threshold greater than 0 and no more than 1.5.";
            return;
        }

        try {
            uniformityThresholdSaveButton.disabled = true;
            uniformityThresholdSaveStatus.textContent =
                "Saving threshold...";

            const data = await uniformityRequest(
                "/api/settings/uniformity-threshold",
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        threshold
                    })
                }
            );

            const savedThreshold = Number(
                data.uniformity_color_threshold
            );

            colorThresholdValue.textContent =
                savedThreshold.toFixed(3);

            uniformityThresholdInput.value =
                savedThreshold.toFixed(3);

            uniformityThresholdSaveStatus.textContent =
                "Threshold saved. It will be used for future evaluations.";
        }
        catch (error) {
            uniformityThresholdSaveStatus.textContent =
                error.message;
        }
        finally {
            uniformityThresholdSaveButton.disabled = false;
        }
    }
);


// ============================================================
// HISTORY DISPLAY
// ============================================================

function renderUniformityHistory(results) {
    uniformityHistory = results;

    const count = results.length;

    uniformityHistoryCount.textContent = (
        `${count} completed test${count === 1 ? "" : "s"}`
    );

    uniformityHistoryTable.innerHTML = "";

    uniformityHistoryEmpty.hidden = count !== 0;

    if (count === 0) {
        uniformityHistoryDetail.hidden = true;
        return;
    }

    results.forEach((record, index) => {
        const result = record.uniformity || {};
        const thresholds = result.thresholds || {};
        const worstPair = result.worst_pair || {};

        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${escapeHtml(formatTimestamp(record.timestamp))}</td>
            <td><strong>${escapeHtml(record.sheet_id)}</strong></td>
            <td>${resultBadge(result.status)}</td>
            <td>${resultBadge(result.color_status)}</td>
            <td>${formatNumber(result.max_pair_distance)}</td>
            <td>${formatNumber(thresholds.color, 3)}</td>
            <td>${escapeHtml(
                worstPair.first && worstPair.second
                    ? `${worstPair.first}–${worstPair.second}`
                    : "-"
            )}</td>
            <td>
                <button
                    class="button small-button uniformity-history-view-button"
                    data-history-index="${index}"
                >
                    View
                </button>
            </td>
        `;

        uniformityHistoryTable.appendChild(row);
    });

    renderUniformityHistoryDetail(results[0]);
}


function renderUniformityHistoryDetail(record) {
    if (!record) {
        uniformityHistoryDetail.hidden = true;
        return;
    }

    const result = record.uniformity || {};
    const thresholds = result.thresholds || {};
    const worstPair = result.worst_pair || {};
    const points = [...(record.regions || [])]
        .sort((first, second) => (
            pointSortKey(first) - pointSortKey(second)
        ));

    const pointRows = points
        .map(point => `
            <tr>
                <td><strong>${escapeHtml(point.region_id)}</strong></td>
                <td>${escapeHtml(point.r)}</td>
                <td>${escapeHtml(point.g)}</td>
                <td>${escapeHtml(point.b)}</td>
                <td>${escapeHtml(point.clear)}</td>
                <td>${formatNumber(point.normalized?.r)}</td>
                <td>${formatNumber(point.normalized?.g)}</td>
                <td>${formatNumber(point.normalized?.b)}</td>
                <td>${formatNumber(
                    point.repeatability?.normalized_p95_distance
                )}</td>
            </tr>
        `)
        .join("");

    uniformityHistoryDetail.innerHTML = `
        <div class="uniformity-history-detail-header">
            <div>
                <p class="section-label">SELECTED TEST</p>
                <h3>${escapeHtml(record.sheet_id)}</h3>
                <p>${escapeHtml(formatTimestamp(record.timestamp))}</p>
            </div>
            <div>${resultBadge(result.status)}</div>
        </div>

        <div class="uniformity-history-metrics">
            <div>
                <span>Colour Result</span>
                <strong>${escapeHtml(result.color_status ?? "-")}</strong>
            </div>
            <div>
                <span>Max Pair Distance</span>
                <strong>${formatNumber(result.max_pair_distance)}</strong>
            </div>
            <div>
                <span>Colour Threshold</span>
                <strong>${formatNumber(thresholds.color, 3)}</strong>
            </div>
            <div>
                <span>Worst Pair</span>
                <strong>${escapeHtml(
                    worstPair.first && worstPair.second
                        ? `${worstPair.first}–${worstPair.second}`
                        : "-"
                )}</strong>
            </div>
            <div>
                <span>Repeatability</span>
                <strong>${escapeHtml(result.repeatability_status ?? "-")}</strong>
            </div>
            <div>
                <span>Max Repeatability p95</span>
                <strong>${formatNumber(
                    result.max_repeatability_p95_distance
                )}</strong>
            </div>
            <div>
                <span>Clear Diagnostic</span>
                <strong>${escapeHtml(result.clear_status ?? "-")}</strong>
            </div>
            <div>
                <span>Max Clear Deviation</span>
                <strong>${formatPercent(result.max_clear_deviation)}</strong>
            </div>
        </div>

        <div class="uniformity-history-detail-table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Point</th>
                        <th>R</th>
                        <th>G</th>
                        <th>B</th>
                        <th>Clear</th>
                        <th>rn</th>
                        <th>gn</th>
                        <th>bn</th>
                        <th>Repeatability p95</th>
                    </tr>
                </thead>
                <tbody>
                    ${pointRows}
                </tbody>
            </table>
        </div>
    `;

    uniformityHistoryDetail.hidden = false;
}


async function refreshUniformityHistory() {
    try {
        if (uniformityHistoryRefreshButton) {
            uniformityHistoryRefreshButton.disabled = true;
        }

        const data = await uniformityRequest(
            "/api/uniformity/history?limit=100"
        );

        const results = data.results || [];

        renderUniformityHistory(results);

        completedNinePointTestCount = Number(
            data.count ?? results.length
        );

        updateUniformityExportButton();
    }
    catch (error) {
        console.error(
            "Nine-point history load error:",
            error
        );

        uniformityHistoryEmpty.hidden = false;
        uniformityHistoryEmpty.textContent =
            `Could not load history: ${error.message}`;
    }
    finally {
        if (uniformityHistoryRefreshButton) {
            uniformityHistoryRefreshButton.disabled = false;
        }
    }
}


uniformityHistoryTable.addEventListener(
    "click",
    event => {
        const button = event.target.closest(
            ".uniformity-history-view-button"
        );

        if (!button) {
            return;
        }

        const index = Number(
            button.dataset.historyIndex
        );

        renderUniformityHistoryDetail(
            uniformityHistory[index]
        );

        uniformityHistoryDetail.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
);


uniformityHistoryRefreshButton.addEventListener(
    "click",
    refreshUniformityHistory
);


// ============================================================
// START TEST
// ============================================================

uniformityStartButton.addEventListener(
    "click",
    async () => {
        const sheetId = (
            uniformitySheetIdInput.value.trim()
            || "SHEET_001"
        );

        try {
            setUniformityBusy(true);

            uniformityStatusText.textContent =
                "Warming white illumination for 8 seconds...";

            uniformityResultText.textContent = "WARMING";
            uniformityResultText.className =
                "uniformity-result waiting";

            const data = await uniformityRequest(
                `/api/uniformity/start/${encodeURIComponent(sheetId)}`,
                {method: "POST"}
            );

            uniformityStatusText.textContent =
                `Active: ${data.session.sheet_id}. `
                + "Move P1 into the measurement window.";

            uniformityResultText.textContent = "ACTIVE";

            colorThresholdValue.textContent = Number(
                data.provisional_thresholds.color
            ).toFixed(3);

            repeatabilityThresholdValue.textContent = Number(
                data.provisional_thresholds.repeatability
            ).toFixed(3);

            uniformityRegionTable.innerHTML = "";

            regionButtons.forEach(button => {
                button.dataset.captured = "false";
                button.classList.remove("captured");
            });

            setUniformityBusy(false);
            uniformityEvaluateButton.disabled = true;
        }
        catch (error) {
            uniformityStatusText.textContent = error.message;
            uniformityResultText.textContent = "ERROR";
            uniformityResultText.className =
                "uniformity-result fail";

            setUniformityBusy(false);
        }
    }
);


// ============================================================
// MEASURE P1-P9
// ============================================================

regionButtons.forEach(button => {
    button.addEventListener(
        "click",
        async () => {
            const regionId = button.dataset.regionId;

            try {
                setUniformityBusy(true);

                uniformityStatusText.textContent =
                    `Measuring ${regionId}: keep the sample still...`;

                const data = await uniformityRequest(
                    `/api/uniformity/region/${regionId}`,
                    {method: "POST"}
                );

                updateRegionRow(data.region);

                button.dataset.captured = "true";
                button.classList.add("captured");

                uniformityStatusText.textContent =
                    `${regionId} captured. Remaining: ${
                        data.remaining_regions.join(", ")
                        || "none"
                    }`;

                setUniformityBusy(false);

                uniformityEvaluateButton.disabled = (
                    data.remaining_regions.length !== 0
                );
            }
            catch (error) {
                uniformityStatusText.textContent = error.message;
                setUniformityBusy(false);
            }
        }
    );
});


// ============================================================
// EVALUATE AND SAVE ONE COMPLETE TEST
// ============================================================

uniformityEvaluateButton.addEventListener(
    "click",
    async () => {
        try {
            setUniformityBusy(true);

            uniformityStatusText.textContent =
                "Evaluating and saving nine-point consistency...";

            const data = await uniformityRequest(
                "/api/uniformity/evaluate",
                {method: "POST"}
            );

            updateCurrentResult(data);

            uniformityStatusText.textContent =
                `Saved nine-point result for ${data.sheet_id}.`;

            setUniformityBusy(false);
            uniformityEvaluateButton.disabled = true;

            await Promise.all([
                refreshUniformityExportInfo(),
                refreshUniformityHistory()
            ]);
        }
        catch (error) {
            uniformityStatusText.textContent = error.message;
            uniformityResultText.textContent = "ERROR";
            uniformityResultText.className =
                "uniformity-result fail";

            setUniformityBusy(false);
        }
    }
);


// ============================================================
// RESET CURRENT TEST
// ============================================================

uniformityResetButton.addEventListener(
    "click",
    async () => {
        try {
            await uniformityRequest(
                "/api/uniformity/reset",
                {method: "POST"}
            );
        }
        catch (error) {
            console.error(error);
        }

        if (
            typeof window.clearHardwareOutputDisplay
            === "function"
        ) {
            window.clearHardwareOutputDisplay();
        }

        resetUniformityDisplay();
        uniformityStartButton.disabled = false;
        uniformityResetButton.disabled = false;
    }
);


// ============================================================
// EXPORT ALL COMPLETED NINE-POINT TESTS
// ============================================================

async function refreshUniformityExportInfo() {
    try {
        const data = await uniformityRequest(
            "/api/uniformity/export-info"
        );

        completedNinePointTestCount = Number(
            data.test_count || 0
        );
    }
    catch (error) {
        console.error(
            "Nine-point export info error:",
            error
        );

        completedNinePointTestCount = 0;
    }

    updateUniformityExportButton();
}


uniformityExportButton.addEventListener(
    "click",
    async () => {
        if (completedNinePointTestCount === 0) {
            return;
        }

        try {
            setUniformityBusy(true);
            uniformityStatusText.textContent =
                "Preparing all completed nine-point tests...";

            const response = await fetch(
                "/api/uniformity/export.csv",
                {cache: "no-store"}
            );

            if (!response.ok) {
                let message = `HTTP ${response.status}`;

                try {
                    const data = await response.json();
                    message = data.detail || message;
                }
                catch (error) {
                    // Keep the HTTP status message.
                }

                throw new Error(message);
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");

            link.href = url;
            link.download = getDownloadFilename(response);

            document.body.appendChild(link);
            link.click();
            link.remove();

            URL.revokeObjectURL(url);

            uniformityStatusText.textContent =
                `Exported all ${completedNinePointTestCount} `
                + "completed nine-point test(s).";
        }
        catch (error) {
            console.error(
                "Nine-point CSV export error:",
                error
            );

            uniformityStatusText.textContent =
                `CSV export failed: ${error.message}`;
        }
        finally {
            setUniformityBusy(false);
            uniformityEvaluateButton.disabled = true;
        }
    }
);


// ============================================================
// INITIALISE
// ============================================================

async function initialiseUniformityPage() {
    resetUniformityDisplay();
    uniformityStartButton.disabled = false;
    uniformityResetButton.disabled = false;

    await Promise.all([
        loadUniformitySettings(),
        refreshUniformityExportInfo(),
        refreshUniformityHistory()
    ]);
}


initialiseUniformityPage();
