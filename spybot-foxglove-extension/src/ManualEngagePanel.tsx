import { PanelExtensionContext, SettingsTreeAction } from "@foxglove/extension";
import {
  ReactElement,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createRoot } from "react-dom/client";

// ─── Types ──────────────────────────────────────────────────────────

interface Vec3 {
  x: number;
  y: number;
  z: number;
}

interface Twist {
  linear: Vec3;
  angular: Vec3;
}

interface Int8Msg {
  data: number;
}

type ScrewDir = -1 | 0 | 1;

interface PanelConfig {
  driveTopic: string;
  screwTopic: string;
  maxLinear: number;
  maxAngular: number;
  publishHz: number;
}

const DEFAULT_CONFIG: PanelConfig = {
  driveTopic: "/cmd_drive",
  screwTopic: "/cmd_screw",
  maxLinear: 1.0,
  maxAngular: 1.0,
  publishHz: 20,
};

// ─── Theme ──────────────────────────────────────────────────────────

interface ThemeColors {
  bg: string;
  bgAlt: string;
  surface: string;
  text: string;
  textMuted: string;
  border: string;
  accent: string;
  accentDim: string;
  success: string;
  warning: string;
  danger: string;
  dangerBg: string;
}

const DARK: ThemeColors = {
  bg: "#0a0a0a",
  bgAlt: "#141414",
  surface: "#1a1a1a",
  text: "#f0f0f0",
  textMuted: "#888",
  border: "#2a2a2a",
  accent: "#4ec9b0",
  accentDim: "#2a5c52",
  success: "#4ec9b0",
  warning: "#e2c044",
  danger: "#ff4e4e",
  dangerBg: "#2a0a0a",
};

const LIGHT: ThemeColors = {
  bg: "#fafafa",
  bgAlt: "#eee",
  surface: "#fff",
  text: "#111",
  textMuted: "#666",
  border: "#ccc",
  accent: "#0a7a6a",
  accentDim: "#9ed9ce",
  success: "#0a7a6a",
  warning: "#8a6b00",
  danger: "#c81f1f",
  dangerBg: "#fbe5e5",
};

function theme(scheme: "light" | "dark"): ThemeColors {
  return scheme === "light" ? LIGHT : DARK;
}

// ─── Helpers ────────────────────────────────────────────────────────

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

function buildTwist(linX: number, angZ: number): Twist {
  return {
    linear: { x: linX, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: angZ },
  };
}

// ─── Joystick component ─────────────────────────────────────────────

interface JoystickProps {
  colors: ThemeColors;
  onChange: (axis: { x: number; y: number }) => void;
  axis: { x: number; y: number };
  size?: number;
}

