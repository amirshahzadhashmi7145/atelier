import type { Snapshot } from "@/lib/types";

export type DeskId = "pm" | "backend" | "frontend" | "ai_engineer" | "qa";

export type Gender = "male" | "female";

export type Desk = {
  id: DeskId;
  /** Honorific + full name, e.g. "Ms. Fatima Siddiqui" */
  label: string;
  title: string;
  name: string;
  gender: Gender;
  /** Job title shown under the name */
  roleTitle: string;
  role: string;
  x: number;
  z: number;
  skin: string;
  hair: string;
};

export const DESKS: Desk[] = [
  {
    id: "pm",
    title: "Ms.",
    name: "Fatima Siddiqui",
    label: "Ms. Fatima Siddiqui",
    gender: "female",
    roleTitle: "Project Manager",
    role: "pm",
    x: -2.4,
    z: -2.8,
    skin: "#c68642",
    hair: "#1c1915",
  },
  {
    id: "backend",
    title: "Mr.",
    name: "Ali Raza",
    label: "Mr. Ali Raza",
    gender: "male",
    roleTitle: "Backend Engineer",
    role: "backend",
    x: 0.8,
    z: -2.8,
    skin: "#d4a574",
    hair: "#2a2420",
  },
  {
    id: "frontend",
    title: "Ms.",
    name: "Ayesha Khan",
    label: "Ms. Ayesha Khan",
    gender: "female",
    roleTitle: "Frontend Engineer",
    role: "frontend",
    x: 3.8,
    z: -2.8,
    skin: "#e0b080",
    hair: "#3d2914",
  },
  {
    id: "ai_engineer",
    title: "Mr.",
    name: "Hassan Mirza",
    label: "Mr. Hassan Mirza",
    gender: "male",
    roleTitle: "AI Engineer",
    role: "ai_engineer",
    x: -2.4,
    z: 1.6,
    skin: "#a67c52",
    hair: "#1a1614",
  },
  {
    id: "qa",
    title: "Ms.",
    name: "Sana Malik",
    label: "Ms. Sana Malik",
    gender: "female",
    roleTitle: "QA Lead",
    role: "qa",
    x: 2.2,
    z: 1.6,
    skin: "#c9956c",
    hair: "#2c1810",
  },
];

/** Shared hangout props in the room. */
export const SPOTS = {
  coffeeMachine: { x: 5.4, z: 3.0 },
  coffeeSip: { x: 4.6, z: 3.5 },
  waterCooler: { x: -5.6, z: 3.2 },
  whiteboard: { x: -5.0, z: -4.4 },
  plant: { x: -6.2, z: 3.8 },
  stretch: { x: 0.4, z: 0.2 },
  snack: { x: 5.0, z: 2.2 },
  /** Game corner (front-left) — players on opposite long sides of the table. */
  foosball: { x: -2.15, z: 3.5 },
  foosballB: { x: -2.15, z: 4.8 },
  reading: { x: -5.8, z: -1.2 },
  microwave: { x: 6.2, z: 1.4 },
  beanbag: { x: -4.2, z: 2.4 },
  phone: { x: -0.6, z: -0.8 },
  /** Outdoor patio — smokers hang here. */
  smoke: { x: 6.4, z: -4.2 },
  smokeB: { x: 5.6, z: -4.6 },
  /** Floor staff anchors */
  reception: { x: 3.8, z: 4.55 },
  printer: { x: 6.4, z: 0.2 },
  trashA: { x: -3.5, z: -4.6 },
  trashB: { x: 5.8, z: 3.8 },
  supply: { x: -7.1, z: 2.2 },
} as const;

export type StaffId = "office_boy" | "receptionist" | "pantry";

export type StaffMember = {
  id: StaffId;
  title: string;
  name: string;
  label: string;
  gender: Gender;
  roleTitle: string;
  skin: string;
  hair: string;
  shirt: string;
  pants: string;
  blazer: string | null;
  shoe: string;
  /** Home / idle position */
  home: { x: number; z: number };
};

