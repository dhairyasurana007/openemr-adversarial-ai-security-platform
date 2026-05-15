import { useState } from "react";

import { PipelineBar } from "./PipelineBar";

export type WorkbenchMode = "manual" | "red_team" | "multi_sequence";
export type TestingMode = "blackbox" | "whitebox";

type GateStep = 1 | 2 | 3;

interface ModeCard {
  id: WorkbenchMode;
  title: string;
  subtitle: string;
  description: string;
  icon: string;
}

const MODES: ModeCard[] = [
  {
    id: "manual",
    title: "Manual Interaction",
    subtitle: "Default",
    description: "Directly interact with the target LLM as a typical user would.",
    icon: "💬",
  },
  {
    id: "red_team",
    title: "Red Team Agent",
    subtitle: "Automated",
    description: "Dispatch automated adversarial campaigns against the target.",
    icon: "⚔",
  },
  {
    id: "multi_sequence",
    title: "Multi-Sequence Attacks",
    subtitle: "Manual / Advanced",
    description: "Build and fire multi-turn attack sequences manually.",
    icon: "⚡",
  },
];

interface Props {
  onStart: (mode: WorkbenchMode, testingMode: TestingMode) => void;
}

function StepIndicator({ current }: { current: GateStep }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      {([1, 2, 3] as GateStep[]).map((n) => (
        <div key={n} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 11,
              fontWeight: 700,
              background: n <= current ? "var(--primary)" : "var(--surface)",
              color: n <= current ? "#fff" : "var(--text-muted)",
              border: `1px solid ${n <= current ? "var(--primary)" : "var(--border)"}`,
              transition: "background 0.2s, border-color 0.2s",
            }}
          >
            {n}
          </div>
          {n < 3 && (
            <div
              style={{
                width: 32,
                height: 1,
                background: n < current ? "var(--primary)" : "var(--border)",
                transition: "background 0.2s",
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function SelectionCard({
  isSelected,
  onClick,
  children,
}: {
  isSelected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        background: isSelected ? "var(--primary-dim)" : "var(--card)",
        border: `1px solid ${isSelected ? "var(--primary)" : "var(--border)"}`,
        borderRadius: "var(--radius-lg)",
        padding: "1.25rem 1rem",
        cursor: "pointer",
        textAlign: "left",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        transition: "border-color 0.15s, background 0.15s",
        outline: "none",
        width: "100%",
      }}
    >
      {children}
    </button>
  );
}

export function SessionGate({ onStart }: Props) {
  const [step, setStep] = useState<GateStep>(1);
  const [testingMode, setTestingMode] = useState<TestingMode>("blackbox");
  const [workbenchMode, setWorkbenchMode] = useState<WorkbenchMode>("manual");

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "70vh",
        gap: "2rem",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div className="page-title" style={{ marginBottom: "0.75rem" }}>Workbench</div>
        <StepIndicator current={step} />
      </div>

      {/* ── Step 1: Logging notice ── */}
      {step === 1 && (
        <div
          style={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "2rem",
            maxWidth: 480,
            width: "100%",
            display: "flex",
            flexDirection: "column",
            gap: "1.5rem",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 32 }}>⚠</div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text)", marginBottom: "0.5rem" }}>
              Session Logging Notice
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              This session will be logged for security testing purposes.
            </div>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            style={{ alignSelf: "center", minWidth: 160 }}
            onClick={() => setStep(2)}
          >
            I acknowledge
          </button>
        </div>
      )}

      {/* ── Step 2: Testing mode ── */}
      {step === 2 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1.5rem",
            width: "100%",
            maxWidth: 560,
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text)", marginBottom: "0.25rem" }}>
              Select Testing Mode
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
              This applies to all attack activity in this session.
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", width: "100%" }}>
            <SelectionCard isSelected={testingMode === "blackbox"} onClick={() => setTestingMode("blackbox")}>
              <div style={{ fontWeight: 600, color: testingMode === "blackbox" ? "var(--primary)" : "var(--text)", fontSize: 14 }}>{testingMode === "blackbox" ? "\u2713 " : ""}Blackbox</div>
              <div style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                No internal knowledge. Test the target as an external attacker would — external API only.
              </div>
            </SelectionCard>

            <SelectionCard isSelected={testingMode === "whitebox"} onClick={() => setTestingMode("whitebox")}>
              <div style={{ fontWeight: 600, color: testingMode === "whitebox" ? "var(--primary)" : "var(--text)", fontSize: 14 }}>{testingMode === "whitebox" ? "\u2713 " : ""}Whitebox</div>
              <div style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                Full access to internals. Test with knowledge of system prompts, source code, and architecture.
              </div>
            </SelectionCard>
          </div>

          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep(1)}>
              Back
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ minWidth: 140 }}
              onClick={() => setStep(3)}
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Workbench mode ── */}
      {step === 3 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1.5rem",
            width: "100%",
            maxWidth: 720,
          }}
        >
          <div style={{ width: "100%" }}>
            <PipelineBar mode={workbenchMode} phase="gate" hasActivity={false} findingCount={0} />
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text)", marginBottom: "0.25rem" }}>
              Select Workbench Mode
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
              Testing as:{" "}
              <span style={{ color: "var(--primary)", fontWeight: 600, textTransform: "capitalize" }}>
                {testingMode}
              </span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", width: "100%" }}>
            {MODES.map((mode) => {
              const isSelected = workbenchMode === mode.id;
              return (
                <SelectionCard key={mode.id} isSelected={isSelected} onClick={() => setWorkbenchMode(mode.id)}>
                  <div style={{ fontSize: 22 }}>{mode.icon}</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, color: isSelected ? "var(--primary)" : "var(--text)", fontSize: 14 }}>
                      {mode.title}
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        letterSpacing: "0.05em",
                        textTransform: "uppercase",
                        color: isSelected ? "var(--primary)" : "var(--text-muted)",
                      }}
                    >
                      {mode.subtitle}
                    </span>
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {mode.description}
                  </div>
                </SelectionCard>
              );
            })}
          </div>

          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep(2)}>
              Back
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ minWidth: 160, padding: "0.6rem 1.5rem", fontSize: 14 }}
              onClick={() => onStart(workbenchMode, testingMode)}
            >
              Start Session
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