function Joystick({ colors, onChange, axis, size = 220 }: JoystickProps): ReactElement {
  const ref = useRef<HTMLDivElement | null>(null);
  const [active, setActive] = useState(false);
  const pointerIdRef = useRef<number | null>(null);

  const updateFromClient = useCallback(
    (clientX: number, clientY: number) => {
      const el = ref.current;
      if (!el) {
        return;
      }
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const r = rect.width / 2;
      const dx = (clientX - cx) / r;
      const dy = (clientY - cy) / r;
      const mag = Math.hypot(dx, dy);
      const scale = mag > 1 ? 1 / mag : 1;
      // screen y grows downward → invert for forward-positive
      onChange({ x: clamp(dx * scale, -1, 1), y: clamp(-dy * scale, -1, 1) });
    },
    [onChange],
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      (e.target as Element).setPointerCapture?.(e.pointerId);
      pointerIdRef.current = e.pointerId;
      setActive(true);
      updateFromClient(e.clientX, e.clientY);
    },
    [updateFromClient],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (pointerIdRef.current !== e.pointerId) {
        return;
      }
      updateFromClient(e.clientX, e.clientY);
    },
    [updateFromClient],
  );

  const handlePointerEnd = useCallback(
    (e: React.PointerEvent) => {
      if (pointerIdRef.current !== e.pointerId) {
        return;
      }
      pointerIdRef.current = null;
      setActive(false);
      onChange({ x: 0, y: 0 });
    },
    [onChange],
  );

  const handleX = (axis.x * 0.5 + 0.5) * 100;
  const handleY = (-axis.y * 0.5 + 0.5) * 100;

  return (
    <div
      ref={ref}
      role="application"
      aria-label="Drive joystick"
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: `radial-gradient(circle at 50% 50%, ${colors.surface} 0%, ${colors.bgAlt} 100%)`,
        border: `2px solid ${active ? colors.accent : colors.border}`,
        position: "relative",
        touchAction: "none",
        userSelect: "none",
        cursor: active ? "grabbing" : "grab",
        boxShadow: `inset 0 0 40px rgba(0,0,0,0.4)`,
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onPointerLeave={handlePointerEnd}
    >
      {/* Crosshair */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: "50%",
          height: 1,
          background: colors.border,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: "50%",
          width: 1,
          background: colors.border,
        }}
      />
      {/* Axis labels */}
      <div
        style={{
          position: "absolute",
          top: 8,
          left: 0,
          right: 0,
          textAlign: "center",
          color: colors.textMuted,
          fontSize: 10,
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: 2,
        }}
      >
        FWD
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 8,
          left: 0,
          right: 0,
          textAlign: "center",
          color: colors.textMuted,
          fontSize: 10,
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: 2,
        }}
      >
        REV
      </div>
      {/* Handle */}
      <div
        style={{
          position: "absolute",
          left: `${handleX}%`,
          top: `${handleY}%`,
          width: size * 0.28,
          height: size * 0.28,
          borderRadius: "50%",
          background: active ? colors.accent : colors.accentDim,
          transform: "translate(-50%, -50%)",
          boxShadow: `0 4px 12px rgba(0,0,0,0.5)`,
          border: `2px solid ${colors.bg}`,
          pointerEvents: "none",
          transition: active ? "none" : "left 120ms ease-out, top 120ms ease-out",
        }}
      />
    </div>
  );
}

// ─── Main panel content ─────────────────────────────────────────────