/** Support crew — not tied to project desks. */
export const STAFF: StaffMember[] = [
  {
    id: "office_boy",
    title: "Mr.",
    name: "Bilal Hussain",
    label: "Mr. Bilal Hussain",
    gender: "male",
    roleTitle: "Office Boy",
    skin: "#c68642",
    hair: "#1a1614",
    shirt: "#1e3a5f",
    pants: "#1a1f28",
    blazer: null,
    shoe: "#141210",
    home: { x: 5.0, z: 3.4 },
  },
  {
    id: "receptionist",
    title: "Ms.",
    name: "Zara Ahmed",
    label: "Ms. Zara Ahmed",
    gender: "female",
    roleTitle: "Reception",
    skin: "#e0b080",
    hair: "#2c1810",
    shirt: "#5c3d2e",
    pants: "#2a2430",
    blazer: "#3d2918",
    shoe: "#1a1410",
    home: { x: SPOTS.reception.x, z: SPOTS.reception.z },
  },
  {
    id: "pantry",
    title: "Ms.",
    name: "Nadia Khan",
    label: "Ms. Nadia Khan",
    gender: "female",
    roleTitle: "Pantry Attendant",
    skin: "#d4a574",
    hair: "#1c1915",
    shirt: "#6b3a2a",
    pants: "#2a2018",
    blazer: null,
    shoe: "#1c1915",
    home: { x: SPOTS.coffeeMachine.x - 0.6, z: SPOTS.coffeeMachine.z + 0.5 },
  },
];

export type StaffDuty =
  | "home"
  | "desk_round"
  | "printer"
  | "trash"
  | "pantry"
  | "reception"
  | "meeting"
  | "chai"
  | "water"
  | "files"
  | "snack_restock";

export type StaffView = {
  id: StaffId;
  label: string;
  title: string;
  name: string;
  gender: Gender;
  roleTitle: string;
  activity: string;
  duty: StaffDuty;
  dutyLabel: string;
  skin: string;
  hair: string;
  shirt: string;
  pants: string;
  blazer: string | null;
  shoe: string;
  dialogue?: string;
  holdTray: boolean;
};

export const COFFEE = SPOTS.coffeeMachine;

export type FunKind =
  | "brew"
  | "sip"
  | "water"
  | "board"
  | "plant"
  | "stretch"
  | "snack"
  | "foosball"
  | "read"
  | "microwave"
  | "nap"
  | "phone"
  | "plane"
  | "celebrate"
  | "smoke"
  | null;

export type AgentView = {
  id: DeskId;
  label: string;
  title: string;
  name: string;
  gender: Gender;
  roleTitle: string;
  state: "idle" | "working" | "waiting" | "blocked" | "done";
  activity: string;
  color: string;
  skin: string;
  hair: string;
  taskKey?: string;
  updatedAt?: string;
  /** Overlay line when they are on a break animation. */
  funLabel?: string;
  /** Floating speech bubble text (rotates). */
  dialogue?: string;
};

function personFromDesk(desk: Desk) {
  return {
    id: desk.id,
    label: desk.label,
    title: desk.title,
    name: desk.name,
    gender: desk.gender,
    roleTitle: desk.roleTitle,
    color: COLORS[desk.id],
    skin: desk.skin,
    hair: desk.hair,
  };
}

export type ChatLine = {
  id: string;
  from: string;
  text: string;
  at: number;
};

const COLORS: Record<DeskId, string> = {
  pm: "#8b3a1a",
  backend: "#243d32",
  frontend: "#2f4458",
  ai_engineer: "#5a4a28",
  qa: "#3a5c18",
};

const FUN_LABELS: Record<Exclude<FunKind, null>, string> = {
  brew: "Making coffee",
  sip: "Coffee break",
  water: "Getting water",
  board: "Whiteboard thinking",
  plant: "Watering the plant",
  stretch: "Stretching",
  snack: "Snack run",
  foosball: "Foosball",
  read: "Quiet reading",
  microwave: "Heating lunch",
  nap: "Resting eyes",
  phone: "On a call",
  plane: "Paper plane break",
  celebrate: "Small win",
  smoke: "Patio break",
};

function normalizeRole(role: string): DeskId | null {
  const key = role.toLowerCase().replaceAll(" ", "_");
  if (key === "pm" || key === "project_manager") return "pm";
  if (key === "backend") return "backend";
  if (key === "frontend") return "frontend";
  if (key === "ai_engineer" || key === "ai") return "ai_engineer";
  if (key === "qa" || key === "qa_engineer") return "qa";
  return null;
}

export function demoAgents(): AgentView[] {
  return DESKS.map((desk) => ({
    ...personFromDesk(desk),
    state: "idle" as const,
    activity: "No projects yet — Coders Alley break-room mode",
  }));
}

