export type Criterion = { id: string; key: string; statement: string };

export type Requirement = {
  id: string;
  key: string;
  kind: "functional" | "non_functional" | "constraint";
  title: string;
  statement: string;
  criteria: Criterion[];
};

export type Clarification = {
  id: string;
  round_number: number;
  question: string;
  resolves: string;
  answer: string | null;
  status: string;
};

export type Task = {
  id: string;
  key: string;
  title: string;
  description: string;
  zone: string;
  state: string;
  size: string;
  requirement_keys: string[];
  depends_on: string[];
  retry_count: number;
  max_retries: number;
  branch_name: string | null;
};

export type Snapshot = {
  project: {
    id: string;
    name: string;
    description: string;
    tech_preferences: string | null;
    interpretation: string | null;
    stage: string;
    clarification_round: number;
    max_questions: number;
    max_rounds: number;
    architecture_summary: string | null;
    test_strategy: Record<string, string> | null;
    created_at: string;
    next_actions: string[];
    uncovered_requirement_keys: string[];
  };
  clarifications: Clarification[];
  assumptions: { id: string; statement: string }[];
  stories: { id: string; statement: string }[];
  requirements: Requirement[];
  decisions: {
    id: string;
    title: string;
    context: string;
    options: string[];
    decision: string;
    consequences: string;
  }[];
  ownership: { id: string; glob: string; zone: string }[];
  tasks: Task[];
  gates: { id: string; gate: string; decision: string; note: string | null; created_at: string }[];
  events: {
    id: string;
    type: string;
    actor_kind: string;
    actor_role: string | null;
    payload: Record<string, unknown>;
    input_tokens: number;
    output_tokens: number;
    occurred_at: string;
  }[];
  runs: {
    id: string;
    role: string;
    purpose: string;
    provider: string;
    model: string;
    input_tokens: number;
    output_tokens: number;
  }[];
};

export type ProjectListItem = {
  id: string;
  name: string;
  stage: string;
  created_at: string;
};
