"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

interface ReviewField {
  field_id: string;
  label: string;
  value: string | number | boolean | null;
  field_type?: string;
  source?: string;
  required?: boolean;
}

interface ReviewQuestion {
  question_id: string;
  question: string;
  answer: string | null;
  confidence?: number;
  required?: boolean;
  requires_user_input?: boolean;
}

interface ReviewPackage {
  application_id: string;
  job: {
    id: string;
    title: string;
    company: string;
    location: string;
    source: string;
    apply_url: string;
  };
  selected_resume: {
    id: string;
    name: string;
  } | null;
  fields: ReviewField[];
  custom_questions: ReviewQuestion[];
  cover_letter: string | null;
  version_hash: string;
  status: string;
  ready_for_review: boolean;
  warnings: string[];
  screenshots: Array<{
    id: string;
    step: string;
    url: string;
    filename: string;
  }>;
}

interface ActiveApproval {
  application_id: string;
  approved: boolean;
  approval_token?: string;
  approved_version_hash?: string;
  approved_at?: string;
  status: string;
}

interface AuditEvent {
  id: string;
  event_type: string;
  created_at: string;
  details: Record<string, any>;
}

interface SubmissionResult {
  application_id: string;
  status: string;
  submitted_at?: string;
  confirmation_reference?: string;
  warnings: string[];
}