const STATE_RANK: Record<AgentView["state"], number> = {
  working: 4,
  blocked: 3,
  waiting: 2,
  done: 1,
  idle: 0,
};

/**
 * Merge every project into one floor: each desk shows the hottest work
 * across Atelier, not a single picked board.
 */
export function agentsFromSnapshots(snapshots: Snapshot[]): AgentView[] {
  if (!snapshots.length) return demoAgents();
  if (snapshots.length === 1) return agentsFromSnapshot(snapshots[0]);

  const ranked = snapshots.map((snapshot) => ({
    name: snapshot.project.name,
    agents: agentsFromSnapshot(snapshot),
  }));

  return DESKS.map((desk) => {
    const rows = ranked
      .map((row) => {
        const agent = row.agents.find((item) => item.id === desk.id);
        return agent ? { projectName: row.name, agent } : null;
      })
      .filter((row): row is { projectName: string; agent: AgentView } => row != null)
      .sort((a, b) => {
        const byState = STATE_RANK[b.agent.state] - STATE_RANK[a.agent.state];
        if (byState !== 0) return byState;
        return (b.agent.updatedAt || "").localeCompare(a.agent.updatedAt || "");
      });

    const top = rows[0];
    if (!top) {
      return {
        ...personFromDesk(desk),
        state: "idle" as const,
        activity: "No assigned work yet",
      };
    }

    const active = rows.filter(
      (row) =>
        row.agent.state === "working" ||
        row.agent.state === "blocked" ||
        row.agent.state === "waiting",
    );
    const extra =
      active.length > 1 ? ` · +${active.length - 1} more project${active.length > 2 ? "s" : ""}` : "";

    return {
      ...top.agent,
      activity: `${top.projectName}: ${top.agent.activity}${extra}`,
    };
  });
}

