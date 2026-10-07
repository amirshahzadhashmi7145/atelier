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
  foosball: { x: 1.2, z: 3.6 },
  foosballB: { x: 2.0, z: 3.6 },
  reading: { x: -5.8, z: -1.2 },
  microwave: { x: 6.2, z: 1.4 },
  beanbag: { x: -4.2, z: 2.4 },
  phone: { x: -0.6, z: -0.8 },
  pet: { x: 0, z: 1.2 },
  /** Outdoor patio — smokers hang here. */
  smoke: { x: 6.4, z: -4.2 },
  smokeB: { x: 5.6, z: -4.6 },
} as const;

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
  | "pet"
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
  brew: "Brewing a pour-over",
  sip: "Sipping coffee",
  water: "Refilling water",
  board: "Doodling on the whiteboard",
  plant: "Watering the office plant",
  stretch: "Stretch break",
  snack: "Raid the snack shelf",
  foosball: "Foosball sudden-death",
  read: "Reading on the bean-side nook",
  microwave: "Reheating leftovers",
  nap: "Power nap on the beanbag",
  phone: "Taking a quick call",
  pet: "Scratching the office dog",
  plane: "Launching a paper plane",
  celebrate: "Victory lap — task zone done",
  smoke: "Stress smoke on the patio",
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
    activity: "Select a live project — meanwhile, Coders Alley break-room mode",
  }));
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
  { fun: "pet", x: SPOTS.pet.x, z: SPOTS.pet.z, holdCup: false },
  { fun: "plane", x: SPOTS.stretch.x + 0.8, z: SPOTS.stretch.z - 0.4, holdCup: false },
  { fun: "smoke", x: SPOTS.smoke.x, z: SPOTS.smoke.z, holdCup: false },
];

const LOOP = 36;
const STRESS_LOOP = 22;

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

