"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";

interface BrowserField {
  field_id: string;
  name: string | null;
  label: string | null;
  input_type: string;
  placeholder: string | null;
  selector: string;
  required: boolean;
  options: string[];
  visible: boolean;
  enabled: boolean;
  value: string | null;
}

interface ScreenshotMetadata {
  id: string;
  step: string;
  url: string;
  timestamp: string;
  filename: string;
  relative_path: string;
}

interface ExecutionStateSnapshot {
  application_id: string;
  session_id?: string;
  current_url?: string;
  current_step: string;
  state: string;
  auth_status: string;
  challenge_type: string;
  user_action_required: boolean;
  user_action_reason?: string;
  user_instructions?: string;
  discovered_fields: BrowserField[];
  executed_actions_count: number;
  total_actions_count: number;
  warnings: string[];
  screenshots: ScreenshotMetadata[];
  started_at?: string;
  updated_at: string;
}

export default function BrowserExecutionDashboard() {
  const params = useParams();
  const applicationId = (params?.id as string) || "app_demo_001";

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [execution, setExecution] = useState<ExecutionStateSnapshot>({
    application_id: applicationId,
    session_id: "bsess_demo_active",
    current_url: "https://boards.greenhouse.io/company/jobs/4019283",
    current_step: "ready_for_review",
    state: "READY_FOR_REVIEW",
    auth_status: "AUTHENTICATED",
    challenge_type: "NONE",
    user_action_required: false,
    user_action_reason: undefined,
    user_instructions: undefined,
    discovered_fields: [
      {
        field_id: "first_name",
        name: "first_name",
        label: "First Name",
        input_type: "text",
        placeholder: "Enter your first name",
        selector: "#first_name",
        required: true,
        options: [],
        visible: true,
        enabled: true,
        value: "Ada",
      },
      {
        field_id: "last_name",
        name: "last_name",
        label: "Last Name",
        input_type: "text",
        placeholder: "Enter your last name",
        selector: "#last_name",
        required: true,
        options: [],
        visible: true,
        enabled: true,
        value: "Lovelace",
      },
      {
        field_id: "email",
        name: "email",
        label: "Email Address",
        input_type: "email",
        placeholder: "you@example.com",
        selector: "#email",
        required: true,
        options: [],
        visible: true,
        enabled: true,
        value: "ada@example.com",
      },
      {
        field_id: "resume",
        name: "resume",
        label: "Attach Resume / CV",
        input_type: "file",
        placeholder: null,
        selector: "#resume_upload",
        required: true,
        options: [],
        visible: true,
        enabled: true,
        value: "resume_primary.pdf",
      },
      {
        field_id: "work_auth",
        name: "work_auth",
        label: "Are you authorized to work in the US?",
        input_type: "select",
        placeholder: null,
        selector: "#work_auth",
        required: true,
        options: ["Yes", "No"],
        visible: true,
        enabled: true,
        value: null,
      },
    ],
    executed_actions_count: 4,
    total_actions_count: 5,
    warnings: [
      "Work authorization question requires manual candidate verification before proceeding.",
    ],
    screenshots: [
      {
        id: "scr_initial_01",
        step: "form_initial",
        url: "https://boards.greenhouse.io/company/jobs/4019283",
        timestamp: new Date().toISOString(),
        filename: `${applicationId}_form_initial.png`,
        relative_path: `storage/screenshots/${applicationId}_form_initial.png`,
      },
      {
        id: "scr_filled_02",
        step: "after_safe_fill",
        url: "https://boards.greenhouse.io/company/jobs/4019283",
        timestamp: new Date().toISOString(),
        filename: `${applicationId}_after_safe_fill.png`,
        relative_path: `storage/screenshots/${applicationId}_after_safe_fill.png`,
      },
    ],
    updated_at: new Date().toISOString(),
  });

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/browser/applications/${applicationId}/execution`, {
        headers: { "X-User-ID": "current_user" },
      });
      if (res.ok) {
        const data = await res.json();
        setExecution(data);
      }
    } catch {
      // Keep state if offline in mock dev mode
    } finally {
      setLoading(false);
    }
  };

  const startExecution = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/browser/applications/${applicationId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": "current_user",
        },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setExecution(data);
      } else {
        const err = await res.json();
        setError(err.detail?.message || "Execution start failed");
      }
    } catch (err: any) {
      setError(err.message || "Failed to contact backend API");
    } finally {
      setLoading(false);
    }
  };

  const resumeExecution = async () => {
    if (!execution.session_id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/browser/sessions/${execution.session_id}/resume`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": "current_user",
        },
        body: JSON.stringify({ application_id: applicationId }),
      });
      if (res.ok) {
        const data = await res.json();
        setExecution(data);
      }
    } catch (err: any) {
      setError(err.message || "Resume failed");
    } finally {
      setLoading(false);
    }
  };

  const pauseExecution = async () => {
    if (!execution.session_id) return;
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/browser/sessions/${execution.session_id}/pause`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": "current_user",
        },
        body: JSON.stringify({ application_id: applicationId }),
      });
      if (res.ok) {
        const data = await res.json();
        setExecution(data);
      }
    } catch (err: any) {
      setError(err.message || "Pause failed");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (state: string) => {
    switch (state) {
      case "READY_FOR_REVIEW":
        return <span className="px-3 py-1 text-xs font-semibold rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">Ready for Review</span>;
      case "USER_ACTION_REQUIRED":
      case "AUTHENTICATION_REQUIRED":
        return <span className="px-3 py-1 text-xs font-semibold rounded-full bg-amber-950 text-amber-300 border border-amber-800 animate-pulse">User Action Required</span>;
      case "FILLING":
      case "UPLOAD_IN_PROGRESS":
      case "NAVIGATING":
        return <span className="px-3 py-1 text-xs font-semibold rounded-full bg-blue-950 text-blue-300 border border-blue-800">Filling in Progress</span>;
      case "PAUSED_FOR_USER":
        return <span className="px-3 py-1 text-xs font-semibold rounded-full bg-slate-800 text-slate-300 border border-slate-700">Paused</span>;
      default:
        return <span className="px-3 py-1 text-xs font-semibold rounded-full bg-slate-900 text-slate-400 border border-slate-800">{state}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-800 pb-6 gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
                Browser Execution Console
              </h1>
              {getStatusBadge(execution.state)}
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Application ID: <span className="font-mono text-slate-300">{applicationId}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchStatus}
              disabled={loading}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-sm font-medium rounded-lg border border-slate-700 transition"
            >
              Refresh
            </button>
            <button
              onClick={pauseExecution}
              disabled={loading}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg border border-slate-600 transition"
            >
              Pause
            </button>
            <button
              onClick={startExecution}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg shadow transition"
            >
              Start Preparation
            </button>
          </div>
        </div>

        {/* Invariant Alert Banner */}
        <div className="bg-slate-900/60 border border-indigo-500/30 rounded-xl p-4 flex items-start gap-4">
          <div className="text-indigo-400 text-lg">🛡️</div>
          <div>
            <h4 className="text-sm font-semibold text-indigo-200">Human-In-The-Loop Security Guard Active</h4>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Phase 7 fills verified fields and uploads your selected resume into a live session. 
              <strong> Final submission is strictly disabled</strong> and reserved for Phase 8 human approval.
            </p>
          </div>
        </div>

        {/* User Action Required Prompt */}
        {execution.user_action_required && (
          <div className="bg-amber-950/40 border border-amber-500/40 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-amber-400 font-bold text-lg">⚠️ Action Required:</span>
              <span className="font-mono text-xs bg-amber-900/60 text-amber-300 px-2 py-0.5 rounded">
                {execution.user_action_reason || "INTERVENTION_NEEDED"}
              </span>
            </div>
            <p className="text-sm text-slate-200">
              {execution.user_instructions || "Please complete authentication, CAPTCHA, or required manual fields in the browser session."}
            </p>
            <button
              onClick={resumeExecution}
              disabled={loading}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium rounded-lg shadow transition"
            >
              I have completed this action — Resume Automation
            </button>
          </div>
        )}

        {/* Execution Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Active Portal URL</span>
            <p className="text-sm font-mono text-slate-200 mt-2 truncate" title={execution.current_url || ""}>
              {execution.current_url || "Not started"}
            </p>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Browser Session ID</span>
            <p className="text-sm font-mono text-slate-200 mt-2">
              {execution.session_id || "No active session"}
            </p>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Field Automation Progress</span>
            <div className="flex items-center justify-between mt-2">
              <span className="text-lg font-bold text-indigo-400">
                {execution.executed_actions_count} / {execution.total_actions_count} Fields
              </span>
              <span className="text-xs text-slate-400">
                {execution.total_actions_count ? Math.round((execution.executed_actions_count / execution.total_actions_count) * 100) : 0}%
              </span>
            </div>
          </div>
        </div>

        {/* Discovered Form Fields Table */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex justify-between items-center">
            <h3 className="text-base font-semibold text-white">Inspected Form Fields</h3>
            <span className="text-xs text-slate-400">{execution.discovered_fields.length} detected fields</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Label / Name</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Selector</th>
                  <th className="px-6 py-3">Value Loaded</th>
                  <th className="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {execution.discovered_fields.map((f, i) => (
                  <tr key={i} className="hover:bg-slate-800/30">
                    <td className="px-6 py-4 font-medium text-white flex items-center gap-2">
                      {f.label || f.name}
                      {f.required && <span className="text-rose-400 text-xs">*</span>}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-400">{f.input_type}</td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-400 truncate max-w-xs">{f.selector}</td>
                    <td className="px-6 py-4 text-emerald-400 font-mono text-xs">
                      {f.value || <span className="text-slate-600 italic">Not set</span>}
                    </td>
                    <td className="px-6 py-4">
                      {f.value ? (
                        <span className="px-2 py-0.5 rounded text-xs bg-emerald-950 text-emerald-400 border border-emerald-900">Filled</span>
                      ) : f.required ? (
                        <span className="px-2 py-0.5 rounded text-xs bg-amber-950 text-amber-400 border border-amber-900">User Action</span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-400">Optional</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Visual Checkpoints (Screenshots) */}
        <div className="space-y-4">
          <h3 className="text-base font-semibold text-white">Visual Execution Checkpoints</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {execution.screenshots.map((s, idx) => (
              <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow">
                <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/40">
                  <span className="font-mono text-xs text-indigo-300 font-semibold">{s.step}</span>
                  <span className="text-xs text-slate-500">{new Date(s.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="p-6 bg-slate-950 flex flex-col items-center justify-center min-h-[160px] text-center">
                  <span className="text-3xl mb-2">📸</span>
                  <p className="text-xs font-mono text-slate-400">{s.filename}</p>
                  <p className="text-xs text-slate-600 mt-1">{s.relative_path}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