export function agentsFromSnapshot(snapshot: Snapshot): AgentView[] {
  const { project, tasks, events } = snapshot;
  const stage = project.stage;
  const planning = stage !== "tasks_ready";

  const latestEventAt = events.reduce((max, event) => {
    return event.occurred_at > max ? event.occurred_at : max;
  }, "");

  const latestByRole = new Map<string, { summary: string; at: string }>();
  for (const event of [...events].sort((a, b) => (a.occurred_at < b.occurred_at ? 1 : -1))) {
    const role = event.actor_role ? normalizeRole(event.actor_role) : null;
    if (!role || latestByRole.has(role)) continue;
    const summary =
      typeof event.payload?.summary === "string"
        ? event.payload.summary
        : typeof event.payload?.key === "string"
          ? `${event.type}: ${event.payload.key}`
          : event.type.replaceAll(".", " ");
    latestByRole.set(role, { summary, at: event.occurred_at });
  }

  const reviewing = tasks.find((task) => task.state === "in_review");
  const implementing = tasks.find((task) => task.state === "in_progress");
  const gated = tasks.find((task) => task.state === "gated" || task.state === "changes_requested");

  return DESKS.map((desk) => {
    const base = { ...personFromDesk(desk), updatedAt: latestEventAt };

    if (desk.id === "pm") {
      if (planning) {
        const hint = latestByRole.get("pm");
        return {
          ...base,
          state: "working" as const,
          activity: hint?.summary || `Planning · stage ${stage.replaceAll("_", " ")}`,
          updatedAt: hint?.at || latestEventAt,
        };
      }
      const stalled = tasks.filter((task) => task.state === "escalated" || task.state === "blocked");
      if (stalled.length) {
        return {
          ...base,
          state: "blocked" as const,
          activity: `Escalation: ${stalled.map((t) => t.key).join(", ")}`,
          taskKey: stalled[0].key,
        };
      }
      if (project.paused || project.agents_revoked) {
        return {
          ...base,
          state: "waiting" as const,
          activity: project.paused ? "Project paused — waiting on you" : "Agents revoked — waiting on you",
        };
      }
      return {
        ...base,
        state: "waiting" as const,
        activity: implementing
          ? `Monitoring ${implementing.key}`
          : reviewing
            ? `Waiting on QA for ${reviewing.key}`
            : "Plan ready — monitoring Coders Alley",
      };
    }

    if (desk.id === "qa") {
      if (reviewing) {
        return {
          ...base,
          state: "working" as const,
          activity: `Reviewing ${reviewing.key}: ${reviewing.title}`,
          taskKey: reviewing.key,
          updatedAt: latestByRole.get("qa")?.at || latestEventAt,
        };
      }
      if (gated) {
        return {
          ...base,
          state: "waiting" as const,
          activity: `${gated.key} waiting on merge gate`,
          taskKey: gated.key,
        };
      }
      if (implementing) {
        return {
          ...base,
          state: "waiting" as const,
          activity: `Queued — ${implementing.key} still implementing`,
        };
      }
      return {
        ...base,
        state: "idle" as const,
        activity: latestByRole.get("qa")?.summary || "No review in queue",
        updatedAt: latestByRole.get("qa")?.at || latestEventAt,
      };
    }

    const zoneTasks = tasks.filter((task) => task.zone === desk.role && !task.source_task_id);
    const mineInProgress = zoneTasks.find((task) => task.state === "in_progress");
    const mineReady = zoneTasks.find((task) => task.state === "ready");
    const mineBlocked = zoneTasks.find((task) => task.state === "blocked" || task.state === "escalated");
    const mineRework = zoneTasks.find((task) => task.state === "changes_requested");
    const mineDone =
      zoneTasks.length > 0 && zoneTasks.every((task) => task.state === "done" || task.state === "cancelled");

    if (mineInProgress) {
      return {
        ...base,
        state: "working" as const,
        activity: `Implementing ${mineInProgress.key}: ${mineInProgress.title}`,
        taskKey: mineInProgress.key,
        updatedAt: latestByRole.get(desk.role)?.at || latestEventAt,
      };
    }
    if (mineRework) {
      return {
        ...base,
        state: "waiting" as const,
        activity: `${mineRework.key} sent back — waiting to re-run`,
        taskKey: mineRework.key,
      };
    }
    if (reviewing && reviewing.zone === desk.role) {
      return {
        ...base,
        state: "waiting" as const,
        activity: `${reviewing.key} with QA`,
        taskKey: reviewing.key,
      };
    }
    if (mineBlocked) {
      return {
        ...base,
        state: "blocked" as const,
        activity: `${mineBlocked.key} blocked/escalated`,
        taskKey: mineBlocked.key,
      };
    }
    if (mineReady) {
      return {
        ...base,
        state: "waiting" as const,
        activity: `${mineReady.key} ready — waiting for Run next`,
        taskKey: mineReady.key,
      };
    }
    if (mineDone) {
      return {
        ...base,
        state: "done" as const,
        activity: "Zone complete",
      };
    }
    if (!zoneTasks.length && planning) {
      return {
        ...base,
        state: "idle" as const,
        activity: "Waiting for task breakdown",
      };
    }
    return {
      ...base,
      state: "idle" as const,
      activity: latestByRole.get(desk.role)?.summary || "No assigned work yet",
      updatedAt: latestByRole.get(desk.role)?.at || latestEventAt,
    };
  });
}

export type PoseTarget = {
  x: number;
  z: number;
  sit: boolean;
  faceDesk: boolean;
  fun: FunKind;
  holdCup: boolean;
};

type FunSlot = { fun: Exclude<FunKind, null>; x: number; z: number; holdCup: boolean; sit?: boolean };

const FUN_ROTATION: FunSlot[] = [
  { fun: "brew", x: SPOTS.coffeeMachine.x, z: SPOTS.coffeeMachine.z, holdCup: true },
  { fun: "sip", x: SPOTS.coffeeSip.x, z: SPOTS.coffeeSip.z, holdCup: true },
  { fun: "snack", x: SPOTS.snack.x, z: SPOTS.snack.z, holdCup: false },
  { fun: "water", x: SPOTS.waterCooler.x, z: SPOTS.waterCooler.z, holdCup: false },
  { fun: "board", x: SPOTS.whiteboard.x, z: SPOTS.whiteboard.z, holdCup: false },
  { fun: "plant", x: SPOTS.plant.x, z: SPOTS.plant.z, holdCup: false },
  { fun: "stretch", x: SPOTS.stretch.x, z: SPOTS.stretch.z, holdCup: false },
  { fun: "foosball", x: SPOTS.foosball.x, z: SPOTS.foosball.z, holdCup: false },
  { fun: "read", x: SPOTS.reading.x, z: SPOTS.reading.z, holdCup: false, sit: true },
  { fun: "microwave", x: SPOTS.microwave.x, z: SPOTS.microwave.z, holdCup: false },
  { fun: "nap", x: SPOTS.beanbag.x, z: SPOTS.beanbag.z, holdCup: false, sit: true },
  { fun: "phone", x: SPOTS.phone.x, z: SPOTS.phone.z, holdCup: false },
  { fun: "plane", x: SPOTS.stretch.x + 0.8, z: SPOTS.stretch.z - 0.4, holdCup: false },
  { fun: "smoke", x: SPOTS.smoke.x, z: SPOTS.smoke.z, holdCup: false },
];