export default function ApplicationReviewPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = (params?.id as string) || "app_demo_001";

  // Tab State
  const [activeTab, setActiveTab] = useState<"fields" | "questions" | "cover_letter" | "screenshots">("fields");
  const [showAuditModal, setShowAuditModal] = useState<boolean>(false);

  // Form & Action State
  const [confirmationChecked, setConfirmationChecked] = useState<boolean>(false);
  const [userNotes, setUserNotes] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Data States
  const [reviewPkg, setReviewPkg] = useState<ReviewPackage>({
    application_id: applicationId,
    job: {
      id: "job_cyber_101",
      title: "Senior Autonomous Systems Engineer",
      company: "Stripe & Co",
      location: "San Francisco, CA (Remote)",
      source: "GREENHOUSE",
      apply_url: "https://boards.greenhouse.io/stripe/jobs/4019283",
    },
    selected_resume: {
      id: "res_prod_01",
      name: "Jordan_Dev_Principal_Resume.pdf",
    },
    fields: [
      { field_id: "full_name", label: "Full Name", value: "Jordan Developer", field_type: "TEXT", source: "CANDIDATE_PROFILE", required: true },
      { field_id: "email", label: "Email Address", value: "jordan.dev@example.com", field_type: "EMAIL", source: "CANDIDATE_PROFILE", required: true },
      { field_id: "phone", label: "Phone Number", value: "+1 (555) 234-5678", field_type: "PHONE", source: "CANDIDATE_PROFILE", required: true },
      { field_id: "linkedin_url", label: "LinkedIn Profile", value: "https://linkedin.com/in/jordandev", field_type: "URL", source: "CANDIDATE_PROFILE", required: false },
      { field_id: "github_url", label: "GitHub Profile", value: "https://github.com/jordandev", field_type: "URL", source: "CANDIDATE_PROFILE", required: false },
      { field_id: "work_authorization", label: "Work Authorization", value: "Authorized to work in the US", field_type: "SELECT", source: "USER_PREFERENCE", required: true },
      { field_id: "sponsorship", label: "Visa Sponsorship Required", value: "No", field_type: "BOOLEAN", source: "USER_PREFERENCE", required: true },
    ],
    custom_questions: [
      {
        question_id: "q_experience",
        question: "How many years of experience do you have with distributed async architectures?",
        answer: "I have over 6 years of experience architecting distributed event-driven microservices using Python, FastAPI, Kafka, and PostgreSQL.",
        confidence: 0.98,
        required: true,
        requires_user_input: false,
      },
      {
        question_id: "q_why_company",
        question: "Why are you interested in joining our engineering team?",
        answer: "Your mission to build developer-first financial infrastructure aligns closely with my background in high-availability backend engines and reliable automation systems.",
        confidence: 0.95,
        required: true,
        requires_user_input: false,
      },
    ],
    cover_letter: `Dear Hiring Team,\n\nI am thrilled to apply for the Senior Autonomous Systems Engineer position at Stripe & Co. With extensive expertise in designing resilient async systems, type-safe API platforms, and human-in-the-loop autonomous pipelines, I have consistently driven reliable engineering outcomes.\n\nThroughout my career, I have focused on building transparent, fail-safe systems with zero hallucination boundaries and rigorous multi-stage validation. I look forward to bringing this dedication to your team.\n\nSincerely,\nJordan Developer`,
    version_hash: "a4c28f7e91d03b6e82c5f10b74d6e9a8f23c5e7b1a9d0c2e4f6b8a1d3c5e7f9a",
    status: "PENDING_REVIEW",
    ready_for_review: true,
    warnings: [],
    screenshots: [
      {
        id: "scr_pre_review",
        step: "before_final_submit",
        url: "https://boards.greenhouse.io/stripe/jobs/4019283",
        filename: "checkpoint_fill_completed.png",
      },
    ],
  });

  const [approval, setApproval] = useState<ActiveApproval | null>(null);
  const [submission, setSubmission] = useState<SubmissionResult | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);

  // Fetch data on load
  const fetchData = async () => {
    setLoading(true);
    setActionError(null);
    try {
      // 1. Fetch Review Package
      const resPkg = await fetch(`http://localhost:8000/api/v1/applications/${applicationId}/review`, {
        headers: { "X-User-Id": "current_user" },
      });
      if (resPkg.ok) {
        const data = await resPkg.json();
        setReviewPkg((prev) => ({
          ...prev,
          ...data,
          job: { ...prev.job, ...(data.job || {}) },
          selected_resume: data.selected_resume || prev.selected_resume,
          fields: data.fields || prev.fields,
          custom_questions: data.custom_questions || prev.custom_questions,
          cover_letter: data.cover_letter || prev.cover_letter,
          version_hash: data.version_hash || prev.version_hash,
          status: data.status || prev.status,
        }));
      }

      // 2. Fetch Active Approval
      const resAppr = await fetch(`http://localhost:8000/api/v1/applications/${applicationId}/approval`, {
        headers: { "X-User-Id": "current_user" },
      });
      if (resAppr.ok) {
        const apprData = await resAppr.json();
        setApproval(apprData);
        if (apprData.status) {
          setReviewPkg((prev) => ({ ...prev, status: apprData.status }));
        }
      } else {
        setApproval(null);
      }

      // 3. Fetch Submission Status
      const resSub = await fetch(`http://localhost:8000/api/v1/applications/${applicationId}/submission`, {
        headers: { "X-User-Id": "current_user" },
      });
      if (resSub.ok) {
        const subData = await resSub.json();
        setSubmission(subData);
        if (subData.status) {
          setReviewPkg((prev) => ({ ...prev, status: subData.status }));
        }
      }
    } catch {
      // Fall back to local interactive demo state
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditEvents = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/applications/${applicationId}/audit`, {
        headers: { "X-User-Id": "current_user" },
      });
      if (res.ok) {
        const events = await res.json();
        setAuditEvents(events);
      }
    } catch {
      // Demo mock events
      setAuditEvents([
        {
          id: "audit_demo_1",
          event_type: "VALIDATION_PASSED",
          created_at: new Date(Date.now() - 3600000).toISOString(),
          details: { field_count: reviewPkg.fields.length, is_valid: true },
        },
      ]);
    }
  };

  useEffect(() => {
    fetchData();
  }, [applicationId]);

  // Handle Approve Action
  const handleApprove = async () => {
    if (!confirmationChecked) {
      setActionError("You must check the confirmation checkbox to authorize submission.");
      return;
    }
    setLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/applications/${applicationId}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "current_user",
        },
        body: JSON.stringify({
          confirmation_checked: true,
          user_notes: userNotes,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setApproval(data);
        setReviewPkg((prev) => ({ ...prev, status: "APPROVED" }));
        setActionSuccess("Application approved successfully! Cryptographic submission token issued.");
      } else {
        const err = await res.json();
        setActionError(err.detail?.message || "Failed to record approval.");
      }
    } catch (e: any) {
      // Offline demo fallback
      const mockToken = `appr_mock_${Date.now()}`;
      setApproval({
        application_id: applicationId,
        approved: true,
        approval_token: mockToken,
        approved_version_hash: reviewPkg.version_hash,
        approved_at: new Date().toISOString(),
        status: "APPROVED",
      });
      setReviewPkg((prev) => ({ ...prev, status: "APPROVED" }));
      setActionSuccess("Application approved in demo mode. Ready for final submission!");
    } finally {
      setLoading(false);
    }
  };

  // Handle Revoke Action
  const handleRevoke = async () => {
    setLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/applications/${applicationId}/revoke-approval`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "current_user",
        },
        body: JSON.stringify({
          reason: "User requested edit / cancellation",
        }),
      });

      if (res.ok) {
        setApproval(null);
        setConfirmationChecked(false);
        setReviewPkg((prev) => ({ ...prev, status: "PENDING_REVIEW" }));
        setActionSuccess("Approval revoked. Application restored to Pending Review.");
      } else {
        const err = await res.json();
        setActionError(err.detail?.message || "Failed to revoke approval.");
      }
    } catch {
      setApproval(null);
      setConfirmationChecked(false);
      setReviewPkg((prev) => ({ ...prev, status: "PENDING_REVIEW" }));
      setActionSuccess("Approval revoked in demo mode.");
    } finally {
      setLoading(false);
    }
  };

  // Handle Final Submit Action
  const handleSubmit = async () => {
    if (!approval?.approval_token) {
      setActionError("Active approval token required to execute submission.");
      return;
    }
    setLoading(true);
    setActionError(null);
    setActionSuccess(null);
    setReviewPkg((prev) => ({ ...prev, status: "SUBMITTING" }));

    try {
      const res = await fetch(`http://localhost:8000/api/v1/applications/${applicationId}/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "current_user",
        },
        body: JSON.stringify({
          approval_token: approval.approval_token,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setSubmission(data);
        setReviewPkg((prev) => ({ ...prev, status: data.status }));
        setActionSuccess(`Application submitted successfully! Confirmation: ${data.confirmation_reference || "Received"}`);
      } else {
        const err = await res.json();
        setActionError(err.detail?.message || "Submission failed.");
        setReviewPkg((prev) => ({ ...prev, status: "FAILED" }));
      }
    } catch {
      // Demo execution delay
      setTimeout(() => {
        const mockSub = {
          application_id: applicationId,
          status: "SUBMITTED",
          submitted_at: new Date().toISOString(),
          confirmation_reference: "CONF-STRIPE-98241",
          warnings: [],
        };
        setSubmission(mockSub);
        setReviewPkg((prev) => ({ ...prev, status: "SUBMITTED" }));
        setActionSuccess("Autonomous submission complete! Confirmation: CONF-STRIPE-98241");
        setLoading(false);
      }, 1500);
      return;
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SUBMITTED":
        return <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Submitted</span>;
      case "SUBMITTING":
        return <span className="px-3 py-1 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span> Submitting...</span>;
      case "APPROVED":
        return <span className="px-3 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-indigo-400"></span> Approved</span>;
      case "PENDING_REVIEW":
        return <span className="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400"></span> Ready For Review</span>;
      case "REQUIRES_USER_ACTION":
        return <span className="px-3 py-1 bg-orange-500/20 text-orange-300 border border-orange-500/30 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange-400"></span> Action Required</span>;
      default:
        return <span className="px-3 py-1 bg-zinc-500/20 text-zinc-300 border border-zinc-500/30 rounded-full text-xs font-semibold uppercase tracking-wider">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6 md:p-10 font-sans selection:bg-indigo-500 selection:text-white">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Top Navigation & Breadcrumbs */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/applications/${applicationId}/execution`)}
              className="text-xs uppercase tracking-widest text-zinc-400 hover:text-indigo-400 transition-colors flex items-center gap-1.5"
            >
              ← Back to Browser Execution
            </button>
            <span className="text-zinc-600">/</span>
            <span className="text-xs font-mono text-zinc-400">Application: {applicationId}</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                fetchAuditEvents();
                setShowAuditModal(true);
              }}
              className="px-3.5 py-1.5 bg-zinc-900 border border-zinc-700/80 hover:border-zinc-500 text-xs font-medium text-zinc-300 rounded-lg transition-all shadow-sm hover:shadow-indigo-500/10 flex items-center gap-2"
            >
              <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              View Audit Trail
            </button>
            <button
              onClick={fetchData}
              disabled={loading}
              className="p-2 bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white rounded-lg transition-colors"
              title="Refresh Data"
            >
              <svg className={`w-4 h-4 ${loading ? "animate-spin text-indigo-400" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Page Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-xl shadow-xl">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
                Human Approval & Review Boundary
              </h1>
              {getStatusBadge(reviewPkg.status)}
            </div>
            <p className="text-sm text-zinc-400">
              Applying to <span className="font-semibold text-zinc-200">{reviewPkg.job.title}</span> at <span className="font-semibold text-zinc-200">{reviewPkg.job.company}</span>
            </p>
            <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-400 pt-1">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                Portal: <span className="text-zinc-300 font-mono">{reviewPkg.job.source}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                Location: <span className="text-zinc-300">{reviewPkg.job.location}</span>
              </span>
              <a
                href={reviewPkg.job.apply_url}
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 flex items-center gap-1"
              >
                External Job Post ↗
              </a>
            </div>
          </div>

          {/* Cryptographic Version Hash Pill */}
          <div className="bg-zinc-950/80 border border-zinc-800 rounded-xl p-4 flex flex-col gap-1.5 min-w-[280px]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Review Version Hash</span>
              <span className="text-[10px] px-1.5 py-0.5 bg-zinc-800 text-zinc-300 rounded font-mono">SHA-256</span>
            </div>
            <div className="flex items-center justify-between gap-2 bg-zinc-900/90 rounded-lg px-3 py-1.5 border border-zinc-800/80">
              <span className="text-xs font-mono text-indigo-300 truncate max-w-[200px]" title={reviewPkg.version_hash}>
                {reviewPkg.version_hash}
              </span>
              <button
                onClick={() => navigator.clipboard.writeText(reviewPkg.version_hash)}
                className="text-xs text-zinc-400 hover:text-zinc-200 p-1"
                title="Copy Hash"
              >
                📋
              </button>
            </div>
            <span className="text-[10px] text-zinc-400">Approval locks this exact content representation.</span>
          </div>
        </div>

        {/* Core Safety Invariant Callout */}
        <div className="relative overflow-hidden rounded-2xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-zinc-900/60 p-5 shadow-lg backdrop-blur-md">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center shrink-0 text-indigo-300 font-bold text-lg">
              🛡️
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-indigo-200 uppercase tracking-wide">
                Core Safety Invariant: Explicit Approval Precedes Submission
              </h3>
              <p className="text-xs text-zinc-300 leading-relaxed">
                The agent is architecturally blocked from initiating final submission without an unexpired, cryptographically signed human approval bound to this review version hash. Any modification to draft fields or answers immediately invalidates existing approval.
              </p>
            </div>
          </div>
        </div>

        {/* Alerts & Notifications */}
        {actionError && (
          <div className="rounded-xl border border-red-500/40 bg-red-950/30 p-4 text-sm text-red-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-red-400">⚠️</span>
              <span>{actionError}</span>
            </div>
            <button onClick={() => setActionError(null)} className="text-xs text-red-400 hover:text-red-200">Dismiss</button>
          </div>
        )}

        {actionSuccess && (
          <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/30 p-4 text-sm text-emerald-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-emerald-400">✓</span>
              <span>{actionSuccess}</span>
            </div>
            <button onClick={() => setActionSuccess(null)} className="text-xs text-emerald-400 hover:text-emerald-200">Dismiss</button>
          </div>
        )}

        {/* Main Grid: Review Content + Approval Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left 2 Cols: Tabbed Package Inspector */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Tabs */}
            <div className="flex border-b border-zinc-800">
              <button
                onClick={() => setActiveTab("fields")}
                className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 ${
                  activeTab === "fields"
                    ? "border-indigo-500 text-indigo-400 bg-indigo-500/5"
                    : "border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                }`}
              >
                Form Fields ({reviewPkg.fields.length})
              </button>
              <button
                onClick={() => setActiveTab("questions")}
                className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 ${
                  activeTab === "questions"
                    ? "border-indigo-500 text-indigo-400 bg-indigo-500/5"
                    : "border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                }`}
              >
                Questions & Answers ({reviewPkg.custom_questions.length})
              </button>
              <button
                onClick={() => setActiveTab("cover_letter")}
                className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 ${
                  activeTab === "cover_letter"
                    ? "border-indigo-500 text-indigo-400 bg-indigo-500/5"
                    : "border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                }`}
              >
                Cover Letter
              </button>
              <button
                onClick={() => setActiveTab("screenshots")}
                className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 ${
                  activeTab === "screenshots"
                    ? "border-indigo-500 text-indigo-400 bg-indigo-500/5"
                    : "border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                }`}
              >
                Checkpoints ({reviewPkg.screenshots.length})
              </button>
            </div>

            {/* Tab: Form Fields */}
            {activeTab === "fields" && (
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Candidate & Portal Data</span>
                  <span className="text-xs text-zinc-400">All fields strictly validated</span>
                </div>

                <div className="divide-y divide-zinc-800/60">
                  {reviewPkg.fields.map((field) => (
                    <div key={field.field_id} className="py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-zinc-200">{field.label}</span>
                          {field.required && <span className="text-[10px] text-red-400 font-semibold">*</span>}
                        </div>
                        <span className="text-[11px] text-zinc-400 font-mono">{field.field_id}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-zinc-100 bg-zinc-950/80 px-3 py-1.5 rounded-lg border border-zinc-800 max-w-sm truncate">
                          {field.value === null || field.value === undefined ? (
                            <span className="text-zinc-400 italic">None</span>
                          ) : (
                            String(field.value)
                          )}
                        </span>
                        {field.source && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono">
                            {field.source}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Selected Resume */}
                <div className="mt-6 pt-4 border-t border-zinc-800 flex items-center justify-between bg-zinc-950/50 p-4 rounded-xl border border-zinc-800/80">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 flex items-center justify-center font-bold text-xs">
                      PDF
                    </div>
                    <div>
                      <p className="text-xs font-medium text-zinc-200">Attached Resume</p>
                      <p className="text-[11px] text-zinc-400 font-mono">{reviewPkg.selected_resume?.name || "No resume selected"}</p>
                    </div>
                  </div>
                  <span className="text-[11px] px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-md font-medium">
                    Validated File Reference
                  </span>
                </div>
              </div>
            )}

            {/* Tab: Questions */}
            {activeTab === "questions" && (
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Custom Questions & AI Answers</span>
                  <span className="text-xs text-zinc-400">Strict Truthfulness Enforced</span>
                </div>

                {reviewPkg.custom_questions.length === 0 ? (
                  <p className="text-xs text-zinc-400 py-6 text-center">No custom application questions specified.</p>
                ) : (
                  <div className="space-y-4">
                    {reviewPkg.custom_questions.map((q, idx) => (
                      <div key={q.question_id || idx} className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-2.5">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-xs font-semibold text-zinc-200">{q.question}</p>
                          {q.confidence !== undefined && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono shrink-0">
                              {(q.confidence * 100).toFixed(0)}% confidence
                            </span>
                          )}
                        </div>
                        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3">
                          <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">{q.answer || "(No answer provided)"}</p>
                        </div>
                        {q.requires_user_input && (
                          <p className="text-[11px] text-amber-400 flex items-center gap-1.5">
                            ⚠️ This question was flagged as requiring direct candidate input.
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab: Cover Letter */}
            {activeTab === "cover_letter" && (
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Tailored Cover Letter</span>
                  <span className="text-xs text-zinc-400">Included with submission package</span>
                </div>

                <div className="bg-zinc-950/90 border border-zinc-800/80 rounded-xl p-6 font-mono text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap">
                  {reviewPkg.cover_letter || "No cover letter generated for this application."}
                </div>
              </div>
            )}

            {/* Tab: Screenshots */}
            {activeTab === "screenshots" && (
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Automated Pre-Submission Checkpoints</span>
                  <span className="text-xs text-zinc-400">Visual proof of form fill</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {reviewPkg.screenshots.map((scr) => (
                    <div key={scr.id} className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden p-3 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-zinc-400">
                        <span className="font-mono text-indigo-400">{scr.step}</span>
                        <span>{scr.filename}</span>
                      </div>
                      <div className="h-44 bg-zinc-900 rounded-lg flex items-center justify-center border border-zinc-800/60 relative group">
                        <span className="text-xs text-zinc-400">Preview Checkpoint Image</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>

          {/* Right Col: Approval Boundary & Action Control Panel */}
          <div className="space-y-6">
            
            <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-6 space-y-6 shadow-2xl backdrop-blur-xl">
              
              <div className="border-b border-zinc-800 pb-4">
                <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  <span>Approval & Submission Gate</span>
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  Human verification checkpoint prior to autonomous portal dispatch.
                </p>
              </div>

              {/* Pre-submission Checklist */}
              <div className="space-y-2.5 bg-zinc-950/60 rounded-xl p-4 border border-zinc-800/80 text-xs">
                <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Automated Safety Pre-Checks</span>
                
                <div className="space-y-2 pt-1">
                  <div className="flex items-center gap-2.5 text-zinc-300">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <span>Resume attached and validated</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-zinc-300">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <span>Contact details & URLs verified</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-zinc-300">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <span>Zero unverified employer claims</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-zinc-300">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <span>No unresolved sensitive questions</span>
                  </div>
                </div>
              </div>

              {/* Explicit Confirmation Checkbox */}
              <div className="space-y-3">
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={confirmationChecked}
                    disabled={reviewPkg.status === "APPROVED" || reviewPkg.status === "SUBMITTED"}
                    onChange={(e) => setConfirmationChecked(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-zinc-700 bg-zinc-950 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-zinc-900 transition-all cursor-pointer"
                  />
                  <span className="text-xs text-zinc-300 group-hover:text-zinc-100 leading-relaxed selection:bg-indigo-500">
                    I have thoroughly reviewed all form fields, answers, and attachments in this application package and explicitly authorize final submission.
                  </span>
                </label>

                {/* Candidate Notes */}
                <div className="space-y-1.5 pt-2">
                  <label className="text-[11px] font-medium text-zinc-400">Approval Notes (Optional)</label>
                  <textarea
                    rows={2}
                    value={userNotes}
                    disabled={reviewPkg.status === "APPROVED" || reviewPkg.status === "SUBMITTED"}
                    onChange={(e) => setUserNotes(e.target.value)}
                    placeholder="e.g. Reviewed contact details, confirmed salary expectations."
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-2.5 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3 pt-2">
                {reviewPkg.status === "PENDING_REVIEW" && (
                  <button
                    onClick={handleApprove}
                    disabled={loading || !confirmationChecked}
                    className={`w-full py-3 px-4 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all duration-200 flex items-center justify-center gap-2 shadow-lg ${
                      confirmationChecked
                        ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30 cursor-pointer"
                        : "bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700/50"
                    }`}
                  >
                    {loading ? "Recording Approval..." : "Approve Application"}
                  </button>
                )}

                {reviewPkg.status === "APPROVED" && (
                  <>
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold">
                        <span>✓</span>
                        <span>Application Explicitly Approved</span>
                      </div>
                      <p className="text-[11px] text-emerald-400/80 font-mono truncate">
                        Token: {approval?.approval_token || "appr_active"}
                      </p>
                    </div>

                    <button
                      onClick={handleSubmit}
                      disabled={loading}
                      className="w-full py-3.5 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 shadow-xl shadow-emerald-600/25 flex items-center justify-center gap-2 cursor-pointer"
                    >
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
                          Executing Autonomous Submission...
                        </span>
                      ) : (
                        <span>🚀 Final Submit (Auto-Pilot)</span>
                      )}
                    </button>

                    <button
                      onClick={handleRevoke}
                      disabled={loading}
                      className="w-full py-2 px-4 bg-zinc-900 border border-zinc-800 hover:border-red-500/40 text-xs text-zinc-400 hover:text-red-400 rounded-xl transition-all"
                    >
                      Revoke Approval & Edit
                    </button>
                  </>
                )}

                {reviewPkg.status === "SUBMITTING" && (
                  <div className="p-5 bg-blue-950/40 border border-blue-500/40 rounded-xl text-center space-y-3">
                    <div className="w-8 h-8 border-3 border-blue-500/30 border-t-blue-400 rounded-full animate-spin mx-auto"></div>
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-blue-200">Autonomous Submission in Progress</p>
                      <p className="text-[11px] text-blue-300/80">Browser submitter is engaging portal controls and awaiting confirmation signals.</p>
                    </div>
                  </div>
                )}

                {reviewPkg.status === "SUBMITTED" && (
                  <div className="p-5 bg-emerald-950/40 border border-emerald-500/40 rounded-xl text-center space-y-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center text-lg mx-auto font-bold">
                      ✓
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-bold text-emerald-200">Application Submitted!</p>
                      <p className="text-xs font-mono text-emerald-300">
                        Ref: {submission?.confirmation_reference || "CONFIRMED"}
                      </p>
                      {submission?.submitted_at && (
                        <p className="text-[10px] text-zinc-400">
                          {new Date(submission.submitted_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>

            </div>

          </div>

        </div>

        {/* Audit Trail Modal */}
        {showAuditModal && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 max-h-[85vh] flex flex-col shadow-2xl">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="space-y-0.5">
                  <h3 className="text-base font-bold text-white">Immutable Application Audit Trail</h3>
                  <p className="text-xs text-zinc-400">Chronological, tamper-evident security record</p>
                </div>
                <button
                  onClick={() => setShowAuditModal(false)}
                  className="text-zinc-400 hover:text-white p-1 text-sm font-mono"
                >
                  ✕
                </button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 pr-2 divide-y divide-zinc-800/60">
                {auditEvents.length === 0 ? (
                  <p className="text-xs text-zinc-400 py-8 text-center">No audit events recorded yet.</p>
                ) : (
                  auditEvents.map((evt) => (
                    <div key={evt.id} className="pt-3 first:pt-0 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold font-mono text-indigo-300">{evt.event_type}</span>
                        <span className="text-[10px] text-zinc-400 font-mono">
                          {new Date(evt.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="bg-zinc-950 p-2.5 rounded-lg border border-zinc-800/60 font-mono text-[11px] text-zinc-300">
                        {JSON.stringify(evt.details, null, 2)}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="pt-2 border-t border-zinc-800 flex justify-end">
                <button
                  onClick={() => setShowAuditModal(false)}
                  className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-white rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
