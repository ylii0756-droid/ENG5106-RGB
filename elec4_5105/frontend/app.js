console.log("ENG5105 RGB app.js loaded");


// ============================================================
// UI ELEMENTS
// ============================================================

const redValue = document.getElementById("red-value");
const greenValue = document.getElementById("green-value");
const blueValue = document.getElementById("blue-value");
const clearValue = document.getElementById("clear-value");

const sampleColour = document.getElementById("sample-colour");

const referenceR = document.getElementById("reference-r");
const referenceG = document.getElementById("reference-g");
const referenceB = document.getElementById("reference-b");
const referenceColour = document.getElementById("reference-colour");

const referenceStatus = document.getElementById("reference-status");
const calibrationStatus = document.getElementById("calibration-status");

const resultText = document.getElementById("result-text");
const resultDescription = document.getElementById("result-description");

const distanceValue = document.getElementById("distance-value");
const distanceProgress = document.getElementById("distance-progress");

const thresholdValue = document.getElementById("threshold-value");
const thresholdInput = document.getElementById("threshold-input");

const sampleCount = document.getElementById("sample-count");
const meanDistance = document.getElementById("mean-distance");
const stdValue = document.getElementById("std-value");
const stabilityValue = document.getElementById("stability-value");

const sampleIdInput = document.getElementById("sample-id-input");
const samplingCountInput = document.getElementById("sampling-count-input");

const historyTable = document.getElementById("history-table");

const setReferenceButton = document.getElementById("set-reference-button");
const measureButton = document.getElementById("measure-button");
const exportButton = document.getElementById("export-button");

const greenLedIndicator = document.getElementById(
    "green-led-indicator"
);
const redLedIndicator = document.getElementById(
    "red-led-indicator"
);
const buzzerIndicator = document.getElementById(
    "buzzer-indicator"
);

const greenLedState = document.getElementById(
    "green-led-state"
);
const redLedState = document.getElementById(
    "red-led-state"
);
const buzzerState = document.getElementById(
    "buzzer-state"
);

const hardwareOutputMessage = document.getElementById(
    "hardware-output-message"
);


// ============================================================
// BACKEND API
// ============================================================

const API_BASE = "";


// ============================================================
// SYSTEM STATE
// ============================================================

let reference = null;

let measurementHistory = [];

let measurementIntervalMs = 100;

let liveUpdateIntervalMs = 500;

let liveUpdateTimer = null;

let resultIndicationSeconds = 2.0;
let hardwareOutputTimer = null;


// ============================================================
// BASIC UTILITIES
// ============================================================

function sleep(ms) {

    return new Promise(
        resolve => setTimeout(
            resolve,
            ms
        )
    );

}


function calculateMean(values) {

    if (values.length === 0) {
        return 0;
    }

    return (
        values.reduce(
            (sum, value) =>
                sum + value,
            0
        ) / values.length
    );

}


// ============================================================
// PHYSICAL OUTPUT DISPLAY
// ============================================================

function setHardwareOutputCard(
    card,
    stateElement,
    enabled
) {

    if (!card || !stateElement) {
        return;
    }

    card.classList.toggle(
        "active",
        enabled
    );

    stateElement.textContent =
        enabled ? "ON" : "OFF";

}


function resetHardwareOutputCards() {

    setHardwareOutputCard(
        greenLedIndicator,
        greenLedState,
        false
    );

    setHardwareOutputCard(
        redLedIndicator,
        redLedState,
        false
    );

    setHardwareOutputCard(
        buzzerIndicator,
        buzzerState,
        false
    );

    if (hardwareOutputMessage) {
        hardwareOutputMessage.textContent =
            "Outputs are off";
    }

}