/** Seconds per break activity — long holds so movement stays calm. */
const LOOP = 120;
const STRESS_LOOP = 80;
const DIALOGUE_BEAT = 18;

const SMOKE_SLOT: FunSlot = {
  fun: "smoke",
  x: SPOTS.smoke.x,
  z: SPOTS.smoke.z,
  holdCup: false,
};

/** Casual breaks — not while actively implementing. */
function canBreak(state: AgentView["state"]) {
  return state === "idle" || state === "waiting" || state === "done" || state === "blocked";
}

function smokeSlot(index: number): FunSlot {
  return index % 2 === 0
    ? SMOKE_SLOT
    : { fun: "smoke", x: SPOTS.smokeB.x, z: SPOTS.smokeB.z, holdCup: false };
}

function slotFor(agent: AgentView, time: number, index: number): FunSlot {
  // Stress: blocked agents almost always hit the patio
  if (agent.state === "blocked") {
    return smokeSlot(index);
  }
  // Waiting / idle — smoke more often when "stressed" beats land
  if (
    (agent.state === "waiting" || agent.state === "idle") &&
    Math.floor(time / LOOP + index * 2) % 4 === 0
  ) {
    return smokeSlot(index);
  }
  if (agent.state === "done") {
    const celebrate: FunSlot = {
      fun: "celebrate",
      x: DESKS[index]?.x ?? 0,
      z: (DESKS[index]?.z ?? 0) + 1.1,
      holdCup: false,
    };
    if (Math.floor(time / LOOP + index) % 3 === 0) return celebrate;
  }
  if (index % 2 === 1 && Math.floor(time / LOOP) % 2 === 0) {
    return { fun: "foosball", x: SPOTS.foosballB.x, z: SPOTS.foosballB.z, holdCup: false };
  }
  return FUN_ROTATION[(index + Math.floor(time / LOOP)) % FUN_ROTATION.length];
}

/**
 * Working stays at desk. Blocked/idle/waiting can leave for breaks —
 * smokers go to the patio when idle or stressed.
 */
export function targetForAgent(agent: AgentView, desk: Desk, time: number, index: number): PoseTarget {
  const seat: PoseTarget = { x: desk.x, z: desk.z + 0.62, sit: true, faceDesk: true, fun: null, holdCup: false };
  const stand: PoseTarget = { x: desk.x, z: desk.z + 0.85, sit: false, faceDesk: true, fun: null, holdCup: false };

  if (agent.state === "working") return seat;
  if (!canBreak(agent.state)) return stand;

  if (agent.state === "blocked") {
    const cycle = (time + index * 7) % STRESS_LOOP;
    if (cycle >= 10 && cycle <= 24) {
      const slot = smokeSlot(index);
      return {
        x: slot.x,
        z: slot.z,
        sit: false,
        faceDesk: false,
        fun: "smoke",
        holdCup: false,
      };
    }
    return stand;
  }

  const cycle = (time + index * 9) % LOOP;
  const slot = slotFor(agent, time, index);

  /* Longer linger at the activity so walks finish before they turn around. */
  if (cycle >= 22 && cycle <= 44) {
    if (slot.fun === "celebrate") {
      return {
        x: desk.x,
        z: desk.z + 1.0,
        sit: false,
        faceDesk: false,
        fun: "celebrate",
        holdCup: false,
      };
    }
    return {
      x: slot.x,
      z: slot.z,
      sit: Boolean(slot.sit),
      faceDesk: false,
      fun: slot.fun,
      holdCup: slot.holdCup,
    };
  }

  if (cycle > 44 && cycle < 50 && slot.fun === "brew") {
    return { ...stand, holdCup: true, fun: "sip" };
  }

  return stand;
}

/** Fun label matches the pose the character is actually walking to. */
export function currentFun(agent: AgentView, time: number, index: number): FunKind {
  const desk = DESKS.find((d) => d.id === agent.id) ?? DESKS[0];
  return targetForAgent(agent, desk, time, index).fun;
}

