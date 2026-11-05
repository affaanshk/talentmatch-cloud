
import {
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import {
  Activity,
  ArrowUpRight,
  BriefcaseBusiness,
  CheckCircle2,
  CircleAlert,
  FileText,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import {
  ArcElement,
  Chart as ChartJS,
  Legend,
  Tooltip,
  type ChartOptions,
} from "chart.js";
import { Doughnut } from "react-chartjs-2";

ChartJS.register(ArcElement, Tooltip, Legend);

type Job = {
  job_title?: string;
  title?: string;
  job_description?: string;
  description?: string;
  explanation?: string;
  suggestion?: string;
  final_score?: number;
  overall_score?: number;
  bert_score?: number;
  tfidf_score?: number;
  skill_score?: number;
  matched_skills?: string[];
  missing_skills?: string[];
};

type UploadRecord = {
  upload_id?: string;
  id?: string;
  status?: string;
  status_url?: string;
  overall_score?: number | string | null;
  result?: unknown;
  recommendations?: Job[];
  error_message?: string | null;
  error?: string | null;
  [key: string]: unknown;
};

type Analysis = {
  overall_score?: number | string | null;
  recommendations: Job[];
};

function asObject(value: unknown): Record<string, unknown> {
  if (typeof value === "string") {
    try {
      return asObject(JSON.parse(value));
    } catch {
      return {};
    }
  }

  return value !== null && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

function normalize(record: UploadRecord): Analysis {
  const result = asObject(record.result);
  const nested = asObject(result.result);

  const recommendations =
    result.recommendations ??
    nested.recommendations ??
    record.recommendations;

  return {
    overall_score:
      record.overall_score ??
      result.overall_score as number | string | undefined ??
      nested.overall_score as number | string | undefined,
    recommendations: Array.isArray(recommendations)
      ? (recommendations as Job[])
      : [],
  };
}

function score(value: unknown): number {
  const number =
    typeof value === "number" ? value : Number(value);

  if (!Number.isFinite(number)) return 0;

  return Math.max(
    0,
    Math.min(100, number <= 1 ? number * 100 : number),
  );
}

async function responseData(
  response: Response,
): Promise<Record<string, unknown>> {
  const text = await response.text();

  let data: unknown = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(
      `The server returned an invalid response (HTTP ${response.status}).`,
    );
  }

  if (!response.ok) {
    const body = asObject(data);
    const detail = body.detail ?? body.error ?? body.message;

    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed with HTTP ${response.status}.`,
    );
  }

  return asObject(data);
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) =>
    window.setTimeout(resolve, milliseconds),
  );
}

export default function App() {
  const input = useRef<HTMLInputElement>(null);
  const cancelRef = useRef(false);

  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(
    "Upload a PDF to discover relevant career paths.",
  );
  const [error, setError] = useState("");
  const [report, setReport] = useState<Analysis | null>(null);
  const [uploadId, setUploadId] = useState("");

  function choose(selected?: File) {
    setError("");

    if (!selected) return;

    if (
      !selected.name.toLowerCase().endsWith(".pdf") ||
      (selected.type &&
        selected.type !== "application/pdf")
    ) {
      setError("Please select a PDF file.");
      return;
    }

    if (selected.size === 0) {
      setError("The selected file is empty.");
      return;
    }

    if (selected.size > 5 * 1024 * 1024) {
      setError("PDFs must be 5 MB or smaller.");
      return;
    }

    setFile(selected);
    setReport(null);
    setUploadId("");
    setMessage("Ready to analyze.");
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    choose(event.target.files?.[0]);
    event.target.value = "";
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    choose(event.dataTransfer.files?.[0]);
  }

  async function analyze() {
    if (!file || busy) return;

    cancelRef.current = false;
    setBusy(true);
    setError("");
    setReport(null);
    setUploadId("");

    try {
      setMessage("Uploading resume…");

      const form = new FormData();
      form.append("file", file);

      const queued = (await responseData(
        await fetch("/api/upload-resume", {
          method: "POST",
          body: form,
        }),
      )) as UploadRecord;

      const id = String(queued.upload_id ?? queued.id ?? "");

      if (!id) {
        throw new Error("The API did not return an upload ID.");
      }

      setUploadId(id);

      const rawStatusUrl = String(
        queued.status_url ?? `/uploads/${id}`,
      );

      // Keep requests on the Vite proxy unless the API
      // explicitly returns an absolute URL.
      const statusUrl = rawStatusUrl.startsWith("http")
        ? rawStatusUrl
        : `/api${
            rawStatusUrl.startsWith("/")
              ? rawStatusUrl
              : `/${rawStatusUrl}`
          }`;

      const deadline = Date.now() + 5 * 60 * 1000;
      let delay = 1000;

      while (Date.now() < deadline) {
        if (cancelRef.current) {
          setMessage(
            "Stopped waiting. Background processing may continue.",
          );
          return;
        }

        await sleep(delay);

        if (cancelRef.current) {
          setMessage(
            "Stopped waiting. Background processing may continue.",
          );
          return;
        }

        const record = (await responseData(
          await fetch(statusUrl, {
            headers: { Accept: "application/json" },
            cache: "no-store",
          }),
        )) as UploadRecord;

        const status = String(record.status ?? "")
          .trim()
          .toLowerCase();

        if (
          ["completed", "complete", "success"].includes(status)
        ) {
          const analysis = normalize(record);

          setReport(analysis);
          setError("");
          setMessage("Analysis complete.");
          return;
        }

        if (["failed", "error"].includes(status)) {
          throw new Error(
            String(
              record.error_message ??
                record.error ??
                "Resume processing failed.",
            ),
          );
        }

        setMessage(
          status === "processing"
            ? "Analyzing skills and matching roles…"
            : status === "queued"
              ? "Resume queued. Waiting for processing…"
              : `Checking analysis status${
                  status ? ` (${status})` : ""
                }…`,
        );

        delay = Math.min(Math.round(delay * 1.25), 4000);
      }

      throw new Error(
        "Analysis timed out after five minutes. Your upload may still be processing. Check the upload reference before retrying.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Something went wrong.",
      );
      setMessage("Analysis could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  function stopWaiting() {
    cancelRef.current = true;
    setBusy(false);
    setMessage(
      "Stopped waiting. The server may continue processing your upload.",
    );
  }

  function startNewAnalysis() {
    cancelRef.current = true;
    setReport(null);
    setFile(null);
    setUploadId("");
    setError("");
    setMessage("Upload a PDF to discover relevant career paths.");
  }

  const overall = score(report?.overall_score);
  const jobs = report?.recommendations ?? [];

  const chartData = {
    datasets: [
      {
        data: [overall, 100 - overall],
        backgroundColor: [
          overall >= 70
            ? "#57e6b1"
            : overall >= 40
              ? "#f7c76a"
              : "#ff7b8b",
          "rgba(255,255,255,.08)",
        ],
        borderWidth: 0,
        borderRadius: 8,
        circumference: 180,
        rotation: 270,
      },
    ],
  };

  const chartOptions: ChartOptions<"doughnut"> = {
    cutout: "82%",
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
    },
  };

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#">
          <span className="brand-icon">
            <Sparkles size={18} />
          </span>
          TalentMatch <b>AI</b>
        </a>

        <span className="top-note">
          <i /> AI-powered career matching
        </span>
      </header>

      <main>
        <section className="hero">
          <span className="eyebrow">
            <Sparkles size={13} /> YOUR NEXT CHAPTER STARTS HERE
          </span>

          <h1>
            Make your next move
            <br />
            <em>your best move.</em>
          </h1>

          <p>
            Discover roles that fit your experience, uncover skill
            gaps, and turn your resume into a clearer career direction.
          </p>
        </section>

        <section className="layout">
          <div className="panel upload-panel">
            <div className="section-heading">
              <div>
                <small>STEP 01</small>
                <h2>Upload your resume</h2>
              </div>

              <span className="private">
                <ShieldCheck size={16} /> Private by design
              </span>
            </div>

            <input
              ref={input}
              type="file"
              accept=".pdf,application/pdf"
              hidden
              onChange={onFileChange}
            />

            <div
              className={`dropzone ${dragging ? "dragging" : ""}`}
              role="button"
              tabIndex={0}
              onClick={() => {
                if (!busy) input.current?.click();
              }}
              onKeyDown={(event) => {
                if (
                  !busy &&
                  (event.key === "Enter" || event.key === " ")
                ) {
                  event.preventDefault();
                  input.current?.click();
                }
              }}
              onDragOver={(event) => {
                event.preventDefault();
                if (!busy) setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              <span className="file-icon">
                <FileText size={31} />
              </span>

              <strong>
                {file ? file.name : "Drop your resume here"}
              </strong>

              <span className="subtle">
                {file
                  ? `${(file.size / 1024).toFixed(0)} KB · PDF document`
                  : "or browse files on your device"}
              </span>

              {file ? (
                <button
                  className="remove"
                  type="button"
                  disabled={busy}
                  onClick={(event) => {
                    event.stopPropagation();
                    setFile(null);
                    setReport(null);
                    setUploadId("");
                    setMessage("Ready to analyze.");
                    setError("");
                  }}
                >
                  <X size={13} /> Remove file
                </button>
              ) : (
                <small className="file-limit">
                  PDF only · up to 5 MB
                </small>
              )}
            </div>

            <button
              className="primary"
              type="button"
              disabled={!file || busy}
              onClick={analyze}
            >
              {busy ? (
                <>
                  <LoaderCircle className="spin" size={17} />
                  Analyzing resume…
                </>
              ) : (
                <>
                  Analyze my profile <ArrowUpRight size={17} />
                </>
              )}
            </button>

            {busy && (
              <button
                className="cancel"
                type="button"
                onClick={stopWaiting}
              >
                Stop waiting for result
              </button>
            )}

            <p
              className={`status ${error ? "error" : ""}`}
              role="status"
              aria-live="polite"
            >
              {error ? (
                <CircleAlert size={15} />
              ) : busy ? (
                <Activity size={15} />
              ) : (
                <CheckCircle2 size={15} />
              )}
              {error || message}
            </p>

            {uploadId && (
              <p className="reference">
                Upload reference: <code>{uploadId}</code>
              </p>
            )}

            <div className="privacy">
              <ShieldCheck size={15} />
              Upload only resumes you have permission to process.
            </div>
          </div>

          <aside className="side">
            <div className="panel side-card">
              <span className="side-icon">
                <Target size={19} />
              </span>

              <h3>Beyond keyword matching</h3>

              <p>
                Explore recommendations informed by the matching
                signals returned by your TalentMatch engine.
              </p>

              <div className="signal">
                <span>Semantic similarity</span>
                <b>BERT</b>
              </div>

              <div className="signal">
                <span>Keyword relevance</span>
                <b>TF-IDF</b>
              </div>

              <div className="signal">
                <span>Skill gap insights</span>
                <b>✓</b>
              </div>
            </div>

            <div className="tip">
              <Activity size={18} />
              <div>
                <b>Small improvements add up</b>
                <p>
                  Use missing-skill insights to guide your next
                  learning goal.
                </p>
              </div>
            </div>
          </aside>
        </section>

        {report && (
          <section className="results">
            <div className="results-heading">
              <div>
                <small>YOUR RESULTS</small>
                <h2>Your career match report</h2>
                <p>
                  Here’s what the analysis returned for this resume.
                </p>
              </div>

              <button
                className="secondary"
                type="button"
                onClick={startNewAnalysis}
              >
                <RefreshCw size={14} /> New analysis
              </button>
            </div>

            <div className="result-grid">
              <div className="panel score-card">
                <small>OVERALL MATCH</small>
                <h3>Match strength</h3>

                <div className="gauge">
                  <Doughnut
                    data={chartData}
                    options={chartOptions}
                  />

                  <div className="gauge-label">
                    <strong>
                      {Math.round(overall)}
                      <i>%</i>
                    </strong>
                    <span>match score</span>
                  </div>
                </div>

                <p className="score-caption">
                  {overall >= 70
                    ? "Strong alignment with the roles identified."
                    : overall >= 40
                      ? "A promising starting point with room to grow."
                      : "Explore skill gaps to improve future matches."}
                </p>
              </div>

              <div className="panel job-panel">
                <div className="job-panel-heading">
                  <div>
                    <small>PERSONALIZED FOR YOU</small>
                    <h3>Career recommendations</h3>
                  </div>

                  <span className="count">
                    {jobs.length} roles
                  </span>
                </div>

                {!jobs.length ? (
                  <div className="empty">
                    <BriefcaseBusiness size={25} />
                    <b>No recommendations returned</b>
                    <p>
                      The upload completed, but the API result did
                      not include a recommendations array.
                    </p>
                  </div>
                ) : (
                  <div className="jobs">
                    {jobs.map((job, index) => {
                      const title = String(
                        job.job_title ??
                          job.title ??
                          `Recommended role ${index + 1}`,
                      );

                      const jobScore = score(
                        job.final_score ?? job.overall_score,
                      );

                      const matched = Array.isArray(job.matched_skills)
                        ? job.matched_skills
                        : [];

                      const missing = Array.isArray(job.missing_skills)
                        ? job.missing_skills
                        : [];

                      return (
                        <article
                          className="job"
                          key={`${title}-${index}`}
                        >
                          <div className="job-top">
                            <span className="job-icon">
                              <BriefcaseBusiness size={17} />
                            </span>

                            <div className="job-info">
                              <div className="job-title">
                                <h4>{title}</h4>
                                {index === 0 && <b>TOP MATCH</b>}
                              </div>

                              <p>
                                {String(
                                  job.job_description ??
                                    job.description ??
                                    "Recommended based on the analysis signals.",
                                )}
                              </p>
                            </div>

                            <strong className="job-score">
                              {Math.round(jobScore)}%
                              <small>match</small>
                            </strong>
                          </div>

                          {job.explanation && (
                            <p className="explanation">
                              {String(job.explanation)}
                            </p>
                          )}

                          <div className="skill-grid">
                            <div>
                              <small className="good-label">
                                MATCHED SKILLS
                              </small>

                              <div className="chips">
                                {matched.length ? (
                                  matched.map((skill, skillIndex) => (
                                    <span
                                      className="chip good"
                                      key={`${skill}-${skillIndex}`}
                                    >
                                      {String(skill)}
                                    </span>
                                  ))
                                ) : (
                                  <span className="muted">
                                    Not provided
                                  </span>
                                )}
                              </div>
                            </div>

                            <div>
                              <small className="bad-label">
                                SKILL OPPORTUNITIES
                              </small>

                              <div className="chips">
                                {missing.length ? (
                                  missing.map((skill, skillIndex) => (
                                    <span
                                      className="chip bad"
                                      key={`${skill}-${skillIndex}`}
                                    >
                                      {String(skill)}
                                    </span>
                                  ))
                                ) : (
                                  <span className="muted">
                                    No major gaps reported
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          {(job.bert_score != null ||
                            job.tfidf_score != null) && (
                            <div className="breakdown">
                              {job.bert_score != null && (
                                <span>
                                  Semantic
                                  <b>
                                    {Math.round(
                                      score(job.bert_score),
                                    )}
                                    %
                                  </b>
                                </span>
                              )}

                              {job.tfidf_score != null && (
                                <span>
                                  Keyword
                                  <b>
                                    {Math.round(
                                      score(job.tfidf_score),
                                    )}
                                    %
                                  </b>
                                </span>
                              )}
                            </div>
                          )}

                          {job.suggestion && (
                            <p className="suggestion">
                              <Sparkles size={13} />
                              {String(job.suggestion)}
                            </p>
                          )}
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        <section className="steps">
          <small>BUILT FOR CLARITY</small>
          <h2>From resume to next steps.</h2>

          <div className="step-grid">
            <article>
              <span>01</span>
              <FileText size={18} />
              <h3>Share your resume</h3>
              <p>Submit a PDF and follow its processing status.</p>
            </article>

            <article>
              <span>02</span>
              <Activity size={18} />
              <h3>Analyze the signals</h3>
              <p>
                Review the matching information returned by the engine.
              </p>
            </article>

            <article>
              <span>03</span>
              <Target size={18} />
              <h3>Choose a next step</h3>
              <p>
                Use role and skill-gap insights to plan your growth.
              </p>
            </article>
          </div>
        </section>
      </main>

      <footer className="footer">
        TalentMatch AI · Resume insights for your next career move
      </footer>
    </div>
  );
}