window.showHardwareOutput = function(
    status,
    durationSeconds = resultIndicationSeconds
) {

    if (hardwareOutputTimer !== null) {
        clearTimeout(
            hardwareOutputTimer
        );
    }

    resetHardwareOutputCards();

    if (status === "PASS") {

        setHardwareOutputCard(
            greenLedIndicator,
            greenLedState,
            true
        );

        if (hardwareOutputMessage) {
            hardwareOutputMessage.textContent =
                `PASS: green LED on for ${Number(durationSeconds).toFixed(1)} s`;
        }

    }

    else if (status === "FAIL") {

        setHardwareOutputCard(
            redLedIndicator,
            redLedState,
            true
        );

        setHardwareOutputCard(
            buzzerIndicator,
            buzzerState,
            true
        );

        if (hardwareOutputMessage) {
            hardwareOutputMessage.textContent =
                `FAIL: red LED and buzzer on for ${Number(durationSeconds).toFixed(1)} s`;
        }

    }

    else {
        return;
    }

    hardwareOutputTimer = setTimeout(
        () => {
            resetHardwareOutputCards();
            hardwareOutputTimer = null;
        },
        Math.max(
            0,
            Number(durationSeconds) * 1000
        )
    );

};


window.clearHardwareOutputDisplay = function() {

    if (hardwareOutputTimer !== null) {
        clearTimeout(
            hardwareOutputTimer
        );

        hardwareOutputTimer = null;
    }

    resetHardwareOutputCards();

};


// ============================================================
// UPDATE LIVE DISPLAY
// ============================================================

function updateLiveDisplay(reading) {

    redValue.textContent =
        reading.r;

    greenValue.textContent =
        reading.g;

    blueValue.textContent =
        reading.b;

    clearValue.textContent =
        reading.clear ?? "-";


    sampleColour.style.background =
        `rgb(
            ${reading.r},
            ${reading.g},
            ${reading.b}
        )`;

}


// ============================================================
// LOAD SETTINGS
// ============================================================

async function loadSystemSettings() {

    try {

        const response = await fetch(
            `${API_BASE}/api/settings`
        );

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }

        const settings =
            await response.json();


        // The single-point reference threshold is still shown
        // in the Decision Gate. The editable nine-point threshold
        // is managed independently by uniformity.js.
        if (thresholdInput) {
            thresholdInput.value =
                settings.threshold;

            thresholdInput.readOnly = true;
        }

        if (thresholdValue) {
            thresholdValue.textContent =
                Number(
                    settings.threshold
                ).toFixed(3);
        }


        if (
            settings.sampling_count !== undefined
        ) {

            if (samplingCountInput) {
                samplingCountInput.value =
                    settings.sampling_count;
            }

        }


        if (
            settings.measurement_interval_ms !== undefined
        ) {

            measurementIntervalMs =
                settings.measurement_interval_ms;

        }


        if (
            settings.live_update_interval_ms !== undefined
        ) {

            liveUpdateIntervalMs =
                settings.live_update_interval_ms;

        }


        if (
            settings.result_indication_seconds !== undefined
        ) {

            resultIndicationSeconds = Number(
                settings.result_indication_seconds
            );

        }

    }

    catch (error) {

        console.error(
            "Settings load error:",
            error
        );

    }

}


// ============================================================
// LIVE SENSOR
// ============================================================

async function fetchLiveSensorData() {

    try {

        const response = await fetch(
            `${API_BASE}/api/live`
        );

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }

        const data =
            await response.json();

        updateLiveDisplay(
            data.color
        );

        updateSensorConnectionStatus(
            true
        );

    }

    catch (error) {

        console.error(
            "Live sensor error:",
            error
        );

        updateSensorConnectionStatus(
            false
        );

    }

}


// ============================================================
// SENSOR STATUS
// ============================================================

function updateSensorConnectionStatus(
    connected
) {

    const sensorStatus =
        document.querySelector(
            ".system-status .status-item:first-child"
        );

    if (!sensorStatus) {
        return;
    }


    const dot =
        sensorStatus.querySelector(
            ".status-dot"
        );

    const text =
        sensorStatus.querySelector(
            "span:last-child"
        );


    if (connected) {

        dot.className =
            "status-dot status-ok";

        text.textContent =
            "Sensor Connected";

    }

    else {

        dot.className =
            "status-dot status-error";

        text.textContent =
            "Sensor Disconnected";

    }

}