const LINES_BY_FUN: Record<Exclude<FunKind, null>, string[]> = {
  brew: ["Medium roast today.", "Need a minute before standup.", "Coffee first, then the board."],
  sip: ["That's better.", "Okay — back in five.", "Warm cup, clear head."],
  water: ["Refill, then deep work.", "Anyone else thirsty?", "Cooler gossip can wait."],
  board: ["Let's map the edge cases.", "If this arrow is the user…", "Simplest path wins."],
  plant: ["Still alive. Good sign.", "Little water, big difference.", "Office needs something green."],
  stretch: ["Shoulders were locked.", "Two minutes, then keyboard.", "Standing helps."],
  snack: ["Just one.", "Protein bar or regret?", "Back to the desk after this."],
  foosball: ["One game.", "Your serve.", "Okay, best of one."],
  read: ["Quiet corner helps.", "One chapter, then tickets.", "Docs before code sometimes."],
  microwave: ["Lunch in ninety seconds.", "Don't burn it this time.", "Timer's set."],
  nap: ["Eyes closed. Five minutes.", "Don't wake me for nits.", "Resetting."],
  phone: ["Can you hear me?", "I'll send the notes after.", "Yes — same thread."],
  plane: ["Don't tell Fatima.", "Ayesha, catch!", "Okay, that was the break."],
  celebrate: ["That zone is done.", "Nice — next ticket.", "Small win. Keep going."],
  smoke: [
    "Air helps.",
    "Two minutes, then back.",
    "This one's stubborn.",
    "Alright — back to it.",
    "Clear head, then debug.",
  ],
};

const LINES_BY_STATE: Record<AgentView["state"], string[]> = {
  working: [
    "Almost have this test green.",
    "Reviewing the edge case…",
    "Typing through the hard part.",
    "Give me a few more minutes.",
  ],
  waiting: [
    "Waiting on the next handoff.",
    "Queue's quiet right now.",
    "Ping me when it's ready.",
    "I'll stay close to the desk.",
  ],
  blocked: [
    "Need a human decision here.",
    "Stuck — can't move without approval.",
    "Escalation's waiting on you.",
  ],
  idle: ["Ready when there's work.", "Floor's calm for now.", "Coffee's still warm."],
  done: ["That zone looks good.", "Green checks — nice.", "Ready for the next slice."],
};

const BANTER: { a: DeskId; b: DeskId; lines: [string, string] }[] = [
  {
    a: "backend",
    b: "frontend",
    lines: ["Ayesha, API shape is settled — okay to wire?", "Ali, send the sample payload and I'll hook it."],
  },
  {
    a: "qa",
    b: "backend",
    lines: ["Ali, can you share repro steps for that 500?", "Sana, pushing a fix branch now — try again in a bit."],
  },
  {
    a: "pm",
    b: "qa",
    lines: ["Sana, is this still in scope for the round?", "Fatima, yes — I'll mark what slips."],
  },
  {
    a: "frontend",
    b: "ai_engineer",
    lines: ["Hassan, can the model draft empty-state copy?", "Ayesha, sure — keep the tone short."],
  },
  {
    a: "ai_engineer",
    b: "pm",
    lines: ["Fatima, we should budget time for evals.", "Hassan, note it — we'll sequence after this zone."],
  },
  {
    a: "qa",
    b: "frontend",
    lines: ["Ayesha, layout breaks under 360px width.", "Sana, thanks — fixing the flex wrap now."],
  },
  {
    a: "backend",
    b: "pm",
    lines: ["Fatima — stepping out for two minutes.", "Ali, go. I'll hold the board."],
  },
];

function pick<T>(items: T[], salt: number): T {
  return items[Math.abs(Math.floor(salt)) % items.length];
}

