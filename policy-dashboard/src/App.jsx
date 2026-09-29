import { useEffect, useMemo, useState } from "react";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";
import "./App.css";

ChartJS.register(ArcElement, Tooltip, Legend);

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";


function DatasetEvaluationPage({ onBack }) {
  const [dataset, setDataset] = useState(null);
  const [startRecord, setStartRecord] = useState(1);
  const [endRecord, setEndRecord] = useState(1000);
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/dataset/info`)
      .then((res) => res.json())
      .then((data) => setDataset(data));
  }, []);

  const runBatch = async () => {
  if (!dataset) return;

  if (
    startRecord < 1 ||
    endRecord > dataset.total_records ||
    startRecord > endRecord
  ) {
    alert("Invalid record range");
    return;
  }

  setLoading(true);

  try {
    const response = await fetch(
      `${API}/api/dataset/evaluate?start_record=${startRecord}&end_record=${endRecord}`,
      {
        method: "POST",
      }
    );

    const data = await response.json();

    if (!response.ok || data.error) {
      throw new Error(data.error || "Batch evaluation failed");
    }

    setBatch({
      executionId: data.execution_id,
      batchNumber: data.batch_number,
      startRecord: data.start_record,
      endRecord: data.end_record,
      recordsEvaluated: data.records_evaluated,
    });

  } catch (error) {
    console.error(error);
    alert(error.message);
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="dataset-page">

      <button className="back-button" onClick={onBack}>
        ← Back to Dashboard
      </button>

      <div className="dataset-header">
        <h1>DATASET EVALUATION</h1>
        <p>Select a dataset and choose the records to evaluate.</p>
      </div>

      <section className="dataset-card">

        <h3>Dataset</h3>

        {dataset ? (
          <div className="dataset-info">
            <strong>{dataset.filename}</strong>
            <span>
              {dataset.total_records.toLocaleString()} records
            </span>
          </div>
        ) : (
          <p>Loading dataset...</p>
        )}

        <h3 className="range-title">Record Range</h3>

        <div className="range-grid">

          <div>
            <label>Start Record</label>
            <input
              type="number"
              min="1"
              max={dataset?.total_records || 1}
              value={startRecord}
              onChange={(e) => setStartRecord(Number(e.target.value))}
            />
          </div>

          <div>
            <label>End Record</label>
            <input
              type="number"
              min="1"
              max={dataset?.total_records || 1}
              value={endRecord}
              onChange={(e) => setEndRecord(Number(e.target.value))}
            />
          </div>

        </div>

        <button
          className="run-batch-button"
          onClick={runBatch}
          disabled={loading || !dataset}
        >
          {loading ? "Running..." : "Run Batch"}
        </button>

      </section>

      {batch && (
        <section className="batch-result-card">

          <div className="batch-title">
            <span>Batch {batch.batchNumber}</span>
          </div>

          <h2>
            Records {batch.startRecord.toLocaleString()} –{" "}
            {batch.endRecord.toLocaleString()}
          </h2>

          <p>
            {batch.recordsEvaluated.toLocaleString()} records selected
          </p>

        </section>
      )}

    </div>
  );
}



function App() {
  const [page, setPage] = useState("dashboard");

  const [df, setDf] = useState([]);
  const [filter, setFilter] = useState("PASS");

  const [selectedId, setSelectedId] = useState(null);
  const [selectedDetails, setSelectedDetails] = useState(null);

  const [selectedExecutionId, setSelectedExecutionId] =
    useState(null);

  const [showHistory, setShowHistory] = useState(false);

  const [executions, setExecutions] = useState([]);
  const [policyRules, setPolicyRules] = useState([]);
  const [definitions, setDefinitions] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState(null);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  /* =========================================================
     LOAD DATA
  ========================================================= */

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async (executionId = null) => {

  try {

    setLoading(true);
    setError("");

    const executionsResponse =
      await fetch(
        `${API}/api/executions`
      );

    if (!executionsResponse.ok) {
      throw new Error(
        "Could not load execution history"
      );
    }

    const executionsData =
      await executionsResponse.json();

    /*
     * Use the exact same execution
     * that the dashboard uses.
     */
    const activeExecutionId =
      executionId ||
      executionsData[0]?.id ||
      null;

    const evaluationsUrl =
      activeExecutionId
        ? `${API}/api/evaluations?execution_id=${activeExecutionId}`
        : `${API}/api/evaluations`;

    const pipelineUrl =
      activeExecutionId
        ? `${API}/api/pipeline-status?execution_id=${activeExecutionId}`
        : `${API}/api/pipeline-status`;


    const [
      evaluationsResponse,
      rulesResponse,
      definitionsResponse,
      pipelineResponse,
    ] = await Promise.all([

      fetch(evaluationsUrl),

      fetch(
        `${API}/api/rules`
      ),

      fetch(
        `${API}/api/policy/definitions`
      ),

      fetch(pipelineUrl),
    ]);


    if (!evaluationsResponse.ok) {

      throw new Error(
        "Could not load evaluations from API"
      );

    }

    if (!rulesResponse.ok) {

      throw new Error(
        "Could not load policy rules"
      );

    }

    if (!definitionsResponse.ok) {

      throw new Error(
        "Could not load policy definitions"
      );

    }

    if (!pipelineResponse.ok) {

      throw new Error(
        "Could not load pipeline status"
      );

    }


    const evaluations =
      await evaluationsResponse.json();

    const rulesData =
      await rulesResponse.json();

    const definitionsData =
      await definitionsResponse.json();

    const pipelineData =
      await pipelineResponse.json();


    const formatted =
      evaluations.map((row) => ({

        ...row,

        record_id:
          row.record_id,

        decision: String(
          row.decision ??
          row.expected_outcome ??
          ""
        )
          .trim()
          .toUpperCase(),

        expected_outcome: String(
          row.decision ??
          ""
        )
          .trim()
          .toUpperCase(),

        expected_rule_triggers:
          row.triggered_rules || "",

        expected_reason:
          row.reason || "",

        suggested_remediation:
          row.remediation || "",
      }));


    setDf(formatted);

    setExecutions(
      executionsData
    );

    setPolicyRules(
      rulesData
    );

    setDefinitions(
      definitionsData
    );

    setPipelineStatus(
      pipelineData
    );


    if (formatted.length > 0) {

      setSelectedId(
        formatted[0].record_id
      );

      loadSelectedRecord(
        formatted[0].record_id
      );

    }


    setSelectedExecutionId(
      activeExecutionId
    );


  } catch (err) {

    console.error(err);

    setError(
      `${err.message}. Make sure the FastAPI backend is running.`
    );

  } finally {

    setLoading(false);

  }
};


  /* =========================================================
     SELECTED RECORD
  ========================================================= */

  const loadSelectedRecord = async (
    recordId,
    executionId
  ) => {
    try {
      const response = await fetch(
        `${API}/api/evaluations/${recordId}?execution_id=${executionId}`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load record details"
        );
      }

      const data = await response.json();

      if (!data.error) {
        setSelectedDetails(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectRecord = (recordId) => {
  setSelectedId(recordId);
  loadSelectedRecord(
    recordId,
    selectedExecutionId
  );
};

  /* =========================================================
     CURRENT EXECUTION
  ========================================================= */

  const currentExecution = useMemo(() => {
    if (!executions.length) {
      return null;
    }

    if (selectedExecutionId !== null) {
      const selected = executions.find(
        (execution) =>
          Number(execution.id) ===
          Number(selectedExecutionId)
      );

      if (selected) {
        return selected;
      }
    }

    return executions[0];
  }, [
    executions,
    selectedExecutionId,
  ]);

  /* =========================================================
     OUTCOME COUNTS
     
     IMPORTANT:
     These are calculated from the records currently loaded.
     Therefore historical runs also display their own counts.
  ========================================================= */

  const total = df.length;

  const passed = useMemo(
    () =>
      df.filter(
        (record) =>
          String(record.decision)
            .trim()
            .toUpperCase() === "PASS"
      ).length,
    [df]
  );

  const flagged = useMemo(
    () =>
      df.filter(
        (record) =>
          String(record.decision)
            .trim()
            .toUpperCase() === "FLAG"
      ).length,
    [df]
  );

  const blocked = useMemo(
    () =>
      df.filter(
        (record) =>
          String(record.decision)
            .trim()
            .toUpperCase() === "BLOCK"
      ).length,
    [df]
  );

  const passRate = total
    ? ((passed / total) * 100).toFixed(1)
    : "0.0";

  /* =========================================================
     FILTER
   
     IMPORTANT:
     Uses record.decision directly.
     PASS can NEVER contain FLAG/BLOCK records.
  ========================================================= */

  const filteredData = useMemo(() => {
    const status = String(filter).trim().toUpperCase();

    return df.filter((record) => {
      const decision = String(
        record.decision ?? record.expected_outcome ?? ""
      )
        .trim()
        .toUpperCase();

      return decision === status;
    });
  }, [df, filter]);

  /* =========================================================
     SELECTED RECORD OBJECT
  ========================================================= */

  const selectedRecord = useMemo(
  () =>
    filteredData.find(
      (record) =>
        String(record.record_id) ===
        String(selectedId)
    ),
  [filteredData, selectedId]
);

  useEffect(() => {
    if (filteredData.length === 0) {
      setSelectedId(null);
      setSelectedDetails(null);
      return;
    }

    const stillVisible = filteredData.some(
      (record) =>
        String(record.record_id) === String(selectedId)
    );

    if (!stillVisible) {
      const firstRecord = filteredData[0];
      setSelectedId(firstRecord.record_id);
      loadSelectedRecord(
  firstRecord.record_id,
  selectedExecutionId
);
    }
  }, [filter, filteredData]);

  /* =========================================================
     BATCH PROGRESS
  ========================================================= */

  const batchProgress = currentExecution
    ? currentExecution.completed_at
      ? 100
      : 0
    : 0;

  /* =========================================================
     PIE CHART
  ========================================================= */

  const pieData = {
    labels: [
      "PASS",
      "FLAG",
      "BLOCK",
    ],

    datasets: [
      {
        data: [
          passed,
          flagged,
          blocked,
        ],

        backgroundColor: [
          "#22c55e",
          "#f97316",
          "#ef4444",
        ],

        borderWidth: 0,
      },
    ],
  };

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,

    plugins: {
      legend: {
        position: "bottom",

        labels: {
          padding: 18,
          usePointStyle: true,
          pointStyle: "circle",
        },
      },

      tooltip: {
        callbacks: {
          label: function (context) {
            const chartTotal =
              context.dataset.data.reduce(
                (sum, value) =>
                  sum + value,
                0
              );

            const percentage =
              chartTotal
                ? (
                    (context.raw /
                      chartTotal) *
                    100
                  ).toFixed(1)
                : 0;

            return `${context.label}: ${context.raw} (${percentage}%)`;
          },
        },
      },
    },
  };

  /* =========================================================
     HELPERS
  ========================================================= */

  const getOutcomeClass = (outcome) => {
    const value = String(
      outcome || ""
    )
      .trim()
      .toUpperCase();

    if (value === "PASS") {
      return "pass";
    }

    if (value === "FLAG") {
      return "flag";
    }

    return "block";
  };

  const getIcon = (outcome) => {
    const value = String(
      outcome || ""
    )
      .trim()
      .toUpperCase();

    if (value === "PASS") {
      return "✓";
    }

    if (value === "FLAG") {
      return "⚠";
    }

    return "✕";
  };

  const formatLines = (text) => {
    if (!text) {
      return [];
    }

    return String(text)
      .split(";")
      .map((item) => item.trim())
      .filter(Boolean);
  };

  const formatDateTime = (value) => {
    if (!value) {
      return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString();
  };

  const formatFieldName = (field) => {
    return String(field)
      .replaceAll("_", " ")
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase()
      );
  };

  const getRuleDescription = (ruleId) => {
    const rule = policyRules.find(
      (item) =>
        item.rule_id === ruleId
    );

    return (
      rule?.description ||
      "Policy condition detected"
    );
  };

  const getRuleOutcome = (ruleId) => {
    const rule = policyRules.find(
      (item) =>
        item.rule_id === ruleId
    );

    return rule?.outcome || "—";
  };

  const inputData =
    selectedDetails?.input_data || {};

  const inputFields =
    Object.keys(inputData);

  const triggeredRules =
    formatLines(
      selectedRecord?.expected_rule_triggers
    );

  /* =========================================================
     LOADING
  ========================================================= */
  if (page === "dataset") {
  return (
    <DatasetEvaluationPage
      onBack={() => setPage("dashboard")}
    />
  );
}
  if (loading) {
    return (
      <div className="error-page">
        <h2>
          Loading dashboard...
        </h2>
      </div>
    );
  }

  /* =========================================================
     ERROR
  ========================================================= */

  if (error) {
    return (
      <div className="error-page">
        <h2>
          Unable to load dashboard
        </h2>

        <p>{error}</p>

        <button
          onClick={() => loadData()}
          className="filter-button active"
        >
          Retry
        </button>
      </div>
    );
  }

  /* =========================================================
     MAIN UI
  ========================================================= */

  return (
    <div className="app">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="header">

        <div className="header-left">

          <div className="breadcrumb">
            Evaluations
            {" / "}
            {currentExecution
              ? `Run #${currentExecution.id}`
              : "Run"}
          </div>

          <h1>
            Policy Evaluation Results
          </h1>

          <p>
            {total} records evaluated
          </p>

        </div>

      <div className="evaluation-header-actions">

  <div className="run-info">
    <span className="run-label">
      RUN DATE & TIME
    </span>

    <strong className="run-datetime">
      {currentExecution
        ? formatDateTime(
            currentExecution.started_at
          )
        : "—"}
    </strong>
  </div>

  <div className="header-actions-row">

    <button
      className="header-action-btn primary"
      onClick={() => setPage("dataset")}
    >
      Dataset Evaluation
    </button>

    <button
      className="header-action-btn"
      onClick={() => setShowHistory(true)}
    >
      Evaluation History
    </button>

  </div>