function ManualEngagePanelContent({
  context,
}: {
  context: PanelExtensionContext;
}): ReactElement {
  const [renderDone, setRenderDone] = useState<(() => void) | undefined>();
  const [colorScheme, setColorScheme] = useState<"light" | "dark">("dark");
  const [config, setConfig] = useState<PanelConfig>(() => {
    const saved = context.initialState as Partial<PanelConfig> | undefined;
    return { ...DEFAULT_CONFIG, ...saved };
  });

  const [axis, setAxis] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [screwDir, setScrewDir] = useState<ScrewDir>(0);
  const [lastSentDrive, setLastSentDrive] = useState<{ lin: number; ang: number }>({
    lin: 0,
    ang: 0,
  });
  const [lastSentScrew, setLastSentScrew] = useState<ScrewDir>(0);
  const [estopPulse, setEstopPulse] = useState(0);

  // Refs for stable access inside long-lived handlers
  const configRef = useRef(config);
  const axisRef = useRef(axis);
  const screwDirRef = useRef<ScrewDir>(screwDir);
  const advertisedRef = useRef<{ drive: string | null; screw: string | null }>({
    drive: null,
    screw: null,
  });

  useEffect(() => {
    configRef.current = config;
  }, [config]);
  useEffect(() => {
    axisRef.current = axis;
  }, [axis]);
  useEffect(() => {
    screwDirRef.current = screwDir;
  }, [screwDir]);

  const colors = theme(colorScheme);

  // ─── Advertise topics, re-advertise on topic name change ─────────
  useEffect(() => {
    if (advertisedRef.current.drive !== config.driveTopic) {
      context.advertise?.(config.driveTopic, "geometry_msgs/msg/Twist");
      advertisedRef.current.drive = config.driveTopic;
    }
    if (advertisedRef.current.screw !== config.screwTopic) {
      context.advertise?.(config.screwTopic, "std_msgs/msg/Int8");
      advertisedRef.current.screw = config.screwTopic;
    }
  }, [context, config.driveTopic, config.screwTopic]);

  // ─── Render + colorScheme watch ──────────────────────────────────
  useLayoutEffect(() => {
    context.onRender = (renderState, done) => {
      setRenderDone(() => done);
      if (renderState.colorScheme != null) {
        setColorScheme(renderState.colorScheme);
      }
    };
    context.watch("colorScheme");
  }, [context]);

  useEffect(() => {
    renderDone?.();
  }, [renderDone]);

  // ─── Settings editor ─────────────────────────────────────────────
  useEffect(() => {
    context.updatePanelSettingsEditor({
      nodes: {
        topics: {
          label: "Topics",
          icon: "Cube",
          fields: {
            driveTopic: {
              label: "Drive topic (Twist)",
              input: "string",
              value: config.driveTopic,
              help: "geometry_msgs/Twist published on joystick move",
            },
            screwTopic: {
              label: "Screw topic (Int8)",
              input: "string",
              value: config.screwTopic,
              help: "std_msgs/Int8 with values {-1, 0, +1}",
            },
          },
        },
        limits: {
          label: "Limits",
          icon: "Settings",
          fields: {
            maxLinear: {
              label: "Max linear (m/s equiv)",
              input: "number",
              value: config.maxLinear,
              min: 0.05,
              max: 1.0,
              step: 0.05,
              help: "Scales joystick forward magnitude",
            },
            maxAngular: {
              label: "Max angular",
              input: "number",
              value: config.maxAngular,
              min: 0.05,
              max: 1.0,
              step: 0.05,
              help: "Scales joystick yaw magnitude",
            },
            publishHz: {
              label: "Publish rate (Hz)",
              input: "number",
              value: config.publishHz,
              min: 5,
              max: 60,
              step: 1,
              help: "Max publish rate for drive Twist while joystick active",
            },
          },
        },
      },
      actionHandler: (action: SettingsTreeAction) => {
        if (action.action !== "update") {
          return;
        }
        const { path, value } = action.payload;
        setConfig((prev) => {
          const next = { ...prev };
          if (path[1] === "driveTopic" && typeof value === "string") {
            next.driveTopic = value;
          } else if (path[1] === "screwTopic" && typeof value === "string") {
            next.screwTopic = value;
          } else if (path[1] === "maxLinear" && typeof value === "number") {
            next.maxLinear = clamp(value, 0.05, 1.0);
          } else if (path[1] === "maxAngular" && typeof value === "number") {
            next.maxAngular = clamp(value, 0.05, 1.0);
          } else if (path[1] === "publishHz" && typeof value === "number") {
            next.publishHz = clamp(Math.round(value), 5, 60);
          }
          context.saveState(next);
          return next;
        });
      },
    });
  }, [context, config]);

  // ─── Publishers ──────────────────────────────────────────────────

  const publishDrive = useCallback(
    (linX: number, angZ: number) => {
      const msg: Twist = buildTwist(linX, angZ);
      context.publish?.(configRef.current.driveTopic, msg);
      setLastSentDrive({ lin: linX, ang: angZ });
    },
    [context],
  );

  const publishScrew = useCallback(
    (dir: ScrewDir) => {
      const msg: Int8Msg = { data: dir };
      context.publish?.(configRef.current.screwTopic, msg);
      setLastSentScrew(dir);
    },
    [context],
  );

  // ─── Drive publish loop (only runs while joystick has non-zero intent or just released) ──

  const lastPublishedAxisRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  useEffect(() => {
    const hz = config.publishHz;
    const periodMs = Math.max(1000 / hz, 16);
    let timer: ReturnType<typeof setInterval> | null = null;

    const tick = () => {
      const a = axisRef.current;
      const prev = lastPublishedAxisRef.current;
      const changed =
        Math.abs(a.x - prev.x) > 0.001 || Math.abs(a.y - prev.y) > 0.001;
      // Publish while active OR when we need a final zero after release
      const nonZero = Math.abs(a.x) > 0.001 || Math.abs(a.y) > 0.001;
      const prevNonZero = Math.abs(prev.x) > 0.001 || Math.abs(prev.y) > 0.001;
      if (nonZero || (prevNonZero && !nonZero) || changed) {
        const cfg = configRef.current;
        publishDrive(a.y * cfg.maxLinear, a.x * cfg.maxAngular);
        lastPublishedAxisRef.current = { x: a.x, y: a.y };
      }
    };

    timer = setInterval(tick, periodMs);
    return () => {
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [config.publishHz, publishDrive]);

  // ─── Screw handlers ──────────────────────────────────────────────

  const pressScrew = useCallback(
    (dir: ScrewDir) => {
      setScrewDir(dir);
      publishScrew(dir);
    },
    [publishScrew],
  );

  const releaseScrew = useCallback(() => {
    if (screwDirRef.current !== 0) {
      setScrewDir(0);
      publishScrew(0);
    }
  }, [publishScrew]);

  // ─── E-STOP ──────────────────────────────────────────────────────

  const handleEStop = useCallback(() => {
    setAxis({ x: 0, y: 0 });
    lastPublishedAxisRef.current = { x: 0, y: 0 };
    publishDrive(0, 0);
    releaseScrew();
    setEstopPulse((n) => n + 1);
  }, [publishDrive, releaseScrew]);

  // ─── Keyboard controls ───────────────────────────────────────────

  const keysDownRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const recalc = () => {
      const k = keysDownRef.current;
      const x = (k.has("a") ? -1 : 0) + (k.has("d") ? 1 : 0);
      const y = (k.has("w") ? 1 : 0) + (k.has("s") ? -1 : 0);
      setAxis({ x, y });
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.repeat) {
        return;
      }
      const key = e.key.toLowerCase();
      if (["w", "a", "s", "d"].includes(key)) {
        keysDownRef.current.add(key);
        recalc();
        e.preventDefault();
      } else if (key === "r") {
        pressScrew(1);
        e.preventDefault();
      } else if (key === "f") {
        pressScrew(-1);
        e.preventDefault();
      } else if (key === " " || key === "escape") {
        handleEStop();
        e.preventDefault();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (["w", "a", "s", "d"].includes(key)) {
        keysDownRef.current.delete(key);
        recalc();
      } else if (key === "r" || key === "f") {
        releaseScrew();
      }
    };

    const handleBlur = () => {
      keysDownRef.current.clear();
      setAxis({ x: 0, y: 0 });
      releaseScrew();
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", handleBlur);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", handleBlur);
    };
  }, [pressScrew, releaseScrew, handleEStop]);

  // ─── Safety: zero-out on unmount ────────────────────────────────
  useEffect(() => {
    return () => {
      try {
        context.publish?.(configRef.current.driveTopic, buildTwist(0, 0));
        context.publish?.(configRef.current.screwTopic, { data: 0 });
      } catch {
        // ignore — panel tearing down
      }
    };
  }, [context]);

  // ─── Render ─────────────────────────────────────────────────────

  const linOut = axis.y * config.maxLinear;
  const angOut = axis.x * config.maxAngular;

  return (
    <div
      style={{
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        background: colors.bg,
        color: colors.text,
        height: "100%",
        overflow: "auto",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: `2px solid ${colors.accent}`,
          paddingBottom: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 18 }}>🕶️</span>
          <span
            style={{
              fontSize: 14,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: 2,
              color: colors.accent,
            }}
          >
            Spy Bot — Manual Engage
          </span>
        </div>
        <span style={{ fontSize: 10, color: colors.textMuted }}>
          T2 · drive_bridge over serial
        </span>
      </div>

      {/* Status strip */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          fontSize: 11,
        }}
      >
        <StatusCell
          label="linear.x"
          value={linOut.toFixed(2)}
          colors={colors}
          highlight={Math.abs(linOut) > 0.01}
        />
        <StatusCell
          label="angular.z"
          value={angOut.toFixed(2)}
          colors={colors}
          highlight={Math.abs(angOut) > 0.01}
        />
        <StatusCell
          label="screw"
          value={screwDir === 1 ? "+1 UP" : screwDir === -1 ? "-1 DOWN" : "0 idle"}
          colors={colors}
          highlight={screwDir !== 0}
        />
      </div>

      {/* Controls row */}
      <div style={{ display: "flex", gap: 20, alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <Joystick colors={colors} axis={axis} onChange={setAxis} />
          <div style={{ fontSize: 10, color: colors.textMuted, letterSpacing: 1 }}>
            drag · or WASD
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <ScrewButton
            label="▲ SCREW UP"
            hotkey="R"
            colors={colors}
            active={screwDir === 1}
            onDown={() => pressScrew(1)}
            onUp={releaseScrew}
          />
          <ScrewButton
            label="▼ SCREW DOWN"
            hotkey="F"
            colors={colors}
            active={screwDir === -1}
            onDown={() => pressScrew(-1)}
            onUp={releaseScrew}
          />
        </div>
      </div>

      {/* E-STOP */}
      <button
        type="button"
        onClick={handleEStop}
        style={{
          padding: "18px 20px",
          fontSize: 16,
          fontWeight: 800,
          fontFamily: "inherit",
          textTransform: "uppercase",
          letterSpacing: 3,
          background: colors.dangerBg,
          border: `3px solid ${colors.danger}`,
          color: colors.danger,
          cursor: "pointer",
          boxShadow:
            estopPulse > 0 ? `0 0 0 4px ${colors.danger}40` : `inset 0 0 16px ${colors.danger}20`,
          transition: "box-shadow 300ms",
        }}
      >
        🛑 E-STOP (space)
      </button>

      {/* Last-published */}
      <div
        style={{
          fontSize: 10,
          color: colors.textMuted,
          borderTop: `1px solid ${colors.border}`,
          paddingTop: 8,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 4,
        }}
      >
        <span>
          last Twist → {config.driveTopic}: lin=
          {lastSentDrive.lin.toFixed(2)} ang={lastSentDrive.ang.toFixed(2)}
        </span>
        <span>
          last Int8 → {config.screwTopic}: {lastSentScrew}
        </span>
      </div>

      {/* Safety note */}
      <div
        style={{
          fontSize: 10,
          color: colors.textMuted,
          fontStyle: "italic",
          lineHeight: 1.5,
        }}
      >
        RC transmitter overrides serial when channels live. Firmware zero-clamps on 500 ms
        silence. Tap screw buttons near mechanical limits — watchdog is the backstop.
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────

function StatusCell({
  label,
  value,
  colors,
  highlight,
}: {
  label: string;
  value: string;
  colors: ThemeColors;
  highlight?: boolean;
}): ReactElement {
  return (
    <div
      style={{
        padding: "6px 10px",
        background: colors.surface,
        border: `1px solid ${highlight ? colors.accent : colors.border}`,
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      <span style={{ color: colors.textMuted, fontSize: 9, letterSpacing: 1 }}>
        {label.toUpperCase()}
      </span>
      <span
        style={{
          color: highlight ? colors.accent : colors.text,
          fontSize: 13,
          fontWeight: 600,
        }}
      >
        {value}
      </span>
    </div>
  );
}

interface ScrewButtonProps {
  label: string;
  hotkey: string;
  colors: ThemeColors;
  active: boolean;
  onDown: () => void;
  onUp: () => void;
}

function ScrewButton({
  label,
  hotkey,
  colors,
  active,
  onDown,
  onUp,
}: ScrewButtonProps): ReactElement {
  const handleDown = (e: React.PointerEvent) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    onDown();
  };
  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={active}
      onPointerDown={handleDown}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      onPointerLeave={onUp}
      style={{
        padding: "18px 24px",
        minWidth: 180,
        fontSize: 13,
        fontWeight: 700,
        textAlign: "center",
        fontFamily: "inherit",
        textTransform: "uppercase",
        letterSpacing: 2,
        background: active ? colors.accent : colors.surface,
        border: `2px solid ${active ? colors.accent : colors.border}`,
        color: active ? colors.bg : colors.text,
        cursor: "pointer",
        userSelect: "none",
        touchAction: "none",
        transition: "background 80ms, color 80ms",
      }}
    >
      <div>{label}</div>
      <div
        style={{
          fontSize: 9,
          marginTop: 4,
          color: active ? colors.bg : colors.textMuted,
          letterSpacing: 1,
        }}
      >
        hold · [{hotkey}]
      </div>
    </div>
  );
}

// ─── Panel entry ────────────────────────────────────────────────────

export function initManualEngagePanel(context: PanelExtensionContext): () => void {
  const root = createRoot(context.panelElement);
  root.render(<ManualEngagePanelContent context={context} />);
  return () => {
    root.unmount();
  };
}