// ============================================================
// LOAD EXISTING REFERENCE
// ============================================================

async function loadReference() {

    try {

        const response = await fetch(
            `${API_BASE}/api/reference`
        );

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }

        const data =
            await response.json();

        reference =
            data.reference;


        if (reference) {

            updateReferenceDisplay();

            referenceStatus.textContent =
                "Reference Valid";

            calibrationStatus.textContent =
                "Calibrated";

            setReferenceButton.textContent =
                "Recalibrate Reference";

            resultText.textContent =
                "READY";

            resultText.className =
                "result-text waiting";

            resultDescription.textContent =
                "Reference loaded. The system is ready for sample inspection.";

        }

        else {

            referenceStatus.textContent =
                "No Reference";

            calibrationStatus.textContent =
                "Not Calibrated";

        }

    }

    catch (error) {

        console.error(
            "Reference load error:",
            error
        );

        referenceStatus.textContent =
            "Reference Error";

    }

}


// ============================================================
// SET REFERENCE
// ============================================================

setReferenceButton.addEventListener(
    "click",
    async () => {

        try {

            setReferenceButton.disabled =
                true;

            setReferenceButton.textContent =
                "Calibrating...";

            calibrationStatus.textContent =
                "Calibrating";


            const calibrationReadings = [];


            const calibrationSamples =
                parseInt(
                    samplingCountInput?.value || "20"
                ) || 20;


            // ----------------------------------------
            // READ SENSOR MULTIPLE TIMES
            // ----------------------------------------

            for (
                let i = 0;
                i < calibrationSamples;
                i++
            ) {

                const response = await fetch(
                    `${API_BASE}/api/live`
                );


                if (!response.ok) {

                    throw new Error(
                        `Sensor request failed: HTTP ${response.status}`
                    );

                }


                const data =
                    await response.json();


                calibrationReadings.push(
                    data.color
                );


                updateLiveDisplay(
                    data.color
                );


                calibrationStatus.textContent =
                    `Calibrating ${i + 1} / ${calibrationSamples}`;


                await sleep(
                    measurementIntervalMs
                );

            }


            // ----------------------------------------
            // AVERAGE REFERENCE
            // ----------------------------------------

            const averagedReference = {

                r: Math.round(
                    calculateMean(
                        calibrationReadings.map(
                            item => item.r
                        )
                    )
                ),

                g: Math.round(
                    calculateMean(
                        calibrationReadings.map(
                            item => item.g
                        )
                    )
                ),

                b: Math.round(
                    calculateMean(
                        calibrationReadings.map(
                            item => item.b
                        )
                    )
                ),

                clear: Math.round(
                    calculateMean(
                        calibrationReadings.map(
                            item => item.clear
                        )
                    )
                )

            };


            // ----------------------------------------
            // SAVE REFERENCE TO BACKEND
            // ----------------------------------------

            const saveResponse = await fetch(
                `${API_BASE}/api/reference`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        averagedReference
                    )
                }
            );


            if (!saveResponse.ok) {

                const errorData =
                    await saveResponse.json();

                throw new Error(
                    errorData.detail ||
                    `HTTP ${saveResponse.status}`
                );

            }


            const savedData =
                await saveResponse.json();


            reference =
                savedData.reference;


            updateReferenceDisplay();


            referenceStatus.textContent =
                "Reference Valid";

            calibrationStatus.textContent =
                "Calibrated";

            setReferenceButton.textContent =
                "Recalibrate Reference";


            resultText.textContent =
                "READY";

            resultText.className =
                "result-text waiting";

            resultDescription.textContent =
                "Reference locked. The system is ready for sample inspection.";

        }

        catch (error) {

            console.error(
                "Reference calibration error:",
                error
            );


            calibrationStatus.textContent =
                "Calibration failed";

            referenceStatus.textContent =
                "Reference Error";


            resultText.textContent =
                "ERROR";

            resultText.className =
                "result-text fail";

            resultDescription.textContent =
                "Reference calibration failed. Check the sensor connection.";

        }

        finally {

            setReferenceButton.disabled =
                false;


            if (
                calibrationStatus.textContent ===
                "Calibrated"
            ) {

                setReferenceButton.textContent =
                    "Recalibrate Reference";

            }

            else {

                setReferenceButton.textContent =
                    "Set Reference";

            }

        }

    }
);