</div>

      </header>


      {/* =====================================================
          EXECUTION OVERVIEW
      ===================================================== */}

      <section className="execution-overview">

        <div className="execution-overview-header">

          <div>

            <span className="section-eyebrow">
              EXECUTION
            </span>

            <h2>
              Execution #
              {currentExecution?.id || "—"}
            </h2>

            <p>
              {currentExecution?.total_records ||
                total}{" "}
              records processed across{" "}
              {currentExecution?.total_batches ||
                0}{" "}
              batches.
            </p>

          </div>

          <div className="execution-status">
            <span className="status-pulse"></span>
            COMPLETED
          </div>

        </div>


        <div className="execution-metrics">

          <div className="execution-metric primary">

            <div className="metric-icon">
              ◎
            </div>

            <div>
              <span>
                RECORDS EVALUATED
              </span>

              <strong>
                {currentExecution?.total_records ||
                  total}
              </strong>
            </div>

          </div>


          <div className="execution-metric">

            <div className="metric-icon">
              ▦
            </div>

            <div>
              <span>
                BATCH SIZE
              </span>

              <strong>
                {currentExecution?.batch_size ||
                  "—"}
              </strong>

              <small>
                records / batch
              </small>
            </div>

          </div>


          <div className="execution-metric">

            <div className="metric-icon">
              ◫
            </div>

            <div>
              <span>
                BATCHES PROCESSED
              </span>

              <strong>
                {currentExecution?.total_batches ||
                  "—"}
              </strong>

              <small>
                total batches
              </small>
            </div>

          </div>


          <div className="execution-metric">

            <div className="metric-icon">
              ◷
            </div>

            <div>
              <span>
                STARTED
              </span>

              <strong className="date-value">
                {currentExecution
                  ? formatDateTime(
                      currentExecution.started_at
                    )
                  : "—"}
              </strong>
            </div>

          </div>

        </div>


        {/* BATCH PROGRESS */}

        {currentExecution && (
          <div className="batch-progress">

            <div className="batch-progress-header">

              <div>

                <span>
                  BATCH PROCESSING
                </span>

                <strong>
                  {
                    currentExecution.total_records
                  }{" "}
                  records
                  {" · "}
                  {
                    currentExecution.total_batches
                  }{" "}
                  batches
                </strong>

              </div>

              <strong>
                {batchProgress}%
              </strong>

            </div>


            <div className="progress-track">

              <div
                className="progress-fill"
                style={{
                  width: `${batchProgress}%`,
                }}
              />

            </div>


            <div className="batch-labels">

              <span>
                {
                  currentExecution.total_batches
                }{" "}
                batches processed
              </span>

              <span>
                {
                  currentExecution.batch_size
                }{" "}
                records / batch
              </span>

            </div>

          </div>
        )}

      </section>

      <section className="pipeline-validation">

  <div className="pipeline-validation-header">

    <div>

      <span className="section-eyebrow">
        PIPELINE VALIDATION
      </span>

      <h2>
        Policy-as-Code Pipeline
      </h2>

      <p>
        End-to-end validation of policy processing and evaluation.
      </p>

    </div>

    <div
      className={
        `pipeline-complete ${
          pipelineStatus?.summary?.completed_layers ===
          pipelineStatus?.summary?.pipeline_layers
            ? "pipeline-complete-success"
            : "pipeline-complete-warning"
        }`
      }
    >

      {pipelineStatus
        ? `${pipelineStatus.summary.completed_layers}/${pipelineStatus.summary.pipeline_layers} LAYERS PASSED`
        : "LOADING..."}

    </div>

  </div>


  <div className="pipeline-layers">

    {[
      [
        "pdf_extraction",
        "PDF Extraction"
      ],

      [
        "policy_json_generation",
        "Policy JSON Generation"
      ],

      [
        "policy_mapping",
        "Generic Policy Mapping"
      ],

      [
        "rego_generation",
        "Rego Generation"
      ],

      [
        "python_policy_evaluation",
        "Python Policy Evaluation"
      ],

      [
        "opa_evaluation",
        "OPA Policy Evaluation"
      ],

      [
        "dataset",
        "Dataset Validation"
      ],
    ].map(
      ([key, label], index) => {

        const layer =
          pipelineStatus?.pipeline?.[key];

        const passed =
          layer?.status === "PASSED";

        const status =
          layer?.status || "LOADING";

        const detail =
          layer?.detail || "Waiting...";

        return (

          <div
            className={
              `pipeline-layer ${
                passed
                  ? "pipeline-passed"
                  : "pipeline-failed"
              }`
            }
            key={key}
          >

            <div className="pipeline-layer-number">
              {index + 1}
            </div>


            <div className="pipeline-layer-info">

              <strong>
                {label}
              </strong>

              <span>
                {status}
              </span>

              <small>
                {detail}
              </small>

            </div>


            <div className="pipeline-layer-status">

              {passed
                ? "✓"
                : "!"}

            </div>

          </div>

        );

      }
    )}

  </div>


  <div className="pipeline-metrics">

    <div>

      <span>
        RECORDS EVALUATED
      </span>

      <strong>
        {
          pipelineStatus?.execution
            ?.records_evaluated ?? 0
        }
      </strong>

    </div>


    <div>

      <span>
        EXECUTION ID
      </span>

      <strong>
        {pipelineStatus?.execution?.execution_id
          ? `#${pipelineStatus.execution.execution_id}`
          : "—"}
      </strong>

    </div>


    <div>

      <span>
        DECISION MISMATCHES
      </span>

      <strong>
        {
          pipelineStatus?.validation
            ?.decision_mismatches ?? 0
        }
      </strong>

    </div>


    <div>

      <span>
        RULE MISMATCHES
      </span>

      <strong>
        {
          pipelineStatus?.validation
            ?.rule_mismatches ?? 0
        }
      </strong>

    </div>


    <div>

      <span>
        VALIDATION FAILURES
      </span>

      <strong>
        {
          pipelineStatus?.validation
            ?.validation_failures ?? 0
        }
      </strong>

    </div>

  </div>