export function currentFun(agent: AgentView, time: number, index: number): FunKind {
  if (!canBreak(agent.state)) return null;
  if (agent.state === "blocked") {
    const cycle = (time + index * 7) % STRESS_LOOP;
    if (cycle < 8 || cycle > 18) return null;
    return "smoke";
  }
  const cycle = (time + index * 9) % LOOP;
  if (cycle < 20 || cycle > 30) return null;
  return slotFor(agent, time, index).fun;
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
    if (cycle >= 8 && cycle <= 18) {
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

  if (cycle >= 20 && cycle <= 30) {
    if (slot.fun === "celebrate") {
      return {
        x: desk.x + Math.sin(time * 3 + index) * 0.35,
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

  if (cycle > 30 && cycle < 33 && slot.fun === "brew") {
    return { ...stand, holdCup: true, fun: "sip" };
  }

  return stand;
}

const LINES_BY_FUN: Record<Exclude<FunKind, null>, string[]> = {
  brew: ["Oat milk or chaos?", "This shot looks… philosophical.", "Barista mode: engaged."],
  sip: ["Ahh. Deploy fuel.", "Hot. Like prod on Fridays.", "Don't tell PM this is my third."],
  water: ["Hydrate or hallucinate.", "Is this filtered? Asking for my tokens.", "Water cooler lore incoming."],
  board: ["What if we… boxed the arrow?", "This diagram has vibes.", "Future us will thank present us. Maybe."],
  plant: ["You're doing great, plant.", "Photosynthesis > standups.", "Grow, little green teammate."],
  stretch: ["Touching toes is a stretch goal.", "Spine says thanks.", "Yoga for YAML."],
  snack: ["Is this free? It's on the shelf.", "Sugar for the sprint.", "I regret nothing. Yet."],
  foosball: ["GOAL— wait, own goal.", "Rod warriors!", "Best of one. Sudden death."],
  read: ["Chapter 3: rediscovering focus.", "Plot twist: the bug was docs.", "Shh. Deep work cosplay."],
  microwave: ["90 seconds of suspense.", "Leftover lasagna diplomacy.", "Beep means destiny."],
  nap: ["Five minutes. Tops.", "Dreaming of green builds.", "Do not disturb / do not merge."],
  phone: ["No I can't hop on a quick call— oh wait.", "You're breaking up. Conveniently.", "Circle back? Let's square it."],
  pet: ["Who's a good merge conflict resolver?", "Soft ears > hard deadlines.", "Dog approved this PR."],
  plane: ["Aerodynamics of procrastination.", "Flying toward main.", "Catch it, Frontend!"],
  celebrate: ["Ship it energy!", "We did a thing!", "Confetti in my heart."],
  smoke: [
    "Patio. Nicotine. Perspective.",
    "This bug owes me a cigarette.",
    "Don't tell compliance.",
    "One drag, then back to the graph.",
    "Stress deploy ritual.",
  ],
};

const LINES_BY_STATE: Record<AgentView["state"], string[]> = {
  working: [
    "One more failing test…",
    "Typing goes brr.",
    "Don't look at the diff yet.",
    "In the zone. Barely.",
  ],
  waiting: [
    "Any day now…",
    "Queue anxiety is real.",
    "I'll just… hover.",
    "Ping me when Run next is brave.",
  ],
  blocked: [
    "Help. Politely screaming.",
    "Blocked harder than a firewall.",
    "Human, we need you.",
  ],
  idle: ["Idle hands, curious brain.", "Waiting for the plot.", "Ambient productivity."],
  done: ["Zone clear. Ego inflated.", "I could get used to green.", "Victory nap loading…"],
};

const BANTER: { a: DeskId; b: DeskId; lines: [string, string] }[] = [
  {
    a: "backend",
    b: "frontend",
    lines: ["Ayesha, API contract is frozen… right?", "Ali bhai, frozen like my CSS. Sure."],
  },
  {
    a: "qa",
    b: "backend",
    lines: ["Ali, can you repro with steps?", "Sana, it works on my branch."],
  },
  {
    a: "pm",
    b: "qa",
    lines: ["Sana, scope is tiny, I swear.", "Fatima ji, that's what you said last round."],
  },
  {
    a: "frontend",
    b: "ai_engineer",
    lines: ["Hassan, can the model write button copy?", "Ayesha, only if you accept weird commas."],
  },
  {
    a: "ai_engineer",
    b: "pm",
    lines: ["Fatima ji, we might need evals.", "Hassan, add it to the backlog of feelings."],
  },
  {
    a: "qa",
    b: "frontend",
    lines: ["Ayesha, Mobile Safari says hi.", "Sana, I fear that sentence."],
  },
  {
    a: "backend",
    b: "pm",
    lines: ["Fatima ji — patio. Coming?", "Ali, bring two. The graph is spicy."],
  },
];

function pick<T>(items: T[], salt: number): T {
  return items[Math.abs(Math.floor(salt)) % items.length];
}

function lineForAgent(agent: AgentView, fun: FunKind, time: number, index: number): string | undefined {
  // Speak in short windows so bubbles feel conversational, not permanent
  const beat = Math.floor((time + index * 3.7) / 4.5);
  const phase = (time + index * 3.7) % 4.5;
  if (phase > 3.2) return undefined; // pause between lines

  // Banter takes priority every few beats
  if (beat % 5 === 0) {
    const pair = BANTER[(beat + index) % BANTER.length];
    if (agent.id === pair.a) return pair.lines[0];
    if (agent.id === pair.b) return pair.lines[1];
  }

  if (fun) {
    return pick(LINES_BY_FUN[fun], beat * 13 + index * 7);
  }

  const taskBit = agent.taskKey ? ` (${agent.taskKey})` : "";
  const base = pick(LINES_BY_STATE[agent.state], beat * 11 + index * 5);
  if (agent.state === "working" && agent.taskKey && beat % 2 === 0) {
    return `${agent.taskKey}: almost elegant.`;
  }
  if (agent.state === "waiting" && agent.taskKey && beat % 2 === 0) {
    return `Still waiting on ${agent.taskKey}…`;
  }
  return base + (beat % 3 === 0 ? taskBit : "");
}

export function withFunOverlay(agents: AgentView[], time: number): AgentView[] {
  return agents.map((agent, index) => {
    const fun = currentFun(agent, time, index);
    let funLabel: string | undefined;
    if (fun === "smoke") {
      funLabel =
        agent.state === "blocked"
          ? "Stress smoke on the patio"
          : agent.state === "waiting"
            ? "Waiting-smoke on the patio"
            : "Idle smoke on the patio";
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

/** Rolling chat feed for the side panel. */
export function chatFeed(agents: AgentView[], time: number): ChatLine[] {
  const lines: ChatLine[] = [];
  const windowStart = Math.max(0, Math.floor(time / 4.5) - 5);
  for (let beat = windowStart; beat <= Math.floor(time / 4.5); beat++) {
    for (const [index, agent] of agents.entries()) {
      const t = beat * 4.5 + 0.5;
      const fun = currentFun(agent, t, index);
      const text = lineForAgent(agent, fun, t, index);
      if (!text) continue;
      // Only keep speakers who actually talk this beat
      const phase = (t + index * 3.7) % 4.5;
      if (phase > 3.2) continue;
      lines.push({
        id: `${beat}-${agent.id}`,
        from: `${agent.title} ${agent.name.split(" ")[0]}`,
        text,
        at: t,
      });
    }
  }
  // Prefer banter pairs + latest
  return lines.slice(-8);
}