// ============================================================
// UPDATE REFERENCE DISPLAY
// ============================================================

function updateReferenceDisplay() {

    if (!reference) {
        return;
    }


    referenceR.textContent =
        reference.r;

    referenceG.textContent =
        reference.g;

    referenceB.textContent =
        reference.b;


    referenceColour.style.background =
        `rgb(
            ${reference.r},
            ${reference.g},
            ${reference.b}
        )`;

}


// ============================================================
// MEASURE SAMPLE
// ============================================================

measureButton.addEventListener(
    "click",
    async () => {

        if (!reference) {

            resultText.textContent =
                "NO REF";

            resultText.className =
                "result-text fail";

            resultDescription.textContent =
                "Please calibrate a reference colour before inspection.";

            return;

        }


        try {

            measureButton.disabled =
                true;

            measureButton.textContent =
                "Measuring...";


            const sampleId =
                sampleIdInput?.value ||
                "S001";


            // Backend performs:
            // sensor read
            // normalisation
            // ΔRGB
            // PASS / FAIL
            // CSV storage

            const response = await fetch(
                `${API_BASE}/api/measure/${encodeURIComponent(sampleId)}`,
                {
                    method: "POST"
                }
            );


            if (!response.ok) {

                const errorData =
                    await response.json();

                throw new Error(
                    errorData.detail ||
                    `HTTP ${response.status}`
                );

            }


            const data =
                await response.json();


            updateLiveDisplay(
                data.color
            );


            updateResult(
                data.difference,
                data.threshold,
                data.status
            );


            await loadHistory();


            incrementSampleId();

        }

        catch (error) {

            console.error(
                "Measurement error:",
                error
            );


            resultText.textContent =
                "ERROR";

            resultText.className =
                "result-text fail";

            resultDescription.textContent =
                "Measurement failed. Check the sensor and backend.";

        }

        finally {

            measureButton.disabled =
                false;

            measureButton.textContent =
                "Measure Sample";

        }

    }
);


// ============================================================
// UPDATE RESULT
// ============================================================

function updateResult(
    distance,
    threshold,
    status
) {

    thresholdValue.textContent =
        Number(
            threshold
        ).toFixed(3);


    distanceValue.textContent =
        Number(
            distance
        ).toFixed(4);


    let progressPercent = 0;


    if (threshold > 0) {

        progressPercent =
            Math.min(
                (distance / threshold) * 100,
                100
            );

    }


    distanceProgress.style.width =
        `${progressPercent}%`;


    if (status === "PASS") {

        resultText.textContent =
            "PASS";

        resultText.className =
            "result-text pass";

        resultDescription.textContent =
            "Color difference is within the production threshold.";

        distanceProgress.style.background =
            "#2dbb67";

    }

    else {

        resultText.textContent =
            "FAIL";

        resultText.className =
            "result-text fail";

        resultDescription.textContent =
            "Color difference exceeds the production threshold.";

        distanceProgress.style.background =
            "#e5484d";

    }


    if (typeof window.showHardwareOutput === "function") {
        window.showHardwareOutput(status);
    }


    // Current backend measure endpoint
    // performs one sensor measurement.

    if (sampleCount) {
        sampleCount.textContent = "1";
    }

    if (meanDistance) {
        meanDistance.textContent =
            Number(distance).toFixed(4);
    }

    if (stdValue) {
        stdValue.textContent = "-";
    }

    if (stabilityValue) {
        stabilityValue.textContent = "-";
    }

}