</section>
      {/* =====================================================
          SUMMARY + CHART
      ===================================================== */}

      <section className="overview">

        <div className="summary-section">

          <div className="summary-grid">

            <div className="summary-card pass-card">

              <span className="card-label">
                ✓ PASS
              </span>

              <strong>
                {passed}
              </strong>

              <small>
                {total
                  ? (
                      (passed /
                        total) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </small>

            </div>


            <div className="summary-card flag-card">

              <span className="card-label">
                ⚠ FLAG
              </span>

              <strong>
                {flagged}
              </strong>

              <small>
                {total
                  ? (
                      (flagged /
                        total) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </small>

            </div>


            <div className="summary-card block-card">

              <span className="card-label">
                ✕ BLOCK
              </span>

              <strong>
                {blocked}
              </strong>

              <small>
                {total
                  ? (
                      (blocked /
                        total) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </small>

            </div>


            <div className="summary-card rate-card">

              <span className="card-label">
                ◔ PASS RATE
              </span>

              <strong>
                {passRate}%
              </strong>

              <small>
                {passed}/{total} passed
              </small>

            </div>

          </div>

        </div>


        <div className="chart-section">

          <div className="chart-header">

            <div>
              <span className="section-eyebrow">
                DISTRIBUTION
              </span>

              <h3>
                Outcome Distribution
              </h3>
            </div>

          </div>

          <div className="pie-container">

            <Pie
              data={pieData}
              options={pieOptions}
            />

          </div>

        </div>

      </section>


      {/* =====================================================
          POLICY DEFINITIONS
      ===================================================== */}

<section className="policy-definitions-section">
  <div className="section-heading">
    <h2>Policy Definitions</h2>
    <p>Key data classification categories used in policy evaluation</p>
  </div>

  <div className="policy-definitions-row">
    <div className="policy-definition-card">
      <div className="policy-definition-code">PII</div>
      <div className="policy-definition-content">
        <h3>Personally Identifiable Information</h3>
        <p>
          Information that can directly identify or be linked to an
          individual.
        </p>
      </div>
    </div>

    <div className="policy-definition-card">
      <div className="policy-definition-code">SPII</div>
      <div className="policy-definition-content">
        <h3>Sensitive Personally Identifiable Information</h3>
        <p>
          Sensitive personal information requiring stronger protection
          and handling controls.
        </p>
      </div>
    </div>

    <div className="policy-definition-card">
      <div className="policy-definition-code">CPII</div>
      <div className="policy-definition-content">
        <h3>Combined Personally Identifiable Information</h3>
        <p>
          A combination of data elements that together can identify or
          re-identify an individual.
        </p>
      </div>
    </div>
  </div>
</section>


      {/* =====================================================
          MAIN CONTENT
      ===================================================== */}

      <section className="main-content">


        {/* ===================================================
            RECORDS
        =================================================== */}

        <div className="records-panel">

          <div className="panel-header">

            <div>

              <span className="section-eyebrow">
                EVALUATED RECORDS
              </span>

              <h2>
                Records
              </h2>

              <span>
                {filteredData.length}{" "}
                {filter} records shown
              </span>

            </div>

          </div>


          {/* FILTERS */}

          <div className="filters">
            <button
              type="button"
              className={`filter-button ${
                filter === "PASS" ? "active" : ""
              }`}
              onClick={() => setFilter("PASS")}
            >
              ✓ PASS
            </button>

            <button
              type="button"
              className={`filter-button ${
                filter === "FLAG" ? "active" : ""
              }`}
              onClick={() => setFilter("FLAG")}
            >
              ⚠ FLAG
            </button>

            <button
              type="button"
              className={`filter-button ${
                filter === "BLOCK" ? "active" : ""
              }`}
              onClick={() => setFilter("BLOCK")}
            >
              ✕ BLOCK
            </button>
          </div>


          {/* RECORD LIST */}

          <div className="record-list">

            {filteredData.length >
            0 ? (

              filteredData.map(
                (record) => {

                  const outcome =
                    String(
                      record.decision ??
                        record.expected_outcome ??
                        ""
                    )
                      .trim()
                      .toUpperCase();

                  const rules =
                    record.expected_rule_triggers ||
                    "No violations";

                  return (

                    <button
                      type="button"
                      key={
                        record.record_id
                      }
                      className={`record-item ${
                        String(
                          selectedId
                        ) ===
                        String(
                          record.record_id
                        )
                          ? "selected"
                          : ""
                      }`}
                      onClick={() =>
                        handleSelectRecord(
                          record.record_id
                        )
                      }
                    >

                      <span
                        className={`status-dot ${getOutcomeClass(
                          outcome
                        )}`}
                      >
                        {getIcon(
                          outcome
                        )}
                      </span>


                      <div className="record-info">

                        <strong>
                          REC-
                          {String(
                            record.record_id
                          ).padStart(
                            4,
                            "0"
                          )}
                        </strong>

                        <span>
                          {rules}
                        </span>

                      </div>


                      <span
                        className={`outcome-text ${getOutcomeClass(
                          outcome
                        )}`}
                      >
                        {outcome}
                      </span>

                    </button>

                  );
                }
              )

            ) : (

              <div className="no-violations">

                No{" "}
                {filter.toLowerCase()}{" "}
                records found.

              </div>

            )}

          </div>

        </div>


        {/* ===================================================
            RECORD ANALYSIS
        =================================================== */}

        <div className="analysis-panel">

          {selectedRecord ? (

            <>

              {/* ANALYSIS HEADER */}

              <div className="analysis-header">

                <div>

                  <span className="analysis-label">
                    RECORD POLICY
                    ANALYSIS
                  </span>

                  <h2>
                    REC-
                    {String(
                      selectedRecord.record_id
                    ).padStart(
                      4,
                      "0"
                    )}
                  </h2>

                </div>


                <span
                  className={`outcome-badge ${getOutcomeClass(
                    selectedRecord.decision
                  )}`}
                >

                  {getIcon(
                    selectedRecord.decision
                  )}

                  {" "}

                  {selectedRecord.decision}

                </span>

              </div>


              <div className="analysis-content">


                {/* POLICY RULES */}

                <section className="analysis-section">

                  <div className="analysis-section-header">

                    <span className="section-eyebrow">
                      POLICY MATCH
                    </span>

                    <h3>
                      Policy Rules
                    </h3>

                  </div>


                  {triggeredRules.length >
                  0 ? (

                    <div className="rule-list">

                      {triggeredRules.map(
                        (rule) => (

                          <div
                            className="rule-item"
                            key={rule}
                          >

                            <strong>
                              {rule}
                            </strong>

                            <span>
                              {getRuleDescription(
                                rule
                              )}
                            </span>

                            <small>
                              Outcome:{" "}
                              {getRuleOutcome(
                                rule
                              )}
                            </small>

                          </div>

                        )
                      )}

                    </div>

                  ) : (

                    <div className="no-violations">

                      ✓ No policy
                      violations
                      detected

                    </div>

                  )}

                </section>


                {/* EXPLANATION */}

                <section className="analysis-section">

                  <div className="analysis-section-header">

                    <span className="section-eyebrow">
                      EVALUATION
                    </span>

                    <h3>
                      Explanation
                    </h3>

                  </div>


                  <div className="line-list">

                    <div className="line-item">

                      <span>
                        •
                      </span>

                      <span>

                        {triggeredRules.length ===
                        0
                          ? "No PII or sensitive information detected."
                          : selectedRecord.expected_reason ||
                            "Policy rule conditions were triggered for this record."}

                      </span>

                    </div>

                  </div>

                </section>


                {/* INPUT DATA */}

                <section className="analysis-section">

                  <div className="analysis-section-header">

                    <span className="section-eyebrow">
                      SOURCE RECORD
                    </span>

                    <h3>
                      Input Data
                    </h3>

                  </div>


                  <div className="input-grid">

                    {inputFields.length >
                    0 ? (

                      inputFields.map(
                        (field) => {

                          const value =
                            inputData[
                              field
                            ];

                          return (

                            <div
                              className="input-item"
                              key={field}
                            >

                              <span>
                                {formatFieldName(
                                  field
                                )}
                              </span>

                              <strong>

                                {value ===
                                  null ||
                                value ===
                                  undefined ||
                                String(
                                  value
                                ).trim() ===
                                  ""
                                  ? "—"
                                  : String(
                                      value
                                    )}

                              </strong>

                            </div>

                          );
                        }
                      )

                    ) : (

                      <div className="no-violations">
                        No input data
                        available.
                      </div>

                    )}

                  </div>

                </section>


                {/* REMEDIATION */}

                <section className="analysis-section">

                  <div className="analysis-section-header">

                    <span className="section-eyebrow">
                      ACTION
                    </span>

                    <h3>
                      Suggested
                      Remediation
                    </h3>

                  </div>


                  <div className="remediation-list">

                    <div className="remediation-item">

                      <span>
                        →
                      </span>

                      <span>

                        {selectedRecord
                          .suggested_remediation ||
                          "No remediation required."}

                      </span>

                    </div>

                  </div>

                </section>

              </div>

            </>

          ) : (

            <div className="no-selection">

              <h3>
                Select a record
              </h3>

              <p>
                Select a record from the
                list to view its policy
                analysis.
              </p>

            </div>

          )}

        </div>

      </section>


      {/* =====================================================
          RIGHT SIDE EVALUATION HISTORY DRAWER
      ===================================================== */}

      {showHistory && (

        <div
          className="history-overlay"
          onClick={() =>
            setShowHistory(false)
          }
        >

          <aside
            className="history-drawer"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            <div className="history-drawer-header">

              <div>

                <span className="section-eyebrow">
                  DATABASE
                </span>

                <h2>
                  Evaluation History
                </h2>

                <p>
                  Previous policy
                  evaluation runs
                </p>

              </div>


              <button
                type="button"
                className="history-close"
                onClick={() =>
                  setShowHistory(false)
                }
              >
                ×
              </button>

            </div>


            <div className="history-drawer-list">

              {executions.length >
              0 ? (

                executions.map(
                  (
                    execution,
                    index
                  ) => {

                    const executionPass =
                      execution.pass_count ??
                      "—";

                    const executionFlag =
                      execution.flag_count ??
                      "—";

                    const executionBlock =
                      execution.block_count ??
                      "—";

                    const isSelected =
                      Number(
                        selectedExecutionId
                      ) ===
                      Number(
                        execution.id
                      );

                    return (

                      <button
                        type="button"
                        key={
                          execution.id
                        }
                        className={`history-run-card ${
                          index === 0
                            ? "current-run"
                            : ""
                        } ${
                          isSelected
                            ? "selected-history"
                            : ""
                        }`}
                        onClick={() => {

                          setFilter(
                            "PASS"
                          );

                          loadData(
                            execution.id
                          );

                          setShowHistory(
                            false
                          );

                        }}
                      >

                        <div className="history-run-top">

                          <strong>
                            Run #
                            {
                              execution.id
                            }
                          </strong>

                          {index ===
                            0 && (

                            <span className="history-current-label">
                              CURRENT
                            </span>

                          )}

                        </div>


                        <div className="history-run-outcomes">

                          <span className="history-pass">
                            ✓{" "}
                            {
                              executionPass
                            }
                          </span>

                          <span className="history-flag">
                            ⚠{" "}
                            {
                              executionFlag
                            }
                          </span>

                          <span className="history-block">
                            ✕{" "}
                            {
                              executionBlock
                            }
                          </span>

                        </div>


                        <div className="history-run-date">

                          {formatDateTime(
                            execution.started_at
                          )}

                        </div>


                        <div className="history-run-meta">

                          <span>
                            {
                              execution.total_records
                            }{" "}
                            records
                          </span>

                          <span>
                            {
                              execution.batch_size
                            }{" "}
                            / batch
                          </span>

                          <span>
                            {
                              execution.total_batches
                            }{" "}
                            batches
                          </span>

                        </div>

                      </button>

                    );
                  }
                )

              ) : (

                <div className="no-history">

                  No evaluation
                  history available.

                </div>

              )}

            </div>

          </aside>

        </div>

      )}

    </div>
  );
}

export default App;