function lineForAgent(agent: AgentView, fun: FunKind, time: number, index: number): string | undefined {
  // Speak rarely — short bubbles, long silence
  const beat = Math.floor((time + index * 5.1) / DIALOGUE_BEAT);
  const phase = (time + index * 5.1) % DIALOGUE_BEAT;
  if (phase > 3.8) return undefined;
  // Stagger who talks so the floor isn't a chorus
  if ((beat + index) % 3 !== 0 && !fun) return undefined;

  if (beat % 8 === 0) {
    const pair = BANTER[(beat + index) % BANTER.length];
    if (agent.id === pair.a) return pair.lines[0];
    if (agent.id === pair.b) return pair.lines[1];
  }

  if (fun) {
    return pick(LINES_BY_FUN[fun], beat * 13 + index * 7);
  }

  if (agent.state === "working" && agent.taskKey && beat % 2 === 0) {
    return `Working through ${agent.taskKey}.`;
  }
  if (agent.state === "waiting" && agent.taskKey && beat % 2 === 0) {
    return `Still waiting on ${agent.taskKey}.`;
  }
  if (agent.state === "blocked" && agent.taskKey) {
    return `${agent.taskKey} needs a decision.`;
  }
  return pick(LINES_BY_STATE[agent.state], beat * 11 + index * 5);
}

export function withFunOverlay(agents: AgentView[], time: number): AgentView[] {
  return agents.map((agent, index) => {
    const fun = currentFun(agent, time, index);
    let funLabel: string | undefined;
    if (fun === "smoke") {
      funLabel =
        agent.state === "blocked"
          ? "Patio break — blocked"
          : agent.state === "waiting"
            ? "Patio break — waiting"
            : "Patio break";
    } else if (fun) {
      funLabel = FUN_LABELS[fun];
    }
    return {
      ...agent,
      funLabel,
      dialogue: lineForAgent(agent, fun, time, index),
    };
  });
}

const STAFF_DUTY_LABEL: Record<StaffDuty, string> = {
  home: "At station",
  desk_round: "Desk round",
  printer: "Printer run",
  trash: "Clearing bins",
  pantry: "Pantry duty",
  reception: "Front desk",
  meeting: "Meeting table",
  chai: "Tea round",
  water: "Water run",
  files: "Filing",
  snack_restock: "Restocking snacks",
};

const STAFF_LINES: Record<StaffId, string[]> = {
  office_boy: [
    "Chai for the backend desk?",
    "Printer's warm — copies coming.",
    "Bins are clear.",
    "Files are on Fatima's desk.",
    "Anything else you need?",
  ],
  receptionist: [
    "Coders Alley — how can I help?",
    "Visitor signed in.",
    "I'll hold your packages.",
    "Meeting room is free after three.",
    "Welcome — desks are that way.",
  ],
  pantry: [
    "Fresh pot in five minutes.",
    "Snacks are restocked.",
    "Cups are washed.",
    "Sugar's on the left.",
    "Tell them lunch is ready.",
  ],
};

type StaffRoute = { duty: StaffDuty; x: number; z: number; sit?: boolean; holdTray?: boolean; face?: number };

function deskVisit(index: number): StaffRoute {
  const desk = DESKS[index % DESKS.length];
  return {
    duty: "desk_round",
    x: desk.x + 0.55,
    z: desk.z + 0.95,
    holdTray: true,
    face: Math.PI,
  };
}

function routesForStaff(id: StaffId): StaffRoute[] {
  if (id === "office_boy") {
    return [
      { duty: "pantry", x: SPOTS.coffeeMachine.x - 0.35, z: SPOTS.coffeeMachine.z + 0.55, holdTray: true },
      deskVisit(0),
      deskVisit(1),
      { duty: "chai", x: SPOTS.coffeeSip.x, z: SPOTS.coffeeSip.z, holdTray: true },
      deskVisit(2),
      { duty: "printer", x: SPOTS.printer.x, z: SPOTS.printer.z, face: 0 },
      deskVisit(3),
      { duty: "files", x: SPOTS.supply.x, z: SPOTS.supply.z, face: Math.PI / 2 },
      deskVisit(4),
      { duty: "trash", x: SPOTS.trashA.x, z: SPOTS.trashA.z },
      { duty: "meeting", x: 0.2, z: 2.9, holdTray: true },
      { duty: "water", x: SPOTS.waterCooler.x + 0.35, z: SPOTS.waterCooler.z },
      { duty: "home", x: STAFF[0].home.x, z: STAFF[0].home.z },
    ];
  }
  if (id === "receptionist") {
    return [
      {
        duty: "reception",
        x: SPOTS.reception.x,
        z: SPOTS.reception.z,
        sit: true,
        face: Math.PI,
      },
      {
        duty: "reception",
        x: SPOTS.reception.x,
        z: SPOTS.reception.z,
        sit: true,
        face: Math.PI,
      },
      { duty: "meeting", x: 0.5, z: 2.7 },
      {
        duty: "reception",
        x: SPOTS.reception.x,
        z: SPOTS.reception.z,
        sit: true,
        face: Math.PI,
      },
      { duty: "pantry", x: SPOTS.coffeeSip.x + 0.3, z: SPOTS.coffeeSip.z },
      {
        duty: "reception",
        x: SPOTS.reception.x,
        z: SPOTS.reception.z,
        sit: true,
        face: Math.PI,
      },
    ];
  }
  return [
    { duty: "pantry", x: SPOTS.coffeeMachine.x - 0.5, z: SPOTS.coffeeMachine.z + 0.45, face: 0 },
    { duty: "snack_restock", x: SPOTS.snack.x - 0.25, z: SPOTS.snack.z + 0.35 },
    { duty: "pantry", x: SPOTS.microwave.x - 0.35, z: SPOTS.microwave.z + 0.3 },
    { duty: "water", x: SPOTS.waterCooler.x + 0.4, z: SPOTS.waterCooler.z - 0.1 },
    { duty: "home", x: STAFF[2].home.x, z: STAFF[2].home.z, face: 0 },
    { duty: "meeting", x: 0.9, z: 2.85, holdTray: true },
  ];
}