// ============================================================
// LOAD HISTORY FROM BACKEND
// ============================================================

async function loadHistory() {

    // The legacy single-point history panel may be removed from
    // the page. In that case there is nothing to load or render.
    if (!historyTable) {
        measurementHistory = [];
        return;
    }

    try {

        const response = await fetch(
            `${API_BASE}/api/history?limit=10`
        );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        measurementHistory =
            data.measurements;


        updateHistoryTable();

    }

    catch (error) {

        console.error(
            "History load error:",
            error
        );

    }

}


// ============================================================
// HISTORY TABLE
// ============================================================

function updateHistoryTable() {

    if (!historyTable) {
        return;
    }

    historyTable.innerHTML =
        "";


    measurementHistory.forEach(
        record => {

            const row =
                document.createElement(
                    "tr"
                );


            row.innerHTML = `

                <td>
                    ${record.sample_id}
                </td>

                <td>
                    ${record.timestamp}
                </td>

                <td>
                    ${record.r}
                </td>

                <td>
                    ${record.g}
                </td>

                <td>
                    ${record.b}
                </td>

                <td>
                    ${Number(record.distance).toFixed(4)}
                </td>

                <td>
                    ${Number(record.threshold).toFixed(3)}
                </td>

                <td>
                    <strong
                        style="
                            color:
                            ${
                                record.result === "PASS"
                                    ? "#2dbb67"
                                    : "#e5484d"
                            };
                        "
                    >
                        ${record.result}
                    </strong>
                </td>

            `;


            historyTable.appendChild(
                row
            );

        }
    );

}


// ============================================================
// SAMPLE ID AUTO INCREMENT
// ============================================================

function incrementSampleId() {

    if (!sampleIdInput) {
        return;
    }

    const current =
        sampleIdInput.value;


    const match =
        current.match(
            /^([A-Za-z]*)(\d+)$/
        );


    if (!match) {
        return;
    }


    const prefix =
        match[1];


    const number =
        parseInt(
            match[2]
        );


    const digits =
        match[2].length;


    sampleIdInput.value =
        prefix +
        String(
            number + 1
        ).padStart(
            digits,
            "0"
        );

}


// ============================================================
// EXPORT CSV
// ============================================================

if (exportButton) {
exportButton.addEventListener(
    "click",
    () => {

        if (
            measurementHistory.length === 0
        ) {

            alert(
                "No inspection data available."
            );

            return;

        }


        const header = [
            "Sample",
            "Timestamp",
            "R",
            "G",
            "B",
            "Clear",
            "Distance",
            "Threshold",
            "Result"
        ];


        const rows =
            measurementHistory.map(
                item => [

                    item.sample_id,

                    item.timestamp,

                    item.r,

                    item.g,

                    item.b,

                    item.clear ?? "",

                    Number(
                        item.distance
                    ).toFixed(4),

                    Number(
                        item.threshold
                    ).toFixed(3),

                    item.result

                ]
            );


        const csv =
            [
                header,
                ...rows
            ]
            .map(
                row =>
                    row.join(",")
            )
            .join("\n");


        const blob =
            new Blob(
                [csv],
                {
                    type:
                        "text/csv;charset=utf-8;"
                }
            );


        const url =
            URL.createObjectURL(
                blob
            );


        const link =
            document.createElement(
                "a"
            );


        link.href =
            url;

        link.download =
            "inspection_history.csv";


        link.click();


        URL.revokeObjectURL(
            url
        );

    }
);
}



// ============================================================
// START APPLICATION
// ============================================================

async function startApplication() {

    await loadSystemSettings();

    await loadReference();

    await loadHistory();

    await fetchLiveSensorData();


    if (liveUpdateTimer !== null) {

        clearInterval(
            liveUpdateTimer
        );

    }


    liveUpdateTimer =
        setInterval(
            fetchLiveSensorData,
            liveUpdateIntervalMs
        );

}


startApplication();