const STAFF_HOLD = 22;

export function targetForStaff(member: StaffMember, time: number, index: number): StaffRoute & { faceDesk: boolean } {
  const routes = routesForStaff(member.id);
  const slot = Math.floor((time + index * 11) / STAFF_HOLD) % routes.length;
  const route = routes[slot];
  return {
    ...route,
    faceDesk: Boolean(route.sit),
  };
}

function staffDialogue(member: StaffMember, duty: StaffDuty, time: number, index: number): string | undefined {
  const beat = Math.floor((time + index * 6.3) / DIALOGUE_BEAT);
  const phase = (time + index * 6.3) % DIALOGUE_BEAT;
  if (phase > 3.5) return undefined;
  if ((beat + index) % 2 !== 0) return undefined;
  if (duty === "chai" || duty === "desk_round") {
    return pick(
      ["Tea?", "Prints for your desk.", "Anything from the pantry?", "Leaving this here."],
      beat * 5 + index,
    );
  }
  return pick(STAFF_LINES[member.id], beat * 9 + index * 3);
}

export function floorStaff(time: number): StaffView[] {
  return STAFF.map((member, index) => {
    const route = targetForStaff(member, time, index);
    return {
      id: member.id,
      label: member.label,
      title: member.title,
      name: member.name,
      gender: member.gender,
      roleTitle: member.roleTitle,
      activity: STAFF_DUTY_LABEL[route.duty],
      duty: route.duty,
      dutyLabel: STAFF_DUTY_LABEL[route.duty],
      skin: member.skin,
      hair: member.hair,
      shirt: member.shirt,
      pants: member.pants,
      blazer: member.blazer,
      shoe: member.shoe,
      holdTray: Boolean(route.holdTray),
      dialogue: staffDialogue(member, route.duty, time, index),
    };
  });
}

/** Rolling chat feed for the side panel. */
export function chatFeed(agents: AgentView[], time: number): ChatLine[] {
  const lines: ChatLine[] = [];
  const windowStart = Math.max(0, Math.floor(time / DIALOGUE_BEAT) - 4);
  for (let beat = windowStart; beat <= Math.floor(time / DIALOGUE_BEAT); beat++) {
    for (const [index, agent] of agents.entries()) {
      const t = beat * DIALOGUE_BEAT + 0.8;
      const fun = currentFun(agent, t, index);
      const text = lineForAgent(agent, fun, t, index);
      if (!text) continue;
      const phase = (t + index * 5.1) % DIALOGUE_BEAT;
      if (phase > 3.8) continue;
      lines.push({
        id: `${beat}-${agent.id}`,
        from: `${agent.title} ${agent.name.split(" ")[0]}`,
        text,
        at: t,
      });
    }
    for (const [index, member] of STAFF.entries()) {
      const t = beat * DIALOGUE_BEAT + 1.2;
      const view = floorStaff(t)[index];
      if (!view?.dialogue) continue;
      lines.push({
        id: `${beat}-${member.id}`,
        from: `${member.title} ${member.name.split(" ")[0]}`,
        text: view.dialogue,
        at: t,
      });
    }
  }
  return lines.sort((a, b) => a.at - b.at).slice(-10);
